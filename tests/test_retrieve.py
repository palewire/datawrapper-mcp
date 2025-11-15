"""Tests for chart retrieval with complete configuration."""

import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from datawrapper_mcp.handlers.retrieve import get_chart_info


@pytest.mark.asyncio
async def test_get_chart_info_returns_complete_config():
    """Test that get_chart_info returns complete Pydantic configuration."""
    # Mock chart object with complete configuration
    mock_chart = MagicMock()
    mock_chart.chart_id = "test123"
    mock_chart.title = "Test Chart"
    mock_chart.chart_type = "bar"
    mock_chart.get_public_url.return_value = "https://datawrapper.dwcdn.net/test123/"
    mock_chart.get_editor_url.return_value = (
        "https://app.datawrapper.de/chart/test123/visualize"
    )

    # Mock complete configuration
    mock_config = {
        "title": "Test Chart",
        "intro": "Test description",
        "byline": "Test Author",
        "source_name": "Test Source",
        "source_url": "https://example.com",
        "color_category": {"Category A": "#1f77b4", "Category B": "#ff7f0e"},
        "custom_range_y": [0, 100],
        "y_grid_format": "0",
        "tooltip_number_format": "0.0",
    }
    mock_chart.model_dump.return_value = mock_config

    with patch("datawrapper_mcp.handlers.retrieve.get_chart", return_value=mock_chart):
        result = await get_chart_info({"chart_id": "test123"})

    # Verify result structure
    assert len(result) == 1
    assert result[0].type == "text"

    # Parse JSON response
    response = json.loads(result[0].text)

    # Verify all expected fields are present
    assert response["chart_id"] == "test123"
    assert response["title"] == "Test Chart"
    assert response["type"] == "bar"
    assert "config" in response
    assert response["public_url"] == "https://datawrapper.dwcdn.net/test123/"
    assert response["edit_url"] == "https://app.datawrapper.de/chart/test123/visualize"

    # Verify complete config is included
    config = response["config"]
    assert config["title"] == "Test Chart"
    assert config["intro"] == "Test description"
    assert config["byline"] == "Test Author"
    assert config["source_name"] == "Test Source"
    assert config["source_url"] == "https://example.com"
    assert config["color_category"] == {
        "Category A": "#1f77b4",
        "Category B": "#ff7f0e",
    }
    assert config["custom_range_y"] == [0, 100]
    assert config["y_grid_format"] == "0"
    assert config["tooltip_number_format"] == "0.0"


@pytest.mark.asyncio
async def test_get_chart_info_config_can_be_reused():
    """Test that retrieved config can be used to create a new chart."""
    # Mock chart with realistic configuration
    mock_chart = MagicMock()
    mock_chart.chart_id = "original123"
    mock_chart.title = "Original Chart"
    mock_chart.chart_type = "line"
    mock_chart.get_public_url.return_value = (
        "https://datawrapper.dwcdn.net/original123/"
    )
    mock_chart.get_editor_url.return_value = (
        "https://app.datawrapper.de/chart/original123/visualize"
    )

    # Configuration that could be reused for a new chart
    reusable_config = {
        "title": "Original Chart",
        "intro": "This is a line chart",
        "lines": [{"column": "sales", "width": "style2", "interpolation": "curved"}],
        "color_category": {"sales": "#1d81a2"},
        "custom_range_y": [0, 1000],
        "y_grid_format": "0,0",
        "tooltip_number_format": "0.00",
    }
    mock_chart.model_dump.return_value = reusable_config

    with patch("datawrapper_mcp.handlers.retrieve.get_chart", return_value=mock_chart):
        result = await get_chart_info({"chart_id": "original123"})

    response = json.loads(result[0].text)
    config = response["config"]

    # Verify config contains all styling properties that could be reused
    assert "lines" in config
    assert config["lines"][0]["column"] == "sales"
    assert config["lines"][0]["width"] == "style2"
    assert config["lines"][0]["interpolation"] == "curved"
    assert "color_category" in config
    assert "custom_range_y" in config
    assert "y_grid_format" in config
    assert "tooltip_number_format" in config

    # Verify the config structure is suitable for create_chart
    # (it should be a dict that can be passed as chart_config parameter)
    assert isinstance(config, dict)
    assert all(isinstance(k, str) for k in config.keys())


@pytest.mark.asyncio
async def test_get_chart_info_includes_all_fields():
    """Test that no fields are excluded from the configuration."""
    mock_chart = MagicMock()
    mock_chart.chart_id = "test456"
    mock_chart.title = "Complete Config Test"
    mock_chart.chart_type = "column"
    mock_chart.get_public_url.return_value = "https://datawrapper.dwcdn.net/test456/"
    mock_chart.get_editor_url.return_value = (
        "https://app.datawrapper.de/chart/test456/visualize"
    )

    # Include various field types to ensure nothing is excluded
    complete_config = {
        "title": "Complete Config Test",
        "intro": "Description",
        "byline": "Author",
        "source_name": "Source",
        "source_url": "https://example.com",
        "data": None,  # Even None values should be included
        "chart_id": "test456",  # Even chart_id should be included
        "color_category": {"A": "#ff0000"},
        "custom_range_y": [0, 100],
        "text_annotations": [{"x": "2023", "y": 50, "text": "Note"}],
        "tooltip_number_format": "0.0",
        "y_grid": "on",
        "x_grid": "off",
    }
    mock_chart.model_dump.return_value = complete_config

    with patch("datawrapper_mcp.handlers.retrieve.get_chart", return_value=mock_chart):
        result = await get_chart_info({"chart_id": "test456"})

    response = json.loads(result[0].text)
    config = response["config"]

    # Verify all fields are present (nothing excluded)
    assert len(config) == len(complete_config)
    for key in complete_config:
        assert key in config
        assert config[key] == complete_config[key]


@pytest.mark.asyncio
async def test_get_chart_info_with_dataframe():
    """Test that DataFrame data is properly serialized to JSON."""
    mock_chart = MagicMock()
    mock_chart.chart_id = "test789"
    mock_chart.title = "DataFrame Test"
    mock_chart.chart_type = "bar"
    mock_chart.get_public_url.return_value = "https://datawrapper.dwcdn.net/test789/"
    mock_chart.get_editor_url.return_value = (
        "https://app.datawrapper.de/chart/test789/visualize"
    )

    # Create a real DataFrame
    df = pd.DataFrame(
        {
            "year": [2020, 2021, 2022],
            "value": [100, 150, 200],
            "category": ["A", "B", "C"],
        }
    )

    # Mock config with real DataFrame
    mock_config = {
        "title": "DataFrame Test",
        "data": df,  # Real DataFrame object
        "color_category": {"A": "#ff0000"},
    }
    mock_chart.model_dump.return_value = mock_config

    with patch("datawrapper_mcp.handlers.retrieve.get_chart", return_value=mock_chart):
        result = await get_chart_info({"chart_id": "test789"})

    # Verify result is JSON serializable
    assert len(result) == 1
    assert result[0].type == "text"

    # Parse JSON response (this would fail if DataFrame wasn't converted)
    response = json.loads(result[0].text)

    # Verify DataFrame was converted to list of records
    config = response["config"]
    assert "data" in config
    assert isinstance(config["data"], list)
    assert len(config["data"]) == 3

    # Verify data structure matches list of records format
    expected_data = [
        {"year": 2020, "value": 100, "category": "A"},
        {"year": 2021, "value": 150, "category": "B"},
        {"year": 2022, "value": 200, "category": "C"},
    ]
    assert config["data"] == expected_data

    # Verify other config fields are preserved
    assert config["title"] == "DataFrame Test"
    assert config["color_category"] == {"A": "#ff0000"}


@pytest.mark.asyncio
async def test_get_chart_info_with_none_data():
    """Test that None data is handled correctly."""
    mock_chart = MagicMock()
    mock_chart.chart_id = "test999"
    mock_chart.title = "No Data Test"
    mock_chart.chart_type = "bar"
    mock_chart.get_public_url.return_value = "https://datawrapper.dwcdn.net/test999/"
    mock_chart.get_editor_url.return_value = (
        "https://app.datawrapper.de/chart/test999/visualize"
    )

    # Mock config with None data
    mock_config = {
        "title": "No Data Test",
        "data": None,
        "color_category": {"A": "#ff0000"},
    }
    mock_chart.model_dump.return_value = mock_config

    with patch("datawrapper_mcp.handlers.retrieve.get_chart", return_value=mock_chart):
        result = await get_chart_info({"chart_id": "test999"})

    # Verify result is JSON serializable
    response = json.loads(result[0].text)

    # Verify None data is preserved
    config = response["config"]
    assert config["data"] is None
    assert config["title"] == "No Data Test"
