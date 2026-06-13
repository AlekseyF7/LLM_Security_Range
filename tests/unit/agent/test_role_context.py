"""Unit tests for src.ai_core.agent.role_context (shared role_var ContextVar)."""

import asyncio

from src.ai_core.agent.role_context import role_var, set_role


def test_default_role_is_anonymous():
    assert role_var.get() == "anonymous"


def test_set_role_yields_token():
    token = set_role("admin")
    try:
        assert role_var.get() == "admin"
    finally:
        role_var.reset(token)
    assert role_var.get() == "anonymous"


def test_role_isolated_across_async_tasks():
    """ContextVar is per-task — child task should see parent's set value."""

    async def child(expected):
        assert role_var.get() == expected

    async def parent():
        token = set_role("user")
        try:
            await child("user")
        finally:
            role_var.reset(token)

    asyncio.run(parent())
