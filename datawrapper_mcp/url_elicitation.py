"""Prototype: real MCP *URL-mode* elicitation for Datawrapper login.

The MCP elicitation spec (URL mode added 2025-11-25, tightened 2026-07-28) is
explicit that servers MUST NOT collect secrets - passwords, API keys, access
tokens - via *form* mode elicitation, because that data is exposed to the MCP
client/LLM context. Secrets MUST go through *URL* mode instead: the server
hands the client a URL, the client gets the user's consent and opens it, and
the actual credential is submitted out-of-band on a page the server hosts -
the client never sees it, only "accept" / "decline" / "cancel".

This supersedes the form-mode `login_to_datawrapper` prototype that shipped
first in this PR (see docs/proposals/march-2026-upgrades.md for the writeup
of why that version didn't comply with the spec).

This module hosts that out-of-band page: a minimal, lazily-started,
localhost-only HTTP server serving a one-time ``/connect/<id>`` form. It's
still a prototype - see the module docstring in server.py's
`login_to_datawrapper` tool for known limitations (no persistence of the
token beyond the pending-connect window, no real per-user identity binding).
"""

import asyncio
import html
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass
from typing import cast

import uvicorn
from datawrapper import Datawrapper
from mcp.types import (
    ElicitRequest,
    ElicitRequestURLParams,
    ElicitResult,
    InputRequiredResult,
    InputResponses,
)
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.routing import Route

logger = logging.getLogger("datawrapper_mcp")

# How long login_guard polls the pending-connect store on each round before
# giving up and re-asking (with the same link) for the client to retry.
_CONNECT_POLL_INTERVAL = 0.5
_CONNECT_POLL_ROUNDS = 40  # ~20s

_TOKEN_SETTINGS_URL = "https://app.datawrapper.de/account/api-tokens"  # noqa: S105 - a URL, not a secret

# How long an unused connect link stays valid before it's swept from memory.
PENDING_TTL_SECONDS = 600

_DEFAULT_PORT = 8420


@dataclass
class PendingConnect:
    """State for one in-flight connect link."""

    created_at: float
    verified: bool = False
    account: dict[str, object] | None = None


# Prototype-scoped, single-process, in-memory store. A real deployment would
# need this shared across replicas (e.g. the SQLite/Fernet storage that
# feat/linked-account-oauth already built for its own token broker) and would
# persist the verified token itself for reuse by other tools - this prototype
# deliberately doesn't retain the token past the check that verifies it.
_pending: dict[str, PendingConnect] = {}
_pending_lock = asyncio.Lock()

_server: uvicorn.Server | None = None
_server_lock = asyncio.Lock()


def _sweep_expired_locked() -> None:
    cutoff = time.monotonic() - PENDING_TTL_SECONDS
    expired = [cid for cid, pending in _pending.items() if pending.created_at < cutoff]
    for connect_id in expired:
        del _pending[connect_id]


async def create_pending_connect() -> str:
    """Register a new pending connect request and return its opaque id."""
    async with _pending_lock:
        _sweep_expired_locked()
        connect_id = secrets.token_urlsafe(24)
        _pending[connect_id] = PendingConnect(created_at=time.monotonic())
        return connect_id


async def get_pending_connect(connect_id: str) -> PendingConnect | None:
    async with _pending_lock:
        return _pending.get(connect_id)


def _render_page(
    *,
    error: str | None = None,
    success: bool = False,
    account: dict[str, object] | None = None,
) -> str:
    if success:
        email = html.escape(str((account or {}).get("email") or "your account"))
        body = f"""
        <h1>Connected ✓</h1>
        <p>Linked as <strong>{email}</strong>. You can close this tab and go
        back to your chat.</p>
        """
    else:
        error_html = f'<p class="error">{html.escape(error)}</p>' if error else ""
        body = f"""
        <h1>Connect your Datawrapper account</h1>
        <p>Create or copy a personal API token at
        <a href="{_TOKEN_SETTINGS_URL}" target="_blank" rel="noopener">
        {_TOKEN_SETTINGS_URL}</a>, then paste it below. This page only sends
        your token to Datawrapper's API to verify it - it never goes back
        through your chat client.</p>
        {error_html}
        <form method="post">
            <input type="password" name="access_token" placeholder="dw_..."
                   autofocus required style="width: 100%; padding: 0.5em;" />
            <button type="submit" style="margin-top: 0.5em; padding: 0.5em 1em;">
                Connect
            </button>
        </form>
        """
    return f"""<!doctype html>
<html>
<head>
    <meta charset="utf-8" />
    <title>Connect to Datawrapper</title>
    <style>
        body {{ font-family: system-ui, sans-serif; max-width: 32em;
                margin: 3em auto; padding: 0 1em; color: #222; }}
        .error {{ color: #b00020; }}
    </style>
</head>
<body>{body}</body>
</html>"""


async def _handle_get(request: Request) -> HTMLResponse:
    connect_id = request.path_params["connect_id"]
    pending = await get_pending_connect(connect_id)
    if pending is None:
        return HTMLResponse(
            _render_page(
                error="This link has expired or was already used. Go back "
                "to your chat and ask to connect again."
            ),
            status_code=404,
        )
    if pending.verified:
        return HTMLResponse(_render_page(success=True, account=pending.account))
    return HTMLResponse(_render_page())


async def _handle_post(request: Request) -> HTMLResponse:
    connect_id = request.path_params["connect_id"]
    pending = await get_pending_connect(connect_id)
    if pending is None:
        return HTMLResponse(
            _render_page(
                error="This link has expired. Go back to your chat and ask "
                "to connect again."
            ),
            status_code=404,
        )

    form = await request.form()
    token = str(form.get("access_token", "")).strip()
    if not token:
        return HTMLResponse(_render_page(error="Please paste a token."))

    client = Datawrapper(access_token=token)
    try:
        account = await asyncio.to_thread(client.get_my_account)
    except Exception as e:
        logger.info(
            "Rejected an invalid token submitted to /connect/%s: %s", connect_id, e
        )
        return HTMLResponse(
            _render_page(
                error="Datawrapper rejected that token. Double check you "
                "copied it in full, then try again."
            )
        )

    resolved_account = {
        "email": account.get("email"),
        "name": account.get("name"),
        "id": account.get("id"),
    }
    async with _pending_lock:
        # Re-fetch inside the lock in case it expired mid-request.
        pending = _pending.get(connect_id)
        if pending is None:
            return HTMLResponse(
                _render_page(
                    error="This link expired while you were typing. Go back "
                    "to your chat and ask to connect again."
                ),
                status_code=404,
            )
        pending.verified = True
        pending.account = resolved_account

    return HTMLResponse(_render_page(success=True, account=resolved_account))


def build_connect_app() -> Starlette:
    """Build the Starlette app serving the out-of-band /connect page."""
    return Starlette(
        routes=[
            Route("/connect/{connect_id}", _handle_get, methods=["GET"]),
            Route("/connect/{connect_id}", _handle_post, methods=["POST"]),
        ]
    )


async def ensure_connect_server_url() -> str:
    """Return the base URL to build ``/connect/<id>`` links against.

    Honors ``DATAWRAPPER_MCP_CONNECT_URL`` for deployments that front the
    connect page with their own public HTTPS reverse proxy - in that case
    nothing local needs to run. Otherwise, lazily starts a localhost-only
    sidecar server (once per process) and points at that instead.
    """
    base_url = os.environ.get("DATAWRAPPER_MCP_CONNECT_URL")
    if base_url:
        return base_url.rstrip("/")

    global _server
    async with _server_lock:
        if _server is None:
            port = int(os.environ.get("DATAWRAPPER_MCP_CONNECT_PORT", _DEFAULT_PORT))
            config = uvicorn.Config(
                build_connect_app(), host="127.0.0.1", port=port, log_level="warning"
            )
            _server = uvicorn.Server(config)
            asyncio.create_task(_server.serve())  # noqa: RUF006 - long-lived sidecar
            for _ in range(100):
                if _server.started:
                    break
                await asyncio.sleep(0.05)

    port = int(os.environ.get("DATAWRAPPER_MCP_CONNECT_PORT", _DEFAULT_PORT))
    return f"http://127.0.0.1:{port}"


async def login_guard(
    input_responses: InputResponses | None, request_state: str | None
) -> str | InputRequiredResult:
    """The login_to_datawrapper tool's multi-round-trip guard (SEP-2322).

    Takes the plain ``ctx.input_responses`` / ``ctx.request_state`` values
    rather than a live ``Context``, so the three rounds of this flow (ask,
    poll-while-waiting, resolve) can be driven directly in tests without
    constructing a real MCP request.
    """
    if input_responses is None:
        connect_id = await create_pending_connect()
        url = f"{await ensure_connect_server_url()}/connect/{connect_id}"
        return _ask_to_connect(url, request_state=connect_id)

    raw_result = input_responses.get("connect")
    if raw_result is None:
        return "Didn't receive a response to the connection prompt. Try again."
    # Our own "connect" input_request only ever carries an ElicitRequest, so
    # the client's answer to it is always an ElicitResult - the wider union
    # on InputResponses covers the other input-request kinds (sampling,
    # roots) this tool never asks for.
    result = cast("ElicitResult", raw_result)
    if result.action == "decline":
        return (
            "Connection declined. Run this again anytime you'd like to link "
            "your Datawrapper account."
        )
    if result.action == "cancel":
        return (
            "Connection prompt was dismissed. Run this again anytime you'd "
            "like to link your Datawrapper account."
        )

    connect_id = request_state or ""
    for _ in range(_CONNECT_POLL_ROUNDS):
        pending = await get_pending_connect(connect_id)
        if pending is not None and pending.verified:
            return json.dumps({"connected": True, **(pending.account or {})}, indent=2)
        await asyncio.sleep(_CONNECT_POLL_INTERVAL)

    # Still not done on the page - ask again with the same link so the
    # client can let the user retry once they've finished there.
    url = f"{await ensure_connect_server_url()}/connect/{connect_id}"
    return _ask_to_connect(
        url,
        request_state=connect_id,
        message=(
            "Still waiting for you to finish at the link above. Click "
            "retry once you've submitted your token there."
        ),
    )


def _ask_to_connect(
    url: str, *, request_state: str, message: str | None = None
) -> InputRequiredResult:
    """Build the URL-mode elicitation ask for login_guard."""
    params = ElicitRequestURLParams(
        message=message
        or (
            "This Datawrapper MCP server would like to connect your "
            "account. Open the link to verify your Datawrapper API token - "
            "it's submitted directly to that page, not to this chat."
        ),
        url=url,
    )
    return InputRequiredResult(
        result_type="input_required",
        input_requests={
            "connect": ElicitRequest(method="elicitation/create", params=params)
        },
        request_state=request_state,
    )
