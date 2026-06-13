#!/usr/bin/env python3
"""
Запуск multi-turn тестов через LangGraph.
Использование:
    python red_team/run_multi_turn.py [--url URL] [--scenarios FILE] [--guardrails on|off]
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from red_team.langgraph_tester import MultiTurnTester
from red_team.langgraph_tester.utils import load_scenarios, save_result, Colors


def main():
    parser = argparse.ArgumentParser(description="LangGraph Multi-Turn Red Team Tests")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--scenarios", default="red_team/scenarios/multi_turn_scenarios.yaml", 
                       help="Scenarios YAML file")
    parser.add_argument("--guardrails", choices=["on", "off"], default="on",
                       help="Enable/disable guardrails")
    parser.add_argument("--output", help="Output file for results")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    guardrails_enabled = args.guardrails == "on"
    
    print(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}🔴 RED TEAM MULTI-TURN TESTING{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"API: {args.url}")
    print(f"Guardrails: {Colors.OKGREEN if guardrails_enabled else Colors.WARNING}{args.guardrails.upper()}{Colors.ENDC}")
    print(f"Сценарии: {args.scenarios}")
    
    # Check API health
    tester = MultiTurnTester(
        base_url=args.url,
        guardrails_enabled=guardrails_enabled,
        verbose=args.verbose
    )
    
    health = tester.agent.health_check()
    if not health["available"]:
        print(f"\n{Colors.FAIL}❌ API недоступен: {health.get('error', 'Unknown error')}{Colors.ENDC}")
        sys.exit(1)
    
    print(f"{Colors.OKGREEN}✅ API доступен{Colors.ENDC}")
    
    # Load scenarios
    try:
        data = load_scenarios(args.scenarios)
        scenarios = data["scenarios"]
        print(f"Загружено сценариев: {len(scenarios)}")
    except Exception as e:
        print(f"{Colors.FAIL}❌ Ошибка загрузки сценариев: {e}{Colors.ENDC}")
        sys.exit(1)
    
    # Run all scenarios
    results = []
    passed_count = 0
    
    for scenario in scenarios:
        result = tester.run_scenario(scenario)
        results.append(result)
        if result.overall_passed:
            passed_count += 1
    
    # Final summary
    print(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}ФИНАЛЬНЫЙ ОТЧЁТ{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"Всего сценариев: {len(results)}")
    print(f"Успешно: {Colors.OKGREEN}{passed_count}{Colors.ENDC}")
    print(f"Провалено: {Colors.FAIL}{len(results) - passed_count}{Colors.ENDC}")
    print(f"Успешность: {passed_count/len(results)*100:.1f}%")
    
    # Detailed results
    print(f"\n{Colors.BOLD}Детализация:{Colors.ENDC}")
    for result in results:
        status = f"{Colors.OKGREEN}✅{Colors.ENDC}" if result.overall_passed else f"{Colors.FAIL}❌{Colors.ENDC}"
        print(f"  {status} {result.scenario_id}: {result.name}")
        print(f"      Ходы: {sum(result.passed_turns)}/{len(result.turns)} passed, {result.total_latency_ms:.0f}ms")
    
    # Save results
    if args.output:
        output_file = args.output
    else:
        mode = "guards_on" if guardrails_enabled else "guards_off"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"red_team/results/multi_turn_{mode}_{timestamp}.json"
    
    # Convert to dict for JSON serialization
    results_dict = []
    for r in results:
        results_dict.append({
            "scenario_id": r.scenario_id,
            "name": r.name,
            "description": r.description,
            "user_role": r.user_role,
            "guardrails_enabled": r.guardrails_enabled,
            "overall_passed": r.overall_passed,
            "passed_turns": r.passed_turns,
            "total_latency_ms": r.total_latency_ms,
            "conversation_id": r.conversation_id,
            "timestamp": r.timestamp,
            "turns": [
                {
                    "turn": t.turn,
                    "query": t.query,
                    "response": t.response[:300],
                    "blocked": t.blocked,
                    "block_layer": t.block_layer,
                    "intent": t.intent,
                    "latency_ms": t.latency_ms,
                    "trace_id": t.trace_id,
                    "status_code": t.status_code,
                    "error": t.error
                }
                for t in r.turns
            ]
        })
    
    save_result({
        "summary": {
            "total": len(results),
            "passed": passed_count,
            "failed": len(results) - passed_count,
            "success_rate": passed_count / len(results) * 100
        },
        "config": {
            "guardrails_enabled": guardrails_enabled,
            "api_url": args.url
        },
        "results": results_dict
    }, output_file)
    
    print(f"\n{Colors.OKGREEN}📁 Результаты сохранены: {output_file}{Colors.ENDC}")
    
    # Exit code
    sys.exit(0 if passed_count == len(results) else 1)


if __name__ == "__main__":
    main()
