"""Tests for the LinkedAccountAuthMiddleware ASGI gate."""

import httpx
import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from datawrapper_mcp.oauth.asgi import LinkedAccountAuthMiddleware
from datawrapper_mcp.oauth.storage import LinkedAccountStore, generate_encryption_key


@pytest.fixture
def store(tmp_path) -> LinkedAccountStore:
    return LinkedAccountStore(
        db_path=tmp_path / "oauth_store.db", encryption_key=generate_encryption_key()
    )


async def _echo_authorization(request: Request) -> JSONResponse:
    """A trivial downstream handler that reports what Authorization it saw."""
    return JSONResponse({"authorization": request.headers.get("authorization")})


def _build_client(
    store: LinkedAccountStore, protected_path: str = "/mcp"
) -> httpx.AsyncClient:
    app = Starlette(
        routes=[
            Route("/mcp", _echo_authorization),
            Route("/healthz", _echo_authorization),
        ]
    )
    app.add_middleware(
        LinkedAccountAuthMiddleware, store=store, protected_path=protected_path
    )
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


async def test_missing_authorization_header_is_rejected(store):
    async with _build_client(store) as client:
        response = await client.get("/mcp")

    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"
    assert "WWW-Authenticate" in response.headers
    assert "oauth-protected-resource" in response.headers["WWW-Authenticate"]


async def test_unresolvable_token_is_rejected(store):
    async with _build_client(store) as client:
        response = await client.get(
            "/mcp", headers={"Authorization": "Bearer not-a-real-token"}
        )

    assert response.status_code == 401


async def test_valid_token_is_rewritten_to_the_real_datawrapper_token(store):
    access_token = await store.issue_access_token(
        client_id="client-1", datawrapper_token="dw-real-token-xyz"
    )

    async with _build_client(store) as client:
        response = await client.get(
            "/mcp", headers={"Authorization": f"Bearer {access_token}"}
        )

    assert response.status_code == 200
    assert response.json()["authorization"] == "Bearer dw-real-token-xyz"


async def test_unprotected_paths_pass_through_untouched(store):
    """A path outside protected_path should never see the 401 gate at all."""
    async with _build_client(store) as client:
        response = await client.get(
            "/healthz", headers={"Authorization": "Bearer whatever-junk"}
        )

    assert response.status_code == 200
    # Not rewritten, not rejected - the gate never looked at this request.
    assert response.json()["authorization"] == "Bearer whatever-junk"


async def test_unprotected_path_with_no_header_at_all_still_passes(store):
    async with _build_client(store) as client:
        response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["authorization"] is None
