"""Handlers for listing and creating Datawrapper folders and moving charts."""

import asyncio
import json
import os
from typing import Any, cast

from datawrapper import Datawrapper
from mcp.types import TextContent

from datawrapper_mcp.types import CreateFolderArgs, ListFoldersArgs, MoveChartArgs

# Datawrapper's own label for the root of a user's personal charts.
_PERSONAL_ROOT_NAME = "My Charts"


def _client(access_token: str | None) -> Datawrapper:
    """Build a client with the same token fallback chain as whoami.py."""
    token = access_token or os.getenv("DATAWRAPPER_ACCESS_TOKEN") or None
    return Datawrapper(access_token=token)


def _chart_summaries(charts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only the chart fields useful for finding a chart."""
    return [
        {"id": chart.get("id"), "title": chart.get("title"), "type": chart.get("type")}
        for chart in charts
    ]


def _flatten_folders(
    folders: list[dict[str, Any]],
    parent_path: list[str],
    team_id: str | None,
    include_charts: bool,
) -> list[dict[str, Any]]:
    """Flatten a nested folder tree into a list with readable paths."""
    flat: list[dict[str, Any]] = []
    for folder in folders:
        path = [*parent_path, folder.get("name", "")]
        charts = folder.get("charts") or []
        entry: dict[str, Any] = {
            "id": folder.get("id"),
            "name": folder.get("name"),
            "path": " / ".join(path),
            "team_id": team_id,
            "chart_count": len(charts),
        }
        if include_charts:
            entry["charts"] = _chart_summaries(charts)
        flat.append(entry)
        flat.extend(
            _flatten_folders(folder.get("folders") or [], path, team_id, include_charts)
        )
    return flat


async def list_folders(arguments: ListFoldersArgs) -> list[TextContent]:
    """List the account's personal and team folders as a flat list."""
    include_charts = arguments.get("include_charts", False)
    client = _client(arguments.get("access_token"))
    response: dict[str, Any] = await asyncio.to_thread(client.get_folders)

    roots: list[dict[str, Any]] = []
    folders: list[dict[str, Any]] = []
    for root in response.get("list", []):
        is_team = root.get("type") == "team"
        team_id = root.get("id") if is_team else None
        root_name = root.get("name") if is_team else _PERSONAL_ROOT_NAME
        charts = root.get("charts") or []
        root_entry: dict[str, Any] = {
            "name": root_name,
            "team_id": team_id,
            "chart_count": len(charts),
        }
        if include_charts:
            root_entry["charts"] = _chart_summaries(charts)
        roots.append(root_entry)
        folders.extend(
            _flatten_folders(
                root.get("folders") or [], [root_name], team_id, include_charts
            )
        )

    result = {
        "roots": roots,
        "folders": folders,
        "usage": (
            "Pass a folder's id as folder_id to create_chart, or to move_chart "
            "to move an existing chart. Charts listed under roots are not in "
            "any folder."
        ),
    }
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def create_folder(arguments: CreateFolderArgs) -> list[TextContent]:
    """Create a folder, optionally inside another folder or a team."""
    client = _client(arguments.get("access_token"))
    folder: dict[str, Any] = await asyncio.to_thread(
        client.create_folder,
        arguments["name"],
        parent_id=arguments.get("parent_id"),
        # Team ids are strings such as "QoYTVkNc", although the library
        # annotates this parameter as an int.
        team_id=cast("int | None", arguments.get("team_id")),
    )

    result = {
        "id": folder.get("id"),
        "name": folder.get("name"),
        "parent_id": folder.get("parentId"),
        "team_id": folder.get("teamId"),
    }
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def move_chart(arguments: MoveChartArgs) -> list[TextContent]:
    """Move a chart into a folder.

    Datawrapper moves the chart into the folder's team (or out of a team, for
    a personal folder) on its own, so only the folder id is sent.
    """
    chart_id = arguments["chart_id"]
    client = _client(arguments.get("access_token"))
    chart: dict[str, Any] = await asyncio.to_thread(
        client.move_chart, chart_id, arguments["folder_id"]
    )

    result = {
        "chart_id": chart.get("id", chart_id),
        "folder_id": chart.get("folderId"),
        "team_id": chart.get("organizationId"),
    }
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
