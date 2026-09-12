"""Shared preview helper for inline chart previews."""

import asyncio
import base64
import logging

from datawrapper.charts.base import BaseChart
from mcp.types import ImageContent

logger = logging.getLogger(__name__)

# Keep this shorter than export_chart_png's default: a preview is a
# best-effort addition to create/publish/update, not the primary request,
# so it shouldn't hold up that response for as long as an explicit export.
PREVIEW_EXPORT_TIMEOUT = 15


async def try_export_preview(
    chart: BaseChart, access_token: str | None = None
) -> ImageContent | None:
    """Export a PNG preview of a chart, returning None on failure.

    Runs the (synchronous, network-bound) export in a thread so a slow
    Datawrapper render doesn't block the event loop - and therefore every
    other concurrent tool call on this server - while it waits.
    """
    try:
        png_bytes = await asyncio.to_thread(
            chart.export_png,
            zoom=1,
            access_token=access_token,
            timeout=PREVIEW_EXPORT_TIMEOUT,
        )
        base64_data = base64.b64encode(png_bytes).decode("utf-8")
        return ImageContent(
            type="image",
            data=base64_data,
            mime_type="image/png",
        )
    except Exception:
        logger.warning("Failed to auto-export PNG preview", exc_info=True)
        return None
