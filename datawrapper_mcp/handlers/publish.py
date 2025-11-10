"""Handler for publishing Datawrapper charts."""

import json

from mcp.types import TextContent
from datawrapper import get_chart

from ..types import PublishChartArgs
from ..utils import get_api_token


async def publish_chart(arguments: PublishChartArgs) -> list[TextContent]:
    """Publish a chart to make it publicly accessible."""
    chart_id = arguments["chart_id"]

    api_token = get_api_token()

    # Get chart and publish using Pydantic instance method
    chart = get_chart(chart_id, access_token=api_token)
    chart.publish(access_token=api_token)

    public_url = chart.get_public_url()

    result = {
        "chart_id": chart_id,
        "public_url": public_url,
        "message": "Chart published successfully!",
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]
