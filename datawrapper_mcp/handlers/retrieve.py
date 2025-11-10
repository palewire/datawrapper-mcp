"""Handler for retrieving chart information."""

import json
import time

from datawrapper import get_chart
from mcp.types import TextContent

from ..logging import get_correlation_id, get_logger, log_duration
from ..utils import get_api_token

logger = get_logger("handlers.retrieve")


async def get_chart_info(arguments: dict) -> list[TextContent]:
    """Get information about an existing chart."""
    start_time = time.time()
    cid = get_correlation_id()
    chart_id = arguments["chart_id"]
    
    logger.info(
        "Retrieving chart information",
        extra={
            "correlation_id": cid,
            "chart_id": chart_id,
        },
    )
    
    api_token = get_api_token()

    # Get chart using factory function
    try:
        chart = get_chart(chart_id, access_token=api_token)

        result = {
            "chart_id": chart.chart_id,
            "title": chart.title,
            "type": chart.chart_type,
            "public_url": chart.get_public_url(),
            "edit_url": chart.get_editor_url(),
        }
        
        logger.info(
            "Chart information retrieved successfully",
            extra={
                "correlation_id": cid,
                "chart_id": chart_id,
                "chart_type": chart.chart_type,
                "duration_ms": log_duration(start_time),
            },
        )
    except Exception as e:
        logger.error(
            "Chart retrieval failed",
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

    return [TextContent(type="text", text=json.dumps(result, indent=2))]
