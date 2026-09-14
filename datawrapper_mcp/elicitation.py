"""Prototype: ask the user for their Datawrapper API token via MCP elicitation.

This is an alternative to the OAuth-shaped linked-account broker explored on
`feat/linked-account-oauth` (issue #57). Instead of standing up an
authorization server (DCR, PKCE, a hosted /authorize form, encrypted token
storage), this uses MCP's own elicitation primitive - a server-initiated,
schema-driven prompt that the client renders as a native form in the chat
itself. No extra HTTP surface, no database.

The tradeoff, per docs/proposals/march-2026-upgrades.md, is client support:
elicitation only works on the older MCP handshake (pre 2026-07-28 era) and
only ~11% of clients implement it at all. `elicit_datawrapper_token()` treats
both "unsupported" and "user declined" as the same "no token" outcome so
callers can fall back without needing to distinguish why nothing came back.
"""

import logging
from dataclasses import dataclass

from fastmcp import Context
from fastmcp.exceptions import ToolError

logger = logging.getLogger("datawrapper_mcp")

TOKEN_SETTINGS_URL = "https://app.datawrapper.de/account/api-tokens"  # noqa: S105 - a URL, not a secret


@dataclass
class DatawrapperTokenInput:
    """Schema for the elicitation form: the user's own Datawrapper API token."""

    access_token: str


async def elicit_datawrapper_token(ctx: Context) -> str | None:
    """Prompt the connected client's user to paste their Datawrapper API token.

    Returns the token, or None if the client doesn't support elicitation
    (raises before the prompt is ever shown) or the user declines/cancels it.
    """
    try:
        result = await ctx.elicit(
            message=(
                "This Datawrapper MCP server would like to act on your behalf. "
                f"Create or copy a personal API token at {TOKEN_SETTINGS_URL}, "
                "then paste it below."
            ),
            response_type=DatawrapperTokenInput,
        )
    except ToolError:
        logger.info(
            "Elicitation unavailable on this connection; client or protocol "
            "era doesn't support server-initiated prompts."
        )
        return None

    if result.action != "accept":
        logger.info("User %s the Datawrapper token prompt.", result.action)
        return None

    token = result.data.access_token.strip()
    return token or None
