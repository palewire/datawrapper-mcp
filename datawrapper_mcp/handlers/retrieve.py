"""Handler for retrieving chart information."""

import json

from datawrapper import get_chart
from mcp.types import TextContent

from ..utils import get_api_token


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
