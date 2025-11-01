"""Handler for exporting Datawrapper charts."""

import base64

from datawrapper import get_chart
from mcp.types import ImageContent

from ..utils import get_api_token


async def export_chart_png(arguments: dict) -> list[ImageContent]:
    """Export a chart as PNG and return it as inline image."""
    api_token = get_api_token()
    chart_id = arguments["chart_id"]

    # Get chart using factory function
    chart = get_chart(chart_id, access_token=api_token)

    # Build export parameters
    export_params = {}
    if "width" in arguments:
        export_params["width"] = arguments["width"]
    if "height" in arguments:
        export_params["height"] = arguments["height"]
    if "plain" in arguments:
        export_params["plain"] = arguments["plain"]
    if "zoom" in arguments:
        export_params["zoom"] = arguments["zoom"]
    if "transparent" in arguments:
        export_params["transparent"] = arguments["transparent"]
    if "border_width" in arguments:
        export_params["borderWidth"] = arguments["border_width"]
    if "border_color" in arguments:
        export_params["borderColor"] = arguments["border_color"]

    # Export PNG using Pydantic instance method
    png_bytes = chart.export_png(access_token=api_token, **export_params)

    # Encode to base64
    base64_data = base64.b64encode(png_bytes).decode("utf-8")

    return [
        ImageContent(
            type="image",
            data=base64_data,
            mimeType="image/png",
        )
    ]
