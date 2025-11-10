"""Handler for creating Datawrapper charts."""

import json
from typing import Any

from mcp.types import TextContent

from ..config import CHART_CLASSES
from ..types import CreateChartArgs
from ..utils import get_api_token, json_to_dataframe


async def create_chart(arguments: CreateChartArgs) -> list[TextContent]:
    """Create a chart with full Pydantic model configuration."""
    api_token = get_api_token()
    chart_type = arguments["chart_type"]

    # Convert data to DataFrame
    df = json_to_dataframe(arguments["data"])

    # Get chart class and validate config
    chart_class: type[Any] = CHART_CLASSES[chart_type]

    # Validate and create chart using Pydantic model
    try:
        chart = chart_class.model_validate(arguments["chart_config"])
    except Exception as e:
        raise ValueError(
            f"Invalid chart configuration: {str(e)}\n\n"
            f"Use get_chart_schema with chart_type '{chart_type}' "
            f"to see the valid schema."
        )

    # Set data on chart instance
    chart.data = df

    # Create chart using Pydantic instance method
    chart.create(access_token=api_token)

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
