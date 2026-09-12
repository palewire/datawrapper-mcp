"""HTTP server entry point for Kubernetes deployment."""

import os

from mcp.types import LATEST_PROTOCOL_VERSION
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from datawrapper_mcp.oauth.asgi import LinkedAccountAuthMiddleware
from datawrapper_mcp.oauth.routes import (
    authorize_endpoint,
    oauth_authorization_server_metadata,
    oauth_protected_resource_metadata,
    register_client_endpoint,
    token_endpoint,
)
from datawrapper_mcp.oauth.storage import LinkedAccountStore
from datawrapper_mcp.server import mcp

MCP_PATH = "/mcp"

# Linked-account mode: when enabled, every caller must complete the
# OAuth-shaped flow in datawrapper_mcp.oauth to attach their own Datawrapper
# token, instead of one connector-wide credential. See
# datawrapper_mcp/oauth/__init__.py for why this exists and INSTALLATION.md
# for the operational setup (including the persistent-storage requirement).
_require_linked_account = os.getenv("REQUIRE_LINKED_ACCOUNT", "").lower() in (
    "1",
    "true",
    "yes",
)
_linked_account_store: LinkedAccountStore | None = None

if _require_linked_account:
    _encryption_key = os.environ.get("TOKEN_ENCRYPTION_KEY")
    if not _encryption_key:
        raise RuntimeError(
            "REQUIRE_LINKED_ACCOUNT is set but TOKEN_ENCRYPTION_KEY is not. "
            "Generate one with: "
            "python -c 'from datawrapper_mcp.oauth.storage import "
            "generate_encryption_key as g; print(g())'"
        )
    _linked_account_store = LinkedAccountStore(
        db_path=os.getenv("OAUTH_STORE_PATH", "oauth_store.db"),
        encryption_key=_encryption_key,
    )

    mcp.custom_route("/.well-known/oauth-authorization-server", methods=["GET"])(
        oauth_authorization_server_metadata
    )
    mcp.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])(
        oauth_protected_resource_metadata(MCP_PATH)
    )
    mcp.custom_route("/register", methods=["POST"])(
        register_client_endpoint(_linked_account_store)
    )
    mcp.custom_route("/authorize", methods=["GET", "POST"])(
        authorize_endpoint(_linked_account_store)
    )
    mcp.custom_route("/token", methods=["POST"])(token_endpoint(_linked_account_store))


@mcp.custom_route("/healthz", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for Kubernetes liveness/readiness probes."""
    return JSONResponse({"status": "healthy", "service": "datawrapper-mcp"})


@mcp.custom_route("/.well-known/mcp.json", methods=["GET"])
async def well_known_mcp(request: Request) -> JSONResponse:
    """MCP server discovery endpoint (SEP-1960)."""
    return JSONResponse(
        {
            "mcp": {
                # Read from the installed SDK so this never goes stale across upgrades.
                "versions": [LATEST_PROTOCOL_VERSION],
                "endpoint": "/mcp",
                "name": "datawrapper-mcp",
                "description": "Create Datawrapper charts via MCP",
                "capabilities": {
                    "tools": True,
                    "resources": True,
                    "apps": True,
                },
            }
        }
    )


if __name__ == "__main__":
    # Get configuration from environment variables
    host = os.getenv("MCP_SERVER_HOST", "0.0.0.0")  # noqa: S104 - container listens on all interfaces
    port = int(os.getenv("MCP_SERVER_PORT", "8501"))

    # Log server start information
    print(f"Starting datawrapper-mcp on {host}:{port}")
    print(f"Health check available at http://{host}:{port}/healthz")
    if _require_linked_account:
        print("Linked-account mode is ON: callers must complete the OAuth flow")

    asgi_middleware = (
        [
            Middleware(
                LinkedAccountAuthMiddleware,
                store=_linked_account_store,
                protected_path=MCP_PATH,
            )
        ]
        if _linked_account_store is not None
        else None
    )

    # Run with streamable-http transport
    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
        middleware=asgi_middleware,
    )
