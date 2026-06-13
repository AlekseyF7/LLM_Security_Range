#!/usr/bin/env bash
# ============================================================
# ingest.sh — загрузка документов в RAG (ChromaDB)
# Запускать ПОСЛЕ start_server.sh
# ============================================================
set -euo pipefail

echo "=== RAG Document Ingestion ==="
echo ""

# Check ChromaDB is reachable (host port 8200 maps to container port 8000)
CHROMA_HOST_PORT="${CHROMA_HOST_PORT:-8200}"
echo "[1/3] Checking ChromaDB on port ${CHROMA_HOST_PORT}..."
if ! curl -sf "http://127.0.0.1:${CHROMA_HOST_PORT}/api/v1/heartbeat" > /dev/null 2>&1; then
    echo "ERROR: ChromaDB is not running on port ${CHROMA_HOST_PORT}. Run ./start_server.sh first."
    exit 1
fi
echo "  ChromaDB is UP"

# Check Ollama has models
echo ""
echo "[2/3] Checking Ollama models..."
if ! docker exec llm-ollama ollama list 2>/dev/null | grep -q "bge-m3"; then
    echo "  Downloading embedding model (bge-m3)..."
    docker exec llm-ollama ollama pull bge-m3
fi
echo "  Embedding model: OK"

if ! docker exec llm-ollama ollama list 2>/dev/null | grep -q "granite4.1:8b"; then
    echo "  Downloading chat model (granite4.1:8b)..."
    docker exec llm-ollama ollama pull granite4.1:8b
fi
echo "  Chat model: OK"

# Verify Ollama embeddings work
echo ""
echo "[3/4] Verifying Ollama embeddings..."
EMBED_TEST=$(docker exec llm-api python -c "
import requests, json
resp = requests.post('http://ollama:11434/api/embeddings', json={'model': 'bge-m3', 'prompt': 'test'}, timeout=30)
data = resp.json()
emb = data.get('embedding', [])
print(f'OK dims={len(emb)}')
" 2>&1)
if echo "$EMBED_TEST" | grep -q "OK dims="; then
    echo "  Embeddings: $EMBED_TEST"
else
    echo "ERROR: Ollama embeddings not working!"
    echo "$EMBED_TEST"
    echo "Make sure 'bge-m3' model is pulled."
    exit 1
fi

# Clear old collection and re-ingest
echo ""
echo "[4/4] Ingesting documents into ChromaDB (clean)..."
docker exec llm-api python -c "
import chromadb, os, logging
logging.basicConfig(level=logging.INFO)
client = chromadb.HttpClient(host='chromadb', port=8000)
coll_name = os.getenv('CHROMA_COLLECTION', 'wiki_docs_v1')
try:
    client.delete_collection(coll_name)
    print(f'Deleted old collection {coll_name}')
except Exception:
    print(f'No existing collection {coll_name}')
from src.ai_core.rag.ingest import ingest_documents
ingest_documents()
"

echo ""
echo "=== Done! Documents loaded into RAG ==="
echo "Test: curl -s http://localhost:8000/api/v1/chat -H 'Content-Type: application/json' -d '{\"query\": \"Покажи данные Петрова\"}' | python3 -m json.tool"
