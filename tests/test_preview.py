"""Tests for the auto-preview helper and its integration with create/update handlers."""

import base64
from unittest.mock import MagicMock, patch

import pytest

from datawrapper_mcp.handlers.preview import try_export_preview


class TestTryExportPreview:
    """Tests for the try_export_preview helper."""

    def test_returns_image_content_on_success(self):
        """Test that a successful export returns ImageContent."""
        mock_chart = MagicMock()
        mock_chart.export_png.return_value = b"PNG_IMAGE_DATA"

        result = try_export_preview(mock_chart)

        assert result is not None
        assert result.type == "image"
        assert result.mimeType == "image/png"
        expected_base64 = base64.b64encode(b"PNG_IMAGE_DATA").decode("utf-8")
        assert result.data == expected_base64
        mock_chart.export_png.assert_called_once_with(zoom=1)

    def test_returns_none_on_failure(self):
        """Test that a failed export returns None and logs a warning."""
        mock_chart = MagicMock()
        mock_chart.export_png.side_effect = Exception("Export failed")

        result = try_export_preview(mock_chart)

        assert result is None


@pytest.mark.asyncio
class TestCreateChartPreview:
    """Tests for preview integration in create_chart handler."""

    async def test_create_includes_preview(self, mock_api_token):
        """Test that create_chart appends an ImageContent when export succeeds."""
        from datawrapper_mcp.handlers.create import create_chart

        mock_instance = MagicMock()
        mock_instance.chart_id = "abc123"
        mock_instance.title = "Test Chart"
        mock_instance.get_editor_url.return_value = (
            "https://app.datawrapper.de/chart/abc123/edit"
        )
        mock_instance.export_png.return_value = b"PNG_DATA"

        chart_cls = MagicMock()
        chart_cls.model_validate.return_value = mock_instance
        with (
            patch(
                "datawrapper_mcp.handlers.create.CHART_CLASSES",
                {"bar": chart_cls},
            ),
            patch(
                "datawrapper_mcp.handlers.create.json_to_dataframe",
                return_value=MagicMock(),
            ),
        ):
            arguments = {
                "chart_type": "bar",
                "data": [{"x": 1}],
                "chart_config": {"title": "Test Chart"},
            }

            metadata, images = await create_chart(arguments)

        assert metadata["chart_id"] == "abc123"
        assert metadata["title"] == "Test Chart"
        assert len(images) == 1
        assert images[0].type == "image"
        assert images[0].mimeType == "image/png"

    async def test_create_without_preview_on_export_failure(self, mock_api_token):
        """Test that create_chart returns only metadata when export fails."""
        from datawrapper_mcp.handlers.create import create_chart

        mock_instance = MagicMock()
        mock_instance.chart_id = "abc123"
        mock_instance.title = "Test Chart"
        mock_instance.get_editor_url.return_value = (
            "https://app.datawrapper.de/chart/abc123/edit"
        )
        mock_instance.export_png.side_effect = Exception("Export unavailable")

        chart_cls = MagicMock()
        chart_cls.model_validate.return_value = mock_instance
        with (
            patch(
                "datawrapper_mcp.handlers.create.CHART_CLASSES",
                {"bar": chart_cls},
            ),
            patch(
                "datawrapper_mcp.handlers.create.json_to_dataframe",
                return_value=MagicMock(),
            ),
        ):
            arguments = {
                "chart_type": "bar",
                "data": [{"x": 1}],
                "chart_config": {"title": "Test Chart"},
            }

            metadata, images = await create_chart(arguments)

        assert metadata["chart_id"] == "abc123"
        assert len(images) == 0


@pytest.mark.asyncio
class TestUpdateChartPreview:
    """Tests for preview integration in update_chart handler."""

    async def test_update_includes_preview(self, mock_api_token, mock_get_chart):
        """Test that update_chart appends an ImageContent when export succeeds."""
        from datawrapper_mcp.handlers.update import update_chart

        mock_chart = mock_get_chart.return_value
        mock_chart.update = MagicMock()
        mock_chart.export_png.return_value = b"PNG_DATA"

        arguments = {
            "chart_id": "test123",
            "chart_config": {"title": "Updated Title"},
        }

        metadata, images = await update_chart(arguments)

        assert "chart_id" in metadata
        assert len(images) == 1
        assert images[0].type == "image"
        assert images[0].mimeType == "image/png"

    async def test_update_without_preview_on_export_failure(
        self, mock_api_token, mock_get_chart
    ):
        """Test that update_chart returns only metadata when export fails."""
        from datawrapper_mcp.handlers.update import update_chart

        mock_chart = mock_get_chart.return_value
        mock_chart.update = MagicMock()
        mock_chart.export_png.side_effect = Exception("Export unavailable")

        arguments = {
            "chart_id": "test123",
            "chart_config": {"title": "Updated Title"},
        }

        metadata, images = await update_chart(arguments)

        assert "chart_id" in metadata
        assert len(images) == 0
