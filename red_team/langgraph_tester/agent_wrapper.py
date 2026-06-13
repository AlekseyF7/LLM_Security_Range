"""Wrapper for LangGraph agent API with multi-turn support."""

import requests
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import time


@dataclass
class TurnResult:
    """Result of a single conversation turn."""
    turn: int
    query: str
    response: str
    blocked: bool
    block_layer: Optional[str]
    intent: Optional[str]
    latency_ms: float
    conversation_id: str
    trace_id: Optional[str]
    status_code: int
    error: Optional[str] = None


class AgentWrapper:
    """Wrapper for LangGraph agent API."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: int = 30,
        verbose: bool = True
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.verbose = verbose
        self.session = requests.Session()
        
    def send_message(
        self,
        query: str,
        conversation_id: str,
        user_role: str = "anonymous",
        guardrails_enabled: bool = True,
        turn: int = 1
    ) -> TurnResult:
        """Send a message in the context of a conversation."""
        
        headers = {
            "Content-Type": "application/json",
            "X-User-Role": user_role
        }
        
        if not guardrails_enabled:
            headers["X-Guardrails-Enabled"] = "false"
        
        payload = {
            "query": query,
            "conversation_id": conversation_id,
            "user_role": user_role,
            "guardrails_enabled": guardrails_enabled,
            "turn": turn,
            "mode": "chat"
        }
        
        start_time = time.time()
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/chat",
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 403:
                data = response.json()
                detail = data.get("detail", {})
                
                return TurnResult(
                    turn=turn,
                    query=query,
                    response=detail.get("message", "Blocked by guard"),
                    blocked=True,
                    block_layer=detail.get("layer", "unknown"),
                    intent=None,
                    latency_ms=latency_ms,
                    conversation_id=conversation_id,
                    trace_id=data.get("trace_id"),
                    status_code=403
                )
            
            response.raise_for_status()
            data = response.json()
            
            return TurnResult(
                turn=turn,
                query=query,
                response=data.get("answer", ""),
                blocked=False,
                block_layer=None,
                intent=data.get("intent"),
                latency_ms=latency_ms,
                conversation_id=conversation_id,
                trace_id=data.get("trace_id"),
                status_code=200
            )
            
        except requests.Timeout:
            return TurnResult(
                turn=turn,
                query=query,
                response="",
                blocked=False,
                block_layer=None,
                intent=None,
                latency_ms=latency_ms,
                conversation_id=conversation_id,
                trace_id=None,
                status_code=408,
                error=f"Timeout after {self.timeout}s"
            )
            
        except requests.RequestException as e:
            return TurnResult(
                turn=turn,
                query=query,
                response="",
                blocked=False,
                block_layer=None,
                intent=None,
                latency_ms=latency_ms,
                conversation_id=conversation_id,
                trace_id=None,
                status_code=500,
                error=str(e)
            )
    
    def health_check(self) -> Dict[str, Any]:
        """Check if API is available."""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/system/status",
                timeout=5
            )
            return {
                "available": response.status_code == 200,
                "status_code": response.status_code,
                "data": response.json() if response.status_code == 200 else None
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e)
            }
