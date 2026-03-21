"""FastMCP middleware for production hardening.

Provides error handling, rate limiting, and timing middleware
built on the FastMCP Middleware base class.
"""

import asyncio
import logging
import time

from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools import ToolResult
from mcp.types import TextContent

logger = logging.getLogger("datawrapper_mcp")


class ErrorHandlingMiddleware(Middleware):
    """Catch unhandled exceptions in tool handlers and return structured errors."""

    async def on_call_tool(
        self,
        context: MiddlewareContext,
        call_next: CallNext,
    ) -> ToolResult:
        try:
            return await call_next(context)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            tool_name = context.message.name if context.message else "unknown"
            logger.exception("Unhandled error in tool '%s'", tool_name)
            return ToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Error in {tool_name}: {e}",
                    )
                ],
            )


class RateLimitingMiddleware(Middleware):
    """Protect against runaway LLM loops that hammer the Datawrapper API.

    Uses a sliding-window counter: tracks call timestamps within the
    current period and rejects calls that exceed the limit.
    """

    def __init__(self, max_calls: int = 60, period: float = 60.0) -> None:
        self.max_calls = max_calls
        self.period = period
        self._timestamps: list[float] = []

    async def on_call_tool(
        self,
        context: MiddlewareContext,
        call_next: CallNext,
    ) -> ToolResult:
        now = time.monotonic()
        cutoff = now - self.period
        self._timestamps = [t for t in self._timestamps if t > cutoff]

        if len(self._timestamps) >= self.max_calls:
            tool_name = context.message.name if context.message else "unknown"
            logger.warning(
                "Rate limit exceeded for tool '%s': %d calls in %.0fs",
                tool_name,
                self.max_calls,
                self.period,
            )
            return ToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=(
                            f"Rate limit exceeded: {self.max_calls} calls per "
                            f"{self.period:.0f}s. Please wait before retrying."
                        ),
                    )
                ],
            )

        self._timestamps.append(now)
        return await call_next(context)


class TimingMiddleware(Middleware):
    """Log execution time for each tool call."""

    async def on_call_tool(
        self,
        context: MiddlewareContext,
        call_next: CallNext,
    ) -> ToolResult:
        tool_name = context.message.name if context.message else "unknown"
        start = time.monotonic()
        try:
            return await call_next(context)
        finally:
            elapsed = time.monotonic() - start
            logger.info("Tool '%s' completed in %.3fs", tool_name, elapsed)
