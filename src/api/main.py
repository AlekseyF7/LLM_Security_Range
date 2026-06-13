"""FastAPI gateway — Smart Wiki LLM SecOps cyber range.

Responsibilities of this gateway:
- X-User-Role extraction via `Depends(get_role)` (no JWT — cyber range).
- GUARDRAILS_ENABLED toggle: bypasses NeMo entirely for demo mode.
- slowapi rate-limit (60 req/min per IP) + behavioral temp-block.
- NeMo Guardrails integration via `src.api.guardrails_runtime`.
- GET /api/v1/system/status for the UI banner.
- Langfuse trace + spans + scores on every layer decision.

This file only delegates through `guardrails_runtime.run_chat_turn`,
which in turn invokes `agent_runner.run_agent`.
"""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.api.deps import Role, get_role, guardrails_enabled
from src.api.guardrails_runtime import GuardDecision, run_chat_turn, runtime_name
from src.api.langfuse_logger import create_trace, flush, md_block, trace_id as _trace_id
from src.api.rate_limit import (
    install_rate_limit,
    is_temp_blocked,
    limiter,
    record_jailbreak_attempt,
)
from src.api.system_status import router as system_status_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("api.main")

app = FastAPI(
    title="Smart Wiki API Gateway",
    version="0.2.0",
    description=(
        "Secure gateway: NeMo Guardrails (L1 input + L4 output) + "
        "tool access control (L3) + slowapi behavioral monitor (L2), "
        "full Langfuse tracing. GUARDRAILS_ENABLED toggle for demo."
    ),
)

# Cyber range — браузер ходит с http://localhost:3001 и
# http://<ubuntu>:3001 на http://localhost:8000 / http://<ubuntu>:8000.
# Без CORS fetch падает с "Failed to fetch" в консоли браузера.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Wire slowapi (no-op if slowapi isn't installed locally).
install_rate_limit(app)

# /api/v1/system/status — consumed by UI banner.
app.include_router(system_status_router)


# ---------------------------------------------------------------------------
# Schemas (stable contract — promptfoo tests depend on this shape)
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    query: str
    mode: str = "chat"


class ChatResponse(BaseModel):
    answer: str
    blocked: bool = False
    guard_message: str | None = None
    # Plumbed through to the UI so each message can deep-link into Langfuse.
    # None when Langfuse is unavailable or the trace couldn't be created.
    trace_id: str | None = None
    # L3/RBAC visibility for the UI chip: {"filtered","hidden","role"} | None.
    # None when the agent never retrieved (e.g. L1 input block). ADDITIVE field —
    # promptfoo / isChatResponseShape assert on answer/blocked/guard_message only.
    rbac: dict | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/chat", response_model=ChatResponse)
@limiter.limit("60/minute")
async def chat(
    request: Request,  # required by slowapi
    payload: ChatRequest,
    role: Role = Depends(get_role),
) -> ChatResponse:
    client_ip = _client_ip(request)

    trace = create_trace(
        name="chat_request",
        input=md_block(
            {"query": payload.query, "mode": payload.mode},
            title="User request",
        ),
        metadata={
            "role": role,
            "client_ip": client_ip,
            "guardrails_enabled": guardrails_enabled(),
            "runtime": runtime_name(),
        },
    )

    # ----- L2: behavioral temp-block check -----
    behavioral = is_temp_blocked(client_ip)
    if behavioral.temp_blocked:
        reason = (
            f"IP temporarily blocked for {behavioral.seconds_remaining}s "
            "(too many jailbreak attempts)."
        )
        _log_guard_decision(
            trace,
            GuardDecision(
                layer="L2_behavioral",
                rail="temp_block",
                allowed=False,
                reason=reason,
                score=1.0,
            ),
        )
        _finalize_trace(trace, {"blocked": True, "layer": "L2_behavioral", "reason": reason})
        raise HTTPException(
            status_code=429,
            detail=ChatResponse(
                answer="", blocked=True, guard_message=reason, trace_id=_trace_id(trace),
            ).model_dump(),
        )

    # ----- Run the guarded turn (L1 + agent + L3 + L4 depending on config) -----
    # parent_trace_id привязывает агентские spans под этот chat-trace в Langfuse —
    # один HTTP-запрос = один root-trace с вложенными observations, а не два
    # параллельных trace (chat + agent).
    try:
        turn = await run_chat_turn(
            query=payload.query,
            role=role,
            parent_trace_id=_trace_id(trace),
        )
    except Exception as exc:
        reason = f"Chat pipeline crashed: {type(exc).__name__}: {exc}"
        logger.exception(reason)
        _finalize_trace(trace, {"blocked": True, "reason": reason})
        raise HTTPException(
            status_code=500,
            detail=ChatResponse(
                answer="", blocked=True, guard_message=reason, trace_id=_trace_id(trace),
            ).model_dump(),
        )

    for decision in turn.decisions:
        _log_guard_decision(trace, decision)

    # Behavioral counter: if L1 (input) blocked, record a jailbreak attempt.
    if turn.blocked and turn.blocked_layer == "L1_input":
        status = record_jailbreak_attempt(client_ip)
        if status.temp_blocked:
            _log_guard_decision(
                trace,
                GuardDecision(
                    layer="L2_behavioral",
                    rail="threshold_exceeded",
                    allowed=False,
                    reason=f"{status.attempts_in_window} attempts in window → 5min block",
                    score=1.0,
                ),
            )

    response = ChatResponse(
        answer=turn.answer,
        blocked=turn.blocked,
        guard_message=turn.guard_message,
        trace_id=_trace_id(trace),
        rbac=turn.rbac,
    )

    _finalize_trace(
        trace,
        {
            **response.model_dump(),
            "blocked_layer": turn.blocked_layer,
            "decisions": [_decision_to_dict(d) for d in turn.decisions],
        },
    )

    if turn.blocked and turn.blocked_layer == "L1_input":
        # Give promptfoo tests a consistent signal: L1 block = 403.
        raise HTTPException(status_code=403, detail=response.model_dump())

    return response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return "unknown"


def _decision_to_dict(d: GuardDecision) -> dict:
    return {
        "layer": d.layer,
        "rail": d.rail,
        "allowed": d.allowed,
        "reason": d.reason,
        "score": d.score,
    }


def _log_guard_decision(trace, decision: GuardDecision) -> None:
    """Emit span + score for a single layer's decision."""
    if trace is None:
        return
    try:
        trace.span(
            name=f"guard.{decision.layer}",
            input=md_block({"rail": decision.rail}, title=f"{decision.layer} check"),
            output=md_block(
                {
                    "allowed": decision.allowed,
                    "reason": decision.reason or "_(no reason)_",
                    "score": decision.score,
                },
                title="Decision",
            ),
        )
    except Exception as exc:
        logger.warning("Failed to log guard span %s: %s", decision.layer, exc)

    # Langfuse scores API is available on real traces but not on DummyTrace;
    # wrap every call to survive both paths.
    score_method = getattr(trace, "score", None)
    if callable(score_method):
        try:
            score_method(
                name=decision.layer,
                value=decision.score,
                comment=decision.reason or decision.rail,
            )
        except Exception as exc:
            logger.debug("Skipping trace.score (%s): %s", decision.layer, exc)


def _finalize_trace(trace, output: dict) -> None:
    if trace is not None:
        try:
            trace.update(output=md_block(output, title="Final response"))
        except Exception as exc:
            logger.warning("Failed to update trace output: %s", exc)
    flush()
