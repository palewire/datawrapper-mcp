"""Handler for publishing Datawrapper charts."""

import json
import time

from datawrapper import get_chart
from mcp.types import TextContent

from ..logging import get_correlation_id, get_logger, log_duration
from ..utils import get_api_token

logger = get_logger("handlers.publish")


async def publish_chart(arguments: dict) -> list[TextContent]:
    """Publish a chart to make it publicly accessible."""
    start_time = time.time()
    cid = get_correlation_id()
    chart_id = arguments["chart_id"]
    
    logger.info(
        "Publishing chart",
        extra={
            "correlation_id": cid,
            "chart_id": chart_id,
        },
    )
    
    api_token = get_api_token()

    # Get chart and publish using Pydantic instance method
    try:
        chart = get_chart(chart_id, access_token=api_token)
        chart.publish(access_token=api_token)
        
        public_url = chart.get_public_url()
        logger.info(
            "Chart published successfully",
            extra={
                "correlation_id": cid,
                "chart_id": chart_id,
                "public_url": public_url,
                "duration_ms": log_duration(start_time),
            },
        )
    except Exception as e:
        logger.error(
            "Chart publication failed",
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

    result = {
        "chart_id": chart_id,
        "public_url": public_url,
        "message": "Chart published successfully!",
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]
