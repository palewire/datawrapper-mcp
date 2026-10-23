"""Handler for copying Datawrapper charts."""

import asyncio
import json
import os
from typing import Any

from datawrapper import Datawrapper, get_chart
from mcp.types import ImageContent, TextContent

from datawrapper_mcp.types import CopyChartArgs

from .preview import try_export_preview


async def copy_chart(arguments: CopyChartArgs) -> list[TextContent | ImageContent]:
    """Copy a chart as is, then give the copy the original's theme.

    Datawrapper's copy keeps the data, the cells edited in the editor, the
    settings and the size, but a copy of a chart in a personal folder gets
    the user's default theme instead of the chart's. The theme is set back in
    the same request that sets the new title and folder, if given.
    """
    chart_id = arguments["chart_id"]
    token = arguments.get("access_token") or None

    source = await asyncio.to_thread(get_chart, chart_id, access_token=token)
    copy = await asyncio.to_thread(source.duplicate, access_token=token)

    changes: dict[str, Any] = {"theme": source.theme}
    if "title" in arguments:
        changes["title"] = arguments["title"]
    if "folder_id" in arguments:
        changes["folderId"] = arguments["folder_id"]
    client = Datawrapper(access_token=token or os.getenv("DATAWRAPPER_ACCESS_TOKEN"))
    chart: dict[str, Any] = await asyncio.to_thread(
        client.patch, f"{client._CHARTS_URL}/{copy.chart_id}", data=changes
    )

    result = {
        "chart_id": copy.chart_id,
        "copied_from": chart_id,
        "title": chart.get("title", copy.title),
        "folder_id": chart.get("folderId"),
        "edit_url": copy.get_editor_url(),
    }
    content: list[TextContent | ImageContent] = [
        TextContent(type="text", text=json.dumps(result, indent=2))
    ]
    preview = await try_export_preview(copy, access_token=token)
    if preview:
        content.append(preview)
    return content
