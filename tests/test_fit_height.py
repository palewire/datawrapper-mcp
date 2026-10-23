"""Charts sized to their content get a new height whenever they change."""

from unittest.mock import patch

import pytest

from datawrapper_mcp.config import fits_content
from datawrapper_mcp.handlers.update import update_chart


@pytest.mark.parametrize(
    ("chart_type", "expected"),
    [
        ("bar", True),
        ("stacked_bar", True),
        ("d3-bars-split", True),
        ("tables", True),
        ("column", False),
        ("line", False),
        ("d3-pies", False),
    ],
)
def test_fits_content(chart_type, expected):
    assert fits_content(chart_type) is expected


@pytest.mark.parametrize(
    ("chart_type", "fit_height"), [("d3-bars", True), ("column-chart", False)]
)
async def test_update_refits_only_content_sized_charts(
    mock_chart, chart_type, fit_height
):
    mock_chart.chart_type = chart_type
    with (
        patch("datawrapper_mcp.handlers.update.get_chart", return_value=mock_chart),
        patch(
            "datawrapper_mcp.handlers.update.try_export_preview", return_value=None
        ) as mock_preview,
    ):
        await update_chart({"chart_id": "abc12", "chart_config": {"title": "New"}})

    assert mock_preview.call_args.kwargs["fit_height"] is fit_height
