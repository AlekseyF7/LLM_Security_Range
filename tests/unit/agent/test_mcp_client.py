"""Unit tests for src.ai_core.agent.mcp_client.

Mocks the MCP session so tests don't need a running mcp-cve container.
Real integration with mcp-cve is exercised in Task 2.5 smoke tests.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.ai_core.agent.mcp_client import call_mcp_tool, MCPCallError


class _FakeSession:
    """Mimics enough of mcp.ClientSession for tests."""

    def __init__(self, result_payload=None, raise_exc=None):
        self._result = result_payload
        self._raise = raise_exc
        self.call_tool = AsyncMock(side_effect=self._call)

    async def _call(self, name, arguments):
        if self._raise:
            raise self._raise
        # FastMCP wraps the tool return value as TextContent objects;
        # the first one carries the JSON-serialised result.
        return MagicMock(content=[MagicMock(type="text", text=self._result)])


class _FakeCtx:
    """Async context manager that yields a _FakeSession."""

    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *exc):
        return None


async def test_call_mcp_tool_returns_list_payload(monkeypatch):
    session = _FakeSession(result_payload='[{"id": "CVE-2021-44228", "description": "RCE in log4j"}]')
    monkeypatch.setattr(
        "src.ai_core.agent.mcp_client._open_session",
        lambda url: _FakeCtx(session),
    )
    out = await call_mcp_tool("lookup_cve", {"query": "CVE-2021-44228"})
    assert isinstance(out, list)
    assert out[0]["id"] == "CVE-2021-44228"


async def test_call_mcp_tool_wraps_dict_as_list(monkeypatch):
    """If server returned a single dict, wrap it as 1-element list for caller-uniform handling."""
    session = _FakeSession(result_payload='{"id": "CVE-2024-1", "description": "lonely"}')
    monkeypatch.setattr(
        "src.ai_core.agent.mcp_client._open_session",
        lambda url: _FakeCtx(session),
    )
    out = await call_mcp_tool("lookup_cve", {"query": "lonely"})
    assert isinstance(out, list)
    assert len(out) == 1
    assert out[0]["id"] == "CVE-2024-1"


async def test_call_mcp_tool_empty_content_yields_empty_list(monkeypatch):
    session = MagicMock()
    session.call_tool = AsyncMock(return_value=MagicMock(content=[]))
    monkeypatch.setattr(
        "src.ai_core.agent.mcp_client._open_session",
        lambda url: _FakeCtx(session),
    )
    out = await call_mcp_tool("lookup_cve", {"query": "nothing"})
    assert out == []


async def test_call_mcp_tool_propagates_transport_error(monkeypatch):
    session = _FakeSession(raise_exc=RuntimeError("transport down"))
    monkeypatch.setattr(
        "src.ai_core.agent.mcp_client._open_session",
        lambda url: _FakeCtx(session),
    )
    with pytest.raises(MCPCallError, match="transport down"):
        await call_mcp_tool("lookup_cve", {"query": "anything"})


async def test_call_mcp_tool_invalid_json_raises(monkeypatch):
    """Server bug → text isn't valid JSON. We surface that as MCPCallError."""
    session = _FakeSession(result_payload="this-is-not-json-{")
    monkeypatch.setattr(
        "src.ai_core.agent.mcp_client._open_session",
        lambda url: _FakeCtx(session),
    )
    with pytest.raises(MCPCallError, match="invalid JSON"):
        await call_mcp_tool("lookup_cve", {"query": "broken"})
