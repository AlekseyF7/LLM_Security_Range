"""Pytest top-level conftest.

Loads pytest-asyncio plugin so async tests don't need explicit markers.
Mode = auto comes from pytest.ini.
"""

pytest_plugins = ("pytest_asyncio",)
