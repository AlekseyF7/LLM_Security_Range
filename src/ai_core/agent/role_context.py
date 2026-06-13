"""Shared ContextVar for the active X-User-Role.

EN: Both src/api/guardrails_runtime.py and src/ai_core/agent/tools.py
    (plus the upcoming add_document and lookup_cve tools) need to read
    the current role per-request. Defining the ContextVar in one place
    keeps them in sync and prevents 'two contexts holding different
    roles' subtle bugs that bit us during the Langfuse parent-trace fix.
RU: Один общий ContextVar для роли пользователя. Читают rails runtime,
    агент, и все будущие admin-only tools. Без shared-модуля легко
    случайно завести два разных контекста и получить странности.
"""

from __future__ import annotations

import contextvars

# Default 'anonymous' is fail-safe: any code path that reads role_var
# without an explicit set sees the least-privileged identity.
role_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "smart_wiki_role", default="anonymous"
)


def set_role(role: str):
    """Set role in current task context. Returns reset-token for cleanup.

    Use in `try/finally` (or async equivalent) to make sure we don't leak
    a role into the next handler:

        token = set_role("admin")
        try:
            ...do work...
        finally:
            role_var.reset(token)
    """
    return role_var.set(role)


# ── L3 / RBAC result side-channel ───────────────────────────────────────
# EN: rag_search (L3) computes how many chunks it hid by role, but run_agent
#     returns only a str. graph.run (which runs INLINE in the runtime's
#     context — only LangGraph *nodes* are context-isolated) writes a compact
#     summary here AFTER the pipeline; guardrails_runtime.run_chat_turn reads
#     it. Default None = no L3 signal (agent never retrieved).
# RU: Боковой канал для результата L3. Ставит graph.run, читает run_chat_turn.
rbac_result_var: contextvars.ContextVar[dict | None] = contextvars.ContextVar(
    "smart_wiki_rbac_result", default=None
)


def rbac_summary(rbac_blocked: bool, hidden_count: int, role: str) -> dict:
    """Compact L3 summary for the UI chip — count + role ONLY.

    Intentionally omits hidden filenames: revealing which restricted docs
    exist to an unauthorized role is itself a meta-leak.
    """
    return {"filtered": bool(rbac_blocked), "hidden": int(hidden_count), "role": role}
