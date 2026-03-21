"""Handler for creating Datawrapper charts."""

from typing import Any

from mcp.types import ImageContent

from ..config import CHART_CLASSES
from ..types import CreateChartArgs
from ..utils import json_to_dataframe
from .preview import try_export_preview


async def create_chart(
    arguments: CreateChartArgs,
) -> tuple[dict[str, Any], list[ImageContent]]:
    """Create a chart with full Pydantic model configuration.

    Returns:
        A tuple of (metadata_dict, preview_images).
    """
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
    chart.create()

    metadata: dict[str, Any] = {
        "chart_id": chart.chart_id,
        "chart_type": chart_type,
        "title": chart.title,
        "edit_url": chart.get_editor_url(),
    }

    images: list[ImageContent] = []
    preview = try_export_preview(chart)
    if preview:
        images.append(preview)

    return metadata, images
