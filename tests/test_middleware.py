"""Tests for production middleware (error handling, rate limiting, timing)."""

import asyncio
import logging
from dataclasses import dataclass
from typing import cast
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp.server.middleware import MiddlewareContext
from fastmcp.tools import ToolResult
from mcp.types import TextContent

from datawrapper_mcp.middleware import (
    BearerTokenMiddleware,
    ErrorHandlingMiddleware,
    RateLimitingMiddleware,
    TimingMiddleware,
)


@dataclass
class _FakeMessage:
    """Minimal stand-in for a CallToolRequestParams message."""

    name: str = "test_tool"
    arguments: dict | None = None


@dataclass
class _FakeContext:
    """Minimal stand-in for MiddlewareContext with the ``.message.name`` path."""

    message: _FakeMessage


def _make_context_with_args(
    tool_name: str = "test_tool",
    arguments: dict | None = None,
) -> MiddlewareContext:
    """Build a MiddlewareContext that also carries ``.message.arguments``."""
    return cast(
        "MiddlewareContext",
        _FakeContext(message=_FakeMessage(name=tool_name, arguments=arguments)),
    )


def _make_context(tool_name: str = "test_tool") -> MiddlewareContext:
    """Build a lightweight MiddlewareContext for unit tests.

    The real MiddlewareContext is a frozen dataclass with many fields.
    We only need ``.message.name`` for the middleware under test, so we
    construct a minimal fake and cast it to satisfy static type checkers.
    """
    return cast("MiddlewareContext", _FakeContext(message=_FakeMessage(name=tool_name)))


def _ok_result() -> ToolResult:
    return ToolResult(content=[TextContent(type="text", text="ok")])


# ---------------------------------------------------------------------------
# ErrorHandlingMiddleware
# ---------------------------------------------------------------------------


class TestErrorHandlingMiddleware:
    """ErrorHandlingMiddleware should catch exceptions and return safe responses."""

    async def test_passes_through_successful_result(self):
        mw = ErrorHandlingMiddleware()
        call_next = AsyncMock(return_value=_ok_result())

        result = await mw.on_call_tool(_make_context(), call_next)

        assert result.content[0].text == "ok"
        call_next.assert_awaited_once()

    async def test_catches_exception_and_raises_tool_error(self):
        from fastmcp.exceptions import ToolError

        mw = ErrorHandlingMiddleware()
        call_next = AsyncMock(side_effect=RuntimeError("boom"))

        with pytest.raises(ToolError, match="my_tool") as exc_info:
            await mw.on_call_tool(_make_context("my_tool"), call_next)

        assert "boom" in str(exc_info.value)

    async def test_logs_exception(self, caplog):
        from fastmcp.exceptions import ToolError

        mw = ErrorHandlingMiddleware()
        call_next = AsyncMock(side_effect=ValueError("bad value"))

        with caplog.at_level(logging.ERROR, logger="datawrapper_mcp"):
            with pytest.raises(ToolError):
                await mw.on_call_tool(_make_context("broken_tool"), call_next)

        assert "broken_tool" in caplog.text

    async def test_reraises_cancelled_error(self):
        mw = ErrorHandlingMiddleware()
        call_next = AsyncMock(side_effect=asyncio.CancelledError())

        with pytest.raises(asyncio.CancelledError):
            await mw.on_call_tool(_make_context(), call_next)


# ---------------------------------------------------------------------------
# RateLimitingMiddleware
# ---------------------------------------------------------------------------


class TestRateLimitingMiddleware:
    """RateLimitingMiddleware should reject calls that exceed the threshold."""

    async def test_allows_calls_under_limit(self):
        mw = RateLimitingMiddleware(max_calls=3, period=60)
        call_next = AsyncMock(return_value=_ok_result())

        for _ in range(3):
            result = await mw.on_call_tool(_make_context(), call_next)
            assert result.content[0].text == "ok"

        assert call_next.await_count == 3

    async def test_rejects_calls_over_limit(self):
        mw = RateLimitingMiddleware(max_calls=2, period=60)
        call_next = AsyncMock(return_value=_ok_result())

        # First two succeed
        await mw.on_call_tool(_make_context(), call_next)
        await mw.on_call_tool(_make_context(), call_next)

        # Third is rejected
        result = await mw.on_call_tool(_make_context(), call_next)

        assert "Rate limit exceeded" in result.content[0].text
        assert call_next.await_count == 2  # third call never reached handler

    async def test_sliding_window_expires_old_calls(self):
        mw = RateLimitingMiddleware(max_calls=1, period=60)
        call_next = AsyncMock(return_value=_ok_result())

        # First call succeeds
        await mw.on_call_tool(_make_context(), call_next)

        # Simulate the timestamp being old enough to fall outside the window
        key = next(iter(mw._timestamps))
        mw._timestamps[key] = [mw._timestamps[key][0] - 120]

        # Next call should succeed because the old one expired
        result = await mw.on_call_tool(_make_context(), call_next)
        assert result.content[0].text == "ok"
        assert call_next.await_count == 2

    async def test_calls_with_different_tokens_have_separate_budgets(self):
        """A runaway loop on one token shouldn't starve another token's budget."""
        mw = RateLimitingMiddleware(max_calls=1, period=60)
        call_next = AsyncMock(return_value=_ok_result())

        ctx_a = _make_context_with_args(arguments={"access_token": "token-a"})
        ctx_b = _make_context_with_args(arguments={"access_token": "token-b"})

        result_a1 = await mw.on_call_tool(ctx_a, call_next)
        result_b1 = await mw.on_call_tool(ctx_b, call_next)
        assert result_a1.content[0].text == "ok"
        assert result_b1.content[0].text == "ok"

        # token-a is now over budget, but token-b should be unaffected
        result_a2 = await mw.on_call_tool(ctx_a, call_next)
        result_b2 = await mw.on_call_tool(ctx_b, call_next)
        assert "Rate limit exceeded" in result_a2.content[0].text
        assert "Rate limit exceeded" in result_b2.content[0].text
        assert call_next.await_count == 2

    async def test_calls_with_no_token_share_the_default_budget(self):
        """Calls that fall back to the server's own token share one bucket."""
        mw = RateLimitingMiddleware(max_calls=1, period=60)
        call_next = AsyncMock(return_value=_ok_result())

        await mw.on_call_tool(_make_context_with_args(arguments={}), call_next)
        result = await mw.on_call_tool(_make_context(), call_next)

        assert "Rate limit exceeded" in result.content[0].text
        assert call_next.await_count == 1

    async def test_stale_token_buckets_are_pruned(self):
        """Buckets for tokens that have gone quiet shouldn't accumulate forever."""
        mw = RateLimitingMiddleware(max_calls=10, period=60)
        call_next = AsyncMock(return_value=_ok_result())

        stale_ctx = _make_context_with_args(arguments={"access_token": "stale-token"})
        await mw.on_call_tool(stale_ctx, call_next)
        stale_key = mw._rate_limit_key(stale_ctx)
        assert stale_key in mw._timestamps

        # Age the stale token's timestamp out of the window, then make an
        # unrelated call - the sweep should drop the stale bucket entirely.
        mw._timestamps[stale_key] = [mw._timestamps[stale_key][0] - 120]
        fresh_ctx = _make_context_with_args(arguments={"access_token": "fresh-token"})
        await mw.on_call_tool(fresh_ctx, call_next)

        assert stale_key not in mw._timestamps
        assert mw._rate_limit_key(fresh_ctx) in mw._timestamps
        assert len(mw._timestamps) == 1


# ---------------------------------------------------------------------------
# TimingMiddleware
# ---------------------------------------------------------------------------


class TestTimingMiddleware:
    """TimingMiddleware should log elapsed time for every tool call."""

    async def test_logs_elapsed_time(self, caplog):
        mw = TimingMiddleware()
        call_next = AsyncMock(return_value=_ok_result())

        with caplog.at_level(logging.INFO, logger="datawrapper_mcp"):
            result = await mw.on_call_tool(_make_context("timed_tool"), call_next)

        assert result.content[0].text == "ok"
        assert "timed_tool" in caplog.text
        assert "completed in" in caplog.text

    async def test_logs_even_when_handler_raises(self, caplog):
        mw = TimingMiddleware()
        call_next = AsyncMock(side_effect=RuntimeError("fail"))

        with caplog.at_level(logging.INFO, logger="datawrapper_mcp"):
            with pytest.raises(RuntimeError, match="fail"):
                await mw.on_call_tool(_make_context("failing_tool"), call_next)

        # Timing is logged even when the handler raises because the log call
        # lives in a finally block. Verify that the timing log is present and
        # that the middleware does not swallow the error on its own.
        assert "failing_tool" in caplog.text
        assert "completed in" in caplog.text


# ---------------------------------------------------------------------------
# BearerTokenMiddleware
# ---------------------------------------------------------------------------


class TestBearerTokenMiddleware:
    """BearerTokenMiddleware should inject bearer tokens into tool arguments."""

    async def test_injects_token_from_header(self):
        """Bearer token from header is injected as access_token."""
        mw = BearerTokenMiddleware()
        call_next = AsyncMock(return_value=_ok_result())
        ctx = _make_context_with_args(arguments={"chart_id": "abc"})

        with patch(
            "datawrapper_mcp.middleware.get_http_headers",
            return_value={"authorization": "Bearer dw_my_token"},
        ):
            await mw.on_call_tool(ctx, call_next)

        assert ctx.message.arguments["access_token"] == "dw_my_token"

    async def test_explicit_arg_takes_precedence(self):
        """Explicit access_token tool argument is not overwritten by header."""
        mw = BearerTokenMiddleware()
        call_next = AsyncMock(return_value=_ok_result())
        ctx = _make_context_with_args(
            arguments={"chart_id": "abc", "access_token": "explicit_token"},
        )

        with patch(
            "datawrapper_mcp.middleware.get_http_headers",
            return_value={"authorization": "Bearer header_token"},
        ):
            await mw.on_call_tool(ctx, call_next)

        assert ctx.message.arguments["access_token"] == "explicit_token"

    async def test_noop_when_no_header(self):
        """No injection when no Authorization header (e.g. stdio transport)."""
        mw = BearerTokenMiddleware()
        call_next = AsyncMock(return_value=_ok_result())
        ctx = _make_context_with_args(arguments={"chart_id": "abc"})

        with patch(
            "datawrapper_mcp.middleware.get_http_headers",
            return_value={},
        ):
            await mw.on_call_tool(ctx, call_next)

        assert "access_token" not in ctx.message.arguments

    async def test_noop_for_non_bearer_header(self):
        """No injection for non-Bearer auth schemes."""
        mw = BearerTokenMiddleware()
        call_next = AsyncMock(return_value=_ok_result())
        ctx = _make_context_with_args(arguments={"chart_id": "abc"})

        with patch(
            "datawrapper_mcp.middleware.get_http_headers",
            return_value={"authorization": "Basic dXNlcjpwYXNz"},
        ):
            await mw.on_call_tool(ctx, call_next)

        assert "access_token" not in ctx.message.arguments

    async def test_noop_when_arguments_is_none(self):
        """No crash when message.arguments is None."""
        mw = BearerTokenMiddleware()
        call_next = AsyncMock(return_value=_ok_result())
        ctx = _make_context_with_args(arguments=None)

        with patch(
            "datawrapper_mcp.middleware.get_http_headers",
            return_value={"authorization": "Bearer dw_token"},
        ):
            await mw.on_call_tool(ctx, call_next)

        assert ctx.message.arguments is None

    async def test_no_injection_for_tools_outside_inject_for(self):
        """Token is NOT injected into tools not listed in inject_for.

        list_chart_types and get_chart_schema don't call the Datawrapper API
        and have no access_token parameter.  Injecting the header token into
        them caused a pydantic ValidationError ("Unexpected keyword argument").
        """
        mw = BearerTokenMiddleware(inject_for=frozenset({"create_chart"}))
        call_next = AsyncMock(return_value=_ok_result())
        ctx = _make_context_with_args(
            tool_name="list_chart_types",
            arguments={},
        )

        with patch(
            "datawrapper_mcp.middleware.get_http_headers",
            return_value={"authorization": "Bearer dw_my_token"},
        ):
            await mw.on_call_tool(ctx, call_next)

        assert "access_token" not in ctx.message.arguments

    async def test_injects_for_tools_in_inject_for(self):
        """Token IS injected for tools listed in inject_for."""
        mw = BearerTokenMiddleware(inject_for=frozenset({"create_chart"}))
        call_next = AsyncMock(return_value=_ok_result())
        ctx = _make_context_with_args(
            tool_name="create_chart",
            arguments={"chart_type": "bar"},
        )

        with patch(
            "datawrapper_mcp.middleware.get_http_headers",
            return_value={"authorization": "Bearer dw_my_token"},
        ):
            await mw.on_call_tool(ctx, call_next)

        assert ctx.message.arguments["access_token"] == "dw_my_token"


# ---------------------------------------------------------------------------
# Middleware ordering (as configured on the real server)
# ---------------------------------------------------------------------------


class TestMiddlewareOrder:
    """FastMCP executes middleware in list order (first = outermost).

    RateLimitingMiddleware reads context.message.arguments["access_token"],
    which only exists if BearerTokenMiddleware has already run - so it must
    be listed first. This guards against that ordering silently regressing.
    """

    def test_bearer_token_runs_before_rate_limiting(self):
        from datawrapper_mcp.server import mcp

        names = [type(m).__name__ for m in mcp.middleware]
        assert names.index("BearerTokenMiddleware") < names.index(
            "RateLimitingMiddleware"
        )
