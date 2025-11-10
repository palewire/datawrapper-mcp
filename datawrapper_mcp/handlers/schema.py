"""Handler for retrieving chart schemas."""

import json
import time

from mcp.types import TextContent

from ..config import CHART_CLASSES
from ..logging import get_correlation_id, get_logger, log_duration

logger = get_logger("handlers.schema")


async def get_chart_schema(arguments: dict) -> list[TextContent]:
    """Get the Pydantic schema for a chart type."""
    start_time = time.time()
    chart_type = arguments["chart_type"]
    
    logger.info(
        "Getting chart schema",
        extra={
            "correlation_id": get_correlation_id(),
            "chart_type": chart_type,
        },
    )
    
    chart_class = CHART_CLASSES[chart_type]

    schema = chart_class.model_json_schema()

    # Remove examples that contain DataFrames (not JSON serializable)
    if "examples" in schema:
        del schema["examples"]

    result = {
        "chart_type": chart_type,
        "class_name": chart_class.__name__,
        "schema": schema,
        "usage": (
            "Use this schema to construct a chart_config dict for create_chart_advanced. "
            "The schema shows all available properties, their types, and descriptions."
        ),
    }

    logger.info(
        "Chart schema retrieved successfully",
        extra={
            "correlation_id": get_correlation_id(),
            "chart_type": chart_type,
            "class_name": chart_class.__name__,
            "duration_ms": log_duration(start_time),
        },
    )
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
