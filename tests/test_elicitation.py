"""Tests for the elicitation-based login prototype."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastmcp.exceptions import ToolError
from fastmcp.server.elicitation import (
    AcceptedElicitation,
    CancelledElicitation,
    DeclinedElicitation,
)

from datawrapper_mcp.elicitation import DatawrapperTokenInput, elicit_datawrapper_token


def _fake_context(elicit_result=None, elicit_side_effect=None):
    ctx = MagicMock()
    ctx.elicit = AsyncMock(return_value=elicit_result, side_effect=elicit_side_effect)
    return ctx


async def test_returns_token_on_accept():
    ctx = _fake_context(
        elicit_result=AcceptedElicitation(
            data=DatawrapperTokenInput(access_token="abc123")
        )
    )

    token = await elicit_datawrapper_token(ctx)

    assert token == "abc123"
    ctx.elicit.assert_awaited_once()
    _, kwargs = ctx.elicit.call_args
    assert kwargs["response_type"] is DatawrapperTokenInput


async def test_strips_whitespace_from_accepted_token():
    ctx = _fake_context(
        elicit_result=AcceptedElicitation(
            data=DatawrapperTokenInput(access_token="  abc123  ")
        )
    )

    token = await elicit_datawrapper_token(ctx)

    assert token == "abc123"


async def test_blank_token_normalizes_to_none():
    ctx = _fake_context(
        elicit_result=AcceptedElicitation(data=DatawrapperTokenInput(access_token=" "))
    )

    token = await elicit_datawrapper_token(ctx)

    assert token is None


async def test_decline_returns_none():
    ctx = _fake_context(elicit_result=DeclinedElicitation())

    token = await elicit_datawrapper_token(ctx)

    assert token is None


async def test_cancel_returns_none():
    ctx = _fake_context(elicit_result=CancelledElicitation())

    token = await elicit_datawrapper_token(ctx)

    assert token is None


async def test_unsupported_client_returns_none_instead_of_raising():
    ctx = _fake_context(elicit_side_effect=ToolError("not supported"))

    token = await elicit_datawrapper_token(ctx)

    assert token is None


async def test_non_tool_error_still_propagates():
    ctx = _fake_context(elicit_side_effect=RuntimeError("boom"))

    with pytest.raises(RuntimeError, match="boom"):
        await elicit_datawrapper_token(ctx)
