"""Tests for the auto-preview helper and its integration with create/update handlers."""

import base64
import struct
from unittest.mock import MagicMock, patch

from datawrapper_mcp.handlers.preview import (
    PNG_SIGNATURE,
    PREVIEW_EXPORT_TIMEOUT,
    try_export_preview,
)


class TestTryExportPreview:
    """Tests for the try_export_preview helper."""

    async def test_returns_image_content_on_success(self):
        """Test that a successful export returns ImageContent."""
        mock_chart = MagicMock()
        mock_chart.export_png.return_value = b"PNG_IMAGE_DATA"

        result = await try_export_preview(mock_chart)

        assert result is not None
        assert result.type == "image"
        assert result.mime_type == "image/png"
        expected_base64 = base64.b64encode(b"PNG_IMAGE_DATA").decode("utf-8")
        assert result.data == expected_base64
        mock_chart.export_png.assert_called_once_with(
            zoom=1, access_token=None, timeout=PREVIEW_EXPORT_TIMEOUT
        )

    async def test_returns_none_on_failure(self):
        """Test that a failed export returns None and logs a warning."""
        mock_chart = MagicMock()
        mock_chart.export_png.side_effect = Exception("Export failed")

        result = await try_export_preview(mock_chart)

        assert result is None

    async def test_fit_height_exports_and_saves_the_natural_height(self):
        """A fitted preview is exported at auto height, and that height saved."""
        mock_chart = MagicMock()
        mock_chart.chart_id = "abc12"
        mock_chart.export_png.return_value = png_header(600, 735)

        with patch("datawrapper_mcp.handlers.preview.Datawrapper") as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client._CHARTS_URL = "https://api.datawrapper.de/v3/charts"
            result = await try_export_preview(mock_chart, "tok", fit_height=True)

        assert result is not None
        mock_chart.export_png.assert_called_once_with(
            zoom=1, access_token="tok", timeout=PREVIEW_EXPORT_TIMEOUT, height="auto"
        )
        mock_client_cls.assert_called_once_with(access_token="tok")
        mock_client.patch.assert_called_once_with(
            "https://api.datawrapper.de/v3/charts/abc12",
            data={"metadata": {"publish": {"embed-height": 735}}},
        )

    async def test_fit_height_keeps_the_preview_if_saving_fails(self):
        """A failed height update doesn't cost the caller its preview."""
        mock_chart = MagicMock()
        mock_chart.chart_id = "abc12"
        mock_chart.export_png.return_value = png_header(600, 735)

        with patch("datawrapper_mcp.handlers.preview.Datawrapper") as mock_client_cls:
            mock_client_cls.return_value.patch.side_effect = Exception("API down")
            result = await try_export_preview(mock_chart, fit_height=True)

        assert result is not None


def png_header(width: int, height: int) -> bytes:
    """The start of a PNG file: signature and IHDR chunk."""
    return (
        PNG_SIGNATURE
        + struct.pack(">I", 13)
        + b"IHDR"
        + struct.pack(">II", width, height)
        + bytes(5)
    )


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
                "datawrapper_mcp.config.CHART_CLASSES",
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
        assert images[0].mime_type == "image/png"

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
                "datawrapper_mcp.config.CHART_CLASSES",
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
        assert images[0].mime_type == "image/png"

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
