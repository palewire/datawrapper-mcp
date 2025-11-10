"""Main MCP server implementation for Datawrapper chart creation."""

import json
from typing import Any, Sequence, cast

from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent, TextContent

from .config import CHART_CLASSES
from .types import (
    CreateChartArgs,
    DeleteChartArgs,
    ExportChartPngArgs,
    GetChartArgs,
    GetChartSchemaArgs,
    PublishChartArgs,
    UpdateChartArgs,
)
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
        chart_class_typed: type[Any] = chart_class
        chart_info[name] = {
            "class_name": chart_class_typed.__name__,
            "schema": chart_class_typed.model_json_schema(),
        }
    return json.dumps(chart_info, indent=2)


@mcp.tool()
async def list_chart_types() -> Sequence[TextContent | ImageContent]:
    """⚠️ DATAWRAPPER MCP TOOL ⚠️
    This is part of the Datawrapper MCP server integration.

    ---

    List all available Datawrapper chart types with brief descriptions.

    Use this tool to discover which chart types you can create. After choosing a type,
    use get_chart_schema(chart_type) to explore detailed configuration options.

    Returns:
        List of available chart types with descriptions
    """
    chart_descriptions = {
        "bar": "Horizontal bar chart - good for comparing categories",
        "line": "Line chart - ideal for showing trends over time",
        "area": "Area chart - filled line chart for emphasizing magnitude",
        "arrow": "Arrow chart - shows before/after comparisons with arrows",
        "column": "Vertical column chart - classic bar chart orientation",
        "multiple_column": "Grouped column chart - compare multiple series side-by-side",
        "scatter": "Scatter plot - visualize correlations between two variables",
        "stacked_bar": "Stacked bar chart - show part-to-whole relationships",
    }

    result = "Available Datawrapper chart types:\n\n"
    for chart_type, description in chart_descriptions.items():
        result += f"• {chart_type}: {description}\n"

    result += "\nTo see detailed configuration options for a specific type, use:\n"
    result += "get_chart_schema(chart_type='your_chosen_type')"

    return [TextContent(type="text", text=result)]


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
        arguments = cast(GetChartSchemaArgs, {"chart_type": chart_type})
        result = await get_chart_schema_handler(arguments)
        return result[0].text
    except Exception as e:
        return f"Error retrieving schema for chart_type '{chart_type}': {str(e)}"


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

    BEST PRACTICES:
    - Start simple, then add customization based on user feedback
    - Only apply styling when requested or when it significantly improves readability
    - Let Datawrapper handle axis scaling automatically unless there's a specific reason to override

    QUICK EXAMPLES:

    1. Basic chart with title:
       chart_config = {
           "title": "Monthly Sales",
           "intro": "Sales data for Q1 2024"
       }

    2. Chart with custom colors:
       chart_config = {
           "title": "Product Comparison",
           "color_category": {
               "Product A": "#1f77b4",
               "Product B": "#ff7f0e"
           }
       }

    3. Styled line chart:
       chart_config = {
           "title": "Sales Trends",
           "lines": [
               {"column": "sales", "width": "style2", "interpolation": "curved"}
           ],
           "custom_range_y": [0, 1000]
       }

    STYLING WORKFLOW:
    1. Use list_chart_types to see available chart types
    2. Use get_chart_schema to explore all options for your chosen type
    3. Refer to https://datawrapper.readthedocs.io/en/latest/ for detailed examples
    4. Build your chart_config with the desired styling properties

    Common styling patterns:
    - Colors: {"color_category": {"sales": "#1d81a2", "profit": "#15607a"}}
    - Line styling: {"lines": [{"column": "sales", "width": "style1", "interpolation": "curved"}]}
    - Axis ranges: {"custom_range_y": [0, 100], "custom_range_x": [2020, 2024]}
        NOTE: Datawrapper's automatic axis scaling is excellent. Only set custom ranges when
        you need specific customization (e.g., comparing multiple charts, forcing zero baseline
        for specific analytical reasons, or matching a house style guide).
    - Grid formatting: {"y_grid_format": "0", "x_grid": "on", "y_grid": "on"}
    - Tooltips: {"tooltip_number_format": "00.00", "tooltip_x_format": "YYYY"}
    - Annotations: {"text_annotations": [{"x": "2023", "y": 50, "text": "Peak"}]}

    See the documentation for chart-type specific examples and advanced patterns.

    Args:
        data: Chart data. RECOMMENDED: Pass data inline as a list or dict.
            PREFERRED FORMATS (use these first):
            1. List of records (RECOMMENDED): [{"year": 2020, "sales": 100}, {"year": 2021, "sales": 150}]
            2. Dict of arrays: {"year": [2020, 2021], "sales": [100, 150]}
            3. JSON string of format 1 or 2: '[{"year": 2020, "sales": 100}]'
            ALTERNATIVE (only for extremely large datasets where inline data is impractical):
            4. File path to CSV or JSON: "/path/to/data.csv" or "/path/to/data.json"
        chart_type: Type of chart to create. Use list_chart_types to see all available types.
            Common types: bar, line, area, arrow, column, multiple_column, scatter, stacked_bar
        chart_config: Complete chart configuration as a Pydantic model dict

    Returns:
        Chart ID and editor URL
    """
    try:
        arguments = cast(
            CreateChartArgs,
            {
                "data": data,
                "chart_type": chart_type,
                "chart_config": chart_config,
            },
        )
        result = await create_chart_handler(arguments)
        return result[0].text
    except Exception as e:
        return f"Error creating chart of type '{chart_type}': {str(e)}"


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
        arguments = cast(PublishChartArgs, {"chart_id": chart_id})
        result = await publish_chart_handler(arguments)
        return result[0].text
    except Exception as e:
        return f"Error publishing chart with ID '{chart_id}': {str(e)}"


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
        arguments = cast(GetChartArgs, {"chart_id": chart_id})
        result = await get_chart_info_handler(arguments)
        return result[0].text
    except Exception as e:
        return f"Error retrieving chart with ID '{chart_id}': {str(e)}"


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

    ⚠️ IMPORTANT LIMITATION: You CANNOT change the chart type with this tool.
    Chart types are immutable once created. To change from one chart type to another
    (e.g., column → stacked_bar, or line → area), you must create a new chart instead.

    WHAT YOU CAN UPDATE:
    • Chart data (add/modify/replace data points)
    • Title, intro, byline, source information
    • Colors, styling, axes configuration
    • Tooltips, annotations, labels
    • Any other configuration options for the existing chart type

    WHAT YOU CANNOT UPDATE:
    ✗ Chart type (bar, line, column, etc.) - this is permanent

    The chart_config must use high-level Pydantic fields only (title, intro,
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
    arguments: dict[str, Any] = {"chart_id": chart_id}
    if data is not None:
        arguments["data"] = data
    if chart_config is not None:
        arguments["chart_config"] = chart_config

    try:
        result = await update_chart_handler(cast(UpdateChartArgs, arguments))
        return result[0].text
    except Exception as e:
        return f"Error updating chart with ID '{chart_id}': {str(e)}"


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
        result = await delete_chart_handler(
            cast(DeleteChartArgs, {"chart_id": chart_id})
        )
        return result[0].text
    except Exception as e:
        return f"Error deleting chart with ID '{chart_id}': {str(e)}"


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

        return await export_chart_png_handler(cast(ExportChartPngArgs, args))
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


def main():
    """Run the MCP server with stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
