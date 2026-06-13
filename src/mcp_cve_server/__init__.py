"""Mini MCP server that exposes one tool: lookup_cve.

EN: Wraps the public NVD REST API. Runs in its own docker container
    (`llm-mcp-cve`) over Streamable HTTP transport on port 8800.
    The api container talks to it through src/ai_core/agent/mcp_client.py.

    Why a separate service: keeps MCP attack surface isolated from the
    main agent (SSRF / response-injection / DoS tests target this
    process specifically), and the in-container subprocess pattern is
    fragile across NeMo / LangGraph event-loops.

RU: Отдельный MCP-сервис в docker-compose. Изоляция от агента +
    проще тестировать атаки на самом MCP.
"""
