"""Shared preview helper for inline chart previews."""

import asyncio
import base64
import logging
import os
import struct
from typing import Any

from datawrapper import Datawrapper
from datawrapper.charts.base import BaseChart
from mcp.types import ImageContent

logger = logging.getLogger(__name__)

# Keep this shorter than export_chart_png's default: a preview is a
# best-effort addition to create/publish/update, not the primary request,
# so it shouldn't hold up that response for as long as an explicit export.
PREVIEW_EXPORT_TIMEOUT = 15

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


async def try_export_preview(
    chart: BaseChart, access_token: str | None = None, *, fit_height: bool = False
) -> ImageContent | None:
    """Export a PNG preview of a chart, returning None on failure.

    With fit_height, the preview is rendered at the chart's natural height and
    that height is saved on the chart, the way the Datawrapper editor sizes a
    new chart. A chart made through the API otherwise keeps a 400px height,
    which cuts off long bar charts and leaves no room to plot a column chart
    with a long intro or legend, in the preview and once published.

    Runs the (synchronous, network-bound) export in a thread so a slow
    Datawrapper render doesn't block the event loop - and therefore every
    other concurrent tool call on this server - while it waits.
    """
    export_params: dict[str, Any] = {
        "zoom": 1,
        "access_token": access_token,
        "timeout": PREVIEW_EXPORT_TIMEOUT,
    }
    if fit_height:
        export_params["height"] = "auto"
    try:
        png_bytes = await asyncio.to_thread(chart.export_png, **export_params)
        base64_data = base64.b64encode(png_bytes).decode("utf-8")
    except Exception:
        logger.warning("Failed to auto-export PNG preview", exc_info=True)
        return None

    if fit_height:
        await _save_height(chart, png_bytes, access_token)

    return ImageContent(
        type="image",
        data=base64_data,
        mime_type="image/png",
    )


async def _save_height(
    chart: BaseChart, png_bytes: bytes, access_token: str | None
) -> None:
    """Save the height of a zoom-1 PNG export as the chart's embed height."""
    if not png_bytes.startswith(PNG_SIGNATURE):
        return
    # The IHDR chunk comes right after the signature; its data starts with the
    # image width and height as big-endian integers.
    (height,) = struct.unpack(">I", png_bytes[20:24])
    token = access_token or os.getenv("DATAWRAPPER_ACCESS_TOKEN")
    client = Datawrapper(access_token=token)
    try:
        await asyncio.to_thread(
            client.patch,
            f"{client._CHARTS_URL}/{chart.chart_id}",
            data={"metadata": {"publish": {"embed-height": height}}},
        )
    except Exception:
        logger.warning("Failed to save the chart's height", exc_info=True)
