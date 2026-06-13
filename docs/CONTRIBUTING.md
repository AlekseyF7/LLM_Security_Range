# Smart Wiki — Contributing

Киберполигон для испытаний безопасности систем на основе LLM. Этот документ — как развернуть стенд, как устроен репозиторий и как контрибьютить. Описание архитектуры — в [architecture.md](architecture.md).

## Развёртывание (dev)

```bash
cd infra
cp .env.example .env          # подставить значения (.env в .gitignore — НЕ коммитить)
docker compose up -d --build
docker compose ps             # все сервисы healthy (langfuse — до 3 мин)
cd .. && ./ingest.sh          # загрузить target_data/ в ChromaDB
```

Локально без Docker:
```bash
PYTHONPATH=. uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --log-level debug
cd web && npm run dev         # фронтенд на :3001
```

## Структура репозитория

```text
src/
├── api/               # FastAPI шлюз: main.py, guardrails_runtime.py, rate_limit.py, system_status.py, deps.py
│   ├── guard_in.py    # legacy regex-фильтр (fallback)
│   └── guard_out.py   # legacy regex-фильтр (fallback)
├── ai_core/
│   ├── guardrails/    # NeMo config.yml / prompts.yml / rails.co (L1/L4)
│   ├── agent/         # LangGraph: graph.py, tools.py, confidentiality.py (L3), mcp_client.py, lookup_cve_tool.py
│   └── rag/           # ingest.py (ChromaDB + Ollama)
└── mcp_cve_server/    # FastMCP: tool lookup_cve → NVD (:8800)
web/                   # Next.js UI (:3001)
target_data/           # документы, poisoned_docs/, confidentiality_map.yaml, scenarios.yaml
red_team/              # multi-turn tester, behavioral, github-интеграция
infra/                 # docker-compose.yml, Dockerfile.{api,web,mcp_cve}, .env.example
docs/                  # architecture.md, demo_script.md, CONTRIBUTING.md
promptfooconfig.yaml   # OWASP LLM Top-10 eval (+ promptfoo_provider.py)
```

## Рабочий процесс Git

Feature Branch Workflow:

- `main` — стабильная ветка (защищена от прямых пушей).
- `dev` — интеграционная ветка; сюда сливаются готовые изменения.
- `feature/*` / `fix/*` / `chore/*` — задачи, ветвятся от `dev`.

Правила:
1. Новая задача — отдельная ветка от `dev`.
2. Коммиты — семантические: `feat:`, `fix:`, `docs:`, `infra:`, `chore:`, `test:`.
3. PR в `dev` с описанием контракта (что на вход, что на выход).
4. Code review перед merge.
5. В `main` сливаем `dev` после прогона тестов.

## Тесты

```bash
TARGET_IP=localhost npx promptfoo eval --no-cache   # ~73 теста по OWASP LLM Top-10
pytest                                              # unit (PYTHONPATH=. или внутри api-контейнера)
```

## Безопасность контента

В `target_data/secret_docs/` и `target_data/poisoned_docs/` — **намеренно фейковые** «секреты» и документы со скрытой инъекцией (тест-фикстуры). Реальные секреты в репозиторий не коммитим; `.env` — в `.gitignore`. Canary-токен (`CANARY_*` в `RAG_SYSTEM_PROMPT`) задаётся только локально.
