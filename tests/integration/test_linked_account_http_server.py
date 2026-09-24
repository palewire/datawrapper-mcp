"""Integration test for the linked-account OAuth flow's real HTTP wiring.

Runs the actual `deployment.app` module as a subprocess with
REQUIRE_LINKED_ACCOUNT set, unlike tests/test_oauth_routes.py and
test_oauth_asgi.py, which test the route handlers and the ASGI gate against
small standalone apps. This one instead proves deployment.app actually wires
the store, the routes, and the middleware together correctly end to end.
"""

import base64
import hashlib
import os
import secrets
from subprocess import PIPE, Popen

import pytest
import requests

from datawrapper_mcp.oauth.storage import generate_encryption_key
from tests.integration.conftest import free_port, wait_until_ready

pytestmark = pytest.mark.integration

STARTUP_TIMEOUT = 15


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(32)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


@pytest.fixture(scope="module")
def linked_account_server(tmp_path_factory):
    port = free_port()
    db_path = tmp_path_factory.mktemp("oauth") / "oauth_store.db"

    env = os.environ.copy()
    env["MCP_SERVER_HOST"] = "127.0.0.1"
    env["MCP_SERVER_PORT"] = str(port)
    env["REQUIRE_LINKED_ACCOUNT"] = "true"
    env["TOKEN_ENCRYPTION_KEY"] = generate_encryption_key()
    env["OAUTH_STORE_PATH"] = str(db_path)

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


def test_mcp_endpoint_requires_auth(linked_account_server):
    response = requests.get(f"{linked_account_server}/mcp", timeout=5)

    assert response.status_code == 401
    assert "oauth-protected-resource" in response.headers["WWW-Authenticate"]


def test_metadata_endpoints_are_public(linked_account_server):
    auth_server = requests.get(
        f"{linked_account_server}/.well-known/oauth-authorization-server", timeout=5
    )
    protected_resource = requests.get(
        f"{linked_account_server}/.well-known/oauth-protected-resource", timeout=5
    )

    assert auth_server.status_code == 200
    assert auth_server.json()["issuer"] == linked_account_server
    assert protected_resource.status_code == 200
    assert protected_resource.json()["resource"] == f"{linked_account_server}/mcp"


def test_full_link_flow_grants_access_to_mcp_endpoint(linked_account_server):
    register_response = requests.post(
        f"{linked_account_server}/register",
        json={"redirect_uris": ["https://claude.ai/api/mcp/auth_callback"]},
        timeout=5,
    )
    client_id = register_response.json()["client_id"]

    verifier, challenge = _pkce_pair()
    redirect_uri = "https://claude.ai/api/mcp/auth_callback"

    authorize_response = requests.post(
        f"{linked_account_server}/authorize",
        data={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": "xyz",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "datawrapper_token": "dw-secret-integration-token",
        },
        timeout=5,
        allow_redirects=False,
    )
    assert authorize_response.status_code == 302
    location = authorize_response.headers["location"]
    code = location.split("code=")[1].split("&")[0]

    token_response = requests.post(
        f"{linked_account_server}/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": verifier,
        },
        timeout=5,
    )
    assert token_response.status_code == 200
    access_token = token_response.json()["access_token"]

    mcp_response = requests.post(
        f"{linked_account_server}/mcp",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        },
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2026-07-28",
                "capabilities": {},
                "clientInfo": {"name": "integration-test", "version": "1.0"},
            },
        },
        timeout=5,
    )

    assert mcp_response.status_code == 200
