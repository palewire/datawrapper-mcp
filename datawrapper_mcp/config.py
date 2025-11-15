"""Configuration and constants for the Datawrapper MCP server."""

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
