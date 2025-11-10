"""Handler for updating Datawrapper charts."""

import json

from mcp.types import TextContent
from datawrapper import get_chart

from ..types import UpdateChartArgs
from ..utils import json_to_dataframe


async def update_chart(arguments: UpdateChartArgs) -> list[TextContent]:
    """Update an existing chart's data or configuration."""
    chart_id = arguments["chart_id"]

    # Get chart using factory function - returns correct Pydantic class instance
    chart = get_chart(chart_id)

    # Update data if provided
    if "data" in arguments:
        df = json_to_dataframe(arguments["data"])
        chart.data = df

    # Update config if provided
    if "chart_config" in arguments:
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

        except Exception as e:
            raise ValueError(
                f"Invalid chart configuration: {str(e)}\n\n"
                f"Use get_chart_schema to see the valid schema for this chart type. "
                f"Only high-level Pydantic fields are accepted."
            )

    # Update using Pydantic instance method
    chart.update()

    result = {
        "chart_id": chart.chart_id,
        "message": "Chart updated successfully!",
        "edit_url": chart.get_editor_url(),
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]
