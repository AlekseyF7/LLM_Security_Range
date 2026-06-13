"""Custom promptfoo provider for Smart Wiki API.

Normalizes both 200 / 403 / 429 responses into {"output": "<json string>"}
so that promptfoo asserts can do `JSON.parse(output).blocked` consistently.

Reads optional `role` from test `vars` and propagates it as the
`X-User-Role` header — required for LLM07 (RBAC) tests.

Env vars:
  TARGET_IP   — Ubuntu host IP (default: localhost). Example:
                  TARGET_IP=192.168.56.10 npx promptfoo eval
  API_PORT    — FastAPI port (default: 8000)

Example test in promptfooconfig.yaml:
  - vars: {query: "...", role: "user"}
"""

import json
import os
import requests


_VALID_ROLES = ("anonymous", "user", "admin")


def call_api(prompt, options, context):
    target_ip = os.getenv("TARGET_IP", "localhost")
    api_port = os.getenv("API_PORT", "8000")
    default_url = f"http://{target_ip}:{api_port}/api/v1/chat"
    url = options.get("config", {}).get("url", default_url)

    # promptfoo passes test vars through `context["vars"]`
    vars_ = (context or {}).get("vars") or {}
    repeat_n = vars_.get("repeat_n")
    repeat_char = vars_.get("repeat_char", "A")
    if repeat_n is not None:
        try:
            n = int(repeat_n)
            prompt = str(repeat_char) * n
        except Exception:
            pass

    # If role is omitted in a test, fall back to env-configurable default.
    # This keeps legacy tests deterministic while still allowing explicit
    # role overrides per scenario (LLM07).
    default_role = str(os.getenv("PROMPTFOO_DEFAULT_ROLE", "")).strip().lower()
    role = str(vars_.get("role", default_role)).strip().lower()
    headers = {"Content-Type": "application/json"}
    if role and role in _VALID_ROLES:
        headers["X-User-Role"] = role

    # mode can be overridden per test: vars: { mode: "rag" }.
    # Keeping default "chat" preserves backward compatibility.
    mode = str(vars_.get("mode", "chat")).strip().lower()
    if mode not in ("chat", "rag", "agent", "cot", "default"):
        mode = "chat"

    try:
        resp = requests.post(
            url,
            json={"query": prompt, "mode": mode},
            headers=headers,
            timeout=120,
        )
        # 403 (L1 GuardIn block) and 429 (L2 behavioral block) carry the same
        # ChatResponse shape inside `detail`. Normalize so asserts work the same way.
        if resp.status_code in (403, 429, 500):
            try:
                payload = resp.json()
            except ValueError:
                payload = {}
            detail = payload.get("detail") if isinstance(payload, dict) else None
            if detail is None:
                detail = {
                    "answer": "",
                    "blocked": True,
                    "guard_message": f"HTTP {resp.status_code} from API",
                }
            return {"output": json.dumps(detail, ensure_ascii=False)}

        resp.raise_for_status()
        return {"output": json.dumps(resp.json(), ensure_ascii=False)}
    except requests.RequestException as exc:
        return {"error": str(exc)}
