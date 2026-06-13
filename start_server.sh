#!/usr/bin/env bash
# ============================================================
# start_server.sh — запуск всей инфраструктуры на Ubuntu
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/infra"

echo "=== LLM Security Server ==="
echo ""

# Load .env for display
source .env 2>/dev/null || true
TARGET_IP="${TARGET_IP:-$(hostname -I | awk '{print $1}')}"

echo "[1/4] Pulling Docker images..."
docker compose pull

echo ""
echo "[2/4] Building containers..."
docker compose build

echo ""
echo "[3/4] Starting all services..."
docker compose up -d

echo ""
echo "[4/4] Waiting for services..."

# Wait for API (60s)
API_OK=false
for i in $(seq 1 30); do
    if curl -s "http://localhost:${API_PORT:-8000}/health" 2>/dev/null | grep -q "ok"; then
        echo "  API:      http://${TARGET_IP}:${API_PORT:-8000}/docs  [OK]"
        API_OK=true
        break
    fi
    sleep 2
done
if [ "$API_OK" = false ]; then
    echo "  API:      не ответил за 60с"
    echo "            Логи: docker compose logs api"
fi

# Wait for Langfuse (180s — первый запуск требует миграций БД)
echo "  Langfuse: ожидание (первый запуск до 3 минут)..."
LANGFUSE_OK=false
for i in $(seq 1 90); do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -L \
        "http://localhost:${LANGFUSE_PORT:-3000}" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]; then
        echo "  Langfuse: http://${TARGET_IP}:${LANGFUSE_PORT:-3000}  [OK]"
        echo "            Логин: admin@demo.local / admin123"
        LANGFUSE_OK=true
        break
    fi
    if [ $((i % 10)) -eq 0 ]; then
        echo "  Langfuse: ещё ждём... ($((i*2))s)"
    fi
    sleep 2
done
if [ "$LANGFUSE_OK" = false ]; then
    echo "  Langfuse: не ответил за 180с"
    echo "            Статус: docker compose ps langfuse"
    echo "            Логи:   docker compose logs langfuse"
fi

echo ""
echo "=== Server is ready ==="
echo ""
echo "Red Team (Kali) command:"
echo "  TARGET_IP=${TARGET_IP} npx promptfoo eval --no-cache"
echo ""
echo "View logs:"
echo "  docker compose logs -f api"
echo ""
echo "Stop:"
echo "  docker compose down"
