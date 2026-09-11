"""Handler for deleting Datawrapper charts."""

import json

from datawrapper import get_chart
from mcp.types import TextContent

from datawrapper_mcp.types import DeleteChartArgs


async def delete_chart(arguments: DeleteChartArgs) -> list[TextContent]:
    """Delete a chart permanently."""
    chart_id = arguments["chart_id"]
    token = arguments.get("access_token")

    # Get chart and delete using Pydantic instance method
    chart = get_chart(chart_id, access_token=token)
    chart.delete(access_token=token)

    result = {
        "chart_id": chart_id,
        "message": "Chart deleted successfully!",
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]
