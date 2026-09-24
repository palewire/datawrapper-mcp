"""Route handlers for the linked-account OAuth flow.

Each `*_endpoint(store)` factory returns a Starlette-compatible handler
closed over that store instance; deployment/app.py registers them onto the
FastMCP server's custom routes. Kept as plain functions rather than a class
since each one maps directly onto a single HTTP endpoint - see the
docstring on each for which one.
"""

from __future__ import annotations

import html
from typing import TYPE_CHECKING

from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse

from .pkce import verify_code_challenge
from .storage import ACCESS_TOKEN_TTL_SECONDS, LinkedAccountStore

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from starlette.requests import Request

    RouteHandler = Callable[[Request], Awaitable[JSONResponse]]
    AuthorizeHandler = Callable[
        [Request], Awaitable[HTMLResponse | RedirectResponse | JSONResponse]
    ]

_AUTHORIZE_FORM = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Link your Datawrapper account</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 32rem; margin: 4rem auto; padding: 0 1rem; color: #1a1a1a; }}
    h1 {{ font-size: 1.25rem; }}
    label {{ display: block; margin-top: 1.5rem; font-weight: 600; }}
    input[type="password"] {{ width: 100%; box-sizing: border-box; padding: 0.5rem; font-size: 1rem; margin-top: 0.5rem; }}
    button {{ margin-top: 1.5rem; padding: 0.6rem 1.5rem; font-size: 1rem; cursor: pointer; }}
    p.hint {{ color: #555; font-size: 0.9rem; }}
    p.error {{ color: #b00020; font-weight: 600; }}
  </style>
</head>
<body>
  <h1>Link your Datawrapper account</h1>
  <p>Paste your own Datawrapper API token below. Charts created through this
  connector will be created under <em>your</em> Datawrapper account, not a
  shared one.</p>
  <p class="hint">Get a token from
    <a href="https://app.datawrapper.de/account/api-tokens" target="_blank" rel="noopener">
      app.datawrapper.de/account/api-tokens
    </a>.
  </p>
  {error_html}
  <form method="POST">
    <label for="datawrapper_token">Datawrapper API token</label>
    <input type="password" id="datawrapper_token" name="datawrapper_token" required autofocus>
    <input type="hidden" name="response_type" value="{response_type}">
    <input type="hidden" name="client_id" value="{client_id}">
    <input type="hidden" name="redirect_uri" value="{redirect_uri}">
    <input type="hidden" name="state" value="{state}">
    <input type="hidden" name="code_challenge" value="{code_challenge}">
    <input type="hidden" name="code_challenge_method" value="{code_challenge_method}">
    <button type="submit">Link account</button>
  </form>
</body>
</html>
"""


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


async def oauth_authorization_server_metadata(request: Request) -> JSONResponse:
    """RFC 8414 authorization server metadata."""
    base_url = _base_url(request)
    return JSONResponse(
        {
            "issuer": base_url,
            "authorization_endpoint": f"{base_url}/authorize",
            "token_endpoint": f"{base_url}/token",
            "registration_endpoint": f"{base_url}/register",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none"],
        }
    )


def oauth_protected_resource_metadata(
    mcp_path: str,
) -> RouteHandler:
    """Build the RFC 9728 protected-resource metadata handler for mcp_path."""

    async def handler(request: Request) -> JSONResponse:
        base_url = _base_url(request)
        return JSONResponse(
            {
                "resource": f"{base_url}{mcp_path}",
                "authorization_servers": [base_url],
            }
        )

    return handler


def register_client_endpoint(store: LinkedAccountStore) -> RouteHandler:
    """Build the POST /register (Dynamic Client Registration, RFC 7591) handler."""

    async def handler(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except ValueError:
            body = {}
        redirect_uris = body.get("redirect_uris") or []
        if not isinstance(redirect_uris, list) or not redirect_uris:
            return JSONResponse(
                {
                    "error": "invalid_client_metadata",
                    "error_description": "redirect_uris is required",
                },
                status_code=400,
            )
        client = await store.register_client([str(uri) for uri in redirect_uris])
        return JSONResponse(
            {
                "client_id": client.client_id,
                "redirect_uris": client.redirect_uris,
                "token_endpoint_auth_method": "none",
                "grant_types": ["authorization_code"],
                "response_types": ["code"],
            }
        )

    return handler


def _render_authorize_form(params: dict[str, str], error: str | None = None) -> str:
    error_html = f'<p class="error">{html.escape(error)}</p>' if error else ""
    return _AUTHORIZE_FORM.format(
        error_html=error_html,
        response_type=html.escape(params.get("response_type", "code")),
        client_id=html.escape(params.get("client_id", "")),
        redirect_uri=html.escape(params.get("redirect_uri", "")),
        state=html.escape(params.get("state", "")),
        code_challenge=html.escape(params.get("code_challenge", "")),
        code_challenge_method=html.escape(params.get("code_challenge_method", "S256")),
    )


def authorize_endpoint(store: LinkedAccountStore) -> AuthorizeHandler:
    """Build the GET/POST /authorize handler (the "consent screen")."""

    async def handler(
        request: Request,
    ) -> HTMLResponse | RedirectResponse | JSONResponse:
        if request.method == "GET":
            params = dict(request.query_params)
        else:
            form = await request.form()
            params = {k: str(v) for k, v in form.items()}

        client_id = params.get("client_id", "")
        redirect_uri = params.get("redirect_uri", "")
        code_challenge = params.get("code_challenge", "")
        state = params.get("state", "")

        client = await store.get_client(client_id) if client_id else None
        if client is None:
            return JSONResponse(
                {"error": "invalid_client", "error_description": "Unknown client_id"},
                status_code=400,
            )
        if redirect_uri not in client.redirect_uris:
            return JSONResponse(
                {
                    "error": "invalid_request",
                    "error_description": "redirect_uri does not match registration",
                },
                status_code=400,
            )
        if params.get("code_challenge_method", "S256") != "S256" or not code_challenge:
            return JSONResponse(
                {
                    "error": "invalid_request",
                    "error_description": "PKCE with S256 is required",
                },
                status_code=400,
            )

        if request.method == "GET":
            return HTMLResponse(_render_authorize_form(params))

        token = (params.get("datawrapper_token") or "").strip()
        if not token:
            return HTMLResponse(
                _render_authorize_form(params, error="Please enter a token."),
                status_code=400,
            )

        code = await store.store_authorization_code(
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            datawrapper_token=token,
        )
        redirect_to = f"{redirect_uri}?code={code}"
        if state:
            redirect_to += f"&state={state}"
        return RedirectResponse(redirect_to, status_code=302)

    return handler


def token_endpoint(store: LinkedAccountStore) -> RouteHandler:
    """Build the POST /token (authorization_code grant, PKCE-verified) handler."""

    async def handler(request: Request) -> JSONResponse:
        form = await request.form()
        grant_type = form.get("grant_type")
        if grant_type != "authorization_code":
            return JSONResponse(
                {"error": "unsupported_grant_type"},
                status_code=400,
            )

        code = str(form.get("code", ""))
        redirect_uri = str(form.get("redirect_uri", ""))
        code_verifier = str(form.get("code_verifier", ""))

        grant = await store.consume_authorization_code(code)
        if grant is None:
            return JSONResponse(
                {
                    "error": "invalid_grant",
                    "error_description": "Unknown or expired code",
                },
                status_code=400,
            )
        if grant.redirect_uri != redirect_uri:
            return JSONResponse(
                {
                    "error": "invalid_grant",
                    "error_description": "redirect_uri mismatch",
                },
                status_code=400,
            )
        if not code_verifier or not verify_code_challenge(
            code_verifier=code_verifier, code_challenge=grant.code_challenge
        ):
            return JSONResponse(
                {
                    "error": "invalid_grant",
                    "error_description": "PKCE verification failed",
                },
                status_code=400,
            )

        access_token = await store.issue_access_token(
            client_id=grant.client_id,
            datawrapper_token=grant.datawrapper_token,
        )
        return JSONResponse(
            {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": ACCESS_TOKEN_TTL_SECONDS,
            }
        )

    return handler
