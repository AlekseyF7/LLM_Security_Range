"""L3/RBAC visibility — pure summary helper + contextvar default.

Imports ONLY role_context (no chromadb) → runs on the dev machine.
"""
from src.ai_core.agent.role_context import rbac_summary, rbac_result_var


def test_rbac_summary_filtered():
    assert rbac_summary(rbac_blocked=True, hidden_count=2, role="anonymous") == {
        "filtered": True,
        "hidden": 2,
        "role": "anonymous",
    }


def test_rbac_summary_nothing_hidden():
    assert rbac_summary(rbac_blocked=False, hidden_count=0, role="admin") == {
        "filtered": False,
        "hidden": 0,
        "role": "admin",
    }


def test_rbac_result_var_default_is_none():
    # Fresh context → no L3 signal unless explicitly set by graph.run.
    assert rbac_result_var.get() is None
