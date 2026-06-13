"""FastMCP server exposing one tool: lookup_cve.

EN: Single-tool MCP server, deliberately minimal — wraps NVD lookup.
    Run via `python -m src.mcp_cve_server` (see __main__.py) on Streamable
    HTTP transport. The api container's mcp_client.py connects through
    docker DNS (mcp-cve:8800).

RU: Минимальный MCP-сервер. Один tool: lookup_cve. Запуск через
    `python -m src.mcp_cve_server` (см. __main__.py).
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from src.mcp_cve_server.nvd_client import lookup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("mcp_cve_server")

mcp = FastMCP(
    name="cve-lookup",
    instructions=(
        "Look up CVE entries from the public NVD database. "
        "Accepts a CVE id (CVE-YYYY-NNNN) or a free-text keyword. "
        "Returns up to 5 vulnerabilities with id, short description, "
        "CVSS base score, and publication date."
    ),
    # EN: MCP's StreamableHTTP transport ships DNS-rebinding protection that
    #     rejects any Host header not in allowed_hosts (default: localhost),
    #     replying 421 Misdirected Request. The api container reaches us by the
    #     docker-DNS name `mcp-cve:8800`, which tripped that check so the call
    #     never even reached the tool. DNS-rebinding protection guards *browser*
    #     clients against a malicious page rebinding DNS to a localhost MCP
    #     server — irrelevant here: mcp-cve lives only on backend_net, its port
    #     is not published, and the sole caller is the api service over the
    #     internal docker network. Disable it so service-name calls work.
    # RU: Транспорт MCP по умолчанию режет Host-заголовок не из localhost
    #     (ответ 421). api ходит к нам по docker-DNS `mcp-cve:8800`. Защита от
    #     DNS-rebinding нужна браузерам; у нас сервис только в backend_net, порт
    #     наружу не проброшен — отключаем, чтобы вызовы по имени сервиса прошли.
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
)


@mcp.tool()
def lookup_cve(query: str) -> list[dict]:
    """Look up CVE entries by ID (CVE-YYYY-NNNN) or keyword.

    Args:
        query: a CVE ID (case-insensitive) like 'CVE-2021-44228', or
               a free-text keyword like 'log4j' / 'kubernetes RCE'.

    Returns:
        List of up to 5 dicts each with:
        - id: canonical CVE id
        - description: first 400 chars of the English description
        - cvss_base_score: numeric (as str) from CVSS v3.1/3.0/2 in priority order
        - published: ISO 8601 publication date
    """
    logger.info("lookup_cve tool called | query=%r", query[:120])
    return lookup(query)
