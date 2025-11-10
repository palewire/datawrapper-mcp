"""Handler for exporting Datawrapper charts."""

import base64
from typing import Any, cast

from datawrapper import get_chart
from mcp.types import ImageContent

from ..types import ExportChartPngArgs
from ..utils import get_api_token


async def export_chart_png(arguments: ExportChartPngArgs) -> list[ImageContent]:
    """Export a chart as PNG and return it as inline image."""
    chart_id = arguments["chart_id"]

    # Build export parameters
    export_params: dict[str, Any] = {}
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
        border_width = arguments["border_width"]
        assert isinstance(border_width, int)
        export_params["borderWidth"] = border_width
    if "border_color" in arguments:
        export_params["borderColor"] = arguments["border_color"]

    api_token = get_api_token()

    # Get chart using factory function
    chart = get_chart(chart_id, access_token=api_token)

    # Export PNG using Pydantic instance method
    png_bytes = chart.export_png(
        access_token=api_token, **cast(dict[str, Any], export_params)
    )

    # Encode to base64
    base64_data = base64.b64encode(png_bytes).decode("utf-8")

    return [
        ImageContent(
            type="image",
            data=base64_data,
            mimeType="image/png",
        )
    ]
