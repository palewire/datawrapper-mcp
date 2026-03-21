# Fix: Use `ToolResult` return type for MCP App compatibility

## Problem

Adding `app=AppConfig(resource_uri=...)` to the `@mcp.tool()` decorator causes `create_chart` and `update_chart` to silently disappear from the tool list. No error is logged, no exception is raised — the tools simply don't register.

## Root cause

FastMCP 3.x auto-generates output schemas from return type annotations. When `app=AppConfig(...)` is present on a tool with return type `Sequence[TextContent | ImageContent]`, FastMCP attempts to generate a JSON schema from that complex union of Pydantic models. The schema generation fails internally and FastMCP swallows the error, silently skipping the tool registration.

## Solution

FastMCP's QR Code example (the official MCP Apps reference at https://gofastmcp.com/apps/low-level) demonstrates the correct pattern: tools with `app=` should return `ToolResult`, not `Sequence[TextContent | ImageContent]`.

`ToolResult` is FastMCP's explicit type for tools that return raw MCP content blocks. It bypasses output schema generation entirely, which is exactly what we need. From the official example:

```python
from fastmcp.tools import ToolResult

@mcp.tool(app=AppConfig(resource_uri=VIEW_URI))
def generate_qr(text: str = "https://gofastmcp.com") -> ToolResult:
    """Generate a QR code from text."""
    ...
    return ToolResult(
        content=[types.ImageContent(type="image", data=b64, mimeType="image/png")]
    )
```

## Secondary fix: input validation

FastMCP 3.x uses strict Pydantic validation by default. Claude Desktop sends `chart_config` and `data` as JSON strings rather than parsed objects. The old SDK-bundled FastMCP coerced these automatically; FastMCP 3.x does not. The fix is to accept `str` in the type annotation and parse manually.

## Files changed

| File                                  | Change                                                                                                    |
| ------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `datawrapper_mcp/server.py`           | Change `create_chart` and `update_chart` return types to `ToolResult`, add JSON string parsing for inputs |
| `datawrapper_mcp/handlers/create.py`  | Change return type to use `ToolResult`                                                                    |
| `datawrapper_mcp/handlers/update.py`  | Change return type to use `ToolResult`                                                                    |
| `datawrapper_mcp/handlers/preview.py` | Update to return content compatible with `ToolResult`                                                     |

## Step-by-step changes

### Step 1: Update `create_chart` in `server.py`

```python
# Before
@mcp.tool(app=CHART_VIEW_APP)
async def create_chart(
    data: str | list | dict,
    chart_type: str,
    chart_config: dict,
) -> Sequence[TextContent | ImageContent]:
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
        return [
            TextContent(
                type="text",
                text=f"Error creating chart of type '{chart_type}': {str(e)}",
            )
        ]

# After
from fastmcp.tools import ToolResult

@mcp.tool(app=CHART_VIEW_APP)
async def create_chart(
    data: str | list | dict,
    chart_type: str,
    chart_config: dict | str,
) -> ToolResult:
    # FastMCP 3.x strict validation: Claude may send these as JSON strings
    if isinstance(chart_config, str):
        chart_config = json.loads(chart_config)
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            pass  # It's a file path, not JSON

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
        return ToolResult(content=result)
    except Exception as e:
        return ToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Error creating chart of type '{chart_type}': {str(e)}",
                )
            ]
        )
```

### Step 2: Update `update_chart` in `server.py`

```python
# Before
@mcp.tool(app=CHART_VIEW_APP)
async def update_chart(
    chart_id: str,
    data: str | list | dict | None = None,
    chart_config: dict | None = None,
) -> Sequence[TextContent | ImageContent]:
    arguments: dict[str, Any] = {"chart_id": chart_id}
    if data is not None:
        arguments["data"] = data
    if chart_config is not None:
        arguments["chart_config"] = chart_config

    try:
        return await update_chart_handler(cast(UpdateChartArgs, arguments))
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=f"Error updating chart with ID '{chart_id}': {str(e)}",
            )
        ]

# After
@mcp.tool(app=CHART_VIEW_APP)
async def update_chart(
    chart_id: str,
    data: str | list | dict | None = None,
    chart_config: dict | str | None = None,
) -> ToolResult:
    # FastMCP 3.x strict validation: Claude may send these as JSON strings
    if isinstance(chart_config, str):
        chart_config = json.loads(chart_config)
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            pass  # It's a file path, not JSON

    arguments: dict[str, Any] = {"chart_id": chart_id}
    if data is not None:
        arguments["data"] = data
    if chart_config is not None:
        arguments["chart_config"] = chart_config

    try:
        result = await update_chart_handler(cast(UpdateChartArgs, arguments))
        return ToolResult(content=result)
    except Exception as e:
        return ToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Error updating chart with ID '{chart_id}': {str(e)}",
                )
            ]
        )
```

### Step 3: Verify handler return types are compatible

The existing handlers (`create.py`, `update.py`) return `list[Union[TextContent, ImageContent]]`. The `ToolResult(content=...)` constructor accepts a list of content blocks, so this is directly compatible — the handler return value can be passed straight to `ToolResult(content=result)`. No handler changes needed.

### Step 4: Add import to `server.py`

Add at the top of the file:

```python
from fastmcp.tools import ToolResult
```

## What stays the same

- All handler files (`create.py`, `update.py`, `preview.py`, etc.) remain unchanged
- The `ui://` resource handler and `AppConfig` CSP configuration remain unchanged
- The `views.py` module and vendored SDK remain unchanged
- All other tools (`list_chart_types`, `get_chart_schema`, `publish_chart`, `get_chart`, `delete_chart`, `export_chart_png`) remain unchanged
- The PNG auto-preview behavior is preserved — `ToolResult` wraps the same `[TextContent, ImageContent]` list

## Why this works

`ToolResult` is FastMCP 3.x's designated escape hatch for tools that need to return raw MCP content blocks without triggering output schema generation. From the FastMCP docs:

> For full control over tool responses including the `_meta` field (for passing data to client applications without exposing it to the model), you can return `CallToolResult` directly.

`ToolResult` wraps `CallToolResult` and tells FastMCP: "don't generate a schema, don't validate the output, just pass these content blocks through." This is exactly the pattern used in FastMCP's own MCP Apps examples.

## Testing

After applying this change:

- [ ] `create_chart` appears in the tools list (was silently missing before)
- [ ] `update_chart` appears in the tools list (was silently missing before)
- [ ] Creating a chart works with dict and JSON string inputs for `chart_config` and `data`
- [ ] The PNG auto-preview still appears in the tool result
- [ ] The `ui://` resource is still registered and served
- [ ] All other tools continue to work unchanged
