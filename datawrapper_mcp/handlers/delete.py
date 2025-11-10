"""Handler for deleting Datawrapper charts."""

import json
import time

from datawrapper import get_chart
from mcp.types import TextContent

from ..logging import get_correlation_id, get_logger, log_duration
from ..types import DeleteChartArgs
from ..utils import get_api_token

logger = get_logger("handlers.delete")


async def delete_chart(arguments: DeleteChartArgs) -> list[TextContent]:
    """Delete a chart permanently."""
    start_time = time.time()
    cid = get_correlation_id()
    chart_id = arguments["chart_id"]
    
    logger.info(
        "Deleting chart",
        extra={
            "correlation_id": cid,
            "chart_id": chart_id,
        },
    )
    
    api_token = get_api_token()

    # Get chart and delete using Pydantic instance method
    try:
        chart = get_chart(chart_id, access_token=api_token)
        chart.delete(access_token=api_token)
        
        logger.info(
            "Chart deleted successfully",
            extra={
                "correlation_id": cid,
                "chart_id": chart_id,
                "duration_ms": log_duration(start_time),
            },
        )
    except Exception as e:
        logger.error(
            "Chart deletion failed",
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
        "message": "Chart deleted successfully!",
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]
