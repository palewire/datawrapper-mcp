"""Tests for the list_folders, create_folder and move_chart handlers."""

import json
from unittest.mock import MagicMock, patch

import pytest

from datawrapper_mcp.handlers.folders import create_folder, list_folders, move_chart

# Shape of GET /v3/folders: one root for the user's personal charts, then one
# per team, each holding nested folders.
FOLDERS_RESPONSE = {
    "list": [
        {
            "type": "user",
            "id": 42,
            "charts": [{"id": "root1", "title": "Loose chart", "type": "d3-bars"}],
            "folders": [
                {
                    "id": 101,
                    "name": "Drafts",
                    "charts": [],
                    "folders": [
                        {
                            "id": 102,
                            "name": "Old",
                            "charts": [
                                {
                                    "id": "abc12",
                                    "title": "Old chart",
                                    "type": "d3-lines",
                                }
                            ],
                            "folders": [],
                        }
                    ],
                }
            ],
        },
        {
            "type": "team",
            "id": "QoYTVkNc",
            "name": "Newsroom",
            "charts": [],
            "folders": [{"id": 201, "name": "Elections", "charts": [], "folders": []}],
        },
    ],
    "total": 2,
}


@pytest.fixture
def mock_datawrapper_client():
    with patch("datawrapper_mcp.handlers.folders.Datawrapper") as mock_class:
        client = MagicMock()
        mock_class.return_value = client
        yield mock_class, client


async def test_list_folders_flattens_nested_folders(mock_datawrapper_client):
    _, client = mock_datawrapper_client
    client.get_folders.return_value = FOLDERS_RESPONSE

    result = json.loads((await list_folders({}))[0].text)

    assert result["folders"] == [
        {
            "id": 101,
            "name": "Drafts",
            "path": "My Charts / Drafts",
            "team_id": None,
            "chart_count": 0,
        },
        {
            "id": 102,
            "name": "Old",
            "path": "My Charts / Drafts / Old",
            "team_id": None,
            "chart_count": 1,
        },
        {
            "id": 201,
            "name": "Elections",
            "path": "Newsroom / Elections",
            "team_id": "QoYTVkNc",
            "chart_count": 0,
        },
    ]
    assert result["roots"] == [
        {"name": "My Charts", "team_id": None, "chart_count": 1},
        {"name": "Newsroom", "team_id": "QoYTVkNc", "chart_count": 0},
    ]
    assert "move_chart" in result["usage"]


async def test_list_folders_can_include_charts(mock_datawrapper_client):
    _, client = mock_datawrapper_client
    client.get_folders.return_value = FOLDERS_RESPONSE

    result = json.loads((await list_folders({"include_charts": True}))[0].text)

    old = next(f for f in result["folders"] if f["id"] == 102)
    assert old["charts"] == [{"id": "abc12", "title": "Old chart", "type": "d3-lines"}]
    assert result["roots"][0]["charts"] == [
        {"id": "root1", "title": "Loose chart", "type": "d3-bars"}
    ]


async def test_list_folders_handles_empty_account(mock_datawrapper_client):
    _, client = mock_datawrapper_client
    client.get_folders.return_value = {"list": [], "total": 0}

    result = json.loads((await list_folders({}))[0].text)

    assert result["roots"] == []
    assert result["folders"] == []


async def test_create_folder_forwards_parent_and_team(mock_datawrapper_client):
    _, client = mock_datawrapper_client
    client.create_folder.return_value = {
        "id": 300,
        "name": "Budget",
        "parentId": 201,
        "teamId": "QoYTVkNc",
        "userId": None,
    }

    result = json.loads(
        (
            await create_folder(
                {"name": "Budget", "parent_id": 201, "team_id": "QoYTVkNc"}
            )
        )[0].text
    )

    client.create_folder.assert_called_once_with(
        "Budget", parent_id=201, team_id="QoYTVkNc"
    )
    assert result == {
        "id": 300,
        "name": "Budget",
        "parent_id": 201,
        "team_id": "QoYTVkNc",
    }


async def test_create_folder_defaults_to_personal(mock_datawrapper_client):
    _, client = mock_datawrapper_client
    client.create_folder.return_value = {"id": 301, "name": "Mine"}

    await create_folder({"name": "Mine"})

    client.create_folder.assert_called_once_with("Mine", parent_id=None, team_id=None)


async def test_move_chart_reports_new_folder_and_team(mock_datawrapper_client):
    _, client = mock_datawrapper_client
    client.move_chart.return_value = {
        "id": "abc12",
        "folderId": 201,
        "organizationId": "QoYTVkNc",
    }

    result = json.loads(
        (await move_chart({"chart_id": "abc12", "folder_id": 201}))[0].text
    )

    client.move_chart.assert_called_once_with("abc12", 201)
    assert result == {"chart_id": "abc12", "folder_id": 201, "team_id": "QoYTVkNc"}


async def test_folder_tools_use_explicit_token(mock_datawrapper_client):
    mock_class, client = mock_datawrapper_client
    client.get_folders.return_value = {"list": []}

    await list_folders({"access_token": "user-token"})

    mock_class.assert_called_once_with(access_token="user-token")


async def test_folder_tools_fall_back_to_env_token(
    mock_datawrapper_client, monkeypatch
):
    mock_class, client = mock_datawrapper_client
    client.move_chart.return_value = {"id": "abc12", "folderId": 1}
    monkeypatch.setenv("DATAWRAPPER_ACCESS_TOKEN", "env-token")

    await move_chart({"chart_id": "abc12", "folder_id": 1, "access_token": ""})

    # Never construct Datawrapper(access_token="") or None when an env token
    # exists - see handlers/whoami.py.
    mock_class.assert_called_once_with(access_token="env-token")
