"""Unit tests for src.ai_core.agent.reset_tool.

Mocks the ChromaDB collection so tests need no real DB. Verifies the
delete filter is EXACTLY where={"user_uploaded": True} (seed docs, which
lack that flag, must never be deleted) and the returned count is the delta.
"""

from unittest.mock import MagicMock

from src.ai_core.agent.reset_tool import reset_user_uploads


def _fake_collection(count_before: int, count_after: int) -> MagicMock:
    c = MagicMock()
    c.count = MagicMock(side_effect=[count_before, count_after])
    c.delete = MagicMock()
    return c


def test_reset_deletes_user_uploads_and_returns_delta(monkeypatch):
    coll = _fake_collection(10, 7)
    monkeypatch.setattr("src.ai_core.agent.reset_tool._get_collection", lambda cfg=None: coll)
    removed = reset_user_uploads()
    assert removed == 3
    coll.delete.assert_called_once_with(where={"user_uploaded": True})


def test_reset_returns_zero_when_nothing_uploaded(monkeypatch):
    coll = _fake_collection(5, 5)
    monkeypatch.setattr("src.ai_core.agent.reset_tool._get_collection", lambda cfg=None: coll)
    assert reset_user_uploads() == 0
    coll.delete.assert_called_once_with(where={"user_uploaded": True})


def test_reset_fail_safe_on_chroma_error(monkeypatch):
    """Chroma down / collection missing → return 0, do not raise (endpoint stays up)."""
    coll = MagicMock()
    coll.count = MagicMock(side_effect=RuntimeError("chroma unavailable"))
    monkeypatch.setattr("src.ai_core.agent.reset_tool._get_collection", lambda cfg=None: coll)
    assert reset_user_uploads() == 0
