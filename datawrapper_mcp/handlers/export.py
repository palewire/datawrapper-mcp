"""Handler for exporting Datawrapper charts."""

import base64
import time

from datawrapper import get_chart
from mcp.types import ImageContent

from ..logging import get_correlation_id, get_logger, log_duration
from ..utils import get_api_token

logger = get_logger("handlers.export")


async def export_chart_png(arguments: dict) -> list[ImageContent]:
    """Export a chart as PNG and return it as inline image."""
    start_time = time.time()
    cid = get_correlation_id()
    chart_id = arguments["chart_id"]
    
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
    
    logger.info(
        "Exporting chart as PNG",
        extra={
            "correlation_id": cid,
            "chart_id": chart_id,
            "export_params": export_params,
        },
    )
    
    api_token = get_api_token()

    # Get chart using factory function
    try:
        chart = get_chart(chart_id, access_token=api_token)

        # Export PNG using Pydantic instance method
        png_bytes = chart.export_png(access_token=api_token, **export_params)

        # Encode to base64
        base64_data = base64.b64encode(png_bytes).decode("utf-8")
        
        logger.info(
            "Chart exported successfully",
            extra={
                "correlation_id": cid,
                "chart_id": chart_id,
                "size_bytes": len(png_bytes),
                "duration_ms": log_duration(start_time),
            },
        )
    except Exception as e:
        logger.error(
            "Chart export failed",
            extra={
                "correlation_id": cid,
                "chart_id": chart_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "duration_ms": log_duration(start_time),
            },
            exc_info=True,
        )
        raise

    return [
        ImageContent(
            type="image",
            data=base64_data,
            mimeType="image/png",
        )
    ]
