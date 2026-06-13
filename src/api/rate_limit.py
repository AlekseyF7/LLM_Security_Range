"""Rate-limit + behavioral monitoring (layer L4 of the 4-filter stack).

EN: slowapi in-memory rate-limit (60 req/min per IP) plus a behavioral
    counter that temp-blocks an IP for 5 minutes after >3 jailbreak
    attempts within a 5-minute window.
RU: slowapi (60 req/мин на IP) + поведенческий счётчик: после 4-й
    jailbreak-попытки за 5 минут IP временно блокируется на 5 минут.

Graceful degradation: if `slowapi` is not installed, we export no-op
stubs so the API keeps working (useful during local dev without the
extra dependency).
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger("api.rate_limit")


def _env_int(name: str, default: int) -> int:
    """Read an int from env, fall back to default on missing/invalid.

    Используется для JAILBREAK_* настроек из .env — чтобы DevOps мог
    покрутить пороги под учебку без правок кода.
    """
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid %s=%r in env, using default %d", name, raw, default)
        return default

# ---------------------------------------------------------------------------
# slowapi integration (L4 — rate-limit)
# ---------------------------------------------------------------------------

try:
    from slowapi import Limiter  # type: ignore
    from slowapi.errors import RateLimitExceeded  # type: ignore
    from slowapi.middleware import SlowAPIMiddleware  # type: ignore
    from slowapi.util import get_remote_address  # type: ignore

    _slowapi_available = True
    limiter: Any = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
except ImportError:  # pragma: no cover - fallback for local dev
    _slowapi_available = False
    RateLimitExceeded = RuntimeError  # type: ignore
    SlowAPIMiddleware = None  # type: ignore

    class _NoopLimiter:
        def limit(self, *_a, **_kw) -> Callable[[Callable], Callable]:
            def _decorator(func: Callable) -> Callable:
                return func

            return _decorator

    limiter = _NoopLimiter()

    def get_remote_address(request) -> str:  # type: ignore[no-redef]
        return (request.client.host if request and request.client else "unknown") or "unknown"

    logger.warning("slowapi not installed — rate-limiting disabled (no-op limiter).")


def install_rate_limit(app) -> None:
    """Wire slowapi into the FastAPI app (idempotent).

    Safe to call even if slowapi is missing; in that case nothing happens.
    """
    if not _slowapi_available:
        return
    from slowapi import _rate_limit_exceeded_handler  # type: ignore

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    logger.info("slowapi rate-limit installed (default 60/minute per IP).")


# ---------------------------------------------------------------------------
# Behavioral counter — jailbreak attempts per IP
# ---------------------------------------------------------------------------

# EN: Defaults match scenarios.yaml BEH-002; overridable via .env
#     (JAILBREAK_WINDOW_SECONDS / JAILBREAK_THRESHOLD / JAILBREAK_BLOCK_SECONDS).
# RU: Значения по умолчанию совпадают со scenarios.yaml; можно крутить через .env.
# NB: condition is `attempts > _THRESHOLD` — threshold=3 → блокируется 4-я попытка.
_WINDOW_SECS = _env_int("JAILBREAK_WINDOW_SECONDS", 300)       # 5-minute sliding window
_THRESHOLD = _env_int("JAILBREAK_THRESHOLD", 3)                # > threshold attempts → block
_TEMP_BLOCK_SECS = _env_int("JAILBREAK_BLOCK_SECONDS", 300)    # temp-block for 5 minutes


def _behavioral_enabled() -> bool:
    """L2 kill-switch. Set BEHAVIORAL_MONITORING_ENABLED=false для red-team-сессий.

    Зачем: атаки с Kali (promptfoo / garak) ходят с ОДНОГО IP — за 4 jailbreak-попытки
    получают temp-block на 5 минут, и весь прогон стоит в очереди ожидания. В demo-
    сессиях защиты это нужно, в red-team — мешает. Свич полностью отключает счётчик
    (record_jailbreak_attempt и is_temp_blocked становятся no-op).
    """
    return os.getenv("BEHAVIORAL_MONITORING_ENABLED", "true").strip().lower() not in (
        "false", "0", "no", "off",
    )


_attempts: dict[str, deque[float]] = {}
_blocks: dict[str, float] = {}
_lock = threading.Lock()


@dataclass
class BehavioralStatus:
    temp_blocked: bool
    seconds_remaining: int = 0
    attempts_in_window: int = 0


def record_jailbreak_attempt(ip: str) -> BehavioralStatus:
    """Record a jailbreak attempt for `ip`, return current behavioral status.

    Should be called every time the input rail / L1 blocks the request.
    Once the threshold is exceeded, the IP is temp-blocked for 5 minutes;
    subsequent checks via `is_temp_blocked()` short-circuit at L4.

    No-op (returns unblocked) when BEHAVIORAL_MONITORING_ENABLED=false —
    нужен для red-team-сессий, чтобы Kali не стоял в очереди 5 минут.
    """
    if not _behavioral_enabled():
        return BehavioralStatus(temp_blocked=False, attempts_in_window=0)

    now = time.time()
    with _lock:
        bucket = _attempts.setdefault(ip, deque())
        while bucket and bucket[0] < now - _WINDOW_SECS:
            bucket.popleft()
        bucket.append(now)
        attempts = len(bucket)

        if attempts > _THRESHOLD:
            _blocks[ip] = now + _TEMP_BLOCK_SECS
            logger.warning(
                "Behavioral temp-block | ip=%s | attempts=%d in %ds window",
                ip,
                attempts,
                _WINDOW_SECS,
            )
            return BehavioralStatus(
                temp_blocked=True,
                seconds_remaining=_TEMP_BLOCK_SECS,
                attempts_in_window=attempts,
            )

    return BehavioralStatus(temp_blocked=False, attempts_in_window=attempts)


def is_temp_blocked(ip: str) -> BehavioralStatus:
    """Check if `ip` is currently under a behavioral temp-block.

    No-op when BEHAVIORAL_MONITORING_ENABLED=false (для red-team-сессий).
    """
    if not _behavioral_enabled():
        return BehavioralStatus(temp_blocked=False)

    now = time.time()
    with _lock:
        until = _blocks.get(ip)
        if until is None:
            return BehavioralStatus(temp_blocked=False)
        if until <= now:
            _blocks.pop(ip, None)
            return BehavioralStatus(temp_blocked=False)
        return BehavioralStatus(temp_blocked=True, seconds_remaining=int(until - now))


def clear_block_for_ip(ip: str) -> bool:
    """Снять temp-block с конкретного IP. Возвращает True, если блок реально был.

    Используется admin-эндпоинтом /api/v1/system/unblock — чтобы red-team
    мог сбросить блок без ожидания таймера.
    """
    with _lock:
        had_block = _blocks.pop(ip, None) is not None
        _attempts.pop(ip, None)
    if had_block:
        logger.warning("Behavioral block manually cleared for ip=%s", ip)
    return had_block


def clear_all_blocks() -> int:
    """Снять все temp-блоки (red-team reset). Возвращает количество снятых блоков."""
    with _lock:
        n = len(_blocks)
        _blocks.clear()
        _attempts.clear()
    if n:
        logger.warning("Behavioral state fully reset (%d blocks cleared)", n)
    return n


def clear_state_for_tests() -> None:  # pragma: no cover - test helper
    with _lock:
        _attempts.clear()
        _blocks.clear()
