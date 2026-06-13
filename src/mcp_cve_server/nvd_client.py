"""NVD REST API client with simple LRU cache.

Public docs: https://nvd.nist.gov/developers/vulnerabilities
Endpoint:    https://services.nvd.nist.gov/rest/json/cves/2.0

EN: No API key — we hit the rate-limited public tier (5 req / 30s).
    LRU cache (256 entries) absorbs repeated queries during demo /
    red-team runs. If you need higher throughput, set NVD_API_KEY env
    and pass it via httpx headers.

RU: Без NVD_API_KEY (5 req/30s публичный rate-limit). 256-entry LRU
    кеш достаточен для демо. Для боевых сценариев нужен API-key.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Any

import httpx

logger = logging.getLogger("mcp_cve_server.nvd_client")

_NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
_CVE_ID_RE = re.compile(r"^CVE-\d{4}-\d{4,7}$", re.IGNORECASE)
_TIMEOUT = httpx.Timeout(15.0, connect=5.0)
_MAX_RESULTS = 5  # ограничиваем response size — иначе LLM-context раздуется


def _is_cve_id(query: str) -> bool:
    return bool(_CVE_ID_RE.match(query.strip()))


def _format_vuln(item: dict[str, Any]) -> dict[str, Any]:
    """Extract the few fields the agent actually needs from the NVD blob.

    NVD response is a multi-kilobyte JSON per CVE; squashing to 4 fields
    keeps the LLM context manageable AND limits the attack surface for
    output-handling injections inside descriptions.
    """
    cve = item.get("cve", {})
    cve_id = cve.get("id", "UNKNOWN")
    descs = cve.get("descriptions") or []
    en_desc = next((d.get("value", "") for d in descs if d.get("lang") == "en"), "")
    metrics = cve.get("metrics", {})
    cvss = ""
    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        bucket = metrics.get(key)
        if bucket:
            cvss = str(bucket[0].get("cvssData", {}).get("baseScore", ""))
            break
    return {
        "id": cve_id,
        "description": en_desc[:400],
        "cvss_base_score": cvss,
        "published": cve.get("published"),
    }


@lru_cache(maxsize=256)
def _fetch_raw(query: str) -> tuple[dict[str, Any], ...]:
    """Cached fetch. Returns a tuple so it's hashable for lru_cache."""
    params: dict[str, Any] = {"resultsPerPage": _MAX_RESULTS}
    if _is_cve_id(query):
        params["cveId"] = query.upper()
    else:
        # NVD rejects keywordSearch > ~120 chars
        params["keywordSearch"] = query[:120]
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.get(_NVD_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        logger.warning("NVD fetch failed | query=%r err=%s", query[:80], exc)
        return tuple()
    items = data.get("vulnerabilities", [])[:_MAX_RESULTS]
    return tuple(_format_vuln(it) for it in items)


def lookup(query: str) -> list[dict[str, Any]]:
    """Public entry point — returns up to 5 vulnerabilities matching query.

    Treats input as a CVE-id (CVE-YYYY-NNNN format) when it matches the
    regex, else as a keyword search. Empty query → empty list, no API call.
    """
    if not query or not query.strip():
        return []
    return list(_fetch_raw(query.strip()))
