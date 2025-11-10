"""Type definitions for handler function arguments."""

import sys
from typing import Any, TypedDict

if sys.version_info >= (3, 11):
    from typing import NotRequired
else:
    from typing_extensions import NotRequired


class CreateChartArgs(TypedDict):
    """Arguments for create_chart handler."""

    data: str | list[dict] | dict[str, list]
    chart_type: str
    chart_config: dict[str, Any]


class UpdateChartArgs(TypedDict):
    """Arguments for update_chart handler."""

    chart_id: str
    data: NotRequired[str | list[dict] | dict[str, list]]
    chart_config: NotRequired[dict[str, Any]]


class PublishChartArgs(TypedDict):
    """Arguments for publish_chart handler."""

    chart_id: str


class GetChartArgs(TypedDict):
    """Arguments for get_chart handler."""

    chart_id: str


class DeleteChartArgs(TypedDict):
    """Arguments for delete_chart handler."""

    chart_id: str


class GetChartSchemaArgs(TypedDict):
    """Arguments for get_chart_schema handler."""

    chart_type: str


class ExportChartPngArgs(TypedDict):
    """Arguments for export_chart_png handler."""

    chart_id: str
    width: NotRequired[int]
    height: NotRequired[int]
    plain: NotRequired[bool]
    zoom: NotRequired[int]
    transparent: NotRequired[bool]
    border_width: NotRequired[int]
    border_color: NotRequired[str]
