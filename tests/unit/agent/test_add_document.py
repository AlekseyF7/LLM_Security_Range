"""Unit tests for src.ai_core.agent.add_document_tool.

Coverage:
- RBAC: anonymous/user denied, admin allowed
- Validation: invalid level, path traversal in source_name,
  empty content, oversized content
- Happy path: writes correct ids/documents/metadatas/embeddings
  with level recorded in metadata for rag_search filtering
"""

from unittest.mock import MagicMock

import pytest

from src.ai_core.agent.role_context import set_role, role_var
from src.ai_core.agent.add_document_tool import (
    add_document,
    AddDocumentError,
    AddDocumentResult,
)


@pytest.fixture
def fake_chroma(monkeypatch):
    """Stub ChromaDB collection so tests don't need a real DB."""
    fake_collection = MagicMock()
    fake_collection.add = MagicMock()
    fake_collection.count = MagicMock(return_value=42)
    monkeypatch.setattr(
        "src.ai_core.agent.add_document_tool._get_collection",
        lambda cfg=None: fake_collection,
    )
    return fake_collection


@pytest.fixture
def fake_embed(monkeypatch):
    """Stub Ollama embedding call — return a fixed 768-dim vector."""
    monkeypatch.setattr(
        "src.ai_core.agent.add_document_tool.ollama_embed",
        lambda text, cfg=None: [0.1] * 768,
    )


# ── RBAC ──────────────────────────────────────────────────────────────


def test_anonymous_blocked(fake_chroma, fake_embed):
    token = set_role("anonymous")
    try:
        with pytest.raises(AddDocumentError, match="admin"):
            add_document(content="hello", level="public", source_name="x.md")
    finally:
        role_var.reset(token)
    assert fake_chroma.add.call_count == 0, "Anonymous must not write to Chroma"


def test_user_blocked(fake_chroma, fake_embed):
    token = set_role("user")
    try:
        with pytest.raises(AddDocumentError, match="admin"):
            add_document(content="hello", level="public", source_name="x.md")
    finally:
        role_var.reset(token)
    assert fake_chroma.add.call_count == 0, "Plain user must not write to Chroma"


def test_admin_allowed_writes_to_chroma(fake_chroma, fake_embed):
    token = set_role("admin")
    try:
        result = add_document(
            content="Корпоративная инструкция: используй 2FA везде где можно.",
            level="internal",
            source_name="security_extra.md",
        )
    finally:
        role_var.reset(token)

    assert isinstance(result, AddDocumentResult)
    assert result.added is True
    assert result.chunks >= 1
    assert result.source_file == "user_uploads/security_extra.md"
    assert result.level == "internal"
    assert result.embedding_dim == 768

    fake_chroma.add.assert_called_once()
    kwargs = fake_chroma.add.call_args.kwargs
    assert kwargs["metadatas"][0]["level"] == "internal", (
        "level must be persisted in chunk metadata so rag_search "
        "can RBAC-filter user-uploaded docs without a YAML round-trip"
    )
    assert kwargs["metadatas"][0]["source_file"] == "user_uploads/security_extra.md"
    assert kwargs["metadatas"][0]["user_uploaded"] is True
    assert kwargs["metadatas"][0]["added_by"] == "admin"


# ── Validation ─────────────────────────────────────────────────────────


def test_invalid_level_rejected(fake_chroma, fake_embed):
    token = set_role("admin")
    try:
        with pytest.raises(AddDocumentError, match="level"):
            add_document(content="x", level="top-secret", source_name="x.md")
    finally:
        role_var.reset(token)
    assert fake_chroma.add.call_count == 0


def test_path_traversal_in_source_name_rejected(fake_chroma, fake_embed):
    token = set_role("admin")
    try:
        with pytest.raises(AddDocumentError, match="source_name"):
            add_document(
                content="harmless content",
                level="public",
                source_name="../../etc/passwd",
            )
    finally:
        role_var.reset(token)
    assert fake_chroma.add.call_count == 0


def test_non_safe_charset_in_source_name_rejected(fake_chroma, fake_embed):
    """Кириллица / спецсимволы в source_name должны блокироваться."""
    token = set_role("admin")
    try:
        with pytest.raises(AddDocumentError, match="source_name"):
            add_document(
                content="x",
                level="public",
                source_name="русское_имя.md",
            )
    finally:
        role_var.reset(token)


def test_empty_content_rejected(fake_chroma, fake_embed):
    token = set_role("admin")
    try:
        with pytest.raises(AddDocumentError, match="content"):
            add_document(content="   \n  ", level="public", source_name="x.md")
    finally:
        role_var.reset(token)


def test_oversized_content_rejected(fake_chroma, fake_embed):
    token = set_role("admin")
    try:
        with pytest.raises(AddDocumentError, match="size|too large"):
            add_document(
                content="A" * 200_001,
                level="public",
                source_name="x.md",
            )
    finally:
        role_var.reset(token)


# ── Explicit role parameter (для LangGraph executor crossing) ────────


def test_explicit_role_overrides_contextvar(fake_chroma, fake_embed):
    """Когда LangGraph executor исполняет node, ContextVar теряется.
    Поэтому передаём role явным аргументом — он должен иметь приоритет."""
    # ContextVar = anonymous (default), но явный role=admin должен пройти
    result = add_document(
        content="Admin content via explicit role",
        level="public",
        source_name="explicit.md",
        role="admin",
    )
    assert result.added is True
    kwargs = fake_chroma.add.call_args.kwargs
    assert kwargs["metadatas"][0]["added_by"] == "admin"


def test_explicit_role_user_blocked_even_if_contextvar_says_admin(fake_chroma, fake_embed):
    """Defense-in-depth: явный role перебивает ContextVar даже когда
    ContextVar говорит admin. Защищает от accidental privilege escalation
    через unfresh ContextVar в re-entrant сценариях."""
    token = set_role("admin")
    try:
        with pytest.raises(AddDocumentError, match="admin"):
            add_document(
                content="x", level="public", source_name="x.md",
                role="user",
            )
    finally:
        role_var.reset(token)
    assert fake_chroma.add.call_count == 0


# ── Regression: cfg=None must NOT propagate into ollama_embed ─────────


def test_cfg_none_is_resolved_via_from_env(fake_chroma, monkeypatch):
    """add_document(cfg=None) должен резолвить RagConfig.from_env() —
    иначе ollama_embed получает None и падает с AttributeError, который
    проходит мимо except AddDocumentError в node_generate_answer.

    Regression от end-to-end-чекпойнта Phase 1: admin-загрузка молча
    падала в Chroma 0 raw + LLM-парафраз в ответе вместо явного 'Документ
    добавлен'.
    """
    captured: dict = {}

    def fake_embed(text, *, cfg):
        captured["cfg"] = cfg
        assert cfg is not None, "ollama_embed must receive a real cfg, not None"
        return [0.1] * 768

    monkeypatch.setattr(
        "src.ai_core.agent.add_document_tool.ollama_embed", fake_embed
    )

    # Simulate from_env() returning a real-looking config
    class _StubCfg:
        ollama_url = "http://stub:11434"
        embedding_model = "stub-model"

    monkeypatch.setattr(
        "src.ai_core.agent.add_document_tool.RagConfig.from_env",
        staticmethod(lambda: _StubCfg()),
    )

    result = add_document(
        content="regression payload",
        level="public",
        source_name="regression.md",
        role="admin",
        cfg=None,
    )
    assert result.added is True
    assert isinstance(captured["cfg"], _StubCfg), "cfg must have been resolved"
