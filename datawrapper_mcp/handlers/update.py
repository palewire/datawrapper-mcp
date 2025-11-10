"""Handler for updating Datawrapper charts."""

import json
import time

from datawrapper import get_chart
from mcp.types import TextContent

from ..logging import get_correlation_id, get_logger, log_duration
from ..types import UpdateChartArgs
from ..utils import get_api_token, json_to_dataframe

logger = get_logger("handlers.update")


async def update_chart(arguments: UpdateChartArgs) -> list[TextContent]:
    """Update an existing chart's data or configuration."""
    start_time = time.time()
    cid = get_correlation_id()
    chart_id = arguments["chart_id"]

    has_data = "data" in arguments
    has_config = "chart_config" in arguments
    config_keys = list(arguments["chart_config"].keys()) if has_config else []

    logger.info(
        "Updating chart",
        extra={
            "correlation_id": cid,
            "chart_id": chart_id,
            "has_data": has_data,
            "has_config": has_config,
            "config_keys": config_keys,
        },
    )

    api_token = get_api_token()

    # Get chart using factory function - returns correct Pydantic class instance
    chart = get_chart(chart_id, access_token=api_token)

    # Update data if provided
    if has_data:
        df = json_to_dataframe(arguments["data"])
        chart.data = df
        logger.debug(
            "Chart data updated",
            extra={
                "correlation_id": cid,
                "chart_id": chart_id,
                "rows": len(df),
                "columns": len(df.columns),
            },
        )

    # Update config if provided
    if has_config:
        # Directly set attributes on the chart instance
        # Pydantic will validate each assignment automatically due to validate_assignment=True
        try:
            # Build a mapping of aliases to field names
            alias_to_field = {}
            for field_name, field_info in chart.model_fields.items():
                # Add the field name itself
                alias_to_field[field_name] = field_name
                # Add any aliases
                if field_info.alias:
                    alias_to_field[field_info.alias] = field_name

            for key, value in arguments["chart_config"].items():
                # Convert alias to field name if needed
                field_name = alias_to_field.get(key, key)
                setattr(chart, field_name, value)

            logger.debug(
                "Chart config updated",
                extra={
                    "correlation_id": cid,
                    "chart_id": chart_id,
                    "updated_fields": config_keys,
                },
            )
        except Exception as e:
            logger.error(
                "Chart config validation failed",
                extra={
                    "correlation_id": cid,
                    "chart_id": chart_id,
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
                    f"Use get_chart_schema to see the valid schema for this chart type. "
                    f"Only high-level Pydantic fields are accepted.",
                )
            ]

    # Update using Pydantic instance method
    try:
        chart.update(access_token=api_token)

        logger.info(
            "Chart updated successfully",
            extra={
                "correlation_id": cid,
                "chart_id": chart_id,
                "duration_ms": log_duration(start_time),
            },
        )
    except Exception as e:
        logger.error(
            "Chart update failed",
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
        "chart_id": chart.chart_id,
        "message": "Chart updated successfully!",
        "edit_url": chart.get_editor_url(),
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]
