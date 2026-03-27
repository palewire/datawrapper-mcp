"""FastMCP middleware for production hardening.

Provides error handling, rate limiting, and timing middleware
built on the FastMCP Middleware base class.
"""

import asyncio
import logging
import time

from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools import ToolResult
from mcp.types import TextContent

logger = logging.getLogger("datawrapper_mcp")


class BearerTokenMiddleware(Middleware):
    """Inject Authorization bearer token as access_token into tool arguments.

    Reads the HTTP Authorization header and, if present, injects the bearer
    token as ``access_token`` into the tool arguments dict — but only for
    tools listed in *inject_for*. An explicit ``access_token`` tool argument
    always takes precedence (via setdefault).
    On stdio transports, get_http_headers() returns {} so this is a no-op.

    Parameters
    ----------
    inject_for:
        Tool names whose arguments should receive the bearer token.
        When *None* (the default), the token is injected into **every**
        tool call — this preserves backward-compatible behaviour but may
        cause validation errors for tools that do not declare an
        ``access_token`` parameter.
    """

    def __init__(self, *, inject_for: frozenset[str] | None = None) -> None:
        self._inject_for = inject_for

    async def on_call_tool(
        self,
        context: MiddlewareContext,
        call_next: CallNext,
    ) -> ToolResult:
        headers = get_http_headers(include={"authorization"})
        auth = headers.get("authorization", "")
        if auth.startswith("Bearer ") and context.message:
            token = auth.removeprefix("Bearer ").strip()
            if token and context.message.arguments is not None:
                if self._inject_for is None or context.message.name in self._inject_for:
                    context.message.arguments.setdefault("access_token", token)
        return await call_next(context)


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
            raise ToolError(f"Error in {tool_name}: {e}") from e


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
