# Datawrapper MCP App via PrefabUI: Implementation Plan

## Summary

Use PrefabUI — a declarative Python UI framework integrated with FastMCP — to build an MCP App that renders Datawrapper charts inline in the conversation. This replaces the custom HTML approach that was blocked by a FastMCP `app=AppConfig(...)` bug. PrefabUI's `app=True` parameter takes a different code path that works in FastMCP 3.1.1.

## Why PrefabUI instead of custom HTML

We spent significant time debugging `app=AppConfig(resource_uri=...)` on the `@mcp.tool()` decorator. It silently drops tools from the tool list in FastMCP 3.1.1 — the tools register correctly in Python but Claude Desktop doesn't surface them. Every workaround failed (`structured_output=False`, `json_response=True`, `strict_input_validation=False`, `ToolResult` return type, snake_case vs camelCase, raw dict form).

PrefabUI uses `app=True` instead of `app=AppConfig(...)`, which takes a completely different internal code path. Testing confirms it works:

```
$ uv run python -c "..."
hello: meta={'ui': {'resourceUri': 'ui://prefab/renderer.html', 'csp': {'resourceDomains': []}}}
```

The tool registers with proper `_meta.ui` metadata. FastMCP auto-registers a shared Prefab renderer (`ui://prefab/renderer.html`) and wires everything automatically.

## Key PrefabUI components

PrefabUI has the exact components we need:

**`Image`** — Renders an image from a URL or base64 data URI. Fields: `src`, `alt`, `width`, `height`. For the PNG preview: `Image(src=f"data:image/png;base64,{png_data}")`.

**`Embed`** — Renders an iframe. Fields: `url`, `html`, `width`, `height`, `sandbox`, `allow`. For the Datawrapper embed: `Embed(url=f"https://datawrapper.dwcdn.net/{chart_id}/", height="400px")`.

**`Link`** — Renders a clickable `<a>` tag. Preferred for "Open in editor" — renders as a direct link the user can click, rather than the indirect `SendMessage` workaround. If `Link` doesn't work in the sandboxed iframe, fall back to `SendMessage`.

**`Button`** — With `on_click` accepting `CallTool` actions for Publish.

**`CallTool`** — MCP action that calls a server tool from the UI. For publish: `CallTool("publish_chart", arguments={"chart_id": chart_id})`.

**`SendMessage`** — MCP action that sends a message to the chat as if the user typed it. Fallback for "Open in editor" if `Link` doesn't work.

**`Column`, `Row`, `Text`, `Badge`, `Card`** — Layout and display components for structuring the View.

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Claude / Host                                  │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │  Sandboxed iframe                         │  │
│  │  (PrefabUI renderer: ui://prefab/...)     │  │
│  │                                           │  │
│  │  ┌───────────────────────────────────┐    │  │
│  │  │ Image: base64 PNG preview         │    │  │
│  │  │ (or Embed: DW interactive iframe) │    │  │
│  │  └───────────────────────────────────┘    │  │
│  │                                           │  │
│  │  [Publish]  [Open in editor]  chart_id    │  │
│  └───────────────────────────────────────────┘  │
│                    ▲                            │
│                    │ postMessage (JSON-RPC)      │
│                    ▼                            │
│  ┌───────────────────────────────────────────┐  │
│  │  MCP Server (Python + FastMCP 3.x)        │  │
│  │                                           │  │
│  │  create_chart  → returns PrefabApp        │  │
│  │  update_chart  → returns PrefabApp        │  │
│  │  publish_chart → returns PrefabApp        │  │
│  │  (existing handlers do the real work)     │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### How it works

1. Claude calls `create_chart`. FastMCP sees `app=True`, knows to render the PrefabUI View.
2. The tool handler creates the chart (existing logic), exports a PNG preview (existing logic), then builds a PrefabUI component tree with the Image, action buttons, and chart metadata.
3. The tool returns a `PrefabApp` with the component tree and initial state.
4. The host renders the Prefab renderer in a sandboxed iframe and passes the `structuredContent` to it.
5. The user sees the chart preview inline with Publish and Open in Editor buttons.
6. Clicking Publish calls `publish_chart` via `CallTool`, which can return a new `PrefabApp` with the Embed component showing the live interactive chart.

### Display states

**After create (unpublished):** PNG preview rendered via `Image` component, with Publish and Open in Editor buttons.

**After publish:** If `publish_chart` is wired to return a `PrefabApp`, it can show the live Datawrapper embed via the `Embed` component. If not, the PNG preview stays with a success message.

**After update:** New PNG preview rendered, with Re-publish prompt.

## What changes

### Dependencies

Add PrefabUI:

```toml
# pyproject.toml
dependencies = [
    "datawrapper>=2.0.14",
    "fastmcp[apps]==3.1.1",
    "prefab-ui==0.8.0",
    "pandas>=2.0.0",
]
```

### server.py: change `create_chart` and `update_chart`

The tools change from returning `Sequence[TextContent | ImageContent]` to returning `PrefabApp` (or `ToolResult` wrapping a `PrefabApp`). The `app=True` parameter replaces `app=AppConfig(...)`.

```python
from prefab_ui.app import PrefabApp
from prefab_ui.components import (
    Column, Row, Text, Button, Image, Link, Badge, Card, CardContent, CardFooter,
)
from prefab_ui.actions.mcp import CallTool
from fastmcp.tools import ToolResult

@mcp.tool(app=True)
async def create_chart(
    data: str | list | dict,
    chart_type: str,
    chart_config: dict | str,
) -> ToolResult:
    # Parse JSON strings (FastMCP 3.x strict validation)
    if isinstance(chart_config, str):
        chart_config = json.loads(chart_config)
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            pass

    # Create chart using existing handler
    arguments: CreateChartArgs = {
        "data": data,
        "chart_type": chart_type,
        "chart_config": chart_config,
    }
    result = await create_chart_handler(arguments)

    # Extract chart metadata and PNG from handler result
    text_content = next((r for r in result if r.type == "text"), None)
    if text_content is None:
        return ToolResult(content="Chart creation failed: no response from handler")
    image_content = next((r for r in result if r.type == "image"), None)
    chart_data = json.loads(text_content.text)

    chart_id = chart_data["chart_id"]
    edit_url = chart_data["edit_url"]
    title = chart_data.get("title", "")

    # Build PrefabUI component tree
    with Column(gap=4, css_class="p-4") as view:
        # Chart preview
        if image_content:
            Image(
                src=f"data:{image_content.mimeType};base64,{image_content.data}",
                alt=title,
                css_class="w-full rounded",
            )
        else:
            Text("Chart created (no preview available)")

        # Action bar
        with Row(gap=2, align="center"):
            Button(
                "Publish",
                on_click=CallTool(
                    "publish_chart",
                    arguments={"chart_id": chart_id},
                ),
            )
            # Prefer Link for direct clickability; fall back to SendMessage if
            # Link doesn't work inside the sandboxed iframe.
            Link("Open in editor", href=edit_url)
            Text(chart_id, css_class="ml-auto text-xs text-muted-foreground font-mono")

    return ToolResult(
        content=f"Chart '{title}' created (ID: {chart_id}). Edit: {edit_url}",
        structured_content=PrefabApp(
            view=view,
            state={"chart_id": chart_id, "edit_url": edit_url},
        ),
    )
```

Same pattern for `update_chart`.

### Key design decisions

**`ToolResult` wrapping `PrefabApp`.** By returning `ToolResult(content=..., structured_content=PrefabApp(...))`, the model gets a text summary it can reason about while the user sees the interactive UI. Without this, the model only sees `"[Rendered Prefab UI]"` which gives it no context.

**PNG preview via `Image` component.** The existing auto-preview handler exports a base64 PNG. The `Image` component displays it inline using a data URI (`data:image/png;base64,...`). This works in the unpublished state without any Datawrapper CDN dependency.

**`CallTool` for Publish.** The Publish button calls `publish_chart` through MCP — same authentication, same permissions, no leaving the chat. The `publish_chart` tool doesn't currently return a `PrefabApp`, so the initial implementation will show the publish result as text. A later enhancement could have `publish_chart` return a `PrefabApp` with an `Embed` component showing the live chart.

**`Link` for Open in Editor.** PrefabUI's `Link` component renders a clickable `<a>` tag, which is the cleanest way to let the user open the Datawrapper editor. If `Link` doesn't work inside the sandboxed iframe (e.g., blocked by CSP or sandbox attribute), fall back to `SendMessage(f"Open {edit_url} in my browser")` as a workaround — but test `Link` first.

**Input validation.** `chart_config` and `data` accept `str` and parse manually with `json.loads()` to handle FastMCP 3.x's strict Pydantic validation.

**PNG preview size limit.** The `structuredContent` field in an MCP tool result has a 25,000 token limit. A `zoom=2` PNG can be 200-400KB raw, which becomes 270-530KB base64-encoded — potentially exceeding the limit. Default to `zoom=1` for PrefabUI previews. If a chart's base64 PNG still exceeds 200KB at `zoom=1`, skip the inline preview and show a text fallback instead.

### Existing handlers: no changes

All handler files (`create.py`, `update.py`, `preview.py`, etc.) remain unchanged. The PrefabUI layer sits in `server.py` only — it consumes the handler results and builds a component tree from them.

### Files to remove

- `datawrapper_mcp/views.py` — no longer needed (PrefabUI replaces custom HTML)
- `datawrapper_mcp/vendor/ext-apps.js` — no longer needed (PrefabUI bundles its own renderer)

### Updated: pyproject.toml

```toml
dependencies = [
    "datawrapper>=2.0.14",
    "fastmcp[apps]==3.1.1",
    "prefab-ui==0.8.0",
    "pandas>=2.0.0",
]

[tool.setuptools.package-data]
datawrapper_mcp = ["py.typed"]  # Remove vendor/*.js
```

### Updated: deployment/requirements.txt

```
fastmcp[apps]==3.1.1
prefab-ui==0.8.0
datawrapper>=2.0.7
pandas>=2.0.0
starlette>=0.27.0
uvicorn>=0.23.0
```

## Open questions

1. **Does `app=True` work with `ToolResult` return type?** The FastMCP docs show `app=True` with `PrefabApp` return type, and `ToolResult` wrapping `PrefabApp` in `structured_content`. Both should work but need testing with the actual server.

2. **Does `Embed` work for Datawrapper charts?** The `Embed` component renders an iframe. If the host's CSP allows `frame-src` for `datawrapper.dwcdn.net`, the live embed would work. But PrefabUI auto-generates CSP from the app config — we may need `PrefabApp(connect_domains=["https://datawrapper.dwcdn.net"])` or a similar mechanism. The `Embed` component has `sandbox` and `allow` props for iframe configuration. This needs testing.

3. **How does `CallTool` display its result?** When the user clicks Publish and `CallTool` invokes `publish_chart`, what does the user see? If `publish_chart` returns a plain string (as it does now), the Prefab renderer needs to handle that. The FastMCP docs show using `Slot` and `SetState` to dynamically update the UI with tool results — this pattern could show a success message or swap in the Embed component.

4. **Does `Link` work inside the sandboxed iframe?** We'll try `Link` first for "Open in editor". If the sandbox or CSP blocks it, fall back to `SendMessage`. This is tested in Step 4.

5. **Image size limits.** *Decision:* Default to `zoom=1` for PrefabUI previews. If a chart's base64 PNG exceeds 200KB at `zoom=1`, skip the inline preview and show a text fallback. The `structuredContent` field has a 25,000 token limit — a `zoom=2` PNG can easily exceed this.

6. **PrefabUI and FastMCP maturity warning.** Both PrefabUI and FastMCP's MCP Apps integration carry explicit warnings about being in early, active development with frequent breaking changes. Pin both: `prefab-ui==0.8.0` and `fastmcp[apps]==3.1.1`. Since we're coupling two pre-1.0 libraries, pinning both prevents one upgrading and breaking compatibility with the other. Be prepared for API changes when upgrading either.

## Implementation steps

### Step 1: Install dependencies

```bash
uv add "fastmcp[apps]" "prefab-ui==0.8.0"
```

Verify the test script still works:

```bash
uv run python -c "
from fastmcp import FastMCP
from prefab_ui.app import PrefabApp
from prefab_ui.components import Column, Heading
mcp = FastMCP('test')
@mcp.tool(app=True)
def hello() -> PrefabApp:
    with Column() as view:
        Heading('Hello')
    return PrefabApp(view=view)
import asyncio
async def check():
    tools = await mcp.list_tools()
    for t in tools:
        print(f'{t.name}: meta={t.meta}')
asyncio.run(check())
"
```

### Step 2: Update `create_chart` in server.py

Replace the current `create_chart` implementation with the PrefabUI version. Key changes:

- `app=True` instead of `app=AppConfig(...)`
- Return type: `ToolResult` (wrapping `PrefabApp` in `structured_content`)
- Build component tree from handler results
- Parse JSON string inputs

### Step 3: Update `update_chart` in server.py

Same pattern as `create_chart`. Build a component tree showing the updated PNG preview with a Re-publish button.

### Step 4: Test locally

Restart Claude Desktop. Test with the old code still in place (don't remove it until PrefabUI is confirmed working):

- [ ] `create_chart` appears in the tool list (was missing with `AppConfig`)
- [ ] `update_chart` appears in the tool list
- [ ] Creating a chart shows the PrefabUI View inline with PNG preview
- [ ] PNG preview stays within size limits at `zoom=1`
- [ ] Publish button calls `publish_chart` successfully
- [ ] `Link` component works for "Open in editor" (if not, swap to `SendMessage` fallback)
- [ ] Update chart shows new preview
- [ ] Non-PrefabUI tools (`list_chart_types`, `get_chart_schema`, etc.) still work
- [ ] Model can reason about the chart (text content in `ToolResult`)

### Step 5: Remove custom HTML artifacts

Only after Step 4 passes. Remove `views.py`, `vendor/ext-apps.js`, and the `chart_view_resource` resource handler from `server.py`. Remove `CHART_VIEW_URI` and `CHART_VIEW_APP` constants. PrefabUI handles the renderer registration automatically.

### Step 6: Enhance publish flow (optional)

If the basic flow works, enhance `publish_chart` to return a `PrefabApp` with an `Embed` component showing the live Datawrapper chart. Use `Slot` and `SetState` pattern from the PrefabUI docs to dynamically swap the PNG for the live embed after publishing.

### Step 7: Update documentation

- Update `AGENTS.md` with PrefabUI dependency and MCP Apps capability
- Update `server.json` version
- Remove references to custom HTML, vendored SDK, and `views.py`
- Document the PrefabUI maturity warning and version pin

### Step 8: Ship

Update `pyproject.toml` version. Tag release. Publish to PyPI.

## What success looks like

A user asks Claude to create a chart. The PrefabUI View renders inline in the conversation showing a static preview of the chart with Publish and Open in Editor buttons. The user clicks Publish and the chart is published without leaving the chat. The user asks Claude to update the chart, and the View refreshes with a new preview. All of this is built in pure Python — no HTML, no JavaScript, no vendored SDK, no build step.
