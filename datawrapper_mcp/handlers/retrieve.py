"""Handler for retrieving chart information."""

import json

from mcp.types import TextContent
from datawrapper import get_chart

from ..types import GetChartArgs


async def get_chart_info(arguments: GetChartArgs) -> list[TextContent]:
    """Get information about an existing chart including complete configuration."""
    chart_id = arguments["chart_id"]

    # Get chart using factory function
    chart = get_chart(chart_id)

    result = {
        "chart_id": chart.chart_id,
        "title": chart.title,
        "type": chart.chart_type,
        "config": chart.model_dump(),  # Complete Pydantic model dump
        "public_url": chart.get_public_url(),
        "edit_url": chart.get_editor_url(),
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]
