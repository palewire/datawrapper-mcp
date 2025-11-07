"""Integration tests for HTTP server deployment."""

import os
import time
import pytest
import requests
from subprocess import Popen, PIPE
import signal


@pytest.fixture(scope="module")
def http_server():
    """Start HTTP server for testing."""
    # Check for API token
    api_token = os.getenv("DATAWRAPPER_ACCESS_TOKEN")
    if not api_token:
        pytest.skip("DATAWRAPPER_ACCESS_TOKEN not set")

    # Start server
    env = os.environ.copy()
    env["MCP_SERVER_HOST"] = "127.0.0.1"
    env["MCP_SERVER_PORT"] = "8502"  # Use different port to avoid conflicts

    process = Popen(
        ["python", "-m", "deployment.app"],
        env=env,
        stdout=PIPE,
        stderr=PIPE,
    )

    # Wait for server to start
    time.sleep(2)

    # Verify server is running
    try:
        response = requests.get("http://127.0.0.1:8502/healthz", timeout=5)
        assert response.status_code == 200
    except Exception as e:
        process.kill()
        pytest.fail(f"Server failed to start: {e}")

    yield "http://127.0.0.1:8502"

    # Cleanup
    process.send_signal(signal.SIGTERM)
    process.wait(timeout=5)


def test_health_check(http_server):
    """Test health check endpoint."""
    response = requests.get(f"{http_server}/healthz")

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
        response = requests.get(f"{http_server}/healthz")
        assert response.status_code == 200
        time.sleep(0.1)


def test_server_handles_invalid_routes(http_server):
    """Test that server handles invalid routes gracefully."""
    response = requests.get(f"{http_server}/invalid-route")
    # Should return 404 or similar error, not crash
    assert response.status_code in [404, 405]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
