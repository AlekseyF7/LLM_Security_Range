"""Confidentiality map loader + RBAC checker.

EN: Loads `target_data/confidentiality_map.yaml` once at import-time.
    Provides `level_for(source_file)` and `allowed_for(role, source_file)`
    helpers used by the RAG tool to filter retrieved chunks.

RU: Загружает carta из YAML один раз при импорте. Даёт API для
    LangGraph-узла tool: rag_search, чтобы он отфильтровал чанки
    из ChromaDB по списку разрешённых для роли уровней.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml

logger = logging.getLogger("ai_core.agent.confidentiality")

DEFAULT_MAP_PATH = "target_data/confidentiality_map.yaml"
_FAIL_CLOSED_LEVEL = "restricted"


@dataclass(frozen=True)
class DocMeta:
    level: str
    owner: str | None
    canary: str | None
    poisoned: bool
    contains: str | None


class ConfidentialityMap:
    """Wraps the YAML map. Constructed once via `load_default()`."""

    def __init__(
        self,
        documents: dict[str, DocMeta],
        rbac: dict[str, list[str]],
        default_level: str,
    ) -> None:
        self._documents = documents
        self._rbac = {role: set(levels) for role, levels in rbac.items()}
        self._default_level = default_level

    # ── Lookups ─────────────────────────────────────────────────────────
    def level_for(self, source_file: str) -> str:
        """Return level for a path. Fail-closed if not in map."""
        key = self._normalize(source_file)
        meta = self._documents.get(key)
        if meta is None:
            logger.debug("Unknown doc '%s' → fail-closed to '%s'.", key, self._default_level)
            return self._default_level
        return meta.level

    def meta_for(self, source_file: str) -> DocMeta | None:
        return self._documents.get(self._normalize(source_file))

    def allowed_for(self, role: str, source_file: str) -> bool:
        """True if `role` may see chunk from this `source_file`."""
        allowed_levels = self._rbac.get(role)
        if allowed_levels is None:
            logger.warning("Unknown role '%s' → deny.", role)
            return False
        return self.level_for(source_file) in allowed_levels

    def allowed_for_chunk(
        self,
        role: str,
        source_file: str,
        chunk_level: str | None = None,
    ) -> bool:
        """RBAC check that honors per-chunk metadata level if present.

        EN: If `chunk_level` is provided (e.g. from chunk.metadata['level']
            for user-uploaded docs created via add_document), it takes
            precedence over the YAML map. This lets admin tag a chunk as
            'restricted' even when its base source_file is 'public' in
            YAML — useful for sensitive content inserted into an otherwise
            public document. Invalid chunk_level values are ignored and we
            fall back to the YAML-based level_for().
        RU: Metadata-level чанка перебивает YAML, чтобы admin мог пометить
            конкретный чанк как restricted даже если базовый source_file
            считается public. Невалидные значения (опечатки) игнорируем —
            fail-safe fallback на YAML.
        """
        effective = (
            chunk_level
            if chunk_level in {"public", "internal", "restricted"}
            else self.level_for(source_file)
        )
        allowed_levels = self._rbac.get(role)
        if allowed_levels is None:
            logger.warning("Unknown role '%s' → deny.", role)
            return False
        return effective in allowed_levels

    def levels_visible_to(self, role: str) -> set[str]:
        return set(self._rbac.get(role, ()))

    def all_canaries(self) -> set[str]:
        return {m.canary for m in self._documents.values() if m.canary}

    # ── Helpers ─────────────────────────────────────────────────────────
    @staticmethod
    def _normalize(source_file: str) -> str:
        """Map absolute/Windows paths to the relative YAML key form."""
        if not source_file:
            return ""
        s = str(source_file).replace("\\", "/")
        marker = "/target_data/"
        if marker in s:
            s = s.split(marker, 1)[1]
        elif s.startswith("target_data/"):
            s = s[len("target_data/"):]
        return s


def load_default(path: str | None = None) -> ConfidentialityMap:
    """Load the YAML map. Returns a fail-closed map on any error."""
    map_path = path or os.getenv("CONFIDENTIALITY_MAP_PATH", DEFAULT_MAP_PATH)
    p = Path(map_path)
    if not p.exists():
        logger.warning(
            "Confidentiality map not found at %s — using empty (fail-closed) map. "
            "All documents will be treated as 'restricted'.",
            map_path,
        )
        return ConfidentialityMap(documents={}, rbac={}, default_level=_FAIL_CLOSED_LEVEL)

    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        logger.error("Failed to parse %s: %s — fail-closed.", map_path, exc)
        return ConfidentialityMap(documents={}, rbac={}, default_level=_FAIL_CLOSED_LEVEL)

    docs: dict[str, DocMeta] = {}
    for key, raw_meta in (raw.get("documents") or {}).items():
        docs[str(key)] = DocMeta(
            level=str(raw_meta.get("level", _FAIL_CLOSED_LEVEL)),
            owner=raw_meta.get("owner"),
            canary=raw_meta.get("canary"),
            poisoned=bool(raw_meta.get("poisoned", False)),
            contains=raw_meta.get("contains"),
        )

    rbac = raw.get("rbac") or {
        "anonymous": ["public"],
        "user": ["public", "internal"],
        "admin": ["public", "internal", "restricted"],
    }
    default_level = str(raw.get("default_level", _FAIL_CLOSED_LEVEL))
    logger.info(
        "Confidentiality map loaded: %d documents, roles=%s, default='%s'.",
        len(docs), list(rbac.keys()), default_level,
    )
    return ConfidentialityMap(documents=docs, rbac=rbac, default_level=default_level)


# Module-level singleton (loaded lazily on first access)
_singleton: ConfidentialityMap | None = None


def get_map() -> ConfidentialityMap:
    global _singleton
    if _singleton is None:
        _singleton = load_default()
    return _singleton


def filter_chunks(
    role: str,
    items: Iterable[tuple[str, str, dict]],
) -> list[tuple[str, str, dict]]:
    """Generic helper: filter (id, document, metadata) tuples by role.

    Reads `metadata['source_file']` to look up the level.
    """
    cmap = get_map()
    out: list[tuple[str, str, dict]] = []
    for item in items:
        _id, _doc, meta = item
        src = (meta or {}).get("source_file", "")
        if cmap.allowed_for(role, src):
            out.append(item)
    return out
