"""Configuration and constants for the Datawrapper MCP server."""

import difflib
from typing import Any

from datawrapper import (
    AreaChart,
    ArrowChart,
    BarChart,
    ColumnChart,
    LineChart,
    MultipleColumnChart,
    ScatterPlot,
    StackedBarChart,
)

# Map of chart type names to their Pydantic classes
CHART_CLASSES: dict[str, type[Any]] = {
    "bar": BarChart,
    "line": LineChart,
    "area": AreaChart,
    "arrow": ArrowChart,
    "column": ColumnChart,
    "multiple_column": MultipleColumnChart,
    "scatter": ScatterPlot,
    "stacked_bar": StackedBarChart,
}


def resolve_chart_type(chart_type: str) -> type[Any]:
    """Look up a chart type's Pydantic class, or raise a helpful error.

    The error lists close spelling matches (e.g. "stackedbar" ->
    "stacked_bar") so a calling model can self-correct on its next tool
    call, without needing an interactive round-trip back to a human.
    """
    try:
        return CHART_CLASSES[chart_type]
    except KeyError:
        suggestions = difflib.get_close_matches(
            chart_type, CHART_CLASSES, n=3, cutoff=0.5
        )
        hint = (
            f"Did you mean: {', '.join(suggestions)}?"
            if suggestions
            else f"Valid chart types: {', '.join(CHART_CLASSES)}."
        )
        msg = f"Unknown chart_type '{chart_type}'. {hint}"
        raise ValueError(msg) from None


# Map Datawrapper API type IDs to simplified names
# See: https://developer.datawrapper.de/docs/chart-types
API_TYPE_TO_SIMPLIFIED: dict[str, str] = {
    "d3-bars": "bar",
    "d3-bars-stacked": "stacked_bar",
    "d3-arrow-plot": "arrow",
    "column-chart": "column",
    "multiple-columns": "multiple_column",
    "d3-area": "area",
    "d3-lines": "line",
    "d3-scatter-plot": "scatter",
}

# Types whose height follows their content (a row per bar, dot or table row),
# which the Datawrapper editor resizes to fit whenever it renders them. Other
# types keep the height they are given. /v3/visualizations lists these with a
# fixed height and without supportsFitHeight.
FIT_CONTENT_TYPES = {
    "d3-arrow-plot",
    "d3-bars",
    "d3-bars-bullet",
    "d3-bars-grouped",
    "d3-bars-split",
    "d3-bars-stacked",
    "d3-dot-plot",
    "d3-range-plot",
    "tables",
}


def fits_content(chart_type: str) -> bool:
    """Whether a type, by simplified name or API id, is sized to its content."""
    api_types = {name: api for api, name in API_TYPE_TO_SIMPLIFIED.items()}
    return api_types.get(chart_type, chart_type) in FIT_CONTENT_TYPES
