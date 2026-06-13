"""Entry point: runs the MCP CVE server over Streamable HTTP transport.

EN: FastMCP exposes .streamable_http_app as an ASGI application (either a
    property or a method depending on mcp version). We drive it through
    uvicorn directly — FastMCP.run() in mcp >= 1.0 does NOT accept host
    and port kwargs, those belong to the underlying ASGI server.

    Listens on 0.0.0.0:8800 by default. Override with env vars
    MCP_CVE_HOST / MCP_CVE_PORT (docker compose sets them explicitly).

RU: FastMCP.run() не принимает host/port — это аргументы uvicorn.
    Поэтому берём mcp.streamable_http_app (ASGI-приложение) и поднимаем
    через uvicorn явно.
"""

from __future__ import annotations

import logging
import os

import uvicorn

from src.mcp_cve_server.server import mcp

logger = logging.getLogger("mcp_cve_server.main")


def _resolve_asgi_app():
    """streamable_http_app может быть property или method — поддержим оба."""
    app = mcp.streamable_http_app
    if callable(app):
        app = app()
    return app


def main() -> None:
    host = os.getenv("MCP_CVE_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_CVE_PORT", "8800"))
    app = _resolve_asgi_app()
    logger.info("Starting MCP CVE server on %s:%d (transport=streamable-http)", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
