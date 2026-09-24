"""ASGI middleware enforcing the linked-account OAuth gate on the MCP endpoint.

This runs *before* FastMCP's own request handling, at the raw ASGI level -
not as a FastMCP/MCP tool-call Middleware - because the 401 challenge is
part of the HTTP-transport handshake (RFC 9728 protected-resource
discovery), not something scoped to an individual tool call.

On success, it rewrites the incoming Authorization header in place, from
the opaque access token Claude presents to the real Datawrapper token it
resolves to. Everything downstream - BearerTokenMiddleware,
RateLimitingMiddleware's per-token keying - then works completely
unchanged: they just see an ordinary `Authorization: Bearer <token>`
header, same as the plain BYOK pass-through mode.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.datastructures import Headers
from starlette.responses import JSONResponse

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send

    from .storage import LinkedAccountStore


class LinkedAccountAuthMiddleware:
    """Require a resolvable linked-account access token on `protected_path`."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        store: LinkedAccountStore,
        protected_path: str = "/mcp",
    ) -> None:
        self.app = app
        self.store = store
        self.protected_path = protected_path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith(self.protected_path):
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        auth = headers.get("authorization", "")
        token = (
            auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else ""
        )

        real_token = await self.store.resolve_access_token(token) if token else None
        if real_token is None:
            await self._unauthorized(scope, receive, send)
            return

        new_headers = [
            (name, value)
            for name, value in scope["headers"]
            if name.lower() != b"authorization"
        ]
        new_headers.append((b"authorization", f"Bearer {real_token}".encode()))
        scope = {**scope, "headers": new_headers}
        await self.app(scope, receive, send)

    async def _unauthorized(self, scope: Scope, receive: Receive, send: Send) -> None:
        base_url = _base_url_from_scope(scope)
        response = JSONResponse(
            {"error": "unauthorized"},
            status_code=401,
            headers={
                "WWW-Authenticate": (
                    f'Bearer resource_metadata="{base_url}'
                    f'/.well-known/oauth-protected-resource"'
                )
            },
        )
        await response(scope, receive, send)


def _base_url_from_scope(scope: Scope) -> str:
    headers = Headers(scope=scope)
    host = headers.get("host", "")
    scheme = scope.get("scheme", "http")
    return f"{scheme}://{host}"
