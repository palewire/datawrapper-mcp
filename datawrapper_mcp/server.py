"""Main MCP server implementation for Datawrapper chart creation."""

import json
from typing import Any, Sequence

from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent, TextContent

from .config import CHART_CLASSES
from .handlers import (
    create_chart as create_chart_handler,
    delete_chart as delete_chart_handler,
    export_chart_png as export_chart_png_handler,
    get_chart_info as get_chart_info_handler,
    get_chart_schema as get_chart_schema_handler,
    publish_chart as publish_chart_handler,
    update_chart as update_chart_handler,
)

# Initialize the FastMCP server
mcp = FastMCP("datawrapper-mcp")


@mcp.resource("datawrapper://chart-types")
async def chart_types_resource() -> str:
    """List of available Datawrapper chart types and their Pydantic schemas."""
    chart_info = {}
    for name, chart_class in CHART_CLASSES.items():
        chart_info[name] = {
            "class_name": chart_class.__name__,
            "schema": chart_class.model_json_schema(),
        }
    return json.dumps(chart_info, indent=2)


@mcp.tool()
async def create_chart(
    data: str | list | dict,
    chart_type: str,
    chart_config: dict,
) -> str:
    """⚠️ THIS IS THE DATAWRAPPER INTEGRATION ⚠️
    Use this MCP tool for ALL Datawrapper chart creation.

    DO NOT:
    ❌ Install the 'datawrapper' Python package
    ❌ Use the Datawrapper API directly
    ❌ Import 'from datawrapper import ...'
    ❌ Run pip install datawrapper

    This MCP server IS the complete Datawrapper integration. All Datawrapper operations
    should use the MCP tools provided by this server.

    ---

    Create a Datawrapper chart with full control using Pydantic models.
    This allows you to specify all chart properties including title, description,
    visualization settings, axes, colors, and more. The chart_config should
    be a complete Pydantic model dict matching the schema for the chosen chart type.

    STYLING WORKFLOW:
    1. Use get_chart_schema to explore all available options for your chart type
    2. Refer to https://datawrapper.readthedocs.io/en/latest/ for detailed examples
    3. Build your chart_config with the desired styling properties

    Common styling patterns:
    - Colors: {"color_category": {"sales": "#1d81a2", "profit": "#15607a"}}
    - Line styling: {"lines": [{"column": "sales", "width": "style1", "interpolation": "curved"}]}
    - Axis ranges: {"custom_range_y": [0, 100], "custom_range_x": [2020, 2024]}
    - Grid formatting: {"y_grid_format": "0", "x_grid": "on", "y_grid": "on"}
    - Tooltips: {"tooltip_number_format": "00.00", "tooltip_x_format": "YYYY"}
    - Annotations: {"text_annotations": [{"x": "2023", "y": 50, "text": "Peak"}]}

    See the documentation for chart-type specific examples and advanced patterns.

    Example data format: [{"date": "2024-01", "value": 100}, {"date": "2024-02", "value": 150}]

    Args:
        data: Chart data. RECOMMENDED: Pass data inline as a list or dict.
            PREFERRED FORMATS (use these first):
            1. List of records (RECOMMENDED): [{"year": 2020, "sales": 100}, {"year": 2021, "sales": 150}]
            2. Dict of arrays: {"year": [2020, 2021], "sales": [100, 150]}
            3. JSON string of format 1 or 2: '[{"year": 2020, "sales": 100}]'
            ALTERNATIVE (only for extremely large datasets where inline data is impractical):
            4. File path to CSV or JSON: "/path/to/data.csv" or "/path/to/data.json"
        chart_type: Type of chart to create (bar, line, area, arrow, column, multiple_column, scatter, stacked_bar)
        chart_config: Complete chart configuration as a Pydantic model dict

    Returns:
        Chart ID and editor URL
    """
    try:
        result = await create_chart_handler(
            {
                "data": data,
                "chart_type": chart_type,
                "chart_config": chart_config,
            }
        )
        # Extract text from TextContent
        return result[0].text if result else "Chart created successfully"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
async def get_chart_schema(chart_type: str) -> str:
    """⚠️ DATAWRAPPER MCP TOOL ⚠️
    This is part of the Datawrapper MCP server integration.

    ---

    Get the Pydantic JSON schema for a specific chart type. This is your primary tool
    for discovering styling and configuration options.

    The schema shows:
    - All available properties and their types
    - Enum values (e.g., line widths, interpolation methods)
    - Default values
    - Detailed descriptions for each property

    WORKFLOW: Use this tool first to explore options, then refer to
    https://datawrapper.readthedocs.io/en/latest/ for detailed examples and patterns
    showing how to use these properties in practice.

    Args:
        chart_type: Chart type to get schema for

    Returns:
        JSON schema for the chart type
    """
    try:
        result = await get_chart_schema_handler({"chart_type": chart_type})
        return result[0].text if result else "Schema retrieved successfully"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
async def publish_chart(chart_id: str) -> str:
    """⚠️ DATAWRAPPER MCP TOOL ⚠️
    This is part of the Datawrapper MCP server integration.

    ---

    Publish a Datawrapper chart to make it publicly accessible.
    Returns the public URL of the published chart.
    IMPORTANT: Only use this tool when the user explicitly requests to publish the chart.
    Do not automatically publish charts after creation unless specifically asked.

    Args:
        chart_id: ID of the chart to publish

    Returns:
        Public URL of the published chart
    """
    try:
        result = await publish_chart_handler({"chart_id": chart_id})
        return result[0].text if result else "Chart published successfully"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
async def get_chart(chart_id: str) -> str:
    """⚠️ DATAWRAPPER MCP TOOL ⚠️
    This is part of the Datawrapper MCP server integration.

    ---

    Get information about an existing Datawrapper chart,
    including its metadata, data, and public URL if published.

    Args:
        chart_id: ID of the chart to retrieve

    Returns:
        Chart information including metadata and URLs
    """
    try:
        result = await get_chart_info_handler({"chart_id": chart_id})
        return result[0].text if result else "Chart retrieved successfully"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
async def update_chart(
    chart_id: str,
    data: str | list | dict | None = None,
    chart_config: dict | None = None,
) -> str:
    """⚠️ DATAWRAPPER MCP TOOL ⚠️
    This is part of the Datawrapper MCP server integration.

    ---

    Update an existing Datawrapper chart's data or configuration using Pydantic models.
    IMPORTANT: The chart_config must use high-level Pydantic fields only (title, intro,
    byline, source_name, source_url, etc.). Do NOT use low-level serialized structures
    like 'metadata', 'visualize', or other internal API fields.

    STYLING UPDATES:
    Use get_chart_schema to see available fields, then apply styling changes:
    - Colors: {"color_category": {"sales": "#ff0000"}}
    - Line properties: {"lines": [{"column": "sales", "width": "style2"}]}
    - Axis settings: {"custom_range_y": [0, 200], "y_grid_format": "0,0"}
    - Tooltips: {"tooltip_number_format": "0.0"}

    See https://datawrapper.readthedocs.io/en/latest/ for detailed examples.
    The provided config will be validated through Pydantic and merged with the existing
    chart configuration.

    Args:
        chart_id: ID of the chart to update
        data: New chart data (optional). Same formats as create_chart.
        chart_config: Updated chart configuration using high-level Pydantic fields (optional)

    Returns:
        Confirmation message with editor URL
    """
    try:
        args: dict[str, Any] = {"chart_id": chart_id}
        if data is not None:
            args["data"] = data
        if chart_config is not None:
            args["chart_config"] = chart_config

        result = await update_chart_handler(args)
        return result[0].text if result else "Chart updated successfully"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
async def delete_chart(chart_id: str) -> str:
    """⚠️ DATAWRAPPER MCP TOOL ⚠️
    This is part of the Datawrapper MCP server integration.

    ---

    Delete a Datawrapper chart permanently.

    Args:
        chart_id: ID of the chart to delete

    Returns:
        Confirmation message
    """
    try:
        result = await delete_chart_handler({"chart_id": chart_id})
        return result[0].text if result else "Chart deleted successfully"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
async def export_chart_png(
    chart_id: str,
    width: int | None = None,
    height: int | None = None,
    plain: bool = False,
    zoom: int = 2,
    transparent: bool = False,
    border_width: int = 0,
    border_color: str | None = None,
) -> Sequence[TextContent | ImageContent]:
    """⚠️ DATAWRAPPER MCP TOOL ⚠️
    This is part of the Datawrapper MCP server integration.

    ---

    Export a Datawrapper chart as PNG and display it inline.
    The chart must be created first using create_chart.
    Supports high-resolution output via the zoom parameter.
    IMPORTANT: Only use this tool when the user explicitly requests to see the chart image
    or export it as PNG. Do not automatically export charts after creation unless specifically asked.

    Args:
        chart_id: ID of the chart to export
        width: Width of the image in pixels (optional)
        height: Height of the image in pixels (optional)
        plain: If true, exports only the visualization without header/footer
        zoom: Scale multiplier for resolution, e.g., 2 = 2x resolution
        transparent: If true, exports with transparent background
        border_width: Margin around visualization in pixels
        border_color: Color of the border, e.g., '#FFFFFF' (optional)

    Returns:
        PNG image content
    """
    try:
        args: dict[str, Any] = {
            "chart_id": chart_id,
            "plain": plain,
            "zoom": zoom,
            "transparent": transparent,
            "border_width": border_width,
        }
        if width is not None:
            args["width"] = width
        if height is not None:
            args["height"] = height
        if border_color is not None:
            args["border_color"] = border_color

        return await export_chart_png_handler(args)
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


def main():
    """Run the MCP server with stdio transport (for backwards compatibility)."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
