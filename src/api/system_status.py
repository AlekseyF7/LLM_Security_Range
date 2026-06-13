"""GET /api/v1/system/status — public status endpoint for the UI banner.
POST /api/v1/system/guardrails — admin-only runtime toggle for GUARDRAILS_ENABLED.

EN: Exposes whether guardrails are enabled so the UI can show the
    "⚠️ Protection disabled" banner in demo mode. The admin toggle
    flips an in-process flag (and mirrors it into os.environ) so that
    `deps.guardrails_enabled()` in subsequent requests sees the new
    value without restarting the container.

RU: Отдаёт состояние GUARDRAILS_ENABLED, чтобы UI показывал баннер
    «Защита отключена» в демо-режиме. Админский эндпоинт меняет
    флаг в рантайме без перезапуска контейнера. Это учебный полигон —
    persistent storage / БД для флага не нужно.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.deps import Role, get_role, guardrails_enabled
from src.api.rate_limit import clear_all_blocks, clear_block_for_ip
from src.ai_core.agent.reset_tool import reset_user_uploads

logger = logging.getLogger("api.system_status")

router = APIRouter(prefix="/api/v1/system", tags=["system"])

_STARTED_AT = time.time()
_VERSION = "0.2.0"


class GuardrailsToggleRequest(BaseModel):
    enabled: bool


class UnblockRequest(BaseModel):
    ip: str | None = None  # None → снять все блоки (red-team reset)


@router.get("/status")
def system_status() -> dict[str, Any]:
    return {
        "version": _VERSION,
        "guardrails_enabled": guardrails_enabled(),
        "guardrails_runtime": os.getenv("GUARDRAILS_RUNTIME", "nemo"),
        "uptime_seconds": int(time.time() - _STARTED_AT),
        "chat_model": os.getenv("CHAT_MODEL", "granite4.1:8b"),
        "embedding_model": os.getenv("EMBEDDING_MODEL", "bge-m3"),
    }


@router.post("/guardrails")
def toggle_guardrails(
    payload: GuardrailsToggleRequest,
    role: Role = Depends(get_role),
) -> dict[str, Any]:
    """Flip GUARDRAILS_ENABLED in-process. Admin only.

    Persists ONLY in os.environ (lost on container restart). This is
    intentional — для боевого включения защиты по умолчанию используется
    .env. Тумблер нужен только для демо «с защитой / без» в реальном
    времени, без редеплоя.
    """
    if role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admin can toggle guardrails. Set X-User-Role: admin.",
        )
    new_value = "true" if payload.enabled else "false"
    os.environ["GUARDRAILS_ENABLED"] = new_value
    logger.warning(
        "GUARDRAILS_ENABLED toggled to %s by admin (runtime only, not persisted).",
        new_value,
    )
    return {
        "guardrails_enabled": guardrails_enabled(),
        "guardrails_runtime": os.getenv("GUARDRAILS_RUNTIME", "nemo"),
        "note": "Runtime-only change. Restart resets to .env value.",
    }


@router.post("/unblock")
def unblock_ip(
    payload: UnblockRequest,
    role: Role = Depends(get_role),
) -> dict[str, Any]:
    """Сбросить L2 behavioral temp-block. Admin only.

    Без `ip` → снимает ВСЕ блоки (полный red-team reset). С `ip` →
    снимает блок только с указанного IP.

    Зачем: атаки с Kali идут с одного IP, после 4 jailbreak-попыток весь
    прогон встаёт в очередь на 5 минут. Этот эндпоинт позволяет Red Team
    Lead'у не ждать таймера. Альтернатива — выставить
    BEHAVIORAL_MONITORING_ENABLED=false в .env и перезапустить контейнер.
    """
    if role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admin can unblock IPs. Set X-User-Role: admin.",
        )
    if payload.ip:
        cleared = clear_block_for_ip(payload.ip)
        logger.warning("Admin cleared block | ip=%s | had_block=%s", payload.ip, cleared)
        return {"ip": payload.ip, "had_block": cleared}
    n = clear_all_blocks()
    logger.warning("Admin reset behavioral state | cleared=%d blocks", n)
    return {"ip": None, "cleared_blocks": n}


@router.post("/reset")
def reset_range(role: Role = Depends(get_role)) -> dict[str, Any]:
    """Reset the range to clean seed state between runs. Admin only.

    Purges user-uploaded RAG chunks (everything add_document wrote,
    metadata user_uploaded=True) and clears all L2 behavioral blocks.
    Seed docs (target_data/*) and Langfuse traces are NOT touched; no
    re-ingest happens (use ingest.sh for a full re-seed).
    """
    if role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admin can reset the range. Set X-User-Role: admin.",
        )
    chunks_removed = reset_user_uploads()
    blocks_cleared = clear_all_blocks()
    logger.warning(
        "Admin range reset | chunks_removed=%d blocks_cleared=%d",
        chunks_removed, blocks_cleared,
    )
    return {
        "chunks_removed": chunks_removed,
        "blocks_cleared": blocks_cleared,
        "note": "User-uploaded RAG chunks purged; L2 blocks cleared. Seed docs untouched.",
    }
