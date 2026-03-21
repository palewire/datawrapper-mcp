# Auto-preview PNG on chart create and update

## Problem

When a chart is created or updated via the Datawrapper MCP server, the response only contains a chart ID and an editor URL. The user must leave the chat interface and visit Datawrapper's website to see what the chart looks like. This creates friction in the iterative design loop: create → leave chat → look at chart → come back → request changes → repeat.

## Solution

Modify `create_chart` and `update_chart` to automatically export a PNG preview and return it inline alongside the existing text response. The chart image appears directly in the chat, so the user never has to leave the interface to see the result.

Key design decisions:

- **No publishing required.** The Datawrapper API supports PNG export on unpublished charts, so this feature doesn't change the chart's visibility.
- **Best-effort, non-fatal preview.** PNG export is attempted synchronously and wrapped in a try/except. If it fails for any reason, the text response (chart ID, URLs) is still returned — the preview is a bonus, not a gate.
- **No new tools or parameters.** The change is internal to the existing handlers. From the caller's perspective, the same tools and parameters are used, but the response shape changes from `list[TextContent]` to `Sequence[TextContent | ImageContent]` (text plus an optional image block).

## Files changed

| File                                 | Change                                                                                                                         |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| `datawrapper_mcp/handlers/preview.py`| New helper: `try_export_preview(chart)` returns an `ImageContent` or `None`                                                    |
| `datawrapper_mcp/handlers/create.py` | Import and call `try_export_preview` after `chart.create()`, append result to response                                         |
| `datawrapper_mcp/handlers/update.py` | Import and call `try_export_preview` after `chart.update()`, append result to response                                         |
| `datawrapper_mcp/server.py`          | Change `create_chart` and `update_chart` wrappers to pass through full response (text + image) instead of extracting only text |

## Step-by-step implementation

### Step 1: Create `datawrapper_mcp/handlers/preview.py`

A shared helper that attempts a PNG export and returns an `ImageContent` on success or `None` on failure. Both `create.py` and `update.py` will call this instead of duplicating the export logic.

```python
"""Shared preview helper for inline chart previews."""

import base64
import logging

from datawrapper.charts.base import BaseChart
from mcp.types import ImageContent

logger = logging.getLogger(__name__)


def try_export_preview(chart: BaseChart) -> ImageContent | None:
    """Export a PNG preview of a chart, returning None on failure."""
    try:
        png_bytes = chart.export_png()
        base64_data = base64.b64encode(png_bytes).decode("utf-8")
        return ImageContent(
            type="image",
            data=base64_data,
            mimeType="image/png",
        )
    except Exception as e:
        logger.warning(f"Failed to auto-export PNG preview: {e}")
        return None
```

### Step 2: Update `datawrapper_mcp/handlers/create.py`

The handler's return type changes from `list[TextContent]` to `list[TextContent | ImageContent]`. After calling `chart.create()`, it calls the shared helper and appends the result if present.

Changes from the current file:

1. Add import: `from .preview import try_export_preview`
2. Add import: `from mcp.types import ImageContent`
3. Change return type to `list[TextContent | ImageContent]`
4. After building the text response, call `try_export_preview(chart)` and append the result if not `None`

```python
    response: list[TextContent | ImageContent] = [
        TextContent(type="text", text=json.dumps(result, indent=2))
    ]

    preview = try_export_preview(chart)
    if preview:
        response.append(preview)

    return response
```

### Step 3: Update `datawrapper_mcp/handlers/update.py`

Same pattern as Step 2 — import the helper, change the return type, and append the preview.

```python
    response: list[TextContent | ImageContent] = [
        TextContent(type="text", text=json.dumps(result, indent=2))
    ]

    preview = try_export_preview(chart)
    if preview:
        response.append(preview)

    return response
```

### Step 4: Update `datawrapper_mcp/server.py`

The tool wrappers for `create_chart` and `update_chart` previously returned `-> str` and extracted only the first text element from the handler response:

```python
result = await create_chart_handler(arguments)
return result[0].text  # discards any ImageContent
```

This must change so the wrappers pass through the full handler response, including both `TextContent` and `ImageContent`.

#### 4a. Change the `create_chart` wrapper

Change the return type from `-> str` to `-> Sequence[TextContent | ImageContent]`.

Replace the return-type annotation and the try/except body:

```python
# BEFORE
async def create_chart(
    data: str | list | dict,
    chart_type: str,
    chart_config: dict,
) -> str:
    # ... docstring ...
    try:
        arguments = cast(
            CreateChartArgs,
            {
                "data": data,
                "chart_type": chart_type,
                "chart_config": chart_config,
            },
        )
        result = await create_chart_handler(arguments)
        return result[0].text
    except Exception as e:
        return f"Error creating chart of type '{chart_type}': {str(e)}"

# AFTER
async def create_chart(
    data: str | list | dict,
    chart_type: str,
    chart_config: dict,
) -> Sequence[TextContent | ImageContent]:
    # ... docstring ...
    try:
        arguments = cast(
            CreateChartArgs,
            {
                "data": data,
                "chart_type": chart_type,
                "chart_config": chart_config,
            },
        )
        return await create_chart_handler(arguments)
    except Exception as e:
        return [TextContent(type="text", text=f"Error creating chart of type '{chart_type}': {str(e)}")]
```

#### 4b. Change the `update_chart` wrapper

Same pattern — change the return type and pass through the full response.

```python
# BEFORE
async def update_chart(
    chart_id: str,
    data: str | list | dict | None = None,
    chart_config: dict | None = None,
) -> str:
    # ... docstring ...
    try:
        result = await update_chart_handler(cast(UpdateChartArgs, arguments))
        return result[0].text
    except Exception as e:
        return f"Error updating chart with ID '{chart_id}': {str(e)}"

# AFTER
async def update_chart(
    chart_id: str,
    data: str | list | dict | None = None,
    chart_config: dict | None = None,
) -> Sequence[TextContent | ImageContent]:
    # ... docstring ...
    try:
        return await update_chart_handler(cast(UpdateChartArgs, arguments))
    except Exception as e:
        return [TextContent(type="text", text=f"Error updating chart with ID '{chart_id}': {str(e)}")]
```

## What stays the same

- The `export_chart_png` tool is unchanged and still available for explicit, customized exports (custom dimensions, zoom, transparency, etc.).
- The `publish_chart` tool is unchanged. Auto-preview does not auto-publish.
- The `delete_chart`, `get_chart`, `get_chart_schema`, and `list_chart_types` tools are unchanged.
- The chart ID, edit URL, and all other text metadata are still returned in the response.

## Known limitation

The MCP image content may render inside a collapsible dropdown in the Claude chat UI rather than directly inline. This is a client-side rendering decision in claude.ai, not something the MCP server controls. If the dropdown behavior persists after this change, it would need to be addressed on the client side separately. Regardless, having the preview available in the response is still an improvement over requiring the user to leave the chat.
