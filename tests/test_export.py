"""Tests for export handler."""

import base64
from unittest.mock import MagicMock, patch

import pytest

from datawrapper_mcp.handlers.export import export_chart_png
from datawrapper_mcp.types import ExportChartPngArgs


@pytest.mark.asyncio
class TestExportChartPng:
    """Tests for export_chart_png handler."""

    async def test_export_with_border_parameters(self):
        """Test export_chart_png with border_width and border_color."""
        # Mock chart with export_png method
        mock_chart = MagicMock()
        mock_chart.export_png.return_value = b"PNG_IMAGE_DATA"

        with patch("datawrapper_mcp.handlers.export.get_chart") as mock_get_chart:
            mock_get_chart.return_value = mock_chart

            # Create arguments with border parameters
            args: ExportChartPngArgs = {
                "chart_id": "test123",
                "border_width": 10,
                "border_color": "#FF0000",
            }

            # Call handler
            result = await export_chart_png(args)

            # Verify get_chart was called correctly
            mock_get_chart.assert_called_once_with("test123")

            # Verify export_png was called with border parameters
            mock_chart.export_png.assert_called_once_with(
                border_width=10, border_color="#FF0000"
            )

            # Verify result
            assert len(result) == 1
            assert result[0].type == "image"
            assert result[0].mimeType == "image/png"
            expected_base64 = base64.b64encode(b"PNG_IMAGE_DATA").decode("utf-8")
            assert result[0].data == expected_base64

    async def test_export_with_all_parameters(self):
        """Test export_chart_png with all parameters including borders."""
        # Mock chart with export_png method
        mock_chart = MagicMock()
        mock_chart.export_png.return_value = b"PNG_IMAGE_DATA"

        with patch("datawrapper_mcp.handlers.export.get_chart") as mock_get_chart:
            mock_get_chart.return_value = mock_chart

            # Create arguments with all parameters
            args: ExportChartPngArgs = {
                "chart_id": "test123",
                "width": 800,
                "height": 600,
                "plain": True,
                "zoom": 2,
                "transparent": True,
                "border_width": 5,
                "border_color": "#00FF00",
            }

            # Call handler
            result = await export_chart_png(args)

            # Verify export_png was called with all parameters
            mock_chart.export_png.assert_called_once_with(
                width=800,
                height=600,
                plain=True,
                zoom=2,
                transparent=True,
                border_width=5,
                border_color="#00FF00",
            )

            # Verify result
            assert len(result) == 1
            assert result[0].type == "image"
            assert result[0].mimeType == "image/png"

    async def test_export_without_border_parameters(self):
        """Test export_chart_png without border parameters."""
        # Mock chart with export_png method
        mock_chart = MagicMock()
        mock_chart.export_png.return_value = b"PNG_IMAGE_DATA"

        with patch("datawrapper_mcp.handlers.export.get_chart") as mock_get_chart:
            mock_get_chart.return_value = mock_chart

            # Create arguments without border parameters
            args: ExportChartPngArgs = {
                "chart_id": "test123",
                "width": 800,
                "height": 600,
            }

            # Call handler
            result = await export_chart_png(args)

            # Verify export_png was called without border parameters
            mock_chart.export_png.assert_called_once_with(width=800, height=600)

            # Verify result
            assert len(result) == 1
            assert result[0].type == "image"

    async def test_export_minimal_parameters(self):
        """Test export_chart_png with only chart_id."""
        # Mock chart with export_png method
        mock_chart = MagicMock()
        mock_chart.export_png.return_value = b"PNG_IMAGE_DATA"

        with patch("datawrapper_mcp.handlers.export.get_chart") as mock_get_chart:
            mock_get_chart.return_value = mock_chart

            # Create arguments with only chart_id
            args: ExportChartPngArgs = {"chart_id": "test123"}

            # Call handler
            result = await export_chart_png(args)

            # Verify export_png was called with no parameters
            mock_chart.export_png.assert_called_once_with()

            # Verify result
            assert len(result) == 1
            assert result[0].type == "image"
            assert result[0].mimeType == "image/png"

    async def test_export_with_only_border_width(self):
        """Test export_chart_png with only border_width (no color)."""
        # Mock chart with export_png method
        mock_chart = MagicMock()
        mock_chart.export_png.return_value = b"PNG_IMAGE_DATA"

        with patch("datawrapper_mcp.handlers.export.get_chart") as mock_get_chart:
            mock_get_chart.return_value = mock_chart

            # Create arguments with only border_width
            args: ExportChartPngArgs = {
                "chart_id": "test123",
                "border_width": 15,
            }

            # Call handler
            result = await export_chart_png(args)

            # Verify export_png was called with only border_width
            mock_chart.export_png.assert_called_once_with(border_width=15)

            # Verify result
            assert len(result) == 1
            assert result[0].type == "image"

    async def test_export_with_only_border_color(self):
        """Test export_chart_png with only border_color (no width)."""
        # Mock chart with export_png method
        mock_chart = MagicMock()
        mock_chart.export_png.return_value = b"PNG_IMAGE_DATA"

        with patch("datawrapper_mcp.handlers.export.get_chart") as mock_get_chart:
            mock_get_chart.return_value = mock_chart

            # Create arguments with only border_color
            args: ExportChartPngArgs = {
                "chart_id": "test123",
                "border_color": "#0000FF",
            }

            # Call handler
            result = await export_chart_png(args)

            # Verify export_png was called with only border_color
            mock_chart.export_png.assert_called_once_with(border_color="#0000FF")

            # Verify result
            assert len(result) == 1
            assert result[0].type == "image"

    async def test_export_base64_encoding(self):
        """Test that PNG data is correctly base64 encoded."""
        # Mock chart with export_png method
        mock_chart = MagicMock()
        test_png_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        mock_chart.export_png.return_value = test_png_data

        with patch("datawrapper_mcp.handlers.export.get_chart") as mock_get_chart:
            mock_get_chart.return_value = mock_chart

            # Create arguments
            args: ExportChartPngArgs = {
                "chart_id": "test123",
                "border_width": 10,
                "border_color": "#FFFFFF",
            }

            # Call handler
            result = await export_chart_png(args)

            # Verify base64 encoding
            expected_base64 = base64.b64encode(test_png_data).decode("utf-8")
            assert result[0].data == expected_base64

    async def test_export_error_handling(self):
        """Test error handling when chart export fails."""
        with patch("datawrapper_mcp.handlers.export.get_chart") as mock_get_chart:
            mock_get_chart.side_effect = Exception("Chart not found")

            # Create arguments
            args: ExportChartPngArgs = {
                "chart_id": "invalid123",
                "border_width": 10,
                "border_color": "#FF0000",
            }

            # Verify exception is raised
            with pytest.raises(Exception, match="Chart not found"):
                await export_chart_png(args)
