"""Tests for surfacing DATAWRAPPER_MCP_INSTRUCTIONS to MCP clients."""

import importlib
import os

import pytest

import datawrapper_mcp.server as server_module


@pytest.fixture(autouse=True)
def _reset_server_module():
    """Reload the server module with a clean environment after each test."""
    yield
    os.environ.pop("DATAWRAPPER_MCP_INSTRUCTIONS", None)
    importlib.reload(server_module)


def test_instructions_set_from_env(monkeypatch):
    monkeypatch.setenv(
        "DATAWRAPPER_MCP_INSTRUCTIONS", "Every chart needs alt text and a slug."
    )

    reloaded = importlib.reload(server_module)

    assert reloaded.mcp.instructions == "Every chart needs alt text and a slug."


def test_instructions_default_to_none(monkeypatch):
    monkeypatch.delenv("DATAWRAPPER_MCP_INSTRUCTIONS", raising=False)

    reloaded = importlib.reload(server_module)

    assert reloaded.mcp.instructions is None
