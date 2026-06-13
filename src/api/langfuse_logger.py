"""Langfuse logger wrapper for the API Layer.

Initializes a singleton Langfuse client with retry logic.
Falls back to DummyTrace which prints to stdout when Langfuse is unavailable.
Thread-safe initialization with automatic reconnection.
"""

import json
import logging
import os
import threading
from typing import Any

logger = logging.getLogger("api.langfuse")


def md_block(data: Any, *, title: str | None = None) -> str:
    """Render a value as Markdown for nicer Langfuse UI rendering.

    Langfuse v2 рендерит строковые input/output как markdown, dict-ы
    показывает сырым JSON-tree. Это helper, чтобы spans читались
    глазами без раскрывания JSON-узлов.
    """
    parts: list[str] = []
    if title:
        parts.append(f"### {title}")
        parts.append("")

    if isinstance(data, str):
        parts.append(data if data else "_(empty)_")
        return "\n".join(parts)

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, bool):
                rendered = "✅ true" if value else "❌ false"
            elif isinstance(value, (int, float)) or value is None:
                rendered = f"`{value}`"
            elif isinstance(value, str):
                if "\n" in value or len(value) > 80:
                    rendered = f"\n```\n{value}\n```"
                else:
                    rendered = value
            else:
                rendered = "\n```json\n" + json.dumps(value, indent=2, ensure_ascii=False) + "\n```"
            parts.append(f"- **{key}**: {rendered}")
        return "\n".join(parts)

    return "```json\n" + json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n```"

_langfuse_client = None
_langfuse_lock = threading.Lock()
_MAX_INIT_RETRIES = 3
_init_failure_count = 0


class DummyTrace:
    """Fallback trace: logs to stdout so demo always shows activity.

    Carries an `id` for parity with the real Langfuse trace, so callers
    can plumb a trace_id through to the API response without branching.
    The id is a UUID4 so it's still unique per request — handy when
    grepping the stdout logs.
    """

    def __init__(self, trace_id: str | None = None):
        import uuid
        self.id = trace_id or f"dummy-{uuid.uuid4().hex[:12]}"

    def span(self, name: str = "", **kwargs):
        logger.info("[TRACE SPAN id=%s] %s | %s", self.id, name, kwargs)
        return self

    def update(self, **kwargs):
        logger.info("[TRACE UPDATE id=%s] %s", self.id, kwargs)
        return self

    def end(self, **kwargs):
        logger.debug("[TRACE END id=%s] %s", self.id, kwargs)
        return self


def trace_id(trace) -> str | None:
    """Best-effort extraction of a trace id (real Langfuse or DummyTrace).

    Real Langfuse v2 traces expose `.id`; DummyTrace mirrors the API.
    Returns None for anything else so callers don't have to guard."""
    return getattr(trace, "id", None)


def get_langfuse():
    """Return singleton Langfuse client, or None.

    Thread-safe. Retries initialization up to _MAX_INIT_RETRIES times
    so that a slow Langfuse startup doesn't permanently disable tracing.
    """
    global _langfuse_client, _init_failure_count

    if _langfuse_client is not None:
        return _langfuse_client

    with _langfuse_lock:
        # Double-check after acquiring lock
        if _langfuse_client is not None:
            return _langfuse_client

        if _init_failure_count >= _MAX_INIT_RETRIES:
            return None

        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST")

        if not all([public_key, secret_key, host]):
            logger.warning(
                "Langfuse env vars not set (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST). "
                "Tracing disabled — logging to stdout only."
            )
            _init_failure_count = _MAX_INIT_RETRIES
            return None

        try:
            from langfuse import Langfuse

            _langfuse_client = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                host=host,
            )
            logger.info("Langfuse client initialized (host=%s)", host)
            return _langfuse_client
        except Exception as exc:
            _init_failure_count += 1
            remaining = _MAX_INIT_RETRIES - _init_failure_count
            logger.warning(
                "Failed to initialize Langfuse (attempt %d/%d): %s. %s",
                _init_failure_count,
                _MAX_INIT_RETRIES,
                exc,
                f"{remaining} retries left." if remaining > 0 else "Tracing disabled.",
            )
            return None


def create_trace(name: str, **kwargs):
    """Create a Langfuse trace, or DummyTrace if unavailable.

    Returns an object with .span() and .update() methods in both cases.
    """
    client = get_langfuse()
    if client is None:
        logger.info("[TRACE] %s | %s", name, kwargs)
        return DummyTrace()

    try:
        return client.trace(name=name, **kwargs)
    except Exception as exc:
        logger.warning("Langfuse trace creation failed: %s", exc)
        return DummyTrace()


def flush():
    """Flush pending Langfuse events."""
    client = get_langfuse()
    if client is not None:
        try:
            client.flush()
        except Exception as exc:
            logger.warning("Langfuse flush failed: %s", exc)
