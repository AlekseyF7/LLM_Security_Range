"""Unit tests for ConfidentialityMap.allowed_for_chunk (Task 1.4).

allowed_for_chunk(role, source_file, chunk_level=...) extends RBAC to
honor per-chunk metadata level. Critical for user-uploaded docs (from
add_document tool), which carry their level in chunk.metadata.level
instead of being registered in confidentiality_map.yaml.
"""

from src.ai_core.agent.confidentiality import ConfidentialityMap, DocMeta


def _map() -> ConfidentialityMap:
    """Build a minimal map covering 1 known doc + standard rbac."""
    return ConfidentialityMap(
        documents={
            "secret_docs/policy_vpn.md": DocMeta(
                level="public", owner="it", canary=None, poisoned=False, contains=None,
            ),
        },
        rbac={
            "anonymous": ["public"],
            "user": ["public", "internal"],
            "admin": ["public", "internal", "restricted"],
        },
        default_level="restricted",
    )


def test_allowed_for_chunk_uses_metadata_level_when_provided():
    """Unknown source_file but chunk_level=internal → user can see, anonymous can't."""
    cmap = _map()
    assert cmap.allowed_for_chunk(
        "user", "user_uploads/foo.md", chunk_level="internal"
    ) is True
    assert cmap.allowed_for_chunk(
        "anonymous", "user_uploads/foo.md", chunk_level="internal"
    ) is False


def test_allowed_for_chunk_fails_closed_when_metadata_missing():
    """Unknown source_file + no chunk_level → fall back to default_level (restricted).

    anonymous sees nothing; admin sees because 'restricted' is in admin's rbac.
    """
    cmap = _map()
    assert cmap.allowed_for_chunk(
        "anonymous", "user_uploads/foo.md", chunk_level=None
    ) is False
    assert cmap.allowed_for_chunk(
        "admin", "user_uploads/foo.md", chunk_level=None
    ) is True


def test_allowed_for_chunk_metadata_overrides_yaml_to_stricter():
    """If chunk metadata says 'restricted', YAML's 'public' setting is overridden.

    Use case: admin uploads sensitive content via add_document with level=restricted;
    that chunk must be hidden from non-admins regardless of any base-doc YAML rule.
    """
    cmap = _map()
    assert cmap.allowed_for_chunk(
        "anonymous", "secret_docs/policy_vpn.md", chunk_level="restricted"
    ) is False
    assert cmap.allowed_for_chunk(
        "admin", "secret_docs/policy_vpn.md", chunk_level="restricted"
    ) is True


def test_allowed_for_chunk_invalid_metadata_falls_back_to_yaml():
    """Bogus chunk_level value (typo) ignored — fall back to YAML map."""
    cmap = _map()
    # Bogus value — should NOT silently grant access
    assert cmap.allowed_for_chunk(
        "anonymous", "secret_docs/policy_vpn.md", chunk_level="top-secret"
    ) is True  # YAML says policy_vpn.md = public, anonymous sees it


def test_backwards_compat_allowed_for_unchanged():
    """Existing allowed_for(role, src) must keep working identically."""
    cmap = _map()
    assert cmap.allowed_for("anonymous", "secret_docs/policy_vpn.md") is True
    assert cmap.allowed_for("anonymous", "user_uploads/foo.md") is False
    assert cmap.allowed_for("admin", "user_uploads/foo.md") is True
