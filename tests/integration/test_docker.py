"""Integration tests for Docker deployment.

Docker is preinstalled on GitHub-hosted runners, so these run in CI too. They
don't need a real Datawrapper API token: the routes under test (health check,
discovery) never call the Datawrapper API, so a placeholder token is enough to
let the container start.
"""

import subprocess

import pytest
import requests

from tests.integration.conftest import free_port, wait_until_ready

# Building and starting a Docker image is much slower than the suite's
# default 60s timeout, so give this module's tests more room to run. Also
# marked "integration" so CI runs it once instead of once per Python version.
pytestmark = [pytest.mark.timeout(300), pytest.mark.integration]

CONTAINER_PORT = 8501
STARTUP_TIMEOUT = 30


@pytest.fixture(scope="module")
def docker_image():
    """Build Docker image for testing."""
    # Check if Docker is available
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("Docker not available")

    # Build image
    print("\nBuilding Docker image...")
    result = subprocess.run(
        ["docker", "build", "-t", "datawrapper-mcp:test", "."],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        pytest.fail(f"Docker build failed: {result.stderr}")

    yield "datawrapper-mcp:test"

    # Cleanup: remove test image
    subprocess.run(["docker", "rmi", "datawrapper-mcp:test"], capture_output=True)


@pytest.fixture(scope="module")
def docker_container(docker_image):
    """Run Docker container for testing."""
    host_port = free_port()

    # Start container
    print("\nStarting Docker container...")
    result = subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "-p",
            f"{host_port}:{CONTAINER_PORT}",
            "-e",
            "DATAWRAPPER_ACCESS_TOKEN=placeholder-token-not-used",
            "-e",
            "MCP_SERVER_HOST=0.0.0.0",
            "-e",
            f"MCP_SERVER_PORT={CONTAINER_PORT}",
            docker_image,
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        pytest.fail(f"Docker run failed: {result.stderr}")

    container_id = result.stdout.strip()
    base_url = f"http://localhost:{host_port}"

    try:
        wait_until_ready(f"{base_url}/healthz", STARTUP_TIMEOUT)
    except TimeoutError:
        logs = subprocess.run(
            ["docker", "logs", container_id], capture_output=True, text=True
        )
        subprocess.run(["docker", "rm", "-f", container_id], capture_output=True)
        pytest.fail(
            f"Container failed to become ready. Logs:\n{logs.stdout}\n{logs.stderr}"
        )

    yield base_url, container_id

    # Cleanup: stop and remove container
    subprocess.run(["docker", "stop", container_id], capture_output=True)
    subprocess.run(["docker", "rm", container_id], capture_output=True)


def test_docker_health_check(docker_container):
    """Test health check endpoint in Docker container."""
    base_url, _container_id = docker_container

    response = requests.get(f"{base_url}/healthz", timeout=10)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "datawrapper-mcp"


def test_docker_container_logs(docker_container):
    """Test that container logs show successful startup."""
    _base_url, container_id = docker_container

    result = subprocess.run(
        ["docker", "logs", container_id], capture_output=True, text=True
    )

    logs = result.stdout + result.stderr

    # Check for successful startup indicators
    # (Adjust these based on your actual log output)
    assert "error" not in logs.lower() or (
        "error" in logs.lower() and "0 errors" in logs.lower()
    )


def test_docker_container_running(docker_container):
    """Test that container stays running."""
    _base_url, container_id = docker_container

    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", container_id],
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "true"


def test_docker_sse_endpoint(docker_container):
    """Test that SSE endpoint is accessible in Docker."""
    base_url, _container_id = docker_container

    try:
        response = requests.get(
            f"{base_url}/sse",
            headers={"Accept": "text/event-stream"},
            timeout=2,
            stream=True,
        )
        # Should get a response (even if it's waiting for MCP messages)
        assert response.status_code in [200, 400, 404]
    except requests.exceptions.ReadTimeout:
        # Timeout is expected for SSE connections
        pass


def test_docker_well_known_mcp_json(docker_container):
    """Test .well-known/mcp.json discovery endpoint in Docker container."""
    base_url, _container_id = docker_container

    response = requests.get(f"{base_url}/.well-known/mcp.json", timeout=10)

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


def test_docker_multiple_requests(docker_container):
    """Test that Docker container handles multiple requests."""
    base_url, _container_id = docker_container

    for _ in range(10):
        response = requests.get(f"{base_url}/healthz", timeout=5)
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
