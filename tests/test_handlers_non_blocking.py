"""Regression tests: handlers must not block the event loop.

chart.create()/update()/publish()/delete() and get_chart() are synchronous,
network-bound calls into the Datawrapper API. Each handler wraps them in
asyncio.to_thread() so a slow call only delays its own caller instead of
freezing every other concurrent tool call on the server (see export.py's
equivalent test and PR history for the bug this guards against).

Each test schedules a concurrent "canary" task alongside a handler whose
underlying Datawrapper call is mocked to sleep synchronously, then asserts
the canary completes well before the handler does - proving the handler
isn't running that blocking call directly on the event loop.
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

from datawrapper_mcp.handlers.create import create_chart
from datawrapper_mcp.handlers.delete import delete_chart
from datawrapper_mcp.handlers.publish import publish_chart
from datawrapper_mcp.handlers.retrieve import get_chart_info
from datawrapper_mcp.handlers.update import update_chart

SLOW_CALL_SECONDS = 0.2
CANARY_DELAY_SECONDS = 0.05


def _slow_call(*_args, **_kwargs):
    """Stand in for a slow, synchronous Datawrapper API call."""
    time.sleep(SLOW_CALL_SECONDS)


async def _assert_runs_off_the_event_loop(handler_coro) -> None:
    """Run handler_coro concurrently with a canary task and assert the
    canary - which only needs a quick sleep to complete - finishes first.
    """
    released_at: dict[str, float] = {}

    async def canary():
        await asyncio.sleep(CANARY_DELAY_SECONDS)
        released_at["canary"] = time.monotonic()

    start = time.monotonic()
    canary_task = asyncio.create_task(canary())
    await handler_coro
    await canary_task

    assert released_at["canary"] - start < SLOW_CALL_SECONDS


def _mock_chart(**overrides):
    chart = MagicMock()
    chart.chart_id = "abc123"
    chart.title = "Test Chart"
    chart.get_editor_url.return_value = "https://app.datawrapper.de/chart/abc123/edit"
    chart.get_public_url.return_value = "https://datawrapper.dwcdn.net/abc123/"
    chart.model_dump.return_value = {"title": "Test Chart"}
    chart.export_png.return_value = b"PNG"
    for key, value in overrides.items():
        setattr(chart, key, value)
    return chart


async def test_create_chart_runs_off_the_event_loop():
    mock_chart = _mock_chart()
    mock_chart.create.side_effect = _slow_call
    mock_class = MagicMock()
    mock_class.model_validate.return_value = mock_chart

    with (
        patch("datawrapper_mcp.config.CHART_CLASSES", {"bar": mock_class}),
        patch("datawrapper_mcp.handlers.create.try_export_preview", return_value=None),
    ):
        await _assert_runs_off_the_event_loop(
            create_chart(
                {
                    "data": [{"x": 1}],
                    "chart_type": "bar",
                    "chart_config": {"title": "Test Chart"},
                }
            )
        )


async def test_update_chart_runs_off_the_event_loop():
    mock_chart = _mock_chart()

    def slow_get_chart(*_args, **_kwargs):
        _slow_call()
        return mock_chart

    with (
        patch(
            "datawrapper_mcp.handlers.update.get_chart",
            side_effect=slow_get_chart,
        ),
        patch("datawrapper_mcp.handlers.update.try_export_preview", return_value=None),
    ):
        await _assert_runs_off_the_event_loop(
            update_chart({"chart_id": "abc123", "chart_config": {"title": "New Title"}})
        )


async def test_publish_chart_runs_off_the_event_loop():
    mock_chart = _mock_chart()
    mock_chart.publish.side_effect = _slow_call

    with (
        patch("datawrapper_mcp.handlers.publish.get_chart", return_value=mock_chart),
        patch("datawrapper_mcp.handlers.publish.try_export_preview", return_value=None),
    ):
        await _assert_runs_off_the_event_loop(publish_chart({"chart_id": "abc123"}))


async def test_delete_chart_runs_off_the_event_loop():
    mock_chart = _mock_chart()
    mock_chart.delete.side_effect = _slow_call

    with patch("datawrapper_mcp.handlers.delete.get_chart", return_value=mock_chart):
        await _assert_runs_off_the_event_loop(delete_chart({"chart_id": "abc123"}))


async def test_get_chart_info_runs_off_the_event_loop():
    mock_chart = _mock_chart(chart_type="d3-bars")

    def slow_get_chart(*_args, **_kwargs):
        _slow_call()
        return mock_chart

    with patch(
        "datawrapper_mcp.handlers.retrieve.get_chart",
        side_effect=slow_get_chart,
    ):
        await _assert_runs_off_the_event_loop(get_chart_info({"chart_id": "abc123"}))
