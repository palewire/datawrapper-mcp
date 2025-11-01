"""Handler for updating Datawrapper charts."""

import json

from datawrapper import get_chart
from mcp.types import TextContent

from ..utils import get_api_token, json_to_dataframe


async def update_chart(arguments: dict) -> list[TextContent]:
    """Update an existing chart's data or configuration."""
    api_token = get_api_token()
    chart_id = arguments["chart_id"]

    # Get chart using factory function - returns correct Pydantic class instance
    chart = get_chart(chart_id, access_token=api_token)

    # Update data if provided
    if "data" in arguments:
        df = json_to_dataframe(arguments["data"])
        chart.data = df

    # Update config if provided
    if "chart_config" in arguments:
        # Get the chart's Pydantic class directly from the instance
        chart_class = type(chart)

        # Get current chart state as dict using Python field names (not API aliases)
        # Exclude chart_type and data since they can't/shouldn't be changed via config
        current_config = chart.model_dump(
            by_alias=False, exclude={"chart_type", "data", "chart_id"}
        )

        # Merge the new config with current config
        merged_config = {**current_config, **arguments["chart_config"]}

        # Add back the chart_type since it's required for validation
        merged_config["chart_type"] = chart.chart_type

        # Validate the merged config through Pydantic
        try:
            validated_chart = chart_class.model_validate(merged_config)
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"Invalid chart configuration: {str(e)}\n\n"
                    f"Use get_chart_schema to see the valid schema for this chart type. "
                    f"Only high-level Pydantic fields are accepted.",
                )
            ]

        # Update chart attributes from validated model (excluding data and chart_type)
        for key, value in validated_chart.model_dump(
            exclude={"data", "chart_type", "chart_id"}
        ).items():
            setattr(chart, key, value)

    # Update using Pydantic instance method
    chart.update(access_token=api_token)

    result = {
        "chart_id": chart.chart_id,
        "message": "Chart updated successfully!",
        "edit_url": chart.get_editor_url(),
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]
