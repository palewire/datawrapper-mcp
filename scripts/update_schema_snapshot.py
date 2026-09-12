"""Regenerate the golden MCP tool/resource schema snapshot.

Run this after a deliberate tool/resource change, or a dependency upgrade
that legitimately changes the MCP wire schema, then review the diff before
committing it.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_schema_snapshot import (
    SNAPSHOT_PATH,
    build_schema_snapshot,
)


async def main() -> None:
    """Write the current MCP schema out to the snapshot file."""
    snapshot = await build_schema_snapshot()
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {SNAPSHOT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
