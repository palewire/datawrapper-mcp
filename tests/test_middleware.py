"""Tests for production middleware (error handling, rate limiting, timing)."""

import asyncio
import logging
from dataclasses import dataclass
from typing import cast
from unittest.mock import AsyncMock

import pytest

from datawrapper_mcp.middleware import (
    ErrorHandlingMiddleware,
    RateLimitingMiddleware,
    TimingMiddleware,
)
from fastmcp.server.middleware import MiddlewareContext
from fastmcp.tools import ToolResult
from mcp.types import TextContent


@dataclass
class _FakeMessage:
    """Minimal stand-in for a CallToolRequestParams message."""

    name: str = "test_tool"


@dataclass
class _FakeContext:
    """Minimal stand-in for MiddlewareContext with the ``.message.name`` path."""

    message: _FakeMessage


def _make_context(tool_name: str = "test_tool") -> MiddlewareContext:
    """Build a lightweight MiddlewareContext for unit tests.

    The real MiddlewareContext is a frozen dataclass with many fields.
    We only need ``.message.name`` for the middleware under test, so we
    construct a minimal fake and cast it to satisfy static type checkers.
    """
    return cast(MiddlewareContext, _FakeContext(message=_FakeMessage(name=tool_name)))


def _ok_result() -> ToolResult:
    return ToolResult(content=[TextContent(type="text", text="ok")])


# ---------------------------------------------------------------------------
# ErrorHandlingMiddleware
# ---------------------------------------------------------------------------


class TestErrorHandlingMiddleware:
    """ErrorHandlingMiddleware should catch exceptions and return safe responses."""

    @pytest.mark.asyncio
    async def test_passes_through_successful_result(self):
        mw = ErrorHandlingMiddleware()
        call_next = AsyncMock(return_value=_ok_result())

        result = await mw.on_call_tool(_make_context(), call_next)

        assert result.content[0].text == "ok"
        call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_catches_exception_and_raises_tool_error(self):
        from fastmcp.exceptions import ToolError

        mw = ErrorHandlingMiddleware()
        call_next = AsyncMock(side_effect=RuntimeError("boom"))

        with pytest.raises(ToolError, match="my_tool") as exc_info:
            await mw.on_call_tool(_make_context("my_tool"), call_next)

        assert "boom" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_logs_exception(self, caplog):
        from fastmcp.exceptions import ToolError

        mw = ErrorHandlingMiddleware()
        call_next = AsyncMock(side_effect=ValueError("bad value"))

        with caplog.at_level(logging.ERROR, logger="datawrapper_mcp"):
            with pytest.raises(ToolError):
                await mw.on_call_tool(_make_context("broken_tool"), call_next)

        assert "broken_tool" in caplog.text

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_allows_calls_under_limit(self):
        mw = RateLimitingMiddleware(max_calls=3, period=60)
        call_next = AsyncMock(return_value=_ok_result())

        for _ in range(3):
            result = await mw.on_call_tool(_make_context(), call_next)
            assert result.content[0].text == "ok"

        assert call_next.await_count == 3

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_sliding_window_expires_old_calls(self):
        mw = RateLimitingMiddleware(max_calls=1, period=60)
        call_next = AsyncMock(return_value=_ok_result())

        # First call succeeds
        await mw.on_call_tool(_make_context(), call_next)

        # Simulate the timestamp being old enough to fall outside the window
        mw._timestamps = [mw._timestamps[0] - 120]

        # Next call should succeed because the old one expired
        result = await mw.on_call_tool(_make_context(), call_next)
        assert result.content[0].text == "ok"
        assert call_next.await_count == 2


# ---------------------------------------------------------------------------
# TimingMiddleware
# ---------------------------------------------------------------------------


class TestTimingMiddleware:
    """TimingMiddleware should log elapsed time for every tool call."""

    @pytest.mark.asyncio
    async def test_logs_elapsed_time(self, caplog):
        mw = TimingMiddleware()
        call_next = AsyncMock(return_value=_ok_result())

        with caplog.at_level(logging.INFO, logger="datawrapper_mcp"):
            result = await mw.on_call_tool(_make_context("timed_tool"), call_next)

        assert result.content[0].text == "ok"
        assert "timed_tool" in caplog.text
        assert "completed in" in caplog.text

    @pytest.mark.asyncio
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
