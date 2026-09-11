"""Fast, in-process tests for the Kubernetes/HTTP deployment routes.

These exercise the same Starlette routes as tests/integration/test_http_server.py,
but drive the ASGI app directly over an in-memory transport instead of spawning a
subprocess and a real TCP server. No network, Docker, or API token required, so
they run on every test invocation instead of being skipped.
"""

from collections.abc import AsyncIterator

import httpx
import pytest

import deployment.app  # noqa: F401 - registers custom routes on the shared mcp instance
from datawrapper_mcp.server import mcp


@pytest.fixture
async def app_client() -> AsyncIterator[httpx.AsyncClient]:
    """An httpx client wired directly to the MCP server's ASGI app.

    The routes under test (health check, discovery) are plain Starlette routes
    that don't touch the MCP session manager, so there's no need to run the
    app's lifespan (which owns that manager's task group) just to test them.
    """
    app = mcp.http_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_health_check(app_client):
    response = await app_client.get("/healthz")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "datawrapper-mcp"


async def test_well_known_mcp_json(app_client):
    response = await app_client.get("/.well-known/mcp.json")

    assert response.status_code == 200
    data = response.json()
    mcp_info = data["mcp"]
    assert mcp_info["name"] == "datawrapper-mcp"
    assert mcp_info["endpoint"] == "/mcp"
    assert isinstance(mcp_info["versions"], list)
    assert len(mcp_info["versions"]) > 0
    assert mcp_info["capabilities"] == {
        "tools": True,
        "resources": True,
        "apps": True,
    }


async def test_invalid_route_returns_404(app_client):
    response = await app_client.get("/invalid-route")

    assert response.status_code == 404


async def test_server_responds_to_repeated_requests(app_client):
    """Nothing about health checks should be stateful across calls."""
    for _ in range(5):
        response = await app_client.get("/healthz")
        assert response.status_code == 200
