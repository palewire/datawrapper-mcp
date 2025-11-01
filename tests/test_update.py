"""Tests for update_chart validation."""

import json
from unittest.mock import MagicMock, patch

import pytest
from datawrapper import BarChart
from pydantic import ValidationError


@pytest.mark.asyncio
async def test_update_with_high_level_fields(mock_api_token, mock_get_chart):
    """Test that high-level Pydantic fields are accepted."""
    from datawrapper_mcp.server import update_chart
    
    # Mock the chart's update method
    mock_chart = mock_get_chart.return_value
    mock_chart.model_dump.return_value = {"title": "Original Title"}
    mock_chart.update = MagicMock()
    
    # Mock type() to return a chart class with model_validate
    with patch("datawrapper_mcp.server.type") as mock_type:
        mock_chart_class = MagicMock()
        mock_type.return_value = mock_chart_class
        
        # Mock model_validate to return a validated instance
        validated_chart = MagicMock()
        validated_chart.model_dump.return_value = {
            "title": "Updated Chart Title",
            "intro": "This is an updated introduction",
            "byline": "Updated Author",
            "source_name": "Updated Source",
            "source_url": "https://example.com/updated"
        }
        mock_chart_class.model_validate.return_value = validated_chart
        
        # Use high-level Pydantic fields
        arguments = {
            "chart_id": "test123",
            "chart_config": {
                "title": "Updated Chart Title",
                "intro": "This is an updated introduction",
                "byline": "Updated Author",
                "source_name": "Updated Source",
                "source_url": "https://example.com/updated"
            }
        }
        
        result = await update_chart(arguments)
        
        # Verify the chart was retrieved with access_token as keyword arg
        mock_get_chart.assert_called_once_with("test123", access_token=mock_api_token)
        
        # Verify update was called
        mock_chart.update.assert_called_once_with(access_token=mock_api_token)
        
        # Verify result contains success message
        assert len(result) > 0
        assert result[0].type == "text"
        assert "updated successfully" in result[0].text.lower()


@pytest.mark.asyncio
async def test_update_merges_with_existing_config(mock_api_token, mock_get_chart, mock_bar_chart_class):
    """Test that new config is merged with existing config."""
    from datawrapper_mcp.server import update_chart
    
    # Set up existing chart config
    mock_chart = mock_get_chart.return_value
    mock_chart.model_dump.return_value = {
        "title": "Original Title",
        "intro": "Original intro",
        "byline": "Original Author",
        "source_name": "Original Source",
    }
    mock_chart.update = MagicMock()
    
    # Mock type() to return a chart class with model_validate
    with patch("datawrapper_mcp.server.type") as mock_type:
        mock_chart_class = MagicMock()
        mock_type.return_value = mock_chart_class
        
        # Mock model_validate to return a validated instance with merged config
        validated_chart = MagicMock()
        validated_chart.model_dump.return_value = {
            "title": "New Title",
            "intro": "New intro",
            "byline": "Original Author",
            "source_name": "Original Source",
        }
        mock_chart_class.model_validate.return_value = validated_chart
        
        # Update only title and intro
        arguments = {
            "chart_id": "test123",
            "chart_config": {
                "title": "New Title",
                "intro": "New intro",
            }
        }
        
        result = await update_chart(arguments)
        
        # Verify update was called
        mock_chart.update.assert_called_once_with(access_token=mock_api_token)
        
        # Verify result indicates success
        assert len(result) > 0
        assert result[0].type == "text"


@pytest.mark.asyncio
async def test_update_validates_through_pydantic(mock_api_token, mock_get_chart):
    """Test that config is validated through Pydantic model."""
    from datawrapper_mcp.server import update_chart
    
    mock_chart = mock_get_chart.return_value
    mock_chart.model_dump.return_value = {"title": "Test"}
    mock_chart.update = MagicMock()
    
    # Get the chart class from the mock chart instance
    with patch("datawrapper_mcp.server.type") as mock_type:
        mock_chart_class = MagicMock()
        mock_type.return_value = mock_chart_class
        
        # Mock model_validate to return a validated instance
        validated_chart = MagicMock()
        validated_chart.model_dump.return_value = {
            "title": "Updated Title",
            "intro": "Test intro"
        }
        mock_chart_class.model_validate.return_value = validated_chart
        
        arguments = {
            "chart_id": "test123",
            "chart_config": {
                "title": "Updated Title",
                "intro": "Test intro"
            }
        }
        
        result = await update_chart(arguments)
        
        # Verify model_validate was called
        mock_chart_class.model_validate.assert_called_once()
        
        # Verify the merged config was passed to model_validate
        call_args = mock_chart_class.model_validate.call_args[0][0]
        assert "title" in call_args
        assert call_args["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_update_without_api_token(no_api_token):
    """Test that update fails gracefully without API token."""
    from datawrapper_mcp.server import update_chart
    
    arguments = {
        "chart_id": "test123",
        "chart_config": {"title": "New Title"}
    }
    
    # The call_tool wrapper catches exceptions and returns error text
    # But we're calling update_chart directly, so we expect the ValueError
    try:
        result = await update_chart(arguments)
        # If we get here, check for error in result
        assert len(result) > 0
        assert result[0].type == "text"
        assert "error" in result[0].text.lower() or "token" in result[0].text.lower()
    except ValueError as e:
        # This is expected - the function raises ValueError when no token
        assert "DATAWRAPPER_API_TOKEN" in str(e)


@pytest.mark.asyncio
async def test_update_with_invalid_chart_id(mock_api_token):
    """Test that update handles invalid chart ID gracefully."""
    from datawrapper_mcp.server import update_chart
    
    # Mock get_chart to raise an exception
    with patch("datawrapper_mcp.server.get_chart", side_effect=Exception("Chart not found")):
        arguments = {
            "chart_id": "invalid123",
            "chart_config": {"title": "New Title"}
        }
        
        # The call_tool wrapper catches exceptions, but we're calling directly
        # so we expect the exception to propagate
        try:
            result = await update_chart(arguments)
            # If we get here, check for error in result
            assert len(result) > 0
            assert result[0].type == "text"
            assert "error" in result[0].text.lower()
        except Exception as e:
            # This is expected - the function raises when chart not found
            assert "Chart not found" in str(e)


@pytest.mark.asyncio
async def test_update_preserves_chart_type(mock_api_token, mock_get_chart, mock_bar_chart_class):
    """Test that update preserves the chart type."""
    from datawrapper_mcp.server import update_chart
    
    mock_chart = mock_get_chart.return_value
    mock_chart.chart_type = "d3-bars"
    mock_chart.model_dump.return_value = {"title": "Test"}
    mock_chart.update = MagicMock()
    
    # Mock type() to return a chart class with model_validate
    with patch("datawrapper_mcp.server.type") as mock_type:
        mock_chart_class = MagicMock()
        mock_type.return_value = mock_chart_class
        
        # Mock model_validate to return a validated instance
        validated_chart = MagicMock()
        validated_chart.model_dump.return_value = {"title": "New Title"}
        mock_chart_class.model_validate.return_value = validated_chart
        
        arguments = {
            "chart_id": "test123",
            "chart_config": {"title": "New Title"}
        }
        
        result = await update_chart(arguments)
        
        # Verify chart type wasn't changed
        assert mock_chart.chart_type == "d3-bars"
        
        # Verify update was successful
        mock_chart.update.assert_called_once()


@pytest.mark.asyncio
async def test_update_uses_chart_class_directly(mock_api_token, mock_get_chart):
    """Test that update uses type(chart) to get the chart class."""
    from datawrapper_mcp.server import update_chart
    
    mock_chart = mock_get_chart.return_value
    mock_chart.model_dump.return_value = {"title": "Test"}
    mock_chart.update = MagicMock()
    
    with patch("datawrapper_mcp.server.type") as mock_type:
        mock_chart_class = MagicMock()
        mock_type.return_value = mock_chart_class
        
        validated_chart = MagicMock()
        validated_chart.model_dump.return_value = {"title": "New Title"}
        mock_chart_class.model_validate.return_value = validated_chart
        
        arguments = {
            "chart_id": "test123",
            "chart_config": {"title": "New Title"}
        }
        
        await update_chart(arguments)
        
        # Verify type() was called with the chart instance
        mock_type.assert_called_once_with(mock_chart)
        
        # Verify model_validate was called on the chart class
        mock_chart_class.model_validate.assert_called_once()
