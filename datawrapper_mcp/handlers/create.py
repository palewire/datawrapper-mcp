"""Handler for creating Datawrapper charts."""

import json
import time

from mcp.types import TextContent

from ..config import CHART_CLASSES
from ..logging import get_correlation_id, get_logger, log_duration
from ..utils import get_api_token, json_to_dataframe

logger = get_logger("handlers.create")


async def create_chart(arguments: dict) -> list[TextContent]:
    """Create a chart with full Pydantic model configuration."""
    start_time = time.time()
    cid = get_correlation_id()
    
    chart_type = arguments["chart_type"]
    data_type = type(arguments["data"]).__name__
    config_keys = list(arguments["chart_config"].keys()) if arguments.get("chart_config") else []
    
    logger.info(
        "Creating chart",
        extra={
            "correlation_id": cid,
            "chart_type": chart_type,
            "data_type": data_type,
            "config_keys": config_keys,
        },
    )
    
    api_token = get_api_token()

    # Convert data to DataFrame
    df = json_to_dataframe(arguments["data"])

    # Get chart class and validate config
    chart_class = CHART_CLASSES[chart_type]

    # Validate and create chart using Pydantic model
    try:
        chart = chart_class.model_validate(arguments["chart_config"])
    except Exception as e:
        logger.error(
            "Chart validation failed",
            extra={
                "correlation_id": cid,
                "chart_type": chart_type,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "duration_ms": log_duration(start_time),
            },
            exc_info=True,
        )
        return [
            TextContent(
                type="text",
                text=f"Invalid chart configuration: {str(e)}\n\n"
                f"Use get_chart_schema with chart_type '{chart_type}' "
                f"to see the valid schema.",
            )
        ]

    # Set data on chart instance
    chart.data = df

    # Create chart using Pydantic instance method
    try:
        chart.create(access_token=api_token)
        
        logger.info(
            "Chart created successfully",
            extra={
                "correlation_id": cid,
                "chart_id": chart.chart_id,
                "chart_type": chart_type,
                "title": chart.title,
                "duration_ms": log_duration(start_time),
            },
        )
    except Exception as e:
        logger.error(
            "Chart creation failed",
            extra={
                "correlation_id": cid,
                "chart_type": chart_type,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "duration_ms": log_duration(start_time),
            },
            exc_info=True,
        )
        raise

    result = {
        "chart_id": chart.chart_id,
        "chart_type": chart_type,
        "title": chart.title,
        "edit_url": chart.get_editor_url(),
        "message": (
            f"Chart created successfully! Edit it at: {chart.get_editor_url()}\n"
            f"Use publish_chart with chart_id '{chart.chart_id}' to make it public."
        ),
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]
