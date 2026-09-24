"""Tests for the linked-account OAuth route handlers.

These build a small standalone Starlette app directly from the route
factories, independent of deployment.app's module-level wiring (which only
registers routes conditionally at import time based on
REQUIRE_LINKED_ACCOUNT) and independent of the shared datawrapper_mcp.server
FastMCP singleton other test modules also import. That keeps these tests
free of import-order fragility across the test suite.
"""

import base64
import hashlib
import secrets

import httpx
import pytest
from starlette.applications import Starlette
from starlette.routing import Route

from datawrapper_mcp.oauth.routes import (
    authorize_endpoint,
    oauth_authorization_server_metadata,
    oauth_protected_resource_metadata,
    register_client_endpoint,
    token_endpoint,
)
from datawrapper_mcp.oauth.storage import LinkedAccountStore, generate_encryption_key

MCP_PATH = "/mcp"


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(32)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


@pytest.fixture
def store(tmp_path) -> LinkedAccountStore:
    return LinkedAccountStore(
        db_path=tmp_path / "oauth_store.db", encryption_key=generate_encryption_key()
    )


@pytest.fixture
async def client(store) -> httpx.AsyncClient:
    app = Starlette(
        routes=[
            Route(
                "/.well-known/oauth-authorization-server",
                oauth_authorization_server_metadata,
            ),
            Route(
                "/.well-known/oauth-protected-resource",
                oauth_protected_resource_metadata(MCP_PATH),
            ),
            Route("/register", register_client_endpoint(store), methods=["POST"]),
            Route("/authorize", authorize_endpoint(store), methods=["GET", "POST"]),
            Route("/token", token_endpoint(store), methods=["POST"]),
        ]
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as async_client:
        yield async_client


async def test_authorization_server_metadata(client):
    response = await client.get("/.well-known/oauth-authorization-server")

    assert response.status_code == 200
    data = response.json()
    assert data["issuer"] == "http://testserver"
    assert data["authorization_endpoint"] == "http://testserver/authorize"
    assert data["token_endpoint"] == "http://testserver/token"
    assert data["registration_endpoint"] == "http://testserver/register"
    assert data["code_challenge_methods_supported"] == ["S256"]
    assert data["token_endpoint_auth_methods_supported"] == ["none"]


async def test_protected_resource_metadata(client):
    response = await client.get("/.well-known/oauth-protected-resource")

    assert response.status_code == 200
    data = response.json()
    assert data["resource"] == "http://testserver/mcp"
    assert data["authorization_servers"] == ["http://testserver"]


async def test_register_client(client):
    response = await client.post(
        "/register", json={"redirect_uris": ["https://claude.ai/api/mcp/auth_callback"]}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["client_id"]
    assert data["redirect_uris"] == ["https://claude.ai/api/mcp/auth_callback"]
    assert data["token_endpoint_auth_method"] == "none"


async def test_register_client_requires_redirect_uris(client):
    response = await client.post("/register", json={})

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_client_metadata"


async def test_register_client_rejects_malformed_json_body(client):
    response = await client.post(
        "/register",
        content=b"not valid json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_client_metadata"


async def _register_client(client: httpx.AsyncClient) -> str:
    response = await client.post(
        "/register", json={"redirect_uris": ["https://claude.ai/api/mcp/auth_callback"]}
    )
    return response.json()["client_id"]


async def test_full_authorization_code_flow(client):
    """The whole authorize -> token exchange, exactly as a real client would drive it."""
    client_id = await _register_client(client)
    verifier, challenge = _pkce_pair()
    redirect_uri = "https://claude.ai/api/mcp/auth_callback"

    authorize_response = await client.post(
        "/authorize",
        data={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": "xyz",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "datawrapper_token": "dw-secret-token",
        },
        follow_redirects=False,
    )

    assert authorize_response.status_code == 302
    location = authorize_response.headers["location"]
    assert location.startswith(redirect_uri)
    assert "state=xyz" in location
    code = location.split("code=")[1].split("&")[0]

    token_response = await client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": verifier,
        },
    )

    assert token_response.status_code == 200
    data = token_response.json()
    assert data["token_type"] == "Bearer"
    assert data["access_token"]
    assert data["expires_in"] > 0


async def test_authorize_get_shows_form(client):
    client_id = await _register_client(client)

    response = await client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": "https://claude.ai/api/mcp/auth_callback",
            "code_challenge": "abc",
            "code_challenge_method": "S256",
        },
    )

    assert response.status_code == 200
    assert "Link your Datawrapper account" in response.text
    assert "<form" in response.text


async def test_authorize_rejects_unknown_client(client):
    response = await client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": "does-not-exist",
            "redirect_uri": "https://claude.ai/api/mcp/auth_callback",
            "code_challenge": "abc",
            "code_challenge_method": "S256",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_client"


async def test_authorize_rejects_mismatched_redirect_uri(client):
    client_id = await _register_client(client)

    response = await client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": "https://evil.example.com/callback",
            "code_challenge": "abc",
            "code_challenge_method": "S256",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_request"


async def test_authorize_requires_pkce(client):
    client_id = await _register_client(client)

    response = await client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": "https://claude.ai/api/mcp/auth_callback",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_request"


async def test_authorize_post_without_token_reshows_form_with_error(client):
    client_id = await _register_client(client)
    _verifier, challenge = _pkce_pair()

    response = await client.post(
        "/authorize",
        data={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": "https://claude.ai/api/mcp/auth_callback",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "datawrapper_token": "",
        },
    )

    assert response.status_code == 400
    assert "Please enter a token" in response.text


async def test_token_rejects_unsupported_grant_type(client):
    response = await client.post("/token", data={"grant_type": "client_credentials"})

    assert response.status_code == 400
    assert response.json()["error"] == "unsupported_grant_type"


async def test_token_rejects_unknown_code(client):
    response = await client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": "never-issued",
            "redirect_uri": "https://claude.ai/api/mcp/auth_callback",
            "code_verifier": "whatever",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_grant"


async def test_token_rejects_wrong_pkce_verifier(client):
    client_id = await _register_client(client)
    _verifier, challenge = _pkce_pair()
    redirect_uri = "https://claude.ai/api/mcp/auth_callback"

    authorize_response = await client.post(
        "/authorize",
        data={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "datawrapper_token": "dw-secret-token",
        },
        follow_redirects=False,
    )
    code = authorize_response.headers["location"].split("code=")[1].split("&")[0]

    token_response = await client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": "wrong-verifier",
        },
    )

    assert token_response.status_code == 400
    assert token_response.json()["error"] == "invalid_grant"


async def test_token_rejects_redirect_uri_mismatch(client):
    client_id = await _register_client(client)
    verifier, challenge = _pkce_pair()
    redirect_uri = "https://claude.ai/api/mcp/auth_callback"

    authorize_response = await client.post(
        "/authorize",
        data={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "datawrapper_token": "dw-secret-token",
        },
        follow_redirects=False,
    )
    code = authorize_response.headers["location"].split("code=")[1].split("&")[0]

    token_response = await client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "https://different.example.com/callback",
            "code_verifier": verifier,
        },
    )

    assert token_response.status_code == 400
    assert token_response.json()["error"] == "invalid_grant"
