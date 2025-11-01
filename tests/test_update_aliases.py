"""Test that update_chart handles field aliases correctly."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_update_with_alias_field_names(mock_api_token):
    """Test that alias field names (e.g., 'base-color') are converted to Python names (e.g., 'base_color')."""
    from datawrapper_mcp.handlers.update import update_chart

    with patch("datawrapper_mcp.handlers.update.get_chart") as mock_get_chart:
        mock_chart = MagicMock()
        mock_chart.chart_id = "test123"
        mock_chart.update = MagicMock()
        mock_chart.get_editor_url.return_value = (
            "https://app.datawrapper.de/edit/test123/visualize#refine"
        )

        # Mock model_fields to include a field with an alias
        mock_field_info = MagicMock()
        mock_field_info.alias = "base-color"
        mock_chart.model_fields = {
            "base_color": mock_field_info,
            "title": MagicMock(alias=None),
        }

        mock_get_chart.return_value = mock_chart

        # Use the alias name in chart_config
        arguments = {
            "chart_id": "test123",
            "chart_config": {
                "base-color": "#FF5733",  # Using alias format
                "title": "Test Chart",
            },
        }

        result = await update_chart(arguments)

        # Verify the Python field name was used with setattr
        assert mock_chart.base_color == "#FF5733"
        assert mock_chart.title == "Test Chart"

        # Verify update was called
        mock_chart.update.assert_called_once_with(access_token=mock_api_token)

        # Verify success message
        assert len(result) > 0
        assert result[0].type == "text"
        assert "updated successfully" in result[0].text.lower()


@pytest.mark.asyncio
async def test_update_with_python_field_names(mock_api_token):
    """Test that Python field names still work (e.g., 'base_color')."""
    from datawrapper_mcp.handlers.update import update_chart

    with patch("datawrapper_mcp.handlers.update.get_chart") as mock_get_chart:
        mock_chart = MagicMock()
        mock_chart.chart_id = "test123"
        mock_chart.update = MagicMock()
        mock_chart.get_editor_url.return_value = (
            "https://app.datawrapper.de/edit/test123/visualize#refine"
        )

        # Mock model_fields
        mock_field_info = MagicMock()
        mock_field_info.alias = "base-color"
        mock_chart.model_fields = {
            "base_color": mock_field_info,
            "title": MagicMock(alias=None),
        }

        mock_get_chart.return_value = mock_chart

        # Use the Python field name in chart_config
        arguments = {
            "chart_id": "test123",
            "chart_config": {
                "base_color": "#FF5733",  # Using Python field name
                "title": "Test Chart",
            },
        }

        result = await update_chart(arguments)

        # Verify the field was set correctly
        assert mock_chart.base_color == "#FF5733"
        assert mock_chart.title == "Test Chart"

        # Verify update was called
        mock_chart.update.assert_called_once_with(access_token=mock_api_token)

        # Verify success message
        assert len(result) > 0
        assert result[0].type == "text"
        assert "updated successfully" in result[0].text.lower()


@pytest.mark.asyncio
async def test_update_with_mixed_alias_and_python_names(mock_api_token):
    """Test that a mix of alias and Python field names works."""
    from datawrapper_mcp.handlers.update import update_chart

    with patch("datawrapper_mcp.handlers.update.get_chart") as mock_get_chart:
        mock_chart = MagicMock()
        mock_chart.chart_id = "test123"
        mock_chart.update = MagicMock()
        mock_chart.get_editor_url.return_value = (
            "https://app.datawrapper.de/edit/test123/visualize#refine"
        )

        # Mock model_fields with multiple fields with aliases
        mock_chart.model_fields = {
            "base_color": MagicMock(alias="base-color"),
            "source_name": MagicMock(alias="source-name"),
            "title": MagicMock(alias=None),
        }

        mock_get_chart.return_value = mock_chart

        # Mix of alias and Python field names
        arguments = {
            "chart_id": "test123",
            "chart_config": {
                "base-color": "#FF5733",  # Alias
                "source_name": "Test Source",  # Python name
                "title": "Test Chart",  # No alias
            },
        }

        result = await update_chart(arguments)

        # Verify all fields were set correctly
        assert mock_chart.base_color == "#FF5733"
        assert mock_chart.source_name == "Test Source"
        assert mock_chart.title == "Test Chart"

        # Verify update was called
        mock_chart.update.assert_called_once_with(access_token=mock_api_token)

        # Verify success message
        assert len(result) > 0
        assert result[0].type == "text"
        assert "updated successfully" in result[0].text.lower()
