"""Test that update_chart properly handles chart_type field during validation."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_update_validates_via_setattr(mock_api_token):
    """Test that Pydantic validates attributes via validate_assignment.

    The new implementation uses direct attribute assignment with setattr(),
    which triggers Pydantic's validate_assignment=True automatically.
    This is simpler and avoids the model_dump/model_validate cycle.
    """
    from datawrapper_mcp.handlers.update import update_chart

    # Mock get_chart to return a ColumnChart instance
    with patch("datawrapper_mcp.handlers.update.get_chart") as mock_get_chart:
        mock_chart = MagicMock()
        mock_chart.chart_id = "test123"
        mock_chart.chart_type = "column-chart"
        mock_chart.update = MagicMock()
        mock_chart.get_editor_url.return_value = (
            "https://app.datawrapper.de/edit/test123/visualize#refine"
        )

        mock_get_chart.return_value = mock_chart

        arguments = {
            "chart_id": "test123",
            "chart_config": {
                "title": "Updated Title",
            },
        }

        result = await update_chart(arguments)

        # Verify attribute was set directly (Pydantic validates automatically)
        assert mock_chart.title == "Updated Title"

        # Verify chart_type was NOT changed
        assert mock_chart.chart_type == "column-chart"

        # Verify update was successful
        assert len(result) > 0
        assert result[0].type == "text"
        assert "updated successfully" in result[0].text.lower()


@pytest.mark.asyncio
async def test_update_only_sets_provided_fields(mock_api_token):
    """Test that only fields in chart_config are updated via setattr.

    The new implementation directly sets attributes from chart_config,
    so only the fields provided should be updated.
    """
    from datawrapper_mcp.handlers.update import update_chart

    with patch("datawrapper_mcp.handlers.update.get_chart") as mock_get_chart:
        mock_chart = MagicMock()
        mock_chart.chart_id = "test123"
        mock_chart.chart_type = "column-chart"
        mock_chart.title = "Original Title"
        mock_chart.intro = "Original Intro"
        mock_chart.update = MagicMock()
        mock_chart.get_editor_url.return_value = (
            "https://app.datawrapper.de/edit/test123/visualize#refine"
        )

        mock_get_chart.return_value = mock_chart

        arguments = {
            "chart_id": "test123",
            "chart_config": {"title": "New Title"},
        }

        result = await update_chart(arguments)

        # Verify only title was updated
        assert mock_chart.title == "New Title"

        # Verify intro was NOT changed (not in chart_config)
        assert mock_chart.intro == "Original Intro"

        # Verify chart_type was NOT changed (never in chart_config)
        assert mock_chart.chart_type == "column-chart"

        # Verify update was successful
        assert len(result) > 0
        assert result[0].type == "text"
        assert "updated successfully" in result[0].text.lower()
