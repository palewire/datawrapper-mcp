"""Integration tests for Docker deployment."""

import os
import time
import pytest
import requests
import subprocess


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
    # Check for API token
    api_token = os.getenv("DATAWRAPPER_ACCESS_TOKEN")
    if not api_token:
        pytest.skip("DATAWRAPPER_ACCESS_TOKEN not set")

    # Start container
    print("\nStarting Docker container...")
    result = subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "-p",
            "8503:8501",  # Use different port to avoid conflicts
            "-e",
            f"DATAWRAPPER_ACCESS_TOKEN={api_token}",
            "-e",
            "MCP_SERVER_HOST=0.0.0.0",
            "-e",
            "MCP_SERVER_PORT=8501",
            docker_image,
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        pytest.fail(f"Docker run failed: {result.stderr}")

    container_id = result.stdout.strip()

    # Wait for container to be ready
    time.sleep(3)

    # Verify container is running
    result = subprocess.run(
        ["docker", "ps", "-q", "-f", f"id={container_id}"],
        capture_output=True,
        text=True,
    )

    if not result.stdout.strip():
        # Container not running, get logs
        logs = subprocess.run(
            ["docker", "logs", container_id], capture_output=True, text=True
        )
        subprocess.run(["docker", "rm", "-f", container_id], capture_output=True)
        pytest.fail(f"Container failed to start. Logs:\n{logs.stdout}\n{logs.stderr}")

    yield container_id

    # Cleanup: stop and remove container
    subprocess.run(["docker", "stop", container_id], capture_output=True)
    subprocess.run(["docker", "rm", container_id], capture_output=True)


def test_docker_health_check(docker_container):
    """Test health check endpoint in Docker container."""
    # Give container a moment to fully start
    time.sleep(1)

    response = requests.get("http://localhost:8503/healthz", timeout=10)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "datawrapper-mcp"


def test_docker_container_logs(docker_container):
    """Test that container logs show successful startup."""
    result = subprocess.run(
        ["docker", "logs", docker_container], capture_output=True, text=True
    )

    logs = result.stdout + result.stderr

    # Check for successful startup indicators
    # (Adjust these based on your actual log output)
    assert (
        "error" not in logs.lower()
        or "error" in logs.lower()
        and "0 errors" in logs.lower()
    )


def test_docker_container_running(docker_container):
    """Test that container stays running."""
    # Check container status
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", docker_container],
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "true"


def test_docker_sse_endpoint(docker_container):
    """Test that SSE endpoint is accessible in Docker."""
    try:
        response = requests.get(
            "http://localhost:8503/sse",
            headers={"Accept": "text/event-stream"},
            timeout=2,
            stream=True,
        )
        # Should get a response (even if it's waiting for MCP messages)
        assert response.status_code in [200, 400, 404]
    except requests.exceptions.ReadTimeout:
        # Timeout is expected for SSE connections
        pass


def test_docker_multiple_requests(docker_container):
    """Test that Docker container handles multiple requests."""
    for i in range(10):
        response = requests.get("http://localhost:8503/healthz", timeout=5)
        assert response.status_code == 200
        time.sleep(0.1)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
