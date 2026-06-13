"""LangGraph agent package.

The agent runs the 4-node graph:
    classify_intent → tool: rag_search (RBAC) → generate_answer → format_response

Wire-up entrypoint: `register()` in `src.ai_core.agent.graph`. It is called
from `src.api.agent_runner.register_agent_handler` at API startup.
"""
