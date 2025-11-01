#!/usr/bin/env python3
"""Test script to show the output of get_chart_schema."""

import json
from datawrapper import BarChart

# Get the JSON schema for BarChart
schema = BarChart.model_json_schema()

# Remove examples that contain DataFrames (not JSON serializable)
if "examples" in schema:
    del schema["examples"]

# Print the full schema
print("=" * 80)
print("FULL BARCHART JSON SCHEMA")
print("=" * 80)
print(json.dumps(schema, indent=2))

print("\n" + "=" * 80)
print("SAMPLE OF KEY FIELDS WITH DESCRIPTIONS")
print("=" * 80)

# Show some key fields to highlight the descriptions
properties = schema.get("properties", {})
sample_fields = [
    "title",
    "intro",
    "byline",
    "source_name",
    "show_value_labels",
    "value_label_format",
    "custom_range",
    "base_color",
    "sort_bars",
]

for field_name in sample_fields:
    if field_name in properties:
        field_info = properties[field_name]
        print(f"\n{field_name}:")
        print(f"  Type: {field_info.get('type', field_info.get('anyOf', 'N/A'))}")
        print(f"  Description: {field_info.get('description', 'N/A')}")
        if "default" in field_info:
            print(f"  Default: {field_info['default']}")

print("\n" + "=" * 80)
print("REQUIRED FIELDS")
print("=" * 80)
required = schema.get("required", [])
print(f"Required fields: {required if required else 'None - all fields are optional'}")

print("\n" + "=" * 80)
print("TOTAL FIELD COUNT")
print("=" * 80)
print(f"Total properties: {len(properties)}")
