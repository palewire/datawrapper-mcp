"""Handler for updating Datawrapper charts."""

import asyncio
from typing import Any

from datawrapper import get_chart
from mcp.types import ImageContent

from datawrapper_mcp.types import UpdateChartArgs
from datawrapper_mcp.utils import json_to_dataframe

from .preview import try_export_preview


async def update_chart(
    arguments: UpdateChartArgs,
) -> tuple[dict[str, Any], list[ImageContent]]:
    """Update an existing chart's data or configuration.

    Returns:
        A tuple of (metadata_dict, preview_images).
    """
    chart_id = arguments["chart_id"]
    token = arguments.get("access_token")

    # Get chart using factory function - returns correct Pydantic class
    # instance. Synchronous and network-bound, so run it off the event loop
    # (see export.py/preview.py).
    chart = await asyncio.to_thread(get_chart, chart_id, access_token=token)

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
                f"Invalid chart configuration: {e!s}\n\n"
                f"Use get_chart_schema to see the valid schema for this chart type. "
                f"Only high-level Pydantic fields are accepted."
            ) from e

    # Update using Pydantic instance method
    await asyncio.to_thread(chart.update, access_token=token)

    metadata: dict[str, Any] = {
        "chart_id": chart.chart_id,
        "title": chart.title,
        "edit_url": chart.get_editor_url(),
    }

    images: list[ImageContent] = []
    preview = await try_export_preview(chart, access_token=token)
    if preview:
        images.append(preview)

    return metadata, images
