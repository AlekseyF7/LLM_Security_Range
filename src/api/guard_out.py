"""GuardOut — LEGACY output response filter.

DEPRECATED:
  Replaced by NeMo Guardrails via `src.api.guardrails_runtime`.
  Kept as fallback for hosts without `nemoguardrails`. Called from
  `guardrails_runtime._legacy_turn`; not used by `main.py` directly.
"""

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger("api.guard_out")

_XSS_PATTERN = re.compile(r"<\s*/?\s*script", re.IGNORECASE)
_SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_SNILS_PATTERN = re.compile(r"\b\d{3}-\d{3}-\d{3}\s?\d{2}\b")
_CARD_PATTERN = re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b")
_PASSWORD_PATTERN = re.compile(
    r"(?:пароль|password|pass|pwd|ключ|key)\b.{0,40}?(?:[:=\-–—]|is|это)\s*[`\"']?\S{4,}",
    re.IGNORECASE,
)

@dataclass
class GuardResult:
    passed: bool
    reason: str | None = None

def check_output(text: str, *, trace=None) -> GuardResult:
    reasons: list[str] = []

    if _XSS_PATTERN.search(text):
        reasons.append("XSS: <script> tag detected")
    if _SSN_PATTERN.search(text):
        reasons.append("PII: SSN pattern detected")
    if _SNILS_PATTERN.search(text):
        reasons.append("PII: SNILS pattern detected")
    if _CARD_PATTERN.search(text):
        reasons.append("PII: credit card number detected")
    if _PASSWORD_PATTERN.search(text):
        reasons.append("CREDENTIAL: password/key pattern detected")

    passed = len(reasons) == 0
    reason = None if passed else "; ".join(reasons)

    if trace is not None:
        try:
            trace.span(
                name="guard_out",
                input={"text": text[:500]},
                output={"passed": passed, "reason": reason},
            )
        except Exception as exc:
            logger.warning("Failed to log guard_out span: %s", exc)

    if not passed:
        logger.warning("GuardOut BLOCKED | reason=%s", reason)
    else:
        logger.debug("GuardOut PASSED")

    return GuardResult(passed=passed, reason=reason)