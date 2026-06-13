"""Utility functions for LangGraph testing."""

import time
import json
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime


def generate_conversation_id(scenario_id: str) -> str:
    """Generate unique conversation ID."""
    timestamp = int(time.time() * 1000)
    unique_hash = hashlib.md5(f"{scenario_id}_{timestamp}".encode()).hexdigest()[:8]
    return f"redteam_{scenario_id}_{unique_hash}"


def format_latency(ms: float) -> str:
    """Format latency for display."""
    if ms < 1000:
        return f"{ms:.0f}ms"
    return f"{ms/1000:.2f}s"


def save_result(result: Dict[str, Any], filepath: str):
    """Save test result to JSON."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


def load_scenarios(filepath: str) -> Dict[str, Any]:
    """Load scenarios from YAML file."""
    import yaml
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class Colors:
    """Terminal colors for pretty output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
