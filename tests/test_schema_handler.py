"""Tests for the get_chart_schema handler function."""

import json

import pytest

from datawrapper_mcp.handlers.schema import get_chart_schema


@pytest.mark.asyncio
async def test_get_chart_schema_returns_text_content():
    """Test that get_chart_schema returns a list with one TextContent."""
    result = await get_chart_schema({"chart_type": "bar"})

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].type == "text"
    assert isinstance(result[0].text, str)


@pytest.mark.asyncio
async def test_get_chart_schema_returns_valid_json():
    """Test that get_chart_schema returns valid JSON."""
    result = await get_chart_schema({"chart_type": "bar"})

    # Should be parseable as JSON
    data = json.loads(result[0].text)
    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_get_chart_schema_response_structure():
    """Test that response has expected structure."""
    result = await get_chart_schema({"chart_type": "column"})
    data = json.loads(result[0].text)

    # Check all expected keys are present
    assert "chart_type" in data
    assert "class_name" in data
    assert "schema" in data
    assert "usage" in data

    # Check values
    assert data["chart_type"] == "column"
    assert data["class_name"] == "ColumnChart"
    assert isinstance(data["schema"], dict)
    assert isinstance(data["usage"], str)
    assert "create_chart" in data["usage"].lower()


@pytest.mark.asyncio
async def test_get_chart_schema_json_serializable():
    """Test that the entire result is JSON serializable (no DataFrame errors)."""
    result = await get_chart_schema({"chart_type": "line"})

    # This should not raise "Object of type DataFrame is not JSON serializable"
    json_str = result[0].text
    data = json.loads(json_str)

    # Re-serialize to ensure everything is serializable
    json.dumps(data)  # Should not raise


@pytest.mark.asyncio
async def test_get_chart_schema_removes_examples():
    """Test that DataFrame examples are removed from schema."""
    result = await get_chart_schema({"chart_type": "bar"})
    data = json.loads(result[0].text)

    # The schema should not contain examples field
    assert "examples" not in data["schema"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "chart_type,expected_class",
    [
        ("bar", "BarChart"),
        ("line", "LineChart"),
        ("area", "AreaChart"),
        ("arrow", "ArrowChart"),
        ("column", "ColumnChart"),
        ("multiple_column", "MultipleColumnChart"),
        ("scatter", "ScatterPlot"),
        ("stacked_bar", "StackedBarChart"),
    ],
)
async def test_get_chart_schema_all_chart_types(chart_type, expected_class):
    """Test that get_chart_schema works for all supported chart types."""
    result = await get_chart_schema({"chart_type": chart_type})
    data = json.loads(result[0].text)

    assert data["chart_type"] == chart_type
    assert data["class_name"] == expected_class
    assert "schema" in data
    assert isinstance(data["schema"], dict)


@pytest.mark.asyncio
async def test_get_chart_schema_invalid_chart_type():
    """Test that invalid chart type raises KeyError."""
    with pytest.raises(KeyError):
        await get_chart_schema({"chart_type": "invalid_type"})


@pytest.mark.asyncio
async def test_get_chart_schema_missing_chart_type():
    """Test that missing chart_type argument raises KeyError."""
    with pytest.raises(KeyError):
        await get_chart_schema({})


@pytest.mark.asyncio
async def test_get_chart_schema_has_properties():
    """Test that returned schema contains properties."""
    result = await get_chart_schema({"chart_type": "bar"})
    data = json.loads(result[0].text)

    schema = data["schema"]
    assert "properties" in schema
    assert isinstance(schema["properties"], dict)
    assert len(schema["properties"]) > 0


@pytest.mark.asyncio
async def test_get_chart_schema_property_count():
    """Test that schema has a reasonable number of properties."""
    result = await get_chart_schema({"chart_type": "column"})
    data = json.loads(result[0].text)

    properties = data["schema"].get("properties", {})
    # Should have many properties for chart configuration
    assert len(properties) > 10


@pytest.mark.asyncio
async def test_get_chart_schema_has_type():
    """Test that schema has type field."""
    result = await get_chart_schema({"chart_type": "line"})
    data = json.loads(result[0].text)

    schema = data["schema"]
    assert "type" in schema
    assert schema["type"] == "object"


@pytest.mark.asyncio
async def test_get_chart_schema_no_dataframe_in_nested_objects():
    """Test that no DataFrame objects exist anywhere in the result."""
    result = await get_chart_schema({"chart_type": "scatter"})

    # If this doesn't raise, there are no DataFrames
    json_str = result[0].text
    data = json.loads(json_str)

    # Try to re-serialize the entire structure
    # This will fail if any DataFrames are present
    json.dumps(data, indent=2)


@pytest.mark.asyncio
async def test_get_chart_schema_usage_field_helpful():
    """Test that usage field provides helpful information."""
    result = await get_chart_schema({"chart_type": "area"})
    data = json.loads(result[0].text)

    usage = data["usage"]
    assert len(usage) > 20  # Should be a meaningful message
    assert "schema" in usage.lower()
    assert "chart_config" in usage.lower() or "properties" in usage.lower()
