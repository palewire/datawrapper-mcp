"""Golden-snapshot test for the MCP tool/resource surface.

Guards against silent wire-format drift from MCP SDK / FastMCP upgrades -
the kind that changed ImageContent.mimeType -> mime_type and
ToolAnnotations' fields to snake_case without touching our own code. That
upgrade was verified by hand with the MCP Inspector CLI; this test makes
the same check automatic and part of CI.

If a diff here is expected (a deliberate tool/resource change, or a
dependency upgrade that legitimately changes the wire schema), regenerate
the snapshot with:

    make update-schema-snapshot

...and review the diff before committing it.
"""

import json
from pathlib import Path
from typing import Any

from fastmcp import Client

from datawrapper_mcp.server import mcp

SNAPSHOT_PATH = Path(__file__).parent / "snapshots" / "mcp_schema.json"


async def build_schema_snapshot() -> dict[str, Any]:
    """Capture the current MCP tool/resource surface as a JSON-safe dict."""
    async with Client(transport=mcp) as client:
        tools = await client.list_tools()
        resources = await client.list_resources()

    return {
        "tools": {
            tool.name: tool.model_dump(mode="json", exclude_none=True) for tool in tools
        },
        "resources": {
            resource.uri: resource.model_dump(mode="json", exclude_none=True)
            for resource in resources
        },
    }


async def test_schema_matches_snapshot():
    """The live tool/resource schema should match the checked-in snapshot."""
    current = await build_schema_snapshot()
    saved = json.loads(SNAPSHOT_PATH.read_text())

    assert current == saved, (
        "The MCP tool/resource schema no longer matches "
        f"{SNAPSHOT_PATH.relative_to(Path.cwd())}.\n\n"
        "If this change is intentional (a deliberate tool/resource change, "
        "or a dependency upgrade that legitimately changes the wire "
        "schema), regenerate the snapshot with `make update-schema-snapshot` "
        "and review the diff before committing it."
    )
