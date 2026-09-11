"""Shared helpers for integration tests that spin up a real server process."""

import socket
import time
from contextlib import closing

import requests


def free_port() -> int:
    """Ask the OS for an unused TCP port to avoid clashing with other jobs."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _try_request(url: str) -> Exception | None:
    """Attempt one request, returning the exception on failure instead of raising."""
    try:
        requests.get(url, timeout=1)
    except requests.exceptions.RequestException as e:
        return e
    return None


def wait_until_ready(url: str, timeout: float, poll_interval: float = 0.1) -> None:
    """Poll a URL until it responds or the timeout elapses."""
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        last_error = _try_request(url)
        if last_error is None:
            return
        time.sleep(poll_interval)
    raise TimeoutError(f"{url} did not become ready within {timeout}s") from last_error
