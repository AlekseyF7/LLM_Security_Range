"""Async client for the MCP CVE server (streamable HTTP transport).

EN: Thin wrapper around mcp.ClientSession + streamablehttp_client.
    Single public function: call_mcp_tool(tool_name, arguments) — opens
    a session, calls the tool, parses the JSON-encoded text content,
    returns the result as a list of dicts (we wrap single-dict into a
    1-element list so callers don't branch).

    Errors of any kind (transport, JSON parse, unexpected type) are
    wrapped as MCPCallError so the agent layer can render the standard
    refusal phrase.

RU: Async-обёртка над mcp.ClientSession + streamable-HTTP-клиент.
    Один публичный метод call_mcp_tool. Любая ошибка → MCPCallError.
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

logger = logging.getLogger("ai_core.agent.mcp_client")


class MCPCallError(RuntimeError):
    """Raised on any failure of an MCP tool call (transport, parsing, type)."""


def _server_url() -> str:
    """Default to docker service DNS. Override via MCP_CVE_URL env."""
    return os.getenv("MCP_CVE_URL", "http://mcp-cve:8800/mcp")


@asynccontextmanager
async def _open_session(url: str):
    """Open a streamable-HTTP MCP session as an async context manager.

    EN: Yields an initialised mcp.ClientSession. The two underlying async
        contexts (streamable-HTTP transport + ClientSession) MUST be nested
        with real `async with` blocks inside ONE coroutine frame.
        streamablehttp_client runs an internal anyio task group with a
        background reader task; driving its __aenter__/__aexit__ manually
        across stored attributes (the previous _StreamableSession approach)
        tore that task group down out of frame and raised
        "athrow(): asynchronous generator is already running" → HTTP 500.
        Kept as a separate function (not inlined into call_mcp_tool) so
        tests can monkeypatch it with a fake async context manager.
    RU: Отдаёт готовую ClientSession. Оба вложенных async-контекста
        (transport + session) открываются настоящим `async with` в одном
        кадре корутины — иначе anyio task group рушится при teardown.
        Оставлено отдельной функцией ради monkeypatch в тестах.
    """
    # streamablehttp_client yields (read_stream, write_stream, _meta)
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
    """Call a tool on the MCP server. Returns parsed JSON payload as a list.

    Args:
        tool_name: registered MCP tool name (e.g. 'lookup_cve').
        arguments: kwargs passed to the tool.

    Returns:
        List of dicts (server's single-dict responses are wrapped to 1-element list).

    Raises:
        MCPCallError: on transport failure, invalid JSON, or unexpected type.
    """
    url = _server_url()
    logger.info("MCP call → %s tool=%s args_keys=%s", url, tool_name, list(arguments.keys()))
    try:
        async with _open_session(url) as session:
            result = await session.call_tool(tool_name, arguments=arguments)
    except Exception as exc:  # noqa: BLE001 — transport-level errors are not predictable
        raise MCPCallError(f"MCP transport failure: {exc}") from exc

    # FastMCP returns content as a list of TextContent objects;
    # the first is JSON-encoded result.
    content = getattr(result, "content", None) or []
    if not content:
        return []
    first = content[0]
    text = getattr(first, "text", "") or ""
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MCPCallError(f"MCP returned invalid JSON: {exc}") from exc

    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        return [parsed]
    raise MCPCallError(f"MCP returned unexpected type: {type(parsed).__name__}")
