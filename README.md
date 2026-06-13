# LLM Security Range — Smart Wiki Cyber Range

Portfolio version of an LLM security cyber range: a protected corporate Wiki assistant with RAG, red-team scenarios, multi-layer guardrails and observability.

> Note: this repository is a clean portfolio copy of a completed university team project. My main area of work was the AI/RAG part: document ingestion, retrieval, LangGraph agent flow, role-aware retrieval filtering and integration of the agent into the API pipeline.

## What This Project Is

**LLM Security Range** is an isolated environment for testing the security of LLM-based applications. The target system is a corporate Wiki assistant that answers questions using a RAG pipeline. Around it, the project includes attack scenarios, guardrails, RBAC, canary-token leak detection, tracing and a web UI for demonstrations.

The main security idea is simple: run the same system with protection enabled and disabled, then compare behavior on legitimate requests and attacks.

```text
User / Kali
    |
    v
FastAPI Gateway
    |
    |-- L1: Input Guardrails
    |-- L2: Behavioral Monitoring
    |
    v
LangGraph Agent
    |
    |-- RAG Search -> ChromaDB
    |-- L3: Role-Based Retrieval Filtering
    |-- Ollama LLM
    |-- MCP CVE Tool -> NVD
    |
    v
L4: Output Guardrails + Canary Detection
    |
    v
Langfuse Trace + Web UI Result
```

## Key Features

- RAG-based corporate Wiki assistant.
- FastAPI gateway with stable chat contract.
- LangGraph agent flow: `classify_intent -> rag_search -> generate_answer -> format_response`.
- ChromaDB vector store and Ollama-based local models.
- Role-based retrieval filtering for `anonymous`, `user` and `admin`.
- NeMo Guardrails for input and output checks.
- Canary-token detection for indirect prompt injection and system-prompt leakage.
- Behavioral monitoring with rate limits and jailbreak attempt tracking.
- MCP-based CVE lookup service isolated in a Docker network.
- Langfuse observability with traces, spans and scores.
- Next.js web interface with Console, Lab and Dashboard.
- Promptfoo red-team evaluation suite mapped to OWASP LLM Top 10.

## Security Scenarios Covered

- Direct prompt injection and jailbreak attempts.
- Indirect prompt injection through poisoned RAG documents.
- Sensitive data disclosure: credentials, API keys, PII, financial data.
- RBAC bypass attempts.
- Excessive agency / unsafe tool usage.
- XSS-like unsafe output handling.
- Rate-limit and repeated jailbreak behavior.
- Safe CVE lookup through a controlled MCP tool.

## My Contribution

My focus was the AI engineering part of the system:

- Built and integrated the RAG ingestion and answer-generation pipeline.
- Connected the chat API to the RAG/agent runtime.
- Worked on retrieval quality and fallback behavior.
- Implemented the LangGraph agent skeleton with clear pipeline stages.
- Added role-aware filtering so restricted RAG chunks do not reach the LLM context.
- Integrated L3 tool access control into the agent flow.
- Added Langfuse observability for agent nodes and security decisions.
- Helped stabilize promptfoo/RAG evaluation scenarios.

## Tech Stack

### Backend / AI

- Python
- FastAPI
- LangGraph
- ChromaDB
- Ollama
- NeMo Guardrails
- Langfuse
- MCP
- Pydantic
- Pytest

### Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS

### Infrastructure / Evaluation

- Docker Compose
- PostgreSQL
- Promptfoo
- Red-team scripts
- GitHub Actions experiments

## Skills Practiced

- RAG architecture and document ingestion.
- Vector search and retrieval filtering.
- LLM agent design with LangGraph.
- LLM application security.
- Prompt injection and indirect RAG injection defense.
- RBAC for AI tools and retrieved context.
- Observability for LLM systems.
- API design with FastAPI.
- Docker-based local AI infrastructure.
- Automated red-team evaluation.

## Best Fit For

This project is most relevant for roles such as:

- Junior AI Engineer
- LLM Engineer
- Python Backend Developer with AI focus
- RAG Engineer
- AI Security Engineer
- MLOps / AI Platform Junior

## Quick Start

Copy environment template:

```bash
cd infra
cp .env.example .env
```

Start services:

```bash
docker compose up -d --build
```

Ingest target documents:

```bash
./ingest.sh
```

Open:

- Web UI: `http://localhost:3001`
- FastAPI: `http://localhost:8000`
- Langfuse: `http://localhost:3000`

Run red-team eval:

```bash
TARGET_IP=localhost npx promptfoo eval --no-cache
```

## Important Notes

- Documents in `target_data/secret_docs/` and `target_data/poisoned_docs/` contain fake secrets only. They are test fixtures, not real credentials.
- The role model uses `X-User-Role` headers because this is a cyber range, not a production IAM system.
- The project intentionally keeps infrastructure lightweight: Docker Compose and local models instead of Kubernetes, OAuth, Vault or a full production platform.

## Repository Structure

```text
src/api/                 FastAPI gateway, guardrails runtime, status endpoints
src/ai_core/agent/       LangGraph agent, RBAC tools, MCP tools
src/ai_core/rag/         RAG ingestion and LLM calls
src/ai_core/guardrails/  NeMo Guardrails configuration
src/mcp_cve_server/      MCP service for CVE lookup
target_data/             Fake corporate docs, poisoned docs, scenarios
red_team/                Red-team scripts and multi-turn tests
web/                     Next.js UI
infra/                   Docker Compose and service Dockerfiles
tests/                   Unit tests
```

## License

MIT
