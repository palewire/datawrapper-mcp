"""Handler for checking which Datawrapper account is currently authenticated.

Exists to make a specific class of misconfiguration debuggable: on a
personal Claude connector using a "No sign-in" + "Request headers"
Authorization header (see INSTALLATION.md), a missing "Bearer " prefix, an
optional-instead-of-required header, or a wrong header name all cause the
same silent failure - calls quietly fall back to the server's own
DATAWRAPPER_ACCESS_TOKEN instead of the caller's personal token, with no
error at all. Asking "who am I connected as?" surfaces that immediately:
if the account isn't the one you expected, the header isn't actually
reaching the server.
"""

import asyncio
import json
import os
from typing import Any

from datawrapper import Datawrapper
from mcp.types import TextContent

from datawrapper_mcp.types import CheckDatawrapperConnectionArgs

_TOKEN_SETTINGS_URL = "https://app.datawrapper.de/account/api-tokens"  # noqa: S105 - a URL, not a secret


async def check_datawrapper_connection(
    arguments: CheckDatawrapperConnectionArgs,
) -> list[TextContent]:
    """Report which Datawrapper account the current token authenticates as."""
    # Datawrapper() only reads DATAWRAPPER_ACCESS_TOKEN as *its own* default
    # argument, evaluated once at import time - passing an explicit None
    # here would override that and produce a literal "Bearer None" request,
    # so resolve the same fallback chain the datawrapper library's own
    # get_chart() uses instead of relying on Datawrapper()'s default.
    token = (
        arguments.get("access_token") or os.getenv("DATAWRAPPER_ACCESS_TOKEN") or None
    )

    client = Datawrapper(access_token=token)
    try:
        account: dict[str, Any] = await asyncio.to_thread(client.get_my_account)
    except Exception as e:
        message = str(e)
        if "401" in message or "403" in message:
            raise ValueError(
                "Datawrapper rejected this token (authentication failed).\n\n"
                "If you're using a personal Claude connector with a Request "
                "headers Authorization value, double-check that:\n"
                "  1. The value starts with 'Bearer ' (including the space), "
                "followed by your token - not just the token alone\n"
                "  2. The header is marked Required, not optional\n"
                "  3. The header name is exactly 'Authorization'\n"
                "  4. The token hasn't been revoked - get a new one at "
                f"{_TOKEN_SETTINGS_URL}"
            ) from e
        raise ValueError(
            f"Could not reach Datawrapper to check the connection: {e!s}"
        ) from e

    result = {
        "connected": True,
        "email": account.get("email"),
        "name": account.get("name"),
        "id": account.get("id"),
    }
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
