# Multi-Turn Red Team Testing

## Быстрый старт

```bash
# 1. Убедитесь, что API запущен
curl http://localhost:8000/api/v1/system/status

# 2. Запуск multi-turn тестов с защитой
python red_team/run_multi_turn.py --guardrails on --verbose

# 3. Запуск multi-turn тестов без защиты (демонстрация уязвимостей)
python red_team/run_multi_turn.py --guardrails off --verbose

# 4. Полный прогон всех тестов
bash red_team/run_all_tests.sh
