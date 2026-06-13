"""reset_tool — purge user-uploaded RAG chunks (range reset between runs).

EN: reset_user_uploads() deletes every chunk that add_document wrote
    (metadata user_uploaded=True) from the ChromaDB collection, leaving the
    seed corpus (target_data/*, which has no such flag) untouched. Returns
    the number of chunks removed. Fail-safe: any Chroma error → 0 (the admin
    endpoint must not 500 just because the store is briefly unavailable).

RU: Удаляет из RAG-коллекции чанки, залитые через add_document
    (user_uploaded=True). Seed-доки не трогает. Любая ошибка → 0.
"""

from __future__ import annotations

import logging

from src.ai_core.rag.ingest import (
    RagConfig,
    get_chroma_client,
    get_or_create_collection,
)

logger = logging.getLogger("ai_core.agent.reset")

# Marker written by add_document_tool on every user-uploaded chunk.
_USER_UPLOAD_FILTER = {"user_uploaded": True}


def _get_collection(cfg: RagConfig | None = None):
    """Resolve current ChromaDB collection. Indirected for tests."""
    cfg = cfg or RagConfig.from_env()
    return get_or_create_collection(get_chroma_client(cfg), cfg)


def reset_user_uploads(cfg: RagConfig | None = None) -> int:
    """Delete user-uploaded chunks; return how many were removed.

    Fail-safe: returns 0 on any error (missing collection, Chroma down).
    Deletes ONLY where user_uploaded=True — seed docs are never affected.
    """
    try:
        collection = _get_collection(cfg)
        before = collection.count()
        collection.delete(where=_USER_UPLOAD_FILTER)
        after = collection.count()
        removed = max(0, before - after)
        logger.warning("Range reset | removed %d user-uploaded chunks", removed)
        return removed
    except Exception as exc:  # noqa: BLE001 — admin endpoint must stay up
        logger.exception("Range reset failed (returning 0): %s", exc)
        return 0
