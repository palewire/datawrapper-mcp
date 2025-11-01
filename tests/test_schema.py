"""Tests for chart schema generation."""

import json

from datawrapper import BarChart


def test_bar_chart_schema_structure():
    """Test that BarChart schema has expected structure."""
    schema = BarChart.model_json_schema()

    # Remove examples that contain DataFrames (not JSON serializable)
    if "examples" in schema:
        del schema["examples"]

    # Verify basic schema structure
    assert "properties" in schema
    assert "type" in schema
    assert schema["type"] == "object"

    # Verify schema is JSON serializable
    json_str = json.dumps(schema)
    assert json_str is not None


def test_bar_chart_schema_key_fields():
    """Test that BarChart schema contains expected key fields."""
    schema = BarChart.model_json_schema()
    properties = schema.get("properties", {})

    # Check for key fields that should be present
    # Note: Pydantic JSON schema uses hyphens, not underscores
    expected_fields = [
        "title",
        "intro",
        "byline",
        "source-name",
        "source-url",
        "show-value-labels",
        "value-label-format",
        "custom-range",
        "base-color",
        "sort-bars",
    ]

    for field_name in expected_fields:
        assert field_name in properties, (
            f"Expected field '{field_name}' not found in schema"
        )


def test_bar_chart_schema_field_descriptions():
    """Test that key fields have descriptions."""
    schema = BarChart.model_json_schema()
    properties = schema.get("properties", {})

    # Fields that should have descriptions
    # Note: Pydantic JSON schema uses hyphens, not underscores
    fields_with_descriptions = ["title", "intro", "byline", "source-name"]

    for field_name in fields_with_descriptions:
        field_info = properties.get(field_name, {})
        assert "description" in field_info or "title" in field_info, (
            f"Field '{field_name}' should have a description or title"
        )


def test_bar_chart_schema_field_types():
    """Test that key fields have correct types."""
    schema = BarChart.model_json_schema()
    properties = schema.get("properties", {})

    # Check specific field types
    title_field = properties.get("title", {})
    assert "type" in title_field or "anyOf" in title_field, (
        "title field should have type information"
    )

    # If type is present, it should be string or allow null
    if "type" in title_field:
        assert title_field["type"] in ["string", "null"] or isinstance(
            title_field["type"], list
        )


def test_bar_chart_schema_no_required_fields():
    """Test that BarChart has no required fields (all optional)."""
    schema = BarChart.model_json_schema()
    required = schema.get("required", [])

    # All fields should be optional for chart configuration
    assert len(required) == 0, f"Expected no required fields, but found: {required}"


def test_bar_chart_schema_property_count():
    """Test that BarChart schema has a reasonable number of properties."""
    schema = BarChart.model_json_schema()
    properties = schema.get("properties", {})

    # Should have many properties for chart configuration
    assert len(properties) > 10, (
        f"Expected more than 10 properties, found {len(properties)}"
    )
