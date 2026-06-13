"""FastAPI dependencies — role extraction and settings.

EN: Role is passed via X-User-Role header (anonymous | user | admin).
    No JWT — this is an educational cyber range, not a production bank.
RU: Роль приходит в заголовке X-User-Role. JWT не используется — это
    учебный киберполигон.
"""

from __future__ import annotations

import os
from typing import Literal

from fastapi import Header, HTTPException

Role = Literal["anonymous", "user", "admin"]
_VALID_ROLES: tuple[Role, ...] = ("anonymous", "user", "admin")


def get_role(x_user_role: str | None = Header(default=None)) -> Role:
    """Extract role from X-User-Role header, default = anonymous.

    Raises 400 if the header is present but invalid.
    """
    if x_user_role is None or not x_user_role.strip():
        return "anonymous"
    normalized = x_user_role.strip().lower()
    if normalized not in _VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid X-User-Role '{x_user_role}'. "
            f"Allowed: {', '.join(_VALID_ROLES)}.",
        )
    return normalized  # type: ignore[return-value]


def guardrails_enabled() -> bool:
    """Read GUARDRAILS_ENABLED env flag (default true for production)."""
    return os.getenv("GUARDRAILS_ENABLED", "true").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
