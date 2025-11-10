"""Handler for retrieving chart schemas."""

import json
from typing import Any

from mcp.types import TextContent

from ..config import CHART_CLASSES
from ..types import GetChartSchemaArgs


async def get_chart_schema(arguments: GetChartSchemaArgs) -> list[TextContent]:
    """Get the Pydantic schema for a chart type."""
    chart_type = arguments["chart_type"]
    chart_class: type[Any] = CHART_CLASSES[chart_type]

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

    return [TextContent(type="text", text=json.dumps(result, indent=2))]
