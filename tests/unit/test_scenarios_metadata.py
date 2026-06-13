"""Every challenge must carry SP1 metadata: recommended_role / recommended_guards / hint.

Loads target_data/scenarios.yaml only (no chromadb) -> runs on the dev machine.
"""
from pathlib import Path
import yaml

_ROLES = {"anonymous", "user", "admin"}
_GUARDS = {"on", "off"}


def _scenarios():
    p = Path(__file__).resolve().parents[2] / "target_data" / "scenarios.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))["scenarios"]


def test_every_challenge_has_sp1_metadata():
    missing = []
    for s in _scenarios():
        sid = s.get("id", "?")
        role = s.get("recommended_role")
        guards = s.get("recommended_guards")
        hint = s.get("hint")
        if role not in _ROLES:
            missing.append(f"{sid}: recommended_role={role!r}")
        if guards not in _GUARDS:
            missing.append(f"{sid}: recommended_guards={guards!r}")
        if not (isinstance(hint, str) and hint.strip()):
            missing.append(f"{sid}: hint empty")
    assert not missing, "SP1 metadata problems:\n" + "\n".join(missing)


def test_no_legacy_user_role_field():
    # TOOL-001 used `user_role`; it must be migrated to recommended_role.
    leftovers = [s["id"] for s in _scenarios() if "user_role" in s]
    assert not leftovers, f"legacy user_role still present on: {leftovers}"
