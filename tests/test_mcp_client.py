"""In-memory MCP client tests exercising the full protocol stack.

These tests use FastMCP's Client with the server instance as transport,
so every call goes through tool registration, parameter validation,
middleware (error handling, rate limiting, timing), and content serialization.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from datawrapper import BarChart
from fastmcp import Client
from fastmcp.server.elicitation import (
    AcceptedElicitation,
    CancelledElicitation,
    DeclinedElicitation,
)

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

    async def test_returns_chart_types(self, client):
        result = await client.call_tool("list_chart_types", {})

        assert not result.is_error
        text = result.content[0].text
        assert "bar" in text
        assert "line" in text
        assert "scatter" in text

    async def test_includes_usage_hint(self, client):
        result = await client.call_tool("list_chart_types", {})

        text = result.content[0].text
        assert "get_chart_schema" in text


class TestGetChartSchema:
    """get_chart_schema is a pure local lookup."""

    async def test_returns_json_schema(self, client):
        result = await client.call_tool("get_chart_schema", {"chart_type": "bar"})

        assert not result.is_error
        data = json.loads(result.content[0].text)
        assert data["chart_type"] == "bar"
        assert data["class_name"] == "BarChart"
        assert "properties" in data["schema"]

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


@pytest.fixture
def mock_create_flow_with_preview(mock_chart_instance):
    """Like mock_create_flow, but lets try_export_preview run for real.

    ``mock_chart_instance.export_png`` returns fake PNG bytes, so the real
    ``try_export_preview`` helper produces an actual ``ImageContent`` instead
    of the ``None`` the other fixtures force.
    """
    with patch(
        "datawrapper_mcp.config.BarChart.model_validate",
        return_value=mock_chart_instance,
    ):
        yield mock_chart_instance


@pytest.fixture
def mock_existing_chart_flow_with_preview(mock_chart_instance):
    """Like mock_existing_chart_flow, but lets try_export_preview run for real."""
    with (
        patch(
            "datawrapper_mcp.handlers.publish.get_chart",
            return_value=mock_chart_instance,
        ),
        patch(
            "datawrapper_mcp.handlers.update.get_chart",
            return_value=mock_chart_instance,
        ),
        patch(
            "datawrapper_mcp.config.BarChart.model_validate",
            return_value=mock_chart_instance,
        ),
    ):
        yield mock_chart_instance


class TestCreateChart:
    """create_chart through the full MCP stack."""

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

    async def test_accepts_data_as_json_string(
        self, client, mock_api_token, mock_create_flow
    ):
        """FastMCP's strict validation means Claude may send `data` as a JSON string."""
        result = await client.call_tool(
            "create_chart",
            {
                "data": json.dumps([{"year": 2020, "value": 100}]),
                "chart_type": "bar",
                "chart_config": {"title": "Test Chart"},
            },
        )

        assert not result.is_error
        assert "abc123" in result.content[0].text

    async def test_forwards_explicit_access_token(self, client, mock_create_flow):
        """An explicit access_token argument should be forwarded, not just the env var."""
        result = await client.call_tool(
            "create_chart",
            {
                "data": [{"year": 2020, "value": 100}],
                "chart_type": "bar",
                "chart_config": {"title": "Test Chart"},
                "access_token": "explicit_token_xyz",
            },
        )

        assert not result.is_error
        assert "abc123" in result.content[0].text

    async def test_includes_inline_preview_when_available(
        self, client, mock_api_token, mock_create_flow_with_preview
    ):
        """When a PNG preview export succeeds, it should appear in both the
        fallback content and the Apps view."""
        result = await client.call_tool(
            "create_chart",
            {
                "data": [{"year": 2020, "value": 100}],
                "chart_type": "bar",
                "chart_config": {"title": "Test Chart"},
            },
        )

        assert not result.is_error
        image_items = [item for item in result.content if item.type == "image"]
        assert len(image_items) == 1
        assert image_items[0].mime_type == "image/png"

    async def test_invalid_chart_type_suggests_close_match(self, client):
        from fastmcp.exceptions import ToolError

        with pytest.raises(ToolError, match="Did you mean: stacked_bar"):
            await client.call_tool(
                "create_chart",
                {
                    "data": [{"year": 2020, "value": 100}],
                    "chart_type": "stackedbar",
                    "chart_config": {"title": "Test Chart"},
                },
            )


class TestPublishChart:
    """publish_chart through the full MCP stack."""

    async def test_publishes_and_returns_url(
        self, client, mock_api_token, mock_existing_chart_flow
    ):
        mock_existing_chart_flow.publish.return_value = None

        result = await client.call_tool("publish_chart", {"chart_id": "abc123"})

        assert not result.is_error
        text = result.content[0].text
        assert "abc123" in text

    async def test_returns_structured_content(
        self, client, mock_api_token, mock_existing_chart_flow
    ):
        mock_existing_chart_flow.publish.return_value = None

        result = await client.call_tool("publish_chart", {"chart_id": "abc123"})

        assert not result.is_error
        assert result.structured_content is not None

    async def test_includes_inline_preview_when_available(
        self, client, mock_api_token, mock_existing_chart_flow_with_preview
    ):
        mock_existing_chart_flow_with_preview.publish.return_value = None

        result = await client.call_tool("publish_chart", {"chart_id": "abc123"})

        assert not result.is_error
        image_items = [item for item in result.content if item.type == "image"]
        assert len(image_items) == 1


class TestUpdateChart:
    """update_chart through the full MCP stack."""

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

    async def test_accepts_data_and_json_string_config(
        self, client, mock_api_token, mock_existing_chart_flow
    ):
        """Exercises the `data` argument and a chart_config sent as a JSON string."""
        result = await client.call_tool(
            "update_chart",
            {
                "chart_id": "abc123",
                "data": json.dumps([{"year": 2020, "value": 100}]),
                "chart_config": json.dumps({"title": "Updated Title"}),
            },
        )

        assert not result.is_error
        assert "abc123" in result.content[0].text

    async def test_accepts_data_without_chart_config(
        self, client, mock_api_token, mock_existing_chart_flow
    ):
        """chart_config is optional when only updating the underlying data."""
        result = await client.call_tool(
            "update_chart",
            {
                "chart_id": "abc123",
                "data": [{"year": 2020, "value": 100}],
            },
        )

        assert not result.is_error
        assert "abc123" in result.content[0].text

    async def test_forwards_explicit_access_token(
        self, client, mock_existing_chart_flow
    ):
        result = await client.call_tool(
            "update_chart",
            {
                "chart_id": "abc123",
                "chart_config": {"title": "Updated Title"},
                "access_token": "explicit_token_xyz",
            },
        )

        assert not result.is_error
        assert "abc123" in result.content[0].text

    async def test_includes_inline_preview_when_available(
        self, client, mock_api_token, mock_existing_chart_flow_with_preview
    ):
        result = await client.call_tool(
            "update_chart",
            {
                "chart_id": "abc123",
                "chart_config": {"title": "Updated Title"},
            },
        )

        assert not result.is_error
        image_items = [item for item in result.content if item.type == "image"]
        assert len(image_items) == 1


class TestGetChart:
    """get_chart through the full MCP stack."""

    async def test_retrieves_chart_info(
        self, client, mock_api_token, mock_existing_chart_flow
    ):
        result = await client.call_tool("get_chart", {"chart_id": "abc123"})

        assert not result.is_error
        text = result.content[0].text
        assert "abc123" in text


class TestDeleteChart:
    """delete_chart through the full MCP stack."""

    async def test_deletes_chart(
        self, client, mock_api_token, mock_existing_chart_flow
    ):
        mock_existing_chart_flow.delete.return_value = None

        result = await client.call_tool("delete_chart", {"chart_id": "abc123"})

        assert not result.is_error
        text = result.content[0].text
        assert "abc123" in text

    async def test_falls_back_to_deleting_when_elicitation_unavailable(
        self, client, mock_api_token, mock_existing_chart_flow
    ):
        # No elicitation handler is registered on this client, matching a
        # client whose negotiated MCP protocol has no back-channel for
        # server-initiated elicitation. ctx.elicit() should raise ToolError
        # internally, and the tool should fall back to its pre-elicitation
        # behavior rather than blocking deletion entirely.
        mock_existing_chart_flow.delete.return_value = None

        result = await client.call_tool("delete_chart", {"chart_id": "abc123"})

        assert not result.is_error
        mock_existing_chart_flow.delete.assert_called_once()

    async def test_confirmed_deletion_proceeds(
        self, mock_api_token, mock_existing_chart_flow
    ):
        mock_existing_chart_flow.delete.return_value = None

        with patch(
            "fastmcp.Context.elicit",
            new=AsyncMock(return_value=AcceptedElicitation(data=True)),
        ):
            async with Client(transport=mcp) as confirming_client:
                result = await confirming_client.call_tool(
                    "delete_chart", {"chart_id": "abc123"}
                )

        assert not result.is_error
        mock_existing_chart_flow.delete.assert_called_once()

    async def test_declined_deletion_is_not_performed(
        self, mock_api_token, mock_existing_chart_flow
    ):
        with patch(
            "fastmcp.Context.elicit",
            new=AsyncMock(return_value=DeclinedElicitation()),
        ):
            async with Client(transport=mcp) as declining_client:
                result = await declining_client.call_tool(
                    "delete_chart", {"chart_id": "abc123"}
                )

        assert not result.is_error
        assert "not confirmed" in result.content[0].text.lower()
        mock_existing_chart_flow.delete.assert_not_called()

    async def test_rejecting_confirmation_is_not_performed(
        self, mock_api_token, mock_existing_chart_flow
    ):
        # Accepted, but with data=False (e.g. an unusual client that surfaces
        # the boolean prompt as an accepted form with a "no" value).
        with patch(
            "fastmcp.Context.elicit",
            new=AsyncMock(return_value=AcceptedElicitation(data=False)),
        ):
            async with Client(transport=mcp) as declining_client:
                result = await declining_client.call_tool(
                    "delete_chart", {"chart_id": "abc123"}
                )

        assert not result.is_error
        assert "not confirmed" in result.content[0].text.lower()
        mock_existing_chart_flow.delete.assert_not_called()

    async def test_cancelled_deletion_is_not_performed(
        self, mock_api_token, mock_existing_chart_flow
    ):
        with patch(
            "fastmcp.Context.elicit",
            new=AsyncMock(return_value=CancelledElicitation()),
        ):
            async with Client(transport=mcp) as cancelling_client:
                result = await cancelling_client.call_tool(
                    "delete_chart", {"chart_id": "abc123"}
                )

        assert not result.is_error
        mock_existing_chart_flow.delete.assert_not_called()


class TestCheckDatawrapperConnection:
    """check_datawrapper_connection through the full MCP stack."""

    async def test_reports_authenticated_account(self, client, mock_api_token):
        mock_account = MagicMock()
        mock_account.get_my_account.return_value = {
            "id": 7,
            "email": "ben@example.com",
            "name": "Ben",
        }

        with patch(
            "datawrapper_mcp.handlers.whoami.Datawrapper", return_value=mock_account
        ):
            result = await client.call_tool("check_datawrapper_connection", {})

        assert not result.is_error
        data = json.loads(result.content[0].text)
        assert data["email"] == "ben@example.com"
        assert data["connected"] is True

    async def test_uses_explicit_access_token_over_header(self, client):
        """An explicit access_token argument should be forwarded, like other tools."""
        mock_account = MagicMock()
        mock_account.get_my_account.return_value = {"id": 1, "email": "x@example.com"}

        with patch(
            "datawrapper_mcp.handlers.whoami.Datawrapper", return_value=mock_account
        ) as mock_class:
            result = await client.call_tool(
                "check_datawrapper_connection",
                {"access_token": "explicit_token_xyz"},
            )

        assert not result.is_error
        mock_class.assert_called_once_with(access_token="explicit_token_xyz")

    async def test_rejected_token_raises_troubleshooting_error(self, client):
        from fastmcp.exceptions import ToolError

        mock_account = MagicMock()
        mock_account.get_my_account.side_effect = Exception(
            "Request failed with status code 401. Response content: b''"
        )

        with patch(
            "datawrapper_mcp.handlers.whoami.Datawrapper", return_value=mock_account
        ):
            with pytest.raises(ToolError, match="rejected this token"):
                await client.call_tool(
                    "check_datawrapper_connection", {"access_token": "bad"}
                )


class TestExportChartPng:
    """export_chart_png through the full MCP stack."""

    async def test_exports_with_only_required_args(
        self, client, mock_api_token, mock_existing_chart_flow
    ):
        result = await client.call_tool("export_chart_png", {"chart_id": "abc123"})

        assert not result.is_error
        image_items = [item for item in result.content if item.type == "image"]
        assert len(image_items) == 1
        assert image_items[0].mime_type == "image/png"

    async def test_exports_with_all_optional_args(
        self, client, mock_api_token, mock_existing_chart_flow
    ):
        result = await client.call_tool(
            "export_chart_png",
            {
                "chart_id": "abc123",
                "width": 800,
                "height": 600,
                "plain": True,
                "zoom": 2,
                "transparent": True,
                "border_width": 5,
                "border_color": "#FFFFFF",
                "access_token": "explicit_token_xyz",
                "timeout": 90,
            },
        )

        assert not result.is_error
        image_items = [item for item in result.content if item.type == "image"]
        assert len(image_items) == 1


class TestChartTypesResource:
    """The datawrapper://chart-types resource."""

    async def test_lists_chart_schemas(self, client):
        result = await client.read_resource("datawrapper://chart-types")

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "bar" in data
        assert "class_name" in data["bar"]
        assert "schema" in data["bar"]
