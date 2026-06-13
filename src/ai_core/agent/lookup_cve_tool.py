r"""lookup_cve — agent tool wrapping the MCP CVE server.

EN: Validates user query (size + charset) before sending to MCP, then
    delegates to mcp_client.call_mcp_tool. Returns the server's list of
    CVE summaries. All errors wrapped as LookupCveError so the agent
    can render the canonical refusal phrase.

    Charset whitelist is intentionally narrow — it lets through letters,
    digits, dash, dot, comma, space (covers CVE IDs and product
    keywords) but blocks shell-meta characters (`;|<>$\` etc) that
    could indicate prompt-injection or shell-escape attempts.

RU: Валидация ввода и проксирование в MCP. Любая ошибка → LookupCveError.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from src.ai_core.agent.mcp_client import call_mcp_tool, MCPCallError

logger = logging.getLogger("ai_core.agent.lookup_cve")

_MAX_QUERY_LEN = 200
# Allowed: ASCII letters/digits, dash, underscore, dot, space, comma.
# Это покрывает "CVE-YYYY-NNNN" и обычные keywords типа "apache log4j 2.14".
# Намеренно НЕ пропускает: <>;|`$\(){}[]&*?!~"'  — shell/HTML meta.
_SAFE_QUERY_RE = re.compile(r"^[\w\-\.\s,]+$")


class LookupCveError(RuntimeError):
    """Raised on validation or transport failure."""


def _validate(query: str) -> str:
    q = (query or "").strip()
    if not q:
        raise LookupCveError("Query is empty.")
    if len(q) > _MAX_QUERY_LEN:
        raise LookupCveError(f"Query too long (>{_MAX_QUERY_LEN} chars).")
    if not _SAFE_QUERY_RE.match(q):
        raise LookupCveError("Query contains unsupported characters.")
    return q


async def lookup_cve(query: str) -> list[dict[str, Any]]:
    """Look up CVEs via the MCP CVE server. Returns up to 5 entries.

    Args:
        query: either a CVE ID like 'CVE-2021-44228', or a keyword like
               'log4j' / 'kubernetes RCE'. Validated against length and
               charset before sending.

    Returns:
        List of dicts (id, description, cvss_base_score, published).
        Empty list if nothing matched.

    Raises:
        LookupCveError: on validation failure or MCP transport error.
    """
    q = _validate(query)
    try:
        result = await call_mcp_tool("lookup_cve", {"query": q})
    except MCPCallError as exc:
        raise LookupCveError(f"MCP CVE lookup failed: {exc}") from exc
    logger.info("lookup_cve OK | query=%r results=%d", q[:80], len(result))
    return result
