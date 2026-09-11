"""Integration tests for HTTP server deployment.

These start the real `deployment.app` module as a subprocess and talk to it
over a real TCP socket, unlike tests/test_deployment.py which drives the ASGI
app in-process. They don't need a real Datawrapper API token: the routes
under test (health check, discovery) never call the Datawrapper API, so a
placeholder token is enough to let the server start.
"""

import os
from subprocess import PIPE, Popen

import pytest
import requests

from tests.integration.conftest import free_port, wait_until_ready

# Marked "integration" so CI runs it once instead of once per Python version.
pytestmark = pytest.mark.integration

STARTUP_TIMEOUT = 15


@pytest.fixture(scope="module")
def http_server():
    """Start HTTP server for testing."""
    port = free_port()
    env = os.environ.copy()
    env["MCP_SERVER_HOST"] = "127.0.0.1"
    env["MCP_SERVER_PORT"] = str(port)
    env.setdefault("DATAWRAPPER_ACCESS_TOKEN", "placeholder-token-not-used")

    process = Popen(
        ["python", "-m", "deployment.app"],
        env=env,
        stdout=PIPE,
        stderr=PIPE,
    )

    base_url = f"http://127.0.0.1:{port}"
    try:
        wait_until_ready(f"{base_url}/healthz", STARTUP_TIMEOUT)
    except TimeoutError:
        process.kill()
        stdout, stderr = process.communicate(timeout=5)
        pytest.fail(
            f"Server failed to start on port {port}.\n"
            f"stdout: {stdout.decode(errors='replace')}\n"
            f"stderr: {stderr.decode(errors='replace')}"
        )

    yield base_url

    process.terminate()
    try:
        process.wait(timeout=5)
    except Exception:
        process.kill()
        process.wait(timeout=5)


def test_health_check(http_server):
    """Test health check endpoint."""
    response = requests.get(f"{http_server}/healthz", timeout=5)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "datawrapper-mcp"


def test_sse_endpoint_exists(http_server):
    """Test that SSE endpoint is available."""
    # SSE endpoint should accept connections
    # We don't test the full MCP protocol here, just that the endpoint exists
    try:
        response = requests.get(
            f"{http_server}/sse",
            headers={"Accept": "text/event-stream"},
            timeout=2,
            stream=True,
        )
        # Should get a response (even if it's waiting for MCP messages)
        assert response.status_code in [200, 400, 404]
    except requests.exceptions.ReadTimeout:
        # Timeout is expected for SSE connections
        pass


def test_server_responds_to_requests(http_server):
    """Test that server is responsive."""
    # Make multiple health check requests
    for _ in range(5):
        response = requests.get(f"{http_server}/healthz", timeout=5)
        assert response.status_code == 200


def test_well_known_mcp_json(http_server):
    """Test .well-known/mcp.json discovery endpoint."""
    response = requests.get(f"{http_server}/.well-known/mcp.json", timeout=5)

    assert response.status_code == 200
    data = response.json()
    assert "mcp" in data
    mcp = data["mcp"]
    assert mcp["name"] == "datawrapper-mcp"
    assert mcp["endpoint"] == "/mcp"
    assert isinstance(mcp["versions"], list)
    assert len(mcp["versions"]) > 0
    assert mcp["capabilities"]["tools"] is True
    assert mcp["capabilities"]["resources"] is True
    assert mcp["capabilities"]["apps"] is True


def test_server_handles_invalid_routes(http_server):
    """Test that server handles invalid routes gracefully."""
    response = requests.get(f"{http_server}/invalid-route", timeout=5)
    # Should return 404 or similar error, not crash
    assert response.status_code in [404, 405]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
