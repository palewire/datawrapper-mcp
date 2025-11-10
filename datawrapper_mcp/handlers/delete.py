"""Handler for deleting Datawrapper charts."""

import json

from mcp.types import TextContent
from datawrapper import get_chart

from ..types import DeleteChartArgs
from ..utils import get_api_token


async def delete_chart(arguments: DeleteChartArgs) -> list[TextContent]:
    """Delete a chart permanently."""
    chart_id = arguments["chart_id"]

    api_token = get_api_token()

    # Get chart and delete using Pydantic instance method
    chart = get_chart(chart_id, access_token=api_token)
    chart.delete(access_token=api_token)

    result = {
        "chart_id": chart_id,
        "message": "Chart deleted successfully!",
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]
