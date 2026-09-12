"""Handler for retrieving chart schemas."""

import json
from typing import Any

from mcp.types import TextContent

from datawrapper_mcp.config import resolve_chart_type
from datawrapper_mcp.types import GetChartSchemaArgs


def clean_chart_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Strip schema examples that embed a DataFrame (not JSON serializable)."""
    schema.pop("examples", None)
    return schema


async def get_chart_schema(arguments: GetChartSchemaArgs) -> list[TextContent]:
    """Get the Pydantic schema for a chart type."""
    chart_type = arguments["chart_type"]
    chart_class: type[Any] = resolve_chart_type(chart_type)

    schema = clean_chart_schema(chart_class.model_json_schema())

    result = {
        "chart_type": chart_type,
        "class_name": chart_class.__name__,
        "schema": schema,
        "usage": (
            "Use this schema to construct a chart_config dict for create_chart. "
            "The schema shows all available properties, their types, and descriptions."
        ),
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]
