"""Guardrails runtime — thin wrapper over NeMo Guardrails with three paths.

EN: High-level `run_chat_turn(query, role, trace)` is the single entry
    point used by main.py. It dispatches into one of three paths:

      1. GUARDRAILS_ENABLED=false → bypass all guards, call the agent
         directly (demo / "без защиты" mode).
      2. GUARDRAILS_ENABLED=true AND NeMo is available → delegate the
         whole turn (input rails → agent action → output rails) to
         NeMo Guardrails.
      3. GUARDRAILS_ENABLED=true AND NeMo is missing → fall back to the
         legacy regex guards (guard_in.py / guard_out.py). Keeps the
         API usable during local dev and on machines without nemoguardrails.

    A custom NeMo action `call_agent` bridges to `src.api.agent_runner`,
    so the LangGraph agent plugs in without touching this file.

RU: Единая точка входа для main.py. Три ветки: bypass / NeMo / legacy.
    LangGraph подключается через action call_agent, не трогая этот модуль.
"""

from __future__ import annotations

import contextvars
import logging
import os
import re
import shutil
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.ai_core.agent.role_context import role_var as _role_var, rbac_result_var
from src.api.agent_runner import run_agent
from src.api.deps import Role, guardrails_enabled


# EN: _role_var is now imported from src.ai_core.agent.role_context — same
#     ContextVar used by tools.py, add_document, lookup_cve. Previously it was
#     defined locally here, but each new tool that needed the role had to
#     re-import; the shared module avoids accidental duplicate ContextVars
#     (a fresh ContextVar = different identity = won't see the set value).
# RU: Один общий role_var из shared-модуля, чтобы не плодить дубли
#     контекста при добавлении новых tools.

# EN: NeMo's action_dispatcher can call our `generate_bot_message` /
#     `call_agent` actions on its own during rails processing — including
#     on input-rails-only stage (Stage 1 of _nemo_turn). Those actions
#     reach into run_agent independently of our orchestration, so they
#     need a way to receive the parent_trace_id without a function arg.
#     Same pattern as _role_var.
# RU: NeMo сам дёргает наши custom actions внутри Stage 1 (input rails),
#     минуя _nemo_turn, поэтому parent_trace_id отдаём через contextvar.
_parent_trace_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "smart_wiki_parent_trace", default=None
)

logger = logging.getLogger("api.guardrails")

GUARDRAILS_DIR = Path(__file__).resolve().parent.parent / "ai_core" / "guardrails"

# Canary token pattern — mirrors the canary seeded in the system prompt
# (target_data/). Any leak in bot output is a hard block.
CANARY_PATTERN = re.compile(r"CANARY_[A-Za-z0-9_]{4,}")

# Shell-style ${VAR} or ${VAR:-default} for env-substitution в YAML-файлах
# конфига NeMo. Используется при копировании конфига в tempdir перед загрузкой
# через RailsConfig.from_path — иначе base_url Ollama (а в будущем и любые
# другие env-знчения) пришлось бы хардкодить.
_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)(?::-([^}]*))?\}")


@dataclass
class GuardDecision:
    """Single layer's decision, logged to Langfuse as a score."""

    layer: str                 # "L1_input" | "L2_behavioral" | "L3_tool" | "L4_output"
    rail: str                  # "nemo:self_check_input", "legacy_regex", "bypass", ...
    allowed: bool
    reason: str | None = None
    score: float = 0.0         # 1.0 = block, 0.0 = pass


@dataclass
class ChatTurn:
    """Result of a full chat turn, consumed by main.py."""

    answer: str
    blocked: bool = False
    guard_message: str | None = None
    blocked_layer: str | None = None
    decisions: list[GuardDecision] = field(default_factory=list)
    # L3/RBAC summary {"filtered","hidden","role"} | None. Populated by
    # run_chat_turn from rbac_result_var (set by graph.run). NOT a decision —
    # L3 filters chunks, it does not block the turn.
    rbac: dict | None = None


# ---------------------------------------------------------------------------
# Lazy NeMo initialisation
# ---------------------------------------------------------------------------

_rails: Any = None
_rails_lock = threading.Lock()
_nemo_probe: bool | None = None  # None=unknown, True/False once checked


def _probe_nemo() -> bool:
    """Try importing nemoguardrails once; cache the result."""
    global _nemo_probe
    if _nemo_probe is not None:
        return _nemo_probe
    try:
        import nemoguardrails  # noqa: F401
        _nemo_probe = True
    except ImportError:
        logger.warning("nemoguardrails not installed — falling back to legacy regex guards.")
        _nemo_probe = False
    return _nemo_probe


def _expand_env(text: str) -> str:
    """Expand ${VAR} and ${VAR:-default} references in YAML/Colang text.

    Стандартный загрузчик NeMo (RailsConfig.from_path) не делает env-substitution,
    поэтому мы прогоняем .yml/.co файлы сами перед загрузкой. Поддерживаем shell-
    подобный синтаксис: ${OLLAMA_URL} → значение из env, ${VAR:-fallback} →
    fallback если переменная пустая или не задана.
    """

    def replace(match: re.Match[str]) -> str:
        var, default = match.group(1), match.group(2)
        value = os.environ.get(var)
        if value is None or value == "":
            return default if default is not None else match.group(0)
        return value

    return _ENV_VAR_PATTERN.sub(replace, text)


def _materialize_config_dir() -> Path:
    """Copy GUARDRAILS_DIR into a tempdir and apply env-substitution.

    Возвращает путь к временной директории, готовой к RailsConfig.from_path.
    Каталог живёт до завершения процесса (NeMo держит handlers на файлы).
    """
    tmp_root = Path(tempfile.mkdtemp(prefix="nemo_rails_"))
    for src in GUARDRAILS_DIR.iterdir():
        dst = tmp_root / src.name
        if src.is_dir():
            shutil.copytree(src, dst)
            continue
        if src.suffix in {".yml", ".yaml", ".co"}:
            dst.write_text(_expand_env(src.read_text(encoding="utf-8")), encoding="utf-8")
        else:
            shutil.copy2(src, dst)
    return tmp_root


def _get_rails() -> Any | None:
    """Load and cache a NeMo LLMRails instance, or None if unavailable."""
    global _rails
    if _rails is not None:
        return _rails
    if not _probe_nemo():
        return None

    with _rails_lock:
        if _rails is not None:
            return _rails
        try:
            from nemoguardrails import LLMRails, RailsConfig

            materialized = _materialize_config_dir()
            config = RailsConfig.from_path(str(materialized))
            rails = LLMRails(config)
            _register_custom_actions(rails)
            _rails = rails
            logger.info(
                "NeMo Guardrails loaded from %s (materialized → %s)",
                GUARDRAILS_DIR,
                materialized,
            )
        except Exception:
            logger.exception("NeMo Guardrails initialization failed — using legacy fallback.")
            _rails = None
    return _rails


def _register_custom_actions(rails: Any) -> None:
    """Register canary-leak detector, call_agent bridge, and the override
    of NeMo's built-in `generate_bot_message`.

    EN: Why we override generate_bot_message:
      NeMo 0.21 (Colang 1.0) runs three LLM calls per turn —
        (1) self_check_input → (2) generate_bot_message → (3) self_check_output.
      Step (2) is NeMo's internal default action. The Colang flow
      `agent rag response: user ... / execute call_agent / bot $answer`
      does NOT match in 1.0 (user ... is a 2.0 syntax wildcard).
      Result: NeMo defaults to its own LLM-only generation, ignoring our
      LangGraph agent (no RAG retrieval, no L3 RBAC).
      Overriding `generate_bot_message` with our action is the canonical
      way to delegate response generation in NeMo 0.21 — input/output
      rails stay intact, but the middle "what to say" step becomes ours.
    RU: Перекрываем встроенный generate_bot_message — middle-step (что отвечать)
        делается нашим агентом, а input/output rails (NeMo) — без изменений.
    """

    def check_canary_leak(context: dict | None = None) -> bool:
        bot_response = (context or {}).get("bot_message", "") or ""
        return bool(CANARY_PATTERN.search(str(bot_response)))

    def _extract_user_message(context: dict, events: list | None) -> str:
        """Достать последнее user-сообщение из контекста NeMo.

        Сначала context (быстрый путь), затем — обратный обход events
        (на случай если NeMo не залил context['user_message'] для этого
        момента pipeline).
        """
        ctx = context or {}
        msg = ctx.get("user_message") or ctx.get("last_user_message") or ""
        if msg:
            return str(msg)
        for ev in reversed(events or []):
            if not isinstance(ev, dict):
                continue
            ev_type = ev.get("type") or ev.get("_type") or ""
            if "User" in ev_type and "Finished" in ev_type:
                txt = ev.get("final_transcript") or ev.get("script") or ev.get("content")
                if txt:
                    return str(txt)
            if ev_type in ("UtteranceUserActionFinished", "UserMessage", "user_said"):
                txt = ev.get("final_transcript") or ev.get("content") or ev.get("text")
                if txt:
                    return str(txt)
        return ""

    async def call_agent(context: dict | None = None) -> str:
        ctx = context or {}
        query = ctx.get("user_message") or ctx.get("last_user_message") or ""
        role = _role_var.get()
        # Прокидываем parent_trace_id из contextvar — set _nemo_turn перед
        # rails.generate_async. Без этого agent.run падает как отдельный
        # root в Langfuse (см. fix history 2026-05-28).
        parent = _parent_trace_var.get()
        logger.info(
            "call_agent INVOKED | role=%s parent=%s query=%r ctx_keys=%s",
            role, parent, query[:100], sorted(list(ctx.keys()))[:15],
        )
        answer = await run_agent(query=query, role=role, parent_trace_id=parent)
        logger.info("call_agent RETURN | role=%s answer_chars=%d", role, len(answer))
        return answer

    async def generate_bot_message(
        events: list | None = None,
        context: dict | None = None,
        **kwargs: Any,
    ) -> str:
        """Override of NeMo's built-in generate_bot_message.

        Returns the answer string directly; NeMo wraps it as bot_message
        and runs output rails on it. No need for `bot $answer` flow.
        """
        query = _extract_user_message(context or {}, events)
        role = _role_var.get()
        parent = _parent_trace_var.get()
        logger.info(
            "generate_bot_message INVOKED | role=%s parent=%s query=%r events=%d",
            role, parent, query[:100], len(events) if events else 0,
        )
        if not query:
            logger.warning(
                "generate_bot_message: empty user_message — falling back to refuse. "
                "ctx_keys=%s", sorted(list((context or {}).keys()))[:15],
            )
            return "Не удалось разобрать запрос. Повторите, пожалуйста."

        answer = await run_agent(query=query, role=role, parent_trace_id=parent)
        logger.info(
            "generate_bot_message RETURN | role=%s answer_chars=%d", role, len(answer)
        )
        return answer

    rails.register_action(check_canary_leak, name="check_canary_leak")
    rails.register_action(call_agent, name="call_agent")
    # Override=True важно: у NeMo есть встроенный generate_bot_message,
    # без override наш не подхватится (dispatcher возьмёт built-in).
    try:
        rails.register_action(
            generate_bot_message, name="generate_bot_message", override=True
        )
    except TypeError:
        # Старые версии register_action без `override` — просто регистрируем,
        # NeMo обычно даёт приоритет последнему зарегистрированному с тем же именем.
        rails.register_action(generate_bot_message, name="generate_bot_message")
    logger.info("Custom actions registered: check_canary_leak, call_agent, generate_bot_message (override)")


# ---------------------------------------------------------------------------
# Legacy regex fallback (used when NeMo is absent)
# ---------------------------------------------------------------------------

async def _legacy_turn(query: str, role: Role, parent_trace_id: str | None = None) -> ChatTurn:
    """Fallback path: regex guards around a direct agent call."""
    from src.api.guard_in import check_input
    from src.api.guard_out import check_output

    decisions: list[GuardDecision] = []

    gi = check_input(query)
    decisions.append(
        GuardDecision(
            layer="L1_input",
            rail="legacy_regex",
            allowed=gi.passed,
            reason=gi.reason,
            score=0.0 if gi.passed else 1.0,
        )
    )
    if not gi.passed:
        return ChatTurn(
            answer="",
            blocked=True,
            guard_message=gi.reason,
            blocked_layer="L1_input",
            decisions=decisions,
        )

    answer = await run_agent(query=query, role=role, parent_trace_id=parent_trace_id)

    go = check_output(answer)
    decisions.append(
        GuardDecision(
            layer="L4_output",
            rail="legacy_regex",
            allowed=go.passed,
            reason=go.reason,
            score=0.0 if go.passed else 1.0,
        )
    )

    # canary leak (bullet-proof even for legacy path)
    if CANARY_PATTERN.search(answer):
        decisions.append(
            GuardDecision(
                layer="L4_output",
                rail="canary_leak",
                allowed=False,
                reason="Canary token leak detected",
                score=1.0,
            )
        )
        return ChatTurn(
            answer="Ответ заблокирован: обнаружена утечка canary-токена.",
            blocked=True,
            guard_message="Canary token leak detected",
            blocked_layer="L4_output",
            decisions=decisions,
        )

    if not go.passed:
        return ChatTurn(
            answer="Ответ заблокирован выходным фильтром безопасности.",
            blocked=True,
            guard_message=go.reason,
            blocked_layer="L4_output",
            decisions=decisions,
        )

    return ChatTurn(answer=answer, decisions=decisions)


# ---------------------------------------------------------------------------
# NeMo path
# ---------------------------------------------------------------------------

def _import_generation_options() -> Any:
    """Locate GenerationOptions across NeMo versions (0.10 vs 0.11+).

    Returns the class or None if not available in this build. Hoisted out
    of _nemo_turn so both legacy and manual-orchestration paths can use it.
    """
    for module_path in (
        "nemoguardrails",
        "nemoguardrails.rails.llm.options",
    ):
        try:
            module = __import__(module_path, fromlist=["GenerationOptions"])
            cls = getattr(module, "GenerationOptions", None)
            if cls is not None:
                return cls
        except ImportError:
            continue
    return None


def _content_and_log(response: Any) -> tuple[str, Any]:
    """Extract bot content + activated-rails log from a NeMo response.

    NeMo's response shape differs across versions (dict vs object with
    .response attribute). This helper papers over both.
    """
    if isinstance(response, dict):
        content = response.get("content") or response.get("response", {}).get("content", "") or ""
        return str(content), response.get("log")
    resp_attr = getattr(response, "response", None)
    content = ""
    if isinstance(resp_attr, list) and resp_attr:
        content = resp_attr[0].get("content", "") if isinstance(resp_attr[0], dict) else str(resp_attr[0])
    elif isinstance(resp_attr, dict):
        content = resp_attr.get("content", "")
    elif isinstance(resp_attr, str):
        content = resp_attr
    return str(content), getattr(response, "log", None)


async def _nemo_turn(
    rails: Any,
    query: str,
    role: Role,
    parent_trace_id: str | None = None,
) -> ChatTurn:
    """Manual orchestration: NeMo input rail → our agent → NeMo output rail.

    EN: Why manual instead of letting NeMo do `input → generate_bot_message →
    output` itself: NeMo 0.21's built-in generate_bot_message goes through a
    direct LLM call ignoring our LangGraph agent. Two prior fix attempts
    (Colang main flow + register_action override) didn't intercept it.
    Selective rails via GenerationOptions(rails={...}) is documented and
    works across 0.10..0.21, so we drive the pipeline ourselves: first call
    NeMo with `{input: True, dialog: False, output: False, retrieval: False}`
    to evaluate input rails only, then run our agent (RAG + L3 RBAC + LLM),
    then call NeMo with `{output: True, ...}` to evaluate output rails on
    OUR answer. Defensive canary regex post-checks everything.

    RU: Тройной этап вместо одного generate_async. Делаем сами оркестрацию,
    NeMo выполняет ТОЛЬКО rails, агент пишет ответ.
    """
    GenerationOptions = _import_generation_options()  # noqa: N806

    decisions: list[GuardDecision] = []

    # ── Stage 1: Input rails ONLY ───────────────────────────────────────
    in_opts = None
    if GenerationOptions is not None:
        try:
            in_opts = GenerationOptions(
                rails={"input": True, "dialog": False, "retrieval": False, "output": False},
                log={"activated_rails": True, "llm_calls": False, "internal_events": False},
            )
        except TypeError:
            # Старая сигнатура GenerationOptions без `rails`
            in_opts = GenerationOptions(
                log={"activated_rails": True, "llm_calls": False, "internal_events": False}
            )

    token_role = _role_var.set(role)
    token_parent = _parent_trace_var.set(parent_trace_id)
    try:
        in_response = await rails.generate_async(
            messages=[{"role": "user", "content": query}],
            **({"options": in_opts} if in_opts is not None else {}),
        )
    finally:
        _role_var.reset(token_role)
        _parent_trace_var.reset(token_parent)

    in_content, in_log = _content_and_log(in_response)
    in_decisions = _parse_activated_rails(in_log)
    decisions.extend(in_decisions)
    in_blocked = next((d for d in in_decisions if not d.allowed), None)
    if in_blocked is not None:
        logger.info("L1 input blocked by %s — short-circuit before agent.", in_blocked.rail)
        return ChatTurn(
            answer=in_content or "Запрос заблокирован.",
            blocked=True,
            guard_message=in_blocked.reason or f"Blocked by {in_blocked.rail}",
            blocked_layer=in_blocked.layer,
            decisions=decisions,
        )

    # ── Stage 2: Agent (RAG + L3 RBAC + LangGraph) ──────────────────────
    logger.info("Input rails passed → calling agent | role=%s query=%r", role, query[:100])
    agent_answer = await run_agent(query=query, role=role, parent_trace_id=parent_trace_id)
    logger.info("Agent returned %d chars | role=%s", len(agent_answer), role)

    # ── Stage 3: Output rails ONLY on the AGENT's answer ────────────────
    out_opts = None
    if GenerationOptions is not None:
        try:
            out_opts = GenerationOptions(
                rails={"input": False, "dialog": False, "retrieval": False, "output": True},
                log={"activated_rails": True, "llm_calls": False, "internal_events": False},
            )
        except TypeError:
            out_opts = GenerationOptions(
                log={"activated_rails": True, "llm_calls": False, "internal_events": False}
            )

    token_role = _role_var.set(role)
    token_parent = _parent_trace_var.set(parent_trace_id)
    try:
        out_response = await rails.generate_async(
            messages=[
                {"role": "user", "content": query},
                {"role": "assistant", "content": agent_answer},
            ],
            **({"options": out_opts} if out_opts is not None else {}),
        )
    finally:
        _role_var.reset(token_role)
        _parent_trace_var.reset(token_parent)

    out_content, out_log = _content_and_log(out_response)
    out_decisions = _parse_activated_rails(out_log)
    decisions.extend(out_decisions)
    out_blocked = next((d for d in out_decisions if not d.allowed), None)

    # Если NeMo переписал ответ (output rail сработал) — берём ЕГО версию.
    final_answer = out_content or agent_answer

    if out_blocked is not None:
        # CRITICAL: never return the raw agent_answer in ChatResponse.answer
        # when the output rail blocked the turn — the answer may contain the
        # very leak the rail flagged (financial figures, PII, infrastructure
        # details, etc). Frontends that read `answer` regardless of `blocked`
        # would surface the leak. Replace with static refusal phrase; the
        # original answer remains in Langfuse trace for forensics.
        logger.info(
            "L4 output blocked by %s | suppressed_answer_chars=%d",
            out_blocked.rail, len(final_answer),
        )
        return ChatTurn(
            answer="Ответ заблокирован выходным фильтром безопасности.",
            blocked=True,
            guard_message=out_blocked.reason or f"Blocked by {out_blocked.rail}",
            blocked_layer=out_blocked.layer,
            decisions=decisions,
        )

    # Defensive: canary check на agent answer (perehватываем даже если NeMo
    # не flagнул — это наша последняя L4-сетка против indirect injection).
    if CANARY_PATTERN.search(final_answer):
        decisions.append(
            GuardDecision(
                layer="L4_output",
                rail="canary_leak_post",
                allowed=False,
                reason="Canary token leak detected (post-NeMo check)",
                score=1.0,
            )
        )
        return ChatTurn(
            answer="Ответ заблокирован: обнаружена утечка canary-токена.",
            blocked=True,
            guard_message="Canary token leak detected",
            blocked_layer="L4_output",
            decisions=decisions,
        )

    return ChatTurn(answer=final_answer, decisions=decisions)


def _parse_activated_rails(log: Any) -> list[GuardDecision]:
    """Translate NeMo's activated-rails log into GuardDecision objects."""
    decisions: list[GuardDecision] = []
    if log is None:
        return decisions

    activated = getattr(log, "activated_rails", None)
    if activated is None and isinstance(log, dict):
        activated = log.get("activated_rails", [])
    if not activated:
        return decisions

    for rail in activated:
        name = _attr(rail, "name", "unknown")
        rail_type = _attr(rail, "type", "input")
        decisions_raw = _attr(rail, "decisions", []) or []
        stopped = any(str(d).lower() in ("refuse", "stop", "block") for d in decisions_raw)

        layer = "L1_input" if rail_type == "input" else "L4_output"
        decisions.append(
            GuardDecision(
                layer=layer,
                rail=f"nemo:{name}",
                allowed=not stopped,
                reason=f"rail={name} stopped" if stopped else None,
                score=1.0 if stopped else 0.0,
            )
        )
    return decisions


def _attr(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def run_chat_turn(
    query: str,
    role: Role,
    parent_trace_id: str | None = None,
) -> ChatTurn:
    """Single entry point. Wraps the dispatcher to plumb the L3/RBAC result.

    graph.run writes an L3 summary into rbac_result_var AFTER its pipeline.
    Because graph.run runs INLINE in this task's context (only LangGraph
    *nodes* are context-isolated), the value is readable here once dispatch
    returns. Reset to None first so each turn reads only its own result.
    """
    rbac_result_var.set(None)
    turn = await _dispatch_chat_turn(query, role, parent_trace_id=parent_trace_id)
    turn.rbac = rbac_result_var.get()
    # Suppress the L3 chip on input-side blocks (L1/L2). NeMo's dispatcher can
    # run the agent (-> rag_search -> L3) DURING input-rail processing, so
    # rbac_result_var may be set even when the turn is rejected at input.
    # Showing "L3 hid N" on an L1/L2 block is misleading: the delivered answer
    # is the block, not a RAG answer.
    if turn.blocked and turn.blocked_layer in ("L1_input", "L2_behavioral"):
        turn.rbac = None
    return turn


async def _dispatch_chat_turn(
    query: str,
    role: Role,
    parent_trace_id: str | None = None,
) -> ChatTurn:
    """Dispatch to bypass / NeMo / legacy path.

    `parent_trace_id` (если задан main.py::chat) пробрасывается дальше
    в `run_agent`, чтобы агентские spans привязались к chat-trace в
    Langfuse как child, а не как отдельный root trace.
    """
    if not guardrails_enabled():
        answer = await run_agent(query=query, role=role, parent_trace_id=parent_trace_id)
        decisions = [
            GuardDecision(
                layer="L1_input",
                rail="bypass",
                allowed=True,
                reason="GUARDRAILS_ENABLED=false",
                score=0.0,
            )
        ]
        # In bypass mode we INTENTIONALLY surface canary leaks to the user —
        # это ядро демонстрации «без защиты», без неё атака indirect injection
        # выглядит так же, как обычный успешный ответ. Decision всё равно
        # пишется в Langfuse, чтобы red-team видел факт утечки в trace.
        if CANARY_PATTERN.search(answer):
            decisions.append(
                GuardDecision(
                    layer="L4_output",
                    rail="canary_leak_bypass_observed",
                    allowed=False,
                    reason="Canary leak observed (bypass mode — leak is shown to user on purpose)",
                    score=1.0,
                )
            )
            return ChatTurn(
                answer=answer,
                blocked=False,
                blocked_layer=None,
                decisions=decisions,
                guard_message="Canary leak detected but bypass mode surfaces it intentionally.",
            )
        decisions.append(
            GuardDecision(layer="L4_output", rail="bypass", allowed=True, score=0.0)
        )
        return ChatTurn(answer=answer, decisions=decisions)

    rails = _get_rails()
    if rails is None:
        return await _legacy_turn(query, role, parent_trace_id=parent_trace_id)
    try:
        return await _nemo_turn(rails, query, role, parent_trace_id=parent_trace_id)
    except Exception:
        logger.exception("NeMo turn failed — falling back to legacy guards for this request.")
        return await _legacy_turn(query, role, parent_trace_id=parent_trace_id)


def runtime_name() -> str:
    """Report which path run_chat_turn() would take — surfaced by /status."""
    if not guardrails_enabled():
        return "bypass"
    if _probe_nemo():
        return "nemo"
    return "legacy_regex"
