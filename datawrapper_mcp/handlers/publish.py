"""Handler for publishing Datawrapper charts."""

from typing import Any

from datawrapper import get_chart
from mcp.types import ImageContent

from ..types import PublishChartArgs
from .preview import try_export_preview


async def publish_chart(
    arguments: PublishChartArgs,
) -> tuple[dict[str, Any], list[ImageContent]]:
    """Publish a chart and return metadata plus a PNG preview when available."""
    chart_id = arguments["chart_id"]

    # Get chart and publish using Pydantic instance method
    chart = get_chart(chart_id)
    chart.publish()

    metadata: dict[str, Any] = {
        "chart_id": chart.chart_id,
        "public_url": chart.get_public_url(),
        "title": chart.title,
        "edit_url": chart.get_editor_url(),
        "message": "Chart published successfully!",
    }

    images: list[ImageContent] = []
    preview = try_export_preview(chart)
    if preview:
        images.append(preview)

    return metadata, images
