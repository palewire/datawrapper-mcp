"""Tests for BYOK (bring-your-own-key) access_token forwarding."""

from unittest.mock import MagicMock, patch

import pytest

from datawrapper_mcp.handlers.create import create_chart
from datawrapper_mcp.handlers.delete import delete_chart
from datawrapper_mcp.handlers.export import export_chart_png
from datawrapper_mcp.handlers.publish import publish_chart
from datawrapper_mcp.handlers.retrieve import get_chart_info
from datawrapper_mcp.handlers.update import update_chart

USER_TOKEN = "user_token_xyz"


@pytest.fixture
def mock_chart():
    """Create a mock chart instance for token-forwarding tests."""
    chart = MagicMock()
    chart.chart_id = "tok_test"
    chart.chart_type = "d3-bars"
    chart.title = "Token Test"
    chart.intro = ""
    chart.byline = ""
    chart.source_name = ""
    chart.source_url = ""
    chart.model_dump.return_value = {"title": "Token Test"}
    chart.get_editor_url.return_value = "https://app.datawrapper.de/chart/tok_test/edit"
    chart.get_public_url.return_value = "https://datawrapper.dwcdn.net/tok_test/"
    chart.export_png.return_value = b"PNG"
    return chart


# -- create_chart --


async def test_create_forwards_token(mock_chart):
    """create_chart passes access_token to chart.create() and preview."""
    mock_class = MagicMock()
    mock_class.model_validate.return_value = mock_chart

    with (
        patch("datawrapper_mcp.config.CHART_CLASSES", {"bar": mock_class}),
        patch("datawrapper_mcp.handlers.create.try_export_preview") as mock_preview,
    ):
        mock_preview.return_value = None
        await create_chart(
            {
                "data": [{"x": 1}],
                "chart_type": "bar",
                "chart_config": {"title": "T"},
                "access_token": USER_TOKEN,
            }
        )

    mock_chart.create.assert_called_once_with(access_token=USER_TOKEN)
    mock_preview.assert_called_once_with(mock_chart, access_token=USER_TOKEN)


async def test_create_normalizes_empty_token(mock_chart):
    """create_chart normalizes empty string to None (env-var fallback)."""
    mock_class = MagicMock()
    mock_class.model_validate.return_value = mock_chart

    with (
        patch("datawrapper_mcp.config.CHART_CLASSES", {"bar": mock_class}),
        patch("datawrapper_mcp.handlers.create.try_export_preview") as mock_preview,
    ):
        mock_preview.return_value = None
        await create_chart(
            {
                "data": [{"x": 1}],
                "chart_type": "bar",
                "chart_config": {"title": "T"},
                "access_token": "",
            }
        )

    mock_chart.create.assert_called_once_with(access_token=None)
    mock_preview.assert_called_once_with(mock_chart, access_token=None)


# -- update_chart --


async def test_update_forwards_token(mock_chart):
    """update_chart passes access_token to get_chart, chart.update(), and preview."""
    with (
        patch(
            "datawrapper_mcp.handlers.update.get_chart", return_value=mock_chart
        ) as mock_get,
        patch("datawrapper_mcp.handlers.update.try_export_preview") as mock_preview,
    ):
        mock_preview.return_value = None
        await update_chart(
            {
                "chart_id": "tok_test",
                "chart_config": {"title": "New"},
                "access_token": USER_TOKEN,
            }
        )

    mock_get.assert_called_once_with("tok_test", access_token=USER_TOKEN)
    mock_chart.update.assert_called_once_with(access_token=USER_TOKEN)
    mock_preview.assert_called_once_with(mock_chart, access_token=USER_TOKEN)


# -- publish_chart --


async def test_publish_forwards_token(mock_chart):
    """publish_chart passes access_token to get_chart, chart.publish(), and preview."""
    with (
        patch(
            "datawrapper_mcp.handlers.publish.get_chart", return_value=mock_chart
        ) as mock_get,
        patch("datawrapper_mcp.handlers.publish.try_export_preview") as mock_preview,
    ):
        mock_preview.return_value = None
        await publish_chart(
            {
                "chart_id": "tok_test",
                "access_token": USER_TOKEN,
            }
        )

    mock_get.assert_called_once_with("tok_test", access_token=USER_TOKEN)
    mock_chart.publish.assert_called_once_with(access_token=USER_TOKEN)
    mock_preview.assert_called_once_with(mock_chart, access_token=USER_TOKEN)


# -- delete_chart --


async def test_delete_forwards_token(mock_chart):
    """delete_chart passes access_token to get_chart and chart.delete()."""
    with patch(
        "datawrapper_mcp.handlers.delete.get_chart", return_value=mock_chart
    ) as mock_get:
        await delete_chart(
            {
                "chart_id": "tok_test",
                "access_token": USER_TOKEN,
            }
        )

    mock_get.assert_called_once_with("tok_test", access_token=USER_TOKEN)
    mock_chart.delete.assert_called_once_with(access_token=USER_TOKEN)


# -- get_chart_info (retrieve) --


async def test_retrieve_forwards_token(mock_chart):
    """get_chart_info passes access_token to get_chart."""
    with patch(
        "datawrapper_mcp.handlers.retrieve.get_chart", return_value=mock_chart
    ) as mock_get:
        await get_chart_info(
            {
                "chart_id": "tok_test",
                "access_token": USER_TOKEN,
            }
        )

    mock_get.assert_called_once_with("tok_test", access_token=USER_TOKEN)


# -- export_chart_png --


async def test_export_forwards_token(mock_chart):
    """export_chart_png passes access_token to get_chart and chart.export_png()."""
    with patch(
        "datawrapper_mcp.handlers.export.get_chart", return_value=mock_chart
    ) as mock_get:
        await export_chart_png(
            {
                "chart_id": "tok_test",
                "access_token": USER_TOKEN,
            }
        )

    mock_get.assert_called_once_with("tok_test", access_token=USER_TOKEN)
    mock_chart.export_png.assert_called_once_with(access_token=USER_TOKEN)
