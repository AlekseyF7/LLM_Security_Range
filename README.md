# LLM Security Range — Smart Wiki Cyber Range

Портфолио-версия киберполигона для проверки безопасности LLM/RAG-систем: защищенный корпоративный Wiki-ассистент с RAG, red-team сценариями, многослойными guardrails и наблюдаемостью.

> Примечание: это чистая portfolio-копия завершенного университетского командного проекта. Моя основная зона работы — AI/RAG часть: ingest документов, retrieval, LangGraph agent flow, role-aware retrieval filtering и интеграция агента в API pipeline.

## Что это за проект

**LLM Security Range** — изолированная среда для тестирования безопасности приложений на базе LLM. Целевая система — корпоративный Wiki-ассистент, который отвечает на вопросы через RAG-пайплайн. Вокруг него построены сценарии атак, guardrails, RBAC, canary-token leak detection, трассировка и web-интерфейс для демонстрации.

Главная идея безопасности: запускать одну и ту же систему с включенной и выключенной защитой, а затем сравнивать поведение на легитимных запросах и атаках.

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

## Ключевые возможности

- RAG-based корпоративный Wiki-ассистент.
- FastAPI gateway со стабильным chat contract.
- LangGraph agent flow: `classify_intent -> rag_search -> generate_answer -> format_response`.
- Векторное хранилище ChromaDB и локальные модели через Ollama.
- Role-based retrieval filtering для ролей `anonymous`, `user` и `admin`.
- NeMo Guardrails для input/output проверок.
- Canary-token detection для indirect prompt injection и утечек system prompt.
- Behavioral monitoring с rate limits и отслеживанием jailbreak-попыток.
- MCP-based CVE lookup service, изолированный в Docker-сети.
- Langfuse observability: traces, spans и scores.
- Next.js web-интерфейс с Console, Lab и Dashboard.
- Promptfoo red-team evaluation suite, сопоставленный с OWASP LLM Top 10.

## Покрытые security-сценарии

- Direct prompt injection и jailbreak attempts.
- Indirect prompt injection через poisoned RAG documents.
- Sensitive data disclosure: credentials, API keys, PII, financial data.
- RBAC bypass attempts.
- Excessive agency / unsafe tool usage.
- XSS-like unsafe output handling.
- Rate-limit и repeated jailbreak behavior.
- Безопасный CVE lookup через controlled MCP tool.

## Мой вклад

Мой фокус был на AI engineering части системы:

- Собрал и интегрировал RAG ingestion и answer-generation pipeline.
- Подключил chat API к RAG/agent runtime.
- Работал над качеством retrieval и fallback behavior.
- Реализовал LangGraph agent skeleton с понятными стадиями pipeline.
- Добавил role-aware filtering, чтобы restricted RAG chunks не попадали в LLM context.
- Интегрировал L3 tool access control в agent flow.
- Добавил Langfuse observability для agent nodes и security decisions.
- Помог стабилизировать promptfoo/RAG evaluation scenarios.

## Технологический стек

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

## Навыки, которые я оттачивал

- RAG architecture и document ingestion.
- Vector search и retrieval filtering.
- LLM agent design с LangGraph.
- LLM application security.
- Защита от prompt injection и indirect RAG injection.
- RBAC для AI tools и retrieved context.
- Observability для LLM-систем.
- API design на FastAPI.
- Docker-based локальная AI-инфраструктура.
- Automated red-team evaluation.

## Под какие роли подходит проект

Этот проект лучше всего подходит для позиций:

- Junior AI Engineer
- LLM Engineer
- Python Backend Developer with AI focus
- RAG Engineer
- AI Security Engineer
- MLOps / AI Platform Junior

## Быстрый запуск

Скопировать шаблон окружения:

```bash
cd infra
cp .env.example .env
```

Запустить сервисы:

```bash
docker compose up -d --build
```

Загрузить target documents в RAG:

```bash
./ingest.sh
```

Открыть:

- Web UI: `http://localhost:3001`
- FastAPI: `http://localhost:8000`
- Langfuse: `http://localhost:3000`

Запустить red-team evaluation:

```bash
TARGET_IP=localhost npx promptfoo eval --no-cache
```

## Важные примечания

- Документы в `target_data/secret_docs/` и `target_data/poisoned_docs/` содержат только fake secrets. Это тестовые фикстуры, а не реальные credentials.
- Role model использует заголовок `X-User-Role`, потому что это cyber range, а не production IAM system.
- Инфраструктура намеренно оставлена легкой: Docker Compose и локальные модели вместо Kubernetes, OAuth, Vault или полноценной production-платформы.

## Структура репозитория

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

## Лицензия

MIT
