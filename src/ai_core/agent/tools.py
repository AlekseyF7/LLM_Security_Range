"""Agent tools — wraps RAG retrieval with RBAC filtering.

EN: `rag_search(query, role, top_k)` queries ChromaDB, then filters
    chunks by the caller's role using `confidentiality.get_map()`.
    Returns context string + structured trace info for Langfuse.

RU: Инструмент агента «поиск по корпоративной базе». Делает запрос
    в ChromaDB, потом отбрасывает чанки, недоступные роли. Это
    реализация L3 tool access control.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from src.ai_core.agent.confidentiality import get_map
from src.ai_core.rag.ingest import RagConfig, get_chroma_client, get_or_create_collection, ollama_embed

logger = logging.getLogger("ai_core.agent.tools")


@dataclass
class RagSearchResult:
    context: str
    chunks_total: int = 0
    chunks_after_rbac: int = 0
    sources_visible: list[str] = field(default_factory=list)
    sources_hidden: list[str] = field(default_factory=list)
    rbac_blocked: bool = False  # true if RBAC stripped at least one chunk
    diagnostic: str | None = None


def rag_search(
    query: str,
    role: str = "anonymous",
    top_k: int = 6,
    cfg: RagConfig | None = None,
    *,
    oversample_factor: int = 4,
) -> RagSearchResult:
    """Retrieve chunks from ChromaDB, RBAC-filter by role, return top_k visible.

    Why oversample_factor=4:
      Раньше top_k=6 шёл напрямую в Chroma. Если запрос «как настроить VPN»
      семантически сильнее матчился на restricted-документах (poisoned_doc,
      где много про VPN+Wi-Fi+RADIUS), все 6 чанков отфильтровывались RBAC
      для anonymous — и пользователь получал «доступ запрещён» вместо
      легитимного public-документа `policy_vpn.md`, проигравшего по
      cosine-similarity на 7-ю позицию.

      Решение — fetch top_k * oversample_factor чанков (24 по умолчанию),
      отфильтровать по роли, оставить top_k наиболее релевантных видимых.
      Так public-док всё ещё попадёт в выборку гостя, даже если несколько
      restricted-чанков были релевантнее.

    Если агент вызвать локально без ChromaDB — возвращаем пустой результат
    с warning вместо падения.
    """
    cfg = cfg or RagConfig.from_env()
    cmap = get_map()

    # Fail-fast diagnostic: if role has no configured visible levels, the
    # confidentiality map is likely missing/broken (or role is unknown).
    if not cmap.levels_visible_to(role):
        msg = (
            f"RBAC map has no visible levels for role='{role}'. "
            "Check target_data/confidentiality_map.yaml and CONFIDENTIALITY_MAP_PATH."
        )
        logger.warning("RAG search diagnostic: %s", msg)
        return RagSearchResult(context="", rbac_blocked=False, diagnostic=msg)

    fetch_k = max(top_k * oversample_factor, top_k)

    try:
        client = get_chroma_client(cfg)
        collection = get_or_create_collection(client, cfg)
        query_emb = ollama_embed(query, cfg=cfg)
        results = collection.query(
            query_embeddings=[query_emb],
            n_results=fetch_k,
            include=["documents", "metadatas"],
        )
    except Exception as exc:
        logger.exception("RAG search failed: %s", exc)
        return RagSearchResult(
            context="",
            rbac_blocked=False,
            diagnostic=f"RAG backend error: {type(exc).__name__}",
        )

    # If the collection itself is empty, this is an infra/setup problem
    # (ingest was not run), not a semantic "no answer in docs" case.
    try:
        total_docs = int(collection.count())
    except Exception:
        total_docs = -1
    if total_docs == 0:
        msg = (
            "RAG index is empty (collection has 0 documents). "
            "Run ingest.sh before eval."
        )
        logger.warning("RAG search diagnostic: %s", msg)
        return RagSearchResult(context="", rbac_blocked=False, diagnostic=msg)

    docs = (results.get("documents") or [[]])[0]
    metas = (results.get("metadatas") or [[]])[0]
    ids = (results.get("ids") or [[]])[0] if "ids" in results else [""] * len(docs)

    if len(docs) == 0:
        return RagSearchResult(context="")

    visible: list[tuple[str, str, dict]] = []
    hidden_sources: set[str] = set()
    seen_visible_sources: set[str] = set()

    for _id, doc, meta in zip(ids, docs, metas):
        meta = meta or {}
        src = str(meta.get("source_file", "unknown"))
        # chunk_level — set by add_document tool for user-uploaded docs.
        # None для статических документов из target_data/ — fallback на
        # confidentiality_map.yaml. См. ConfidentialityMap.allowed_for_chunk.
        chunk_level = meta.get("level")
        if cmap.allowed_for_chunk(role, src, chunk_level=chunk_level):
            visible.append((str(_id), str(doc), meta))
            seen_visible_sources.add(src)
        else:
            hidden_sources.add(src)

    # Trim oversampled set down to top_k visible — порядок Chroma уже по релевантности.
    visible = visible[:top_k]

    rbac_blocked = bool(hidden_sources)
    if rbac_blocked:
        logger.info(
            "RBAC: role=%s — hidden %d sources (%s), kept %d sources from %d fetched.",
            role, len(hidden_sources), ", ".join(sorted(hidden_sources))[:200],
            len(seen_visible_sources), fetch_k,
        )

    parts: list[str] = []
    for _id, doc, meta in visible:
        src = meta.get("source_file", "unknown")
        idx = meta.get("chunk_index", "?")
        parts.append(f"[{src} :: chunk {idx}]\n{doc}")

    return RagSearchResult(
        context="\n\n".join(parts),
        chunks_total=len(docs),
        chunks_after_rbac=len(visible),
        sources_visible=sorted(seen_visible_sources),
        sources_hidden=sorted(hidden_sources),
        rbac_blocked=rbac_blocked,
    )


def tool_summary(result: RagSearchResult) -> dict[str, Any]:
    """Compact dict for Langfuse span output."""
    return {
        "chunks_total": result.chunks_total,
        "chunks_after_rbac": result.chunks_after_rbac,
        "rbac_blocked": result.rbac_blocked,
        "sources_visible": result.sources_visible,
        "sources_hidden_count": len(result.sources_hidden),
        "context_chars": len(result.context),
    }
