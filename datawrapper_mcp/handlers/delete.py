"""Handler for deleting Datawrapper charts."""

import json

from datawrapper import get_chart
from mcp.types import TextContent

from ..utils import get_api_token


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
