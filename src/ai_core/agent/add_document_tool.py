"""add_document — admin-only RAG write tool.

EN: Lets the LangGraph agent ingest a new document into the existing
    ChromaDB collection when (and only when) the active role is admin.
    Demonstrates LLM07 (Insecure Plugin / Agent Authorization) and
    sets up indirect-injection-via-self-uploaded-doc scenarios for the
    cyber range.

    Architecture notes:
    - Role is read from the shared ContextVar in src.ai_core.agent.role_context.
      `_role_var` is set by guardrails_runtime._nemo_turn for each request,
      so when the LangGraph agent (running in the same task) calls
      add_document(), the right identity flows through automatically.
    - Per-chunk `level` is persisted in metadata so rag_search can
      RBAC-filter user-uploaded docs without a YAML round-trip
      (see ConfidentialityMap.allowed_for_chunk).
    - All validators are fail-closed: any check that doesn't pass raises
      AddDocumentError, and graph.py.node_generate_answer renders it
      through the standard refusal phrase (matched by promptfoo regex).

RU: Admin может через агента залить документ в RAG. Демонстрирует
    LLM07 + готовит площадку для indirect-injection: admin льёт
    poisoned-документ → следующий пользовательский запрос вытаскивает
    его → output guard ловит canary. Жёсткие валидаторы: path-traversal,
    charset, размер, level. Любой fail — AddDocumentError.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from typing import Any

from src.ai_core.agent.role_context import role_var
from src.ai_core.rag.ingest import (
    RagConfig,
    chunk_text,
    get_chroma_client,
    get_or_create_collection,
    ollama_embed,
)

logger = logging.getLogger("ai_core.agent.add_document")

# ── Constants — exposed for tests / external introspection ───────────────

ALLOWED_LEVELS: frozenset[str] = frozenset({"public", "internal", "restricted"})
MAX_CONTENT_BYTES = 200_000  # 200 KB. Защита от content-size attack (LLM04).
USER_UPLOAD_PREFIX = "user_uploads"

# ASCII-only имя файла. Кириллица / спецсимволы блокируются — это упрощает
# поиск по metadata и убирает riski path-traversal через unicode normalisation.
_SAFE_SOURCE_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}\.(md|txt|markdown)$")


class AddDocumentError(Exception):
    """Raised on RBAC denial or input-validation failure.

    The agent layer (node_generate_answer) catches this and renders the
    standard refusal phrase so promptfoo regex assertions match cleanly.
    """


@dataclass
class AddDocumentResult:
    """Structured result returned to the agent on a successful write."""

    added: bool
    chunks: int
    source_file: str
    level: str
    embedding_dim: int


# ── Indirections so tests can monkeypatch без живой Chroma / Ollama ──────


def _get_collection(cfg: RagConfig | None = None):
    """Resolve current ChromaDB collection. Indirected for tests."""
    cfg = cfg or RagConfig.from_env()
    return get_or_create_collection(get_chroma_client(cfg), cfg)


# ── Validators ──────────────────────────────────────────────────────────


def _resolve_role(explicit: str | None) -> str:
    """Pick role from explicit arg (LangGraph state) or ContextVar fallback.

    EN: ContextVar (_role_var) works fine within a single async task, but
        LangGraph's compiled graph runs nodes via its own executor — the
        ContextVar set in src/api/guardrails_runtime.py::_nemo_turn does
        NOT propagate into the agent's node calls. To bridge that, we
        accept an explicit role argument and prefer it over the var.
    RU: ContextVar теряется через границу LangGraph-executor'а, поэтому
        предпочитаем явно переданный role из state.role. ContextVar
        остаётся fallback на случай прямого вызова tool'а в обход графа.
    """
    return explicit if explicit else role_var.get()


def _validate_role(role: str) -> None:
    if role != "admin":
        logger.warning("add_document RBAC denied | role=%s", role)
        raise AddDocumentError(
            f"add_document requires admin role, got '{role}'. "
            "L3 tool access control blocked the request."
        )


def _validate_inputs(content: str, level: str, source_name: str) -> None:
    if level not in ALLOWED_LEVELS:
        raise AddDocumentError(
            f"level must be one of {sorted(ALLOWED_LEVELS)}, got '{level}'."
        )
    if not content or not content.strip():
        raise AddDocumentError("content must be a non-empty string.")
    if len(content.encode("utf-8")) > MAX_CONTENT_BYTES:
        raise AddDocumentError(
            f"content size exceeds {MAX_CONTENT_BYTES} bytes (too large)."
        )
    if not _SAFE_SOURCE_NAME_RE.match(source_name or ""):
        raise AddDocumentError(
            "source_name must match [A-Za-z0-9._-]{1,80}.(md|txt|markdown) — "
            "path traversal, unicode and other special chars are not allowed."
        )


# ── Public entry point ──────────────────────────────────────────────────


def add_document(
    *,
    content: str,
    level: str,
    source_name: str,
    role: str | None = None,
    cfg: RagConfig | None = None,
) -> AddDocumentResult:
    """Ingest one document into the RAG collection. Admin only.

    Args:
        content: document body (Markdown/plain text). Will be chunk_text-ed.
        level: visibility level — one of {"public", "internal", "restricted"}.
        source_name: filename component, validated against a strict regex.
            Stored as `user_uploads/<source_name>` in chunk metadata.
        role: optional explicit role. If provided, overrides the
            role_var ContextVar. Pass state.role from LangGraph nodes
            (the ContextVar set by guardrails_runtime doesn't survive
            LangGraph's executor boundary).
        cfg: optional override of RagConfig (defaults to from_env()).

    Returns:
        AddDocumentResult with chunk count, full source_file path,
        the level persisted in metadata, and embedding dimensionality.

    Raises:
        AddDocumentError: on RBAC denial or any input validation failure.
    """
    effective_role = _resolve_role(role)
    _validate_role(effective_role)
    _validate_inputs(content, level, source_name)

    # Resolve cfg ONCE here so downstream calls (ollama_embed, _get_collection)
    # always see a real RagConfig. Раньше cfg=None пробрасывался в
    # ollama_embed → AttributeError 'NoneType'.ollama_url → bubbled up out of
    # node_generate_answer's `except AddDocumentError`, agent fell back to
    # _rag_generate, and nothing was actually written to Chroma. Unit tests
    # didn't catch this because fake_embed fixture accepts any cfg.
    cfg = cfg or RagConfig.from_env()

    source_file = f"{USER_UPLOAD_PREFIX}/{source_name}"
    chunks = chunk_text(content)
    if not chunks:
        # Should not happen — _validate_inputs already rejects empty.
        # Defensive: chunk_text may return [] on inputs that whitespace-collapse to empty.
        raise AddDocumentError("content produced 0 chunks after normalization.")

    collection = _get_collection(cfg)

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, Any]] = []
    embeddings: list[list[float]] = []

    for idx, chunk in enumerate(chunks):
        # Stable, content-derived id — повторный заход с тем же содержимым
        # перепишет, а не дубл'ит. На демо это удобно (можно re-upload).
        doc_id = hashlib.sha256(
            f"{source_file}:{idx}:{chunk[:200]}".encode("utf-8")
        ).hexdigest()[:32]

        ids.append(doc_id)
        documents.append(chunk)
        metadatas.append(
            {
                "source_file": source_file,
                "chunk_index": idx,
                # ВАЖНО: level хранится в metadata. ConfidentialityMap
                # .allowed_for_chunk() читает его и фильтрует чанки —
                # благодаря этому user-uploaded документы не требуют
                # ручной правки confidentiality_map.yaml.
                "level": level,
                "added_by": effective_role,
                "user_uploaded": True,
            }
        )
        embeddings.append(ollama_embed(chunk, cfg=cfg))

    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings,
    )
    logger.info(
        "add_document OK | source=%s level=%s chunks=%d by=%s",
        source_file, level, len(chunks), effective_role,
    )
    return AddDocumentResult(
        added=True,
        chunks=len(chunks),
        source_file=source_file,
        level=level,
        embedding_dim=len(embeddings[0]) if embeddings else 0,
    )
