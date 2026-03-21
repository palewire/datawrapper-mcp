"""In-memory MCP client tests exercising the full protocol stack.

These tests use FastMCP's Client with the server instance as transport,
so every call goes through tool registration, parameter validation,
middleware (error handling, rate limiting, timing), and content serialization.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from datawrapper import BarChart
from fastmcp import Client

from datawrapper_mcp.server import mcp


@pytest.fixture
async def client():
    """Create an in-memory MCP client connected to the server."""
    async with Client(transport=mcp) as c:
        yield c


# ---------------------------------------------------------------------------
# Pure local tools (no API mocking needed)
# ---------------------------------------------------------------------------


class TestListChartTypes:
    """list_chart_types is a pure local lookup."""

    @pytest.mark.asyncio
    async def test_returns_chart_types(self, client):
        result = await client.call_tool("list_chart_types", {})

        assert not result.is_error
        text = result.content[0].text
        assert "bar" in text
        assert "line" in text
        assert "scatter" in text

    @pytest.mark.asyncio
    async def test_includes_usage_hint(self, client):
        result = await client.call_tool("list_chart_types", {})

        text = result.content[0].text
        assert "get_chart_schema" in text


class TestGetChartSchema:
    """get_chart_schema is a pure local lookup."""

    @pytest.mark.asyncio
    async def test_returns_json_schema(self, client):
        result = await client.call_tool("get_chart_schema", {"chart_type": "bar"})

        assert not result.is_error
        data = json.loads(result.content[0].text)
        assert data["chart_type"] == "bar"
        assert data["class_name"] == "BarChart"
        assert "properties" in data["schema"]

    @pytest.mark.asyncio
    async def test_invalid_chart_type_raises_error(self, client):
        from fastmcp.exceptions import ToolError

        with pytest.raises(ToolError, match="nonexistent"):
            await client.call_tool(
                "get_chart_schema",
                {"chart_type": "nonexistent"},
            )


# ---------------------------------------------------------------------------
# API-dependent tools (mocked at the datawrapper library boundary)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_chart_instance():
    """Create a mock chart that behaves like a real BarChart instance."""
    chart = MagicMock(spec=BarChart)
    chart.chart_id = "abc123"
    chart.title = "Test Chart"
    chart.chart_type = "d3-bars"
    chart.model_dump.return_value = {"title": "Test Chart"}
    chart.get_editor_url.return_value = "https://app.datawrapper.de/chart/abc123/edit"
    chart.get_public_url.return_value = "https://datawrapper.dwcdn.net/abc123/"
    chart.export_png.return_value = b"PNG_FAKE_DATA"
    return chart


@pytest.fixture
def mock_create_flow(mock_chart_instance):
    """Mock the datawrapper library calls used by create_chart handler."""
    with (
        patch(
            "datawrapper_mcp.config.BarChart.model_validate",
            return_value=mock_chart_instance,
        ),
        patch(
            "datawrapper_mcp.handlers.create.try_export_preview",
            return_value=None,
        ),
    ):
        yield mock_chart_instance


@pytest.fixture
def mock_existing_chart_flow(mock_chart_instance):
    """Mock the datawrapper library calls used by get/update/publish/delete handlers."""
    with (
        patch(
            "datawrapper_mcp.handlers.publish.get_chart",
            return_value=mock_chart_instance,
        ),
        patch(
            "datawrapper_mcp.handlers.retrieve.get_chart",
            return_value=mock_chart_instance,
        ),
        patch(
            "datawrapper_mcp.handlers.update.get_chart",
            return_value=mock_chart_instance,
        ),
        patch(
            "datawrapper_mcp.handlers.delete.get_chart",
            return_value=mock_chart_instance,
        ),
        patch(
            "datawrapper_mcp.handlers.export.get_chart",
            return_value=mock_chart_instance,
        ),
        patch(
            "datawrapper_mcp.handlers.create.try_export_preview",
            return_value=None,
        ),
        patch(
            "datawrapper_mcp.handlers.publish.try_export_preview",
            return_value=None,
        ),
        patch(
            "datawrapper_mcp.handlers.update.try_export_preview",
            return_value=None,
        ),
        patch(
            "datawrapper_mcp.config.BarChart.model_validate",
            return_value=mock_chart_instance,
        ),
    ):
        yield mock_chart_instance


class TestCreateChart:
    """create_chart through the full MCP stack."""

    @pytest.mark.asyncio
    async def test_creates_chart_and_returns_metadata(
        self, client, mock_api_token, mock_create_flow
    ):
        result = await client.call_tool(
            "create_chart",
            {
                "data": [{"year": 2020, "value": 100}],
                "chart_type": "bar",
                "chart_config": {"title": "Test Chart"},
            },
        )

        assert not result.is_error
        text = result.content[0].text
        assert "abc123" in text
        assert "Test Chart" in text

    @pytest.mark.asyncio
    async def test_returns_structured_content(
        self, client, mock_api_token, mock_create_flow
    ):
        result = await client.call_tool(
            "create_chart",
            {
                "data": [{"year": 2020, "value": 100}],
                "chart_type": "bar",
                "chart_config": {"title": "Test Chart"},
            },
        )

        assert not result.is_error
        # Apps-capable clients receive structured_content
        assert result.structured_content is not None


class TestPublishChart:
    """publish_chart through the full MCP stack."""

    @pytest.mark.asyncio
    async def test_publishes_and_returns_url(
        self, client, mock_api_token, mock_existing_chart_flow
    ):
        mock_existing_chart_flow.publish.return_value = None

        result = await client.call_tool("publish_chart", {"chart_id": "abc123"})

        assert not result.is_error
        text = result.content[0].text
        assert "abc123" in text

    @pytest.mark.asyncio
    async def test_returns_structured_content(
        self, client, mock_api_token, mock_existing_chart_flow
    ):
        mock_existing_chart_flow.publish.return_value = None

        result = await client.call_tool("publish_chart", {"chart_id": "abc123"})

        assert not result.is_error
        assert result.structured_content is not None


class TestUpdateChart:
    """update_chart through the full MCP stack."""

    @pytest.mark.asyncio
    async def test_updates_chart(
        self, client, mock_api_token, mock_existing_chart_flow
    ):
        result = await client.call_tool(
            "update_chart",
            {
                "chart_id": "abc123",
                "chart_config": {"title": "Updated Title"},
            },
        )

        assert not result.is_error
        text = result.content[0].text
        assert "abc123" in text

    @pytest.mark.asyncio
    async def test_returns_structured_content(
        self, client, mock_api_token, mock_existing_chart_flow
    ):
        result = await client.call_tool(
            "update_chart",
            {
                "chart_id": "abc123",
                "chart_config": {"title": "Updated Title"},
            },
        )

        assert not result.is_error
        assert result.structured_content is not None


class TestGetChart:
    """get_chart through the full MCP stack."""

    @pytest.mark.asyncio
    async def test_retrieves_chart_info(
        self, client, mock_api_token, mock_existing_chart_flow
    ):
        result = await client.call_tool("get_chart", {"chart_id": "abc123"})

        assert not result.is_error
        text = result.content[0].text
        assert "abc123" in text


class TestDeleteChart:
    """delete_chart through the full MCP stack."""

    @pytest.mark.asyncio
    async def test_deletes_chart(
        self, client, mock_api_token, mock_existing_chart_flow
    ):
        mock_existing_chart_flow.delete.return_value = None

        result = await client.call_tool("delete_chart", {"chart_id": "abc123"})

        assert not result.is_error
        text = result.content[0].text
        assert "abc123" in text
