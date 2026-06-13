#!/bin/bash
# Полный прогон всех Red Team тестов

set -e

echo "🔴 RED TEAM FULL TEST SUITE"
echo "============================"

# 1. Single-turn тесты через promptfoo
echo ""
echo "📊 ШАГ 1/3: Single-turn тесты (promptfoo)"
echo "-------------------------------------------"
GUARDRAILS_ENABLED=true npx promptfoo eval --output red_team/results/promptfoo_guards_on.json
GUARDRAILS_ENABLED=false npx promptfoo eval --output red_team/results/promptfoo_guards_off.json

# 2. Multi-turn тесты через LangGraph
echo ""
echo "🔄 ШАГ 2/3: Multi-turn тесты (LangGraph)"
echo "-------------------------------------------"
python red_team/run_multi_turn.py --guardrails on --verbose
python red_team/run_multi_turn.py --guardrails off --verbose

# 3. Генерация сводного отчёта
echo ""
echo "📈 ШАГ 3/3: Генерация отчёта"
echo "-------------------------------------------"
python red_team/generate_combined_report.py

echo ""
echo "✅ Все тесты завершены!"
echo "📁 Результаты: red_team/results/"
echo "📊 Отчёт: red_team/reports/combined_report.html"
