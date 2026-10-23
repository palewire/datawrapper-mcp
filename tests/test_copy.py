"""Tests for the copy_chart handler."""

import json
from unittest.mock import MagicMock, patch

import pytest

from datawrapper_mcp.handlers.copy import copy_chart


@pytest.fixture
def mock_copy_api():
    """Patch the source chart, its copy and the client that edits the copy."""
    source = MagicMock()
    source.theme = "cambio-colombia"
    copy = MagicMock()
    copy.chart_id = "copy1"
    copy.title = "Chart (Copy)"
    copy.get_editor_url.return_value = "https://app.datawrapper.de/chart/copy1/edit"
    source.duplicate.return_value = copy
    with (
        patch(
            "datawrapper_mcp.handlers.copy.get_chart", return_value=source
        ) as mock_get,
        patch("datawrapper_mcp.handlers.copy.Datawrapper") as mock_client_class,
        patch(
            "datawrapper_mcp.handlers.copy.try_export_preview", return_value=None
        ) as mock_preview,
    ):
        client = mock_client_class.return_value
        client._CHARTS_URL = "https://api.datawrapper.de/v3/charts"
        client.patch.return_value = {"title": "Chart (Copy)", "folderId": 7}
        yield mock_get, source, copy, client, mock_preview


async def test_copy_restores_the_theme(mock_copy_api):
    """A copy of a personal chart gets the default theme, so it's set back."""
    mock_get, source, _, client, mock_preview = mock_copy_api

    result = await copy_chart({"chart_id": "orig1"})

    mock_get.assert_called_once_with("orig1", access_token=None)
    source.duplicate.assert_called_once_with(access_token=None)
    client.patch.assert_called_once_with(
        "https://api.datawrapper.de/v3/charts/copy1",
        data={"theme": "cambio-colombia"},
    )
    assert json.loads(result[0].text) == {
        "chart_id": "copy1",
        "copied_from": "orig1",
        "title": "Chart (Copy)",
        "folder_id": 7,
        "edit_url": "https://app.datawrapper.de/chart/copy1/edit",
    }
    assert len(result) == 1
    mock_preview.assert_called_once()


async def test_copy_sets_title_and_folder_in_the_same_request(mock_copy_api):
    *_, client, _ = mock_copy_api

    await copy_chart(
        {"chart_id": "orig1", "title": "New", "folder_id": 9, "access_token": "tok"}
    )

    client.patch.assert_called_once_with(
        "https://api.datawrapper.de/v3/charts/copy1",
        data={"theme": "cambio-colombia", "title": "New", "folderId": 9},
    )
