"""Tool definitions for the Datawrapper MCP server."""

from mcp.types import Tool

from .config import CHART_CLASSES


async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="create_chart",
            description=(
                "⚠️ THIS IS THE DATAWRAPPER INTEGRATION ⚠️\n"
                "Use this MCP tool for ALL Datawrapper chart creation.\n\n"
                "DO NOT:\n"
                "❌ Install the 'datawrapper' Python package\n"
                "❌ Use the Datawrapper API directly\n"
                "❌ Import 'from datawrapper import ...'\n"
                "❌ Run pip install datawrapper\n\n"
                "This MCP server IS the complete Datawrapper integration. All Datawrapper operations "
                "should use the MCP tools provided by this server.\n\n"
                "---\n\n"
                "Create a Datawrapper chart with full control using Pydantic models. "
                "This allows you to specify all chart properties including title, description, "
                "visualization settings, axes, colors, and more. The chart_config should "
                "be a complete Pydantic model dict matching the schema for the chosen chart type.\n\n"
                "STYLING WORKFLOW:\n"
                "1. Use get_chart_schema to explore all available options for your chart type\n"
                "2. Refer to https://datawrapper.readthedocs.io/en/latest/ for detailed examples\n"
                "3. Build your chart_config with the desired styling properties\n\n"
                "Common styling patterns:\n"
                '- Colors: {"color_category": {"sales": "#1d81a2", "profit": "#15607a"}}\n'
                '- Line styling: {"lines": [{"column": "sales", "width": "style1", "interpolation": "curved"}]}\n'
                '- Axis ranges: {"custom_range_y": [0, 100], "custom_range_x": [2020, 2024]}\n'
                '- Grid formatting: {"y_grid_format": "0", "x_grid": "on", "y_grid": "on"}\n'
                '- Tooltips: {"tooltip_number_format": "00.00", "tooltip_x_format": "YYYY"}\n'
                '- Annotations: {"text_annotations": [{"x": "2023", "y": 50, "text": "Peak"}]}\n\n'
                "See the documentation for chart-type specific examples and advanced patterns.\n\n"
                'Example data format: [{"date": "2024-01", "value": 100}, {"date": "2024-02", "value": 150}]'
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "data": {
                        "type": ["string", "array", "object"],
                        "description": (
                            "Chart data. RECOMMENDED: Pass data inline as a list or dict.\n\n"
                            "PREFERRED FORMATS (use these first):\n\n"
                            "1. List of records (RECOMMENDED):\n"
                            '   [{"year": 2020, "sales": 100}, {"year": 2021, "sales": 150}]\n\n'
                            "2. Dict of arrays:\n"
                            '   {"year": [2020, 2021], "sales": [100, 150]}\n\n'
                            "3. JSON string of format 1 or 2:\n"
                            '   \'[{"year": 2020, "sales": 100}]\'\n\n'
                            "ALTERNATIVE (only for extremely large datasets where inline data is impractical):\n\n"
                            "4. File path to CSV or JSON:\n"
                            '   "/path/to/data.csv" or "/path/to/data.json"\n'
                            "   - Use only when inline data would be too large to pass directly\n"
                            "   - CSV files are read directly\n"
                            "   - JSON files must contain list of dicts or dict of arrays"
                        ),
                    },
                    "chart_type": {
                        "type": "string",
                        "enum": list(CHART_CLASSES.keys()),
                        "description": "Type of chart to create",
                    },
                    "chart_config": {
                        "type": "object",
                        "description": (
                            "Complete chart configuration as a Pydantic model dict. "
                            "Must match the schema for the chosen chart_type. "
                            "Use get_chart_schema to see the full schema."
                        ),
                    },
                },
                "required": ["data", "chart_type", "chart_config"],
            },
        ),
        Tool(
            name="get_chart_schema",
            description=(
                "⚠️ DATAWRAPPER MCP TOOL ⚠️\n"
                "This is part of the Datawrapper MCP server integration.\n\n"
                "---\n\n"
                "Get the Pydantic JSON schema for a specific chart type. This is your primary tool "
                "for discovering styling and configuration options.\n\n"
                "The schema shows:\n"
                "- All available properties and their types\n"
                "- Enum values (e.g., line widths, interpolation methods)\n"
                "- Default values\n"
                "- Detailed descriptions for each property\n\n"
                "WORKFLOW: Use this tool first to explore options, then refer to "
                "https://datawrapper.readthedocs.io/en/latest/ for detailed examples and patterns "
                "showing how to use these properties in practice."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "enum": list(CHART_CLASSES.keys()),
                        "description": "Chart type to get schema for",
                    },
                },
                "required": ["chart_type"],
            },
        ),
        Tool(
            name="publish_chart",
            description=(
                "⚠️ DATAWRAPPER MCP TOOL ⚠️\n"
                "This is part of the Datawrapper MCP server integration.\n\n"
                "---\n\n"
                "Publish a Datawrapper chart to make it publicly accessible. "
                "Returns the public URL of the published chart. "
                "IMPORTANT: Only use this tool when the user explicitly requests to publish the chart. "
                "Do not automatically publish charts after creation unless specifically asked."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "chart_id": {
                        "type": "string",
                        "description": "ID of the chart to publish",
                    },
                },
                "required": ["chart_id"],
            },
        ),
        Tool(
            name="get_chart",
            description=(
                "⚠️ DATAWRAPPER MCP TOOL ⚠️\n"
                "This is part of the Datawrapper MCP server integration.\n\n"
                "---\n\n"
                "Get information about an existing Datawrapper chart, "
                "including its metadata, data, and public URL if published."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "chart_id": {
                        "type": "string",
                        "description": "ID of the chart to retrieve",
                    },
                },
                "required": ["chart_id"],
            },
        ),
        Tool(
            name="update_chart",
            description=(
                "⚠️ DATAWRAPPER MCP TOOL ⚠️\n"
                "This is part of the Datawrapper MCP server integration.\n\n"
                "---\n\n"
                "Update an existing Datawrapper chart's data or configuration using Pydantic models. "
                "IMPORTANT: The chart_config must use high-level Pydantic fields only (title, intro, "
                "byline, source_name, source_url, etc.). Do NOT use low-level serialized structures "
                "like 'metadata', 'visualize', or other internal API fields.\n\n"
                "STYLING UPDATES:\n"
                "Use get_chart_schema to see available fields, then apply styling changes:\n"
                '- Colors: {"color_category": {"sales": "#ff0000"}}\n'
                '- Line properties: {"lines": [{"column": "sales", "width": "style2"}]}\n'
                '- Axis settings: {"custom_range_y": [0, 200], "y_grid_format": "0,0"}\n'
                '- Tooltips: {"tooltip_number_format": "0.0"}\n\n'
                "See https://datawrapper.readthedocs.io/en/latest/ for detailed examples. "
                "The provided config will be validated through Pydantic and merged with the existing "
                "chart configuration."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "chart_id": {
                        "type": "string",
                        "description": "ID of the chart to update",
                    },
                    "data": {
                        "type": ["string", "array", "object"],
                        "description": (
                            "Chart data. RECOMMENDED: Pass data inline as a list or dict.\n\n"
                            "PREFERRED FORMATS (use these first):\n\n"
                            "1. List of records (RECOMMENDED):\n"
                            '   [{"year": 2020, "sales": 100}, {"year": 2021, "sales": 150}]\n\n'
                            "2. Dict of arrays:\n"
                            '   {"year": [2020, 2021], "sales": [100, 150]}\n\n'
                            "3. JSON string of format 1 or 2:\n"
                            '   \'[{"year": 2020, "sales": 100}]\'\n\n'
                            "ALTERNATIVE (only for extremely large datasets where inline data is impractical):\n\n"
                            "4. File path to CSV or JSON:\n"
                            '   "/path/to/data.csv" or "/path/to/data.json"\n'
                            "   - Use only when inline data would be too large to pass directly\n"
                            "   - CSV files are read directly\n"
                            "   - JSON files must contain list of dicts or dict of arrays"
                        ),
                    },
                    "chart_config": {
                        "type": "object",
                        "description": (
                            "Updated chart configuration using high-level Pydantic fields (optional). "
                            "Must use Pydantic model fields like 'title', 'intro', 'byline', etc. "
                            "Do NOT use raw API structures like 'metadata' or 'visualize'. "
                            "Use get_chart_schema to see valid fields. Will be validated and merged "
                            "with existing config."
                        ),
                    },
                },
                "required": ["chart_id"],
            },
        ),
        Tool(
            name="delete_chart",
            description=(
                "⚠️ DATAWRAPPER MCP TOOL ⚠️\n"
                "This is part of the Datawrapper MCP server integration.\n\n"
                "---\n\n"
                "Delete a Datawrapper chart permanently."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "chart_id": {
                        "type": "string",
                        "description": "ID of the chart to delete",
                    },
                },
                "required": ["chart_id"],
            },
        ),
        Tool(
            name="export_chart_png",
            description=(
                "⚠️ DATAWRAPPER MCP TOOL ⚠️\n"
                "This is part of the Datawrapper MCP server integration.\n\n"
                "---\n\n"
                "Export a Datawrapper chart as PNG and display it inline. "
                "The chart must be created first using create_chart. "
                "Supports high-resolution output via the zoom parameter. "
                "IMPORTANT: Only use this tool when the user explicitly requests to see the chart image "
                "or export it as PNG. Do not automatically export charts after creation unless specifically asked."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "chart_id": {
                        "type": "string",
                        "description": "ID of the chart to export",
                    },
                    "width": {
                        "type": "integer",
                        "description": "Width of the image in pixels (optional, uses chart width if not specified)",
                    },
                    "height": {
                        "type": "integer",
                        "description": "Height of the image in pixels (optional, uses chart height if not specified)",
                    },
                    "plain": {
                        "type": "boolean",
                        "description": "If true, exports only the visualization without header/footer (default: false)",
                        "default": False,
                    },
                    "zoom": {
                        "type": "integer",
                        "description": "Scale multiplier for resolution, e.g., 2 = 2x resolution (default: 2)",
                        "default": 2,
                    },
                    "transparent": {
                        "type": "boolean",
                        "description": "If true, exports with transparent background (default: false)",
                        "default": False,
                    },
                    "border_width": {
                        "type": "integer",
                        "description": "Margin around visualization in pixels (default: 0)",
                        "default": 0,
                    },
                    "border_color": {
                        "type": "string",
                        "description": "Color of the border, e.g., '#FFFFFF' (optional, uses chart background if not specified)",
                    },
                },
                "required": ["chart_id"],
            },
        ),
    ]
