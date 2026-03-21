"""Shared preview helper for inline chart previews."""

import base64
import logging

from datawrapper.charts.base import BaseChart
from mcp.types import ImageContent

logger = logging.getLogger(__name__)


def try_export_preview(chart: BaseChart) -> ImageContent | None:
    """Export a PNG preview of a chart, returning None on failure."""
    try:
        png_bytes = chart.export_png(zoom=1)
        base64_data = base64.b64encode(png_bytes).decode("utf-8")
        return ImageContent(
            type="image",
            data=base64_data,
            mimeType="image/png",
        )
    except Exception:
        logger.warning("Failed to auto-export PNG preview", exc_info=True)
        return None
