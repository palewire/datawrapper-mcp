"""Tests for chart type conversion in get_chart_info handler."""

import json
from unittest.mock import MagicMock, patch

import pytest

from datawrapper_mcp.config import API_TYPE_TO_SIMPLIFIED, CHART_CLASSES
from datawrapper_mcp.handlers.retrieve import get_chart_info


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "simplified_name,api_type",
    [
        ("bar", "d3-bars"),
        ("stacked_bar", "d3-bars-stacked"),
        ("arrow", "d3-arrow-plot"),
        ("column", "column-chart"),
        ("multiple_column", "multiple-columns"),
        ("area", "d3-area"),
        ("line", "d3-lines"),
        ("scatter", "d3-scatter-plot"),
    ],
)
async def test_get_chart_info_returns_simplified_type(simplified_name, api_type):
    """Test that get_chart_info converts API types to simplified names."""
    # Get the chart class for this type
    chart_class = CHART_CLASSES[simplified_name]

    # Create a mock chart instance
    mock_chart = MagicMock(spec=chart_class)
    mock_chart.chart_id = "test123"
    mock_chart.title = "Test Chart"
    mock_chart.chart_type = api_type  # This is the API type
    mock_chart.get_public_url.return_value = "https://datawrapper.dwcdn.net/test123/"
    mock_chart.get_editor_url.return_value = (
        "https://app.datawrapper.de/chart/test123/visualize"
    )

    # Mock model_dump to return a simple config
    mock_chart.model_dump.return_value = {
        "title": "Test Chart",
        "data": None,
    }

    # Mock get_chart to return our mock
    with patch("datawrapper_mcp.handlers.retrieve.get_chart", return_value=mock_chart):
        result = await get_chart_info({"chart_id": "test123"})

    # Parse the JSON response
    response_data = json.loads(result[0].text)

    # Verify the type field contains the simplified name, not the API type
    assert response_data["type"] == simplified_name
    assert response_data["type"] != api_type
    assert response_data["chart_id"] == "test123"
    assert response_data["title"] == "Test Chart"


@pytest.mark.asyncio
async def test_get_chart_info_handles_unknown_type():
    """Test that get_chart_info handles unknown API types gracefully."""
    # Create a mock chart with an unknown type
    mock_chart = MagicMock()
    mock_chart.chart_id = "test123"
    mock_chart.title = "Test Chart"
    mock_chart.chart_type = "unknown-chart-type"  # Not in our mapping
    mock_chart.get_public_url.return_value = "https://datawrapper.dwcdn.net/test123/"
    mock_chart.get_editor_url.return_value = (
        "https://app.datawrapper.de/chart/test123/visualize"
    )
    mock_chart.model_dump.return_value = {
        "title": "Test Chart",
        "data": None,
    }

    with patch("datawrapper_mcp.handlers.retrieve.get_chart", return_value=mock_chart):
        result = await get_chart_info({"chart_id": "test123"})

    response_data = json.loads(result[0].text)

    # Should fall back to the original API type
    assert response_data["type"] == "unknown-chart-type"


def test_api_type_mapping_completeness():
    """Test that all chart classes have corresponding API type mappings."""
    # Get all simplified names from CHART_CLASSES
    simplified_names = set(CHART_CLASSES.keys())

    # Get all simplified names from the reverse mapping
    mapped_names = set(API_TYPE_TO_SIMPLIFIED.values())

    # They should match exactly
    assert simplified_names == mapped_names, (
        f"Mismatch between CHART_CLASSES and API_TYPE_TO_SIMPLIFIED mappings. "
        f"Missing in mapping: {simplified_names - mapped_names}, "
        f"Extra in mapping: {mapped_names - simplified_names}"
    )


def test_api_type_mapping_uniqueness():
    """Test that each API type maps to exactly one simplified name."""
    # Check for duplicate values in the mapping
    api_types = list(API_TYPE_TO_SIMPLIFIED.keys())
    simplified_names = list(API_TYPE_TO_SIMPLIFIED.values())

    assert len(api_types) == len(set(api_types)), "Duplicate API types in mapping"
    assert len(simplified_names) == len(set(simplified_names)), (
        "Duplicate simplified names in mapping"
    )
