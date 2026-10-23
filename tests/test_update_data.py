"""update_chart uploads data only when new data is sent."""

from unittest.mock import AsyncMock, patch

import pandas as pd
from datawrapper import BarChart

from datawrapper_mcp.handlers.update import update_chart


async def run_update(arguments: dict) -> str | None:
    """Run update_chart on a fetched bar chart and return the data it uploads."""
    chart = BarChart(
        title="Fetched",
        data=pd.DataFrame({"Group": ["Teens", "Adults"], "Unnamed: 1": [1, 2]}),
    )
    chart.chart_id = "abc12"
    uploaded: list[str | None] = []

    def fake_update(self: BarChart, access_token: str | None = None) -> BarChart:
        uploaded.append(self.serialize_data())
        return self

    with (
        patch("datawrapper_mcp.handlers.update.get_chart", return_value=chart),
        patch.object(BarChart, "update", fake_update),
        patch(
            "datawrapper_mcp.handlers.update.try_export_preview",
            new=AsyncMock(return_value=None),
        ),
    ):
        await update_chart({"chart_id": "abc12", **arguments})

    return uploaded[0]


async def test_config_only_update_leaves_data_alone(mock_api_token):
    assert await run_update({"chart_config": {"title": "New title"}}) is None


async def test_update_with_data_uploads_it(mock_api_token):
    csv = await run_update({"data": [{"Group": "Kids", "Value": 3}]})

    assert csv is not None
    assert "Kids" in csv
    assert "Unnamed" not in csv
