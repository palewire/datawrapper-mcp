"""Handler for publishing Datawrapper charts."""

from typing import Any

from datawrapper import get_chart
from mcp.types import ImageContent

from datawrapper_mcp.types import PublishChartArgs

from .preview import try_export_preview


async def publish_chart(
    arguments: PublishChartArgs,
) -> tuple[dict[str, Any], list[ImageContent]]:
    """Publish a chart and return metadata plus a PNG preview when available."""
    chart_id = arguments["chart_id"]
    token = arguments.get("access_token")

    # Get chart and publish using Pydantic instance method
    chart = get_chart(chart_id, access_token=token)
    chart.publish(access_token=token)

    metadata: dict[str, Any] = {
        "chart_id": chart.chart_id,
        "public_url": chart.get_public_url(),
        "title": chart.title,
        "edit_url": chart.get_editor_url(),
        "message": "Chart published successfully!",
    }

    images: list[ImageContent] = []
    preview = await try_export_preview(chart, access_token=token)
    if preview:
        images.append(preview)

    return metadata, images
