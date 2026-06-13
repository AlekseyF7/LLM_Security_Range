#!/usr/bin/env python3
"""Генерация сводного отчёта по всем тестам."""

import json
from pathlib import Path
from datetime import datetime


def generate_report():
    """Generate combined Red Team report."""
    
    results_dir = Path(__file__).parent / "results"
    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    # Load multi-turn results
    multi_turn_files = sorted(results_dir.glob("multi_turn_*.json"), reverse=True)
    
    report = {
        "title": "LLM SecOps Red Team Report",
        "generated": datetime.now().isoformat(),
        "sections": []
    }
    
    for file in multi_turn_files[:2]:  # Latest guards_on and guards_off
        with open(file, 'r') as f:
            data = json.load(f)
        
        mode = "guards_on" if "guards_on" in file.name else "guards_off"
        
        section = {
            "name": f"Multi-turn тесты ({mode})",
            "summary": data["summary"],
            "scenarios": []
        }
        
        for result in data["results"]:
            section["scenarios"].append({
                "id": result["scenario_id"],
                "name": result["name"],
                "passed": result["overall_passed"],
                "turns_passed": f"{sum(result['passed_turns'])}/{len(result['passed_turns'])}",
                "latency_ms": result["total_latency_ms"]
            })
        
        report["sections"].append(section)
    
    # Save JSON report
    json_file = reports_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"✅ Отчёт сохранён: {json_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("СВОДНЫЙ ОТЧЁТ")
    print("="*60)
    
    for section in report["sections"]:
        print(f"\n{section['name']}:")
        print(f"  Всего: {section['summary']['total']}")
        print(f"  Успешно: {section['summary']['passed']}")
        print(f"  Провалено: {section['summary']['failed']}")
        print(f"  Успешность: {section['summary']['success_rate']:.1f}%")


if __name__ == "__main__":
    generate_report()
