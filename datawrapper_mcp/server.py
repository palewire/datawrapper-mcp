"""Main MCP server implementation for Datawrapper chart creation."""

import base64
import json
import os
from typing import Any

import pandas as pd
from datawrapper import (
    AreaChart,
    ArrowChart,
    BarChart,
    ColumnChart,
    LineChart,
    MultipleColumnChart,
    ScatterPlot,
    StackedBarChart,
    get_chart
)
from mcp.server import Server
from mcp.types import ImageContent, Resource, TextContent, Tool

# Initialize the MCP server
app = Server("datawrapper-mcp")

# Map of chart type names to their Pydantic classes
CHART_CLASSES = {
    "bar": BarChart,
    "line": LineChart,
    "area": AreaChart,
    "arrow": ArrowChart,
    "column": ColumnChart,
    "multiple_column": MultipleColumnChart,
    "scatter": ScatterPlot,
    "stacked_bar": StackedBarChart,
}


def get_api_token() -> str:
    """Get the Datawrapper API token from environment."""
    api_token = os.environ.get("DATAWRAPPER_API_TOKEN")
    if not api_token:
        raise ValueError(
            "DATAWRAPPER_API_TOKEN environment variable is required. "
            "Get your token from https://app.datawrapper.de/account/api-tokens"
        )
    return api_token


def json_to_dataframe(data: str | list | dict) -> pd.DataFrame:
    """Convert JSON data to a pandas DataFrame.
    
    Args:
        data: One of:
            - List of records: [{"col1": val1, "col2": val2}, ...]
            - Dict of arrays: {"col1": [val1, val2], "col2": [val3, val4]}
            - JSON string in either format above
        
    Returns:
        pandas DataFrame
        
    Examples:
        >>> json_to_dataframe([{"a": 1, "b": 2}, {"a": 3, "b": 4}])
        >>> json_to_dataframe({"a": [1, 3], "b": [2, 4]})
        >>> json_to_dataframe('[{"a": 1, "b": 2}]')
    """
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string: {e}")
    
    if isinstance(data, list):
        # List of records: [{"col1": val1, "col2": val2}, ...]
        return pd.DataFrame(data)
    elif isinstance(data, dict):
        # Dict of arrays: {"col1": [val1, val2], "col2": [val3, val4]}
        return pd.DataFrame(data)
    else:
        raise ValueError(
            "Data must be one of:\n"
            "  - List of dicts: [{\"col\": val}, ...]\n"
            "  - Dict of arrays: {\"col\": [vals]}\n"
            "  - JSON string in either format"
        )


@app.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources."""
    return [
        Resource(
            uri="datawrapper://chart-types",
            name="Available Chart Types",
            mimeType="application/json",
            description="List of available Datawrapper chart types and their Pydantic schemas",
        )
    ]


@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource by URI."""
    if uri == "datawrapper://chart-types":
        chart_info = {}
        for name, chart_class in CHART_CLASSES.items():
            chart_info[name] = {
                "class_name": chart_class.__name__,
                "schema": chart_class.model_json_schema(),
            }
        return json.dumps(chart_info, indent=2)
    
    raise ValueError(f"Unknown resource URI: {uri}")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="create_chart",
            description=(
                "Create a Datawrapper chart with full control using Pydantic models. "
                "This allows you to specify all chart properties including title, description, "
                "visualization settings, axes, colors, and more. The chart_config should "
                "be a complete Pydantic model dict matching the schema for the chosen chart type. "
                "Use get_chart_schema to see available options for each chart type.\n\n"
                "Example data format: [{\"date\": \"2024-01\", \"value\": 100}, {\"date\": \"2024-02\", \"value\": 150}]"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "data": {
                        "type": ["string", "array", "object"],
                        "description": (
                            "Chart data in one of three formats:\n"
                            "1. List of records (RECOMMENDED): [{\"col1\": val1, \"col2\": val2}, ...]\n"
                            "2. Dict of arrays: {\"col1\": [val1, val2], \"col2\": [val3, val4]}\n"
                            "3. JSON string in either format above"
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
                "Get the Pydantic JSON schema for a specific chart type. "
                "This shows all available properties, their types, defaults, and descriptions. "
                "Use this to understand what options are available when creating charts "
                "with create_chart_advanced."
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
                "Publish a Datawrapper chart to make it publicly accessible. "
                "Returns the public URL of the published chart."
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
                "Update an existing Datawrapper chart's data or configuration using Pydantic models. "
                "IMPORTANT: The chart_config must use high-level Pydantic fields only (title, intro, "
                "byline, source_name, source_url, etc.). Do NOT use low-level serialized structures "
                "like 'metadata', 'visualize', or other internal API fields. Use get_chart_schema to "
                "see the available Pydantic fields for the chart type. The provided config will be "
                "validated through Pydantic and merged with the existing chart configuration."
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
                            "Chart data in one of three formats:\n"
                            "1. List of records (RECOMMENDED): [{\"col1\": val1, \"col2\": val2}, ...]\n"
                            "2. Dict of arrays: {\"col1\": [val1, val2], \"col2\": [val3, val4]}\n"
                            "3. JSON string in either format above"
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
            description="Delete a Datawrapper chart permanently.",
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
                "Export a Datawrapper chart as PNG and display it inline. "
                "This is the recommended method for viewing charts directly in the conversation. "
                "The chart must be created first using create_chart. "
                "Supports high-resolution output via the zoom parameter."
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


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent | ImageContent]:
    """Handle tool calls."""
    try:
        if name == "create_chart":
            return await create_chart(arguments)
        elif name == "get_chart_schema":
            return await get_chart_schema(arguments)
        elif name == "publish_chart":
            return await publish_chart(arguments)
        elif name == "get_chart":
            return await get_chart_info(arguments)
        elif name == "update_chart":
            return await update_chart(arguments)
        elif name == "delete_chart":
            return await delete_chart(arguments)
        elif name == "export_chart_png":
            return await export_chart_png(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def create_chart(arguments: dict) -> list[TextContent]:
    """Create a chart with full Pydantic model configuration."""
    api_token = get_api_token()
    
    # Convert data to DataFrame
    df = json_to_dataframe(arguments["data"])
    
    # Get chart class and validate config
    chart_type = arguments["chart_type"]
    chart_class = CHART_CLASSES[chart_type]
    
    # Validate and create chart using Pydantic model
    try:
        chart = chart_class.model_validate(arguments["chart_config"])
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=f"Invalid chart configuration: {str(e)}\n\n"
                f"Use get_chart_schema with chart_type '{chart_type}' "
                f"to see the valid schema.",
            )
        ]
    
    # Set data on chart instance
    chart.data = df
    
    # Create chart using Pydantic instance method
    chart.create(access_token=api_token)
    
    result = {
        "chart_id": chart.chart_id,
        "chart_type": chart_type,
        "title": chart.title,
        "edit_url": chart.get_editor_url(),
        "message": (
            f"Chart created successfully! Edit it at: {chart.get_editor_url()}\n"
            f"Use publish_chart with chart_id '{chart.chart_id}' to make it public."
        ),
    }
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def get_chart_schema(arguments: dict) -> list[TextContent]:
    """Get the Pydantic schema for a chart type."""
    chart_type = arguments["chart_type"]
    chart_class = CHART_CLASSES[chart_type]
    
    schema = chart_class.model_json_schema()
    
    result = {
        "chart_type": chart_type,
        "class_name": chart_class.__name__,
        "schema": schema,
        "usage": (
            f"Use this schema to construct a chart_config dict for create_chart_advanced. "
            f"The schema shows all available properties, their types, and descriptions."
        ),
    }
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def publish_chart(arguments: dict) -> list[TextContent]:
    """Publish a chart to make it publicly accessible."""
    api_token = get_api_token()
    chart_id = arguments["chart_id"]
    
    # Get chart and publish using Pydantic instance method
    chart = get_chart(chart_id, access_token=api_token)
    chart.publish(access_token=api_token)
    
    result = {
        "chart_id": chart_id,
        "public_url": chart.get_public_url(),
        "message": "Chart published successfully!",
    }
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def get_chart_info(arguments: dict) -> list[TextContent]:
    """Get information about an existing chart."""
    api_token = get_api_token()
    chart_id = arguments["chart_id"]
    
    # Get chart using factory function
    chart = get_chart(chart_id, access_token=api_token)
    
    result = {
        "chart_id": chart.chart_id,
        "title": chart.title,
        "type": chart.chart_type,
        "public_url": chart.get_public_url(),
        "edit_url": chart.get_editor_url(),
    }
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def update_chart(arguments: dict) -> list[TextContent]:
    """Update an existing chart's data or configuration."""
    api_token = get_api_token()
    chart_id = arguments["chart_id"]
    
    # Get chart using factory function - returns correct Pydantic class instance
    chart = get_chart(chart_id, access_token=api_token)
    
    # Update data if provided
    if "data" in arguments:
        df = json_to_dataframe(arguments["data"])
        chart.data = df
    
    # Update config if provided
    if "chart_config" in arguments:
        # Get the chart's Pydantic class directly from the instance
        chart_class = type(chart)
        
        # Get current chart state as dict
        current_config = chart.model_dump()
        
        # Merge the new config with current config
        merged_config = {**current_config, **arguments["chart_config"]}
        
        # Validate the merged config through Pydantic
        try:
            validated_chart = chart_class.model_validate(merged_config)
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"Invalid chart configuration: {str(e)}\n\n"
                    f"Use get_chart_schema to see the valid schema for this chart type. "
                    f"Only high-level Pydantic fields are accepted.",
                )
            ]
        
        # Update chart attributes from validated model
        for key, value in validated_chart.model_dump(exclude={"data"}).items():
            setattr(chart, key, value)
    
    # Update using Pydantic instance method
    chart.update(access_token=api_token)
    
    result = {
        "chart_id": chart.chart_id,
        "message": "Chart updated successfully!",
        "edit_url": chart.get_editor_url(),
    }
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def delete_chart(arguments: dict) -> list[TextContent]:
    """Delete a chart permanently."""
    api_token = get_api_token()
    chart_id = arguments["chart_id"]
    
    # Get chart and delete using Pydantic instance method
    chart = get_chart(chart_id, access_token=api_token)
    chart.delete(access_token=api_token)
    
    result = {
        "chart_id": chart_id,
        "message": "Chart deleted successfully!",
    }
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def export_chart_png(arguments: dict) -> list[ImageContent]:
    """Export a chart as PNG and return it as inline image."""
    api_token = get_api_token()
    chart_id = arguments["chart_id"]
    
    # Get chart using factory function
    chart = get_chart(chart_id, access_token=api_token)
    
    # Build export parameters
    export_params = {}
    if "width" in arguments:
        export_params["width"] = arguments["width"]
    if "height" in arguments:
        export_params["height"] = arguments["height"]
    if "plain" in arguments:
        export_params["plain"] = arguments["plain"]
    if "zoom" in arguments:
        export_params["zoom"] = arguments["zoom"]
    if "transparent" in arguments:
        export_params["transparent"] = arguments["transparent"]
    if "border_width" in arguments:
        export_params["borderWidth"] = arguments["border_width"]
    if "border_color" in arguments:
        export_params["borderColor"] = arguments["border_color"]
    
    # Export PNG using Pydantic instance method
    png_bytes = chart.export_png(access_token=api_token, **export_params)
    
    # Encode to base64
    base64_data = base64.b64encode(png_bytes).decode("utf-8")
    
    return [
        ImageContent(
            type="image",
            data=base64_data,
            mimeType="image/png",
        )
    ]


def main():
    """Run the MCP server."""
    import asyncio
    from mcp.server.stdio import stdio_server
    
    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options(),
            )
    
    asyncio.run(run())


if __name__ == "__main__":
    main()
