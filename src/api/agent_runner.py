"""Agent runner — thin indirection between the API and the agent implementation.

EN: Decouples the API layer (X-User-Role, toggles, NeMo custom actions)
    from the agent. `run_agent` dispatches to a registered handler — the
    LangGraph flow in `src.ai_core.agent.graph` auto-registers at the
    bottom of this module. Without a handler it falls back to
    `generate_answer()` (or `_stub_generate_answer` when chromadb is
    absent). The async signature (query, role) stays stable either way.

RU: Прокладка между API-слоем и агентом. Реализацию подключает
    зарегистрированный обработчик (LangGraph-граф из ai_core.agent.graph),
    без правок в API.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable

logger = logging.getLogger("api.agent_runner")

try:
    from src.ai_core.rag.ingest import generate_answer as _rag_generate
    _rag_available = True
except ImportError:
    _rag_available = False
    logger.warning("chromadb / rag stack missing — agent_runner will use stub answers.")

def _stub_generate_answer(query: str) -> str:
    """Safe fallback: никогда не возвращает fake-credentials.

    Было — при падении RAG stub подставлял захардкоженные СНИЛС / пароли /
    XSS-payload, игнорируя role. В bypass-режиме (guards OFF) это было
    прямой утечкой, обходящей RBAC. Теперь stub отдаёт честный отказ:
    сервис в degraded-режиме, пусть пользователь повторит позже.
    """
    del query  # query не нужен — ответ одинаковый для любой роли/вопроса
    return (
        "⚠️ Сервис работает в ограниченном режиме: RAG-компонент недоступен "
        "(ChromaDB / Ollama). Повторите запрос через минуту или обратитесь "
        "в ServiceDesk (доб. 1500)."
    )


# A registered handler (the LangGraph agent) accepts role + propagates
# tool_access_control decisions. Keep the async signature
# (query, role) -> str.
_agent_handler: Callable[..., str] | None = None


def register_agent_handler(handler: Callable[..., str]) -> None:
    """Swap in a LangGraph agent at import time.

    The handler must accept keyword arguments `query: str` and `role: str`
    and return a `str` (sync or awaitable).
    """
    global _agent_handler
    _agent_handler = handler
    logger.info("Agent handler registered: %s", getattr(handler, "__qualname__", handler))


async def run_agent(
    query: str,
    role: str = "anonymous",
    parent_trace_id: str | None = None,
) -> str:
    """Run the agent for a single turn. Returns the raw LLM answer.

    If `parent_trace_id` is provided, the LangGraph agent attaches its
    Langfuse spans under that trace (parent-child layout). Compatible
    with handlers that don't accept the new kwarg — falls back gracefully.
    """
    if _agent_handler is not None:
        try:
            try:
                result = _agent_handler(query=query, role=role, parent_trace_id=parent_trace_id)
            except TypeError:
                # Legacy handler signature (query, role) — drop parent_trace_id
                result = _agent_handler(query=query, role=role)
            if asyncio.iscoroutine(result):
                return await result
            return str(result)
        except Exception:
            logger.exception("Custom agent handler failed — falling back to direct RAG.")

    if _rag_available:
        try:
            return await asyncio.to_thread(_rag_generate, query)
        except Exception as exc:
            logger.exception("RAG generate_answer failed: %s — using stub answer.", exc)
            return _stub_generate_answer(query)

    return await asyncio.to_thread(_stub_generate_answer, query)


# ── Auto-register LangGraph agent at import-time ────────────────────────
# Placed AT THE BOTTOM to avoid circular import: graph.register() pulls
# `register_agent_handler` from this module, which must already exist by
# the time we trigger the import.
#
# Falls back silently if anything in the agent stack is missing — the
# API stays alive (using direct RAG → stub chain above).
try:
    from src.ai_core.agent.graph import register as _register_langgraph
    _register_langgraph()
except Exception as _exc:  # noqa: BLE001
    logger.warning("LangGraph agent not registered: %s", _exc)
