# Datawrapper MCP App: Implementation Plan

## Summary

Add an interactive MCP App to the existing datawrapper-mcp server so that charts render as live, embeddable Datawrapper iframes directly inside the conversation — visible without clicks, interactive with hover tooltips, and fully integrated with the existing Python tool handlers.

## Problem

When `create_chart` or `update_chart` returns a result, Claude wraps it in a collapsible "Used Datawrapper integration" dropdown. Even with the recent PNG auto-preview patch, users must click twice and scroll to see their chart. The MCP protocol has no mechanism to force inline image rendering — this is a client-side UX decision that only MCP Apps can bypass.

## Spike results

The primary technical risk — whether FastMCP supports the `_meta.ui` field needed by MCP Apps — is resolved. FastMCP 3.0+ has built-in MCP Apps support. The `@mcp.tool()` decorator accepts an `app=` parameter with an `AppConfig` object, and `@mcp.resource()` handles `ui://` URIs with automatic MIME type detection (`text/html;profile=mcp-app`).

```python
from fastmcp import FastMCP
from fastmcp.server.apps import AppConfig, ResourceCSP
```

FastMCP also provides runtime detection of host support via `ctx.client_supports_extension(UI_EXTENSION_ID)`, enabling graceful fallback to PNG previews for non-Apps hosts.

## Architecture

The design layers a thin HTML frontend on top of the existing Python backend. No existing handler code needs to change.

```
┌─────────────────────────────────────────────────┐
│  Claude / Host                                  │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │  Sandboxed iframe (MCP App View)          │  │
│  │                                           │  │
│  │  ┌───────────────────────────────────┐    │  │
│  │  │ Unpublished: static PNG preview   │    │  │
│  │  │ Published: interactive DW embed   │    │  │
│  │  └───────────────────────────────────┘    │  │
│  │                                           │  │
│  │  [Publish] [Re-publish] [Edit in DW ↗]   │  │
│  └───────────────────────────────────────────┘  │
│                    ▲                            │
│                    │ postMessage (JSON-RPC)      │
│                    ▼                            │
│  ┌───────────────────────────────────────────┐  │
│  │  MCP Server (Python + FastMCP 3.x)        │  │
│  │                                           │  │
│  │  Existing handlers:                       │  │
│  │    create_chart, update_chart,            │  │
│  │    publish_chart, export_chart_png, ...   │  │
│  │                                           │  │
│  │  New: ui:// resource handler              │  │
│  │    serves View HTML with vendored SDK     │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### How it works

1. Claude calls `create_chart`. The tool's `_meta.ui.resourceUri` tells the host to fetch the View HTML.
2. The host renders the View in a sandboxed iframe and pushes the tool result (chart ID, edit URL, and base64 PNG preview) via `app.ontoolresult`.
3. The View parses the tool result. Since the chart is unpublished, it displays the PNG preview as a static image.
4. The user clicks Publish. The View calls `publish_chart` via `app.callServerTool()`, then replaces the static PNG with a live Datawrapper embed iframe, confirmed by listening for Datawrapper's `datawrapper:height` postMessage event.
5. The user clicks "Open in editor" to jump to Datawrapper's editing interface in the browser.
6. On `update_chart`, the host pushes the new tool result. The View refreshes the PNG preview and prompts re-publishing to push changes to the CDN.

### Display states

The View has three display states:

**Unpublished (after create or update):** The base64 PNG from the auto-preview patch is rendered as a static `<img>`. The user sees the chart immediately — no blank placeholder. Below the image: a Publish button, an "Open in editor" link, and the chart ID.

**Published (after publish):** The PNG is replaced by a live Datawrapper embed iframe (`https://datawrapper.dwcdn.net/{chart_id}/`). The chart is fully interactive with hover tooltips and responsive sizing. The iframe height adjusts dynamically based on Datawrapper's `datawrapper:height` postMessage events. Below: a Re-publish button, an "Open in editor" link, and the chart ID.

**Updated (after update on a published chart):** The View shows the new PNG preview and a "Re-publish to update live chart" prompt, since the CDN may serve stale content until the chart is re-published.

### Embed load detection

`<iframe>` elements do not fire `onerror` for HTTP-level failures like 404s — that event only triggers on network-level failures. A chart that's unpublished, still propagating to the CDN, or otherwise unavailable will render a blank or error page inside the iframe silently.

The View uses Datawrapper's own signaling instead: published Datawrapper charts emit `postMessage` events including `datawrapper:height` when they render successfully. The View listens for this event with a timeout:

```javascript
let embedLoaded = false;

window.addEventListener("message", (event) => {
  if (typeof event.data === "object" && event.data["datawrapper-height"]) {
    embedLoaded = true;
    const heights = event.data["datawrapper-height"];
    const chartHeight = Object.values(heights)[0];
    if (chartHeight) {
      iframe.style.height = chartHeight + "px";
    }
  }
});

setTimeout(() => {
  if (!embedLoaded) {
    showFallback("Embed not available yet. Try re-publishing.");
  }
}, 5000);
```

This serves double duty: it confirms successful load and dynamically sizes the iframe. Datawrapper charts vary widely in height (a simple bar chart vs. a scrollable table), so hardcoding a fixed height would clip tall charts and waste space on short ones.

### CDN caching after updates

After `update_chart` on a previously published chart, the embed URL doesn't change but the content has. Datawrapper's CDN caches aggressively, so reloading the same URL may serve stale content. The View addresses this two ways:

1. **Cache-busting query parameter.** When refreshing after an update, the View appends `?v={timestamp}` to the embed URL.
2. **Re-publish prompt.** After an update, the View shows a "Re-publish to update live chart" message and button, since re-publishing pushes new content to the CDN.

## What changes

### Dependency: switch to FastMCP 3.x

MCP Apps support requires the standalone FastMCP package (v3.0+), not the SDK-bundled version.

In `pyproject.toml`, replace:

```toml
# Before
dependencies = [
    "datawrapper>=2.0.14",
    "mcp[cli]>=1.20.0",
    "pandas>=2.0.0",
    ...
]

# After
dependencies = [
    "datawrapper>=2.0.14",
    "fastmcp>=3.0.0",
    "pandas>=2.0.0",
    ...
]
```

In `server.py`, update the import:

```python
# Before
from mcp.server.fastmcp import FastMCP

# After
from fastmcp import FastMCP
```

In `deployment/requirements.txt`, make the same swap:

```
# Before
mcp[cli]>=1.20.0

# After
fastmcp>=3.0.0
```

**This is the highest-risk change in the plan.** The standalone FastMCP (PrefectHQ) and the SDK-bundled FastMCP (`mcp.server.fastmcp`) share origins but are different packages with different maintainers and release cadences. Step 1 below includes an explicit validation checkpoint and rollback criteria.

### Existing Python handlers: no changes

All existing handlers remain exactly as they are. The auto-preview PNG patch continues to work and serves as the fallback for hosts that don't support MCP Apps.

### server.py: add `app=` parameter and resource handler

Two additions to the existing `server.py`:

#### 1. Add `AppConfig` to `create_chart` and `update_chart`

```python
from fastmcp.server.apps import AppConfig, ResourceCSP

CHART_VIEW_URI = "ui://datawrapper-mcp/chart-view.html"

@mcp.tool(app=AppConfig(resource_uri=CHART_VIEW_URI))
async def create_chart(
    data: str | list | dict,
    chart_type: str,
    chart_config: dict,
) -> Sequence[TextContent | ImageContent]:
    # ... existing implementation unchanged ...
```

Same for `update_chart`:

```python
@mcp.tool(app=AppConfig(resource_uri=CHART_VIEW_URI))
async def update_chart(
    chart_id: str,
    data: str | list | dict | None = None,
    chart_config: dict | None = None,
) -> Sequence[TextContent | ImageContent]:
    # ... existing implementation unchanged ...
```

#### 2. Add the `ui://` resource handler

```python
from .views import get_chart_view_html

@mcp.resource(
    CHART_VIEW_URI,
    app=AppConfig(
        csp=ResourceCSP(
            frame_domains=["https://datawrapper.dwcdn.net"],
        )
    ),
)
def chart_view_resource() -> str:
    """Interactive chart viewer rendered inline in the conversation."""
    return get_chart_view_html()
```

No `resource_domains` CSP entry needed because the ext-apps SDK is vendored inline.

### New: View module with vendored SDK

#### File structure

```
datawrapper_mcp/
├── vendor/
│   └── ext-apps.js              # Unminified SDK source, diffable
├── views.py                     # HTML template + assembly function
├── handlers/
│   ├── create.py                # Unchanged
│   ├── update.py                # Unchanged
│   └── ...
├── server.py                    # Add app= + resource handler
└── ...
```

#### SDK vendoring approach

The `@modelcontextprotocol/ext-apps` JavaScript SDK is vendored as a separate unminified file rather than loaded from a CDN at runtime. This approach:

- **Keeps diffs readable** when bumping the SDK version — reviewers see exactly what changed in `vendor/ext-apps.js`
- **Eliminates the CDN dependency** — no runtime fetch from unpkg, no `resource_domains` CSP entry needed
- **Avoids version-pin fragility** — not affected if a specific unpkg URL goes stale or the package is unpublished

The `vendor/ext-apps.js` file is the unminified `app-with-deps` module from the `@modelcontextprotocol/ext-apps` npm package.

**To update the vendored SDK:** Download the new version's `app-with-deps` module from npm, replace `vendor/ext-apps.js`, and commit. The diff shows exactly what changed.

#### views.py

The module provides a function that reads the vendored SDK and injects it into the HTML template at serve time:

```python
"""MCP App View for inline chart rendering."""

from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).parent

@lru_cache(maxsize=1)
def get_chart_view_html() -> str:
    """Assemble the View HTML with the vendored SDK inlined.

    Cached so the vendored SDK is read from disk only once.
    """
    sdk_js = (_DIR / "vendor" / "ext-apps.js").read_text()
    html = CHART_VIEW_TEMPLATE.replace("/* VENDOR:EXT_APPS_SDK */", sdk_js)
    return html

CHART_VIEW_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="color-scheme" content="light dark">
  <style>
    ...
  </style>
</head>
<body>
  ...
  <script type="module">
    /* VENDOR:EXT_APPS_SDK */

    // View code using the App class follows here
    ...
  </script>
</body>
</html>"""
```

The vendored SDK is read from disk and injected at serve time, producing a single self-contained HTML document. No build step needed.

### View behavior specification

The View handles:

- **Receiving tool results** via `app.ontoolresult` — parses chart JSON from `TextContent`, extracts base64 PNG from `ImageContent`
- **Unpublished state** — renders the base64 PNG as a static `<img src="data:image/png;base64,...">`, showing the chart immediately with no blank placeholder
- **Published state** — renders Datawrapper embed iframe, confirmed via `datawrapper:height` postMessage, with dynamic height adjustment
- **Updated state** — shows new PNG preview, prompts re-publish with cache-busting `?v={timestamp}` on embed URL
- **Publish button** — calls `publish_chart` via `app.callServerTool()`, shows "Publishing…" loading state, surfaces specific error messages on failure (e.g., "Publish failed: chart not found"), transitions to embed state on success
- **Re-publish button** — same as Publish, appears after updates to push changes to CDN
- **Open in editor button** — uses `app.sendOpenLink(editUrl)` to open Datawrapper editor in the browser; falls back to displaying the URL as copyable text if the host doesn't support `sendOpenLink` or lacks `allow-popups` sandbox flag:

```javascript
editorBtn.addEventListener("click", async () => {
  if (currentEditUrl) {
    try {
      await app.sendOpenLink(currentEditUrl);
    } catch {
      editorBtn.textContent = currentEditUrl;
      editorBtn.style.userSelect = "all";
    }
  }
});
```

- **Error display** — surfaces specific error text from failed `callServerTool` responses, not generic messages

#### Published state detection

The existing `create_chart` handler does not return a `public_url` field. The tool result contains `chart_id`, `chart_type`, `title`, `edit_url`, and `message`. The View assumes unpublished on create and shows the PNG preview. After the user clicks Publish, the View transitions to the embed state. This requires no handler changes.

### pyproject.toml package data

Add the vendored SDK to the package:

```toml
[tool.setuptools.package-data]
datawrapper_mcp = ["py.typed", "vendor/*.js"]
```

### Dockerfile

No changes beyond the dependency swap in `deployment/requirements.txt`. The vendored SDK is a Python package data file — no Node.js build step needed.

### Fallback for non-Apps hosts

The existing PNG auto-preview patch continues to work as the fallback. When a host doesn't support MCP Apps, it ignores the `_meta.ui` field and renders the tool result normally — TextContent plus ImageContent inside the dropdown.

For an explicit optimization, FastMCP provides runtime detection:

```python
from fastmcp import Context
from fastmcp.server.apps import UI_EXTENSION_ID

@mcp.tool(app=AppConfig(resource_uri=CHART_VIEW_URI))
async def create_chart(ctx: Context, ...) -> ...:
    # ... create the chart ...

    if ctx.client_supports_extension(UI_EXTENSION_ID):
        # Leaner response — View handles display via PNG from tool result
        return json.dumps({"chart_id": ..., "edit_url": ...})
    else:
        # Full PNG preview for non-Apps hosts
        return [TextContent(...), ImageContent(...)]
```

This is optional. The PNG preview response works in both contexts — Apps-capable hosts pass the full tool result (including `ImageContent`) to the View via `ontoolresult`. But the explicit check lets you skip the PNG export (saving latency and bandwidth) when an Apps-capable host will render the View anyway.

## Implementation steps

### Step 1: Dependency swap with validation checkpoint

Update `pyproject.toml` and `deployment/requirements.txt` to use `fastmcp>=3.0.0`. Update the import in `server.py`.

**Validation checkpoint — all must pass before proceeding:**

- [ ] Full test suite passes (`pytest`)
- [ ] All existing tools work when called from Claude Desktop (create, update, publish, export, delete, get, schema, list)
- [ ] `deployment/app.py` starts correctly — verify `custom_route`, `streamable-http` transport, and health check endpoint
- [ ] The `datawrapper` library's Pydantic models validate correctly (create a chart, update it, publish it)
- [ ] Type exports work: `from mcp.types import TextContent, ImageContent` still resolves

**Rollback criteria:** If any of the above fail and the fix isn't obvious, revert to `mcp[cli]` and open an issue to investigate. Do not proceed with the MCP App work on a broken foundation.

### Step 2: Vendor the ext-apps SDK

Download the `app-with-deps` module from `@modelcontextprotocol/ext-apps` (current stable version). Save the unminified source as `datawrapper_mcp/vendor/ext-apps.js`. Verify the file is readable and diffable. Update `pyproject.toml` package data to include `vendor/*.js`.

### Step 3: Create the View

Create `datawrapper_mcp/views.py` with the HTML template and the `get_chart_view_html()` assembly function. Implement all View behaviors listed in the View behavior specification above.

### Step 4: Register the resource

Add the `chart_view_resource` function to `server.py` with:

- `@mcp.resource()` decorator with `ui://datawrapper-mcp/chart-view.html` URI
- `AppConfig` with `ResourceCSP(frame_domains=["https://datawrapper.dwcdn.net"])`
- Returns assembled HTML from `get_chart_view_html()`

### Step 5: Add `app=` to tools

Add `app=AppConfig(resource_uri=CHART_VIEW_URI)` to the `create_chart` and `update_chart` tool decorators in `server.py`. No changes to function bodies or return types.

### Step 6: Test end-to-end

Restart Claude Desktop. Test the following scenarios:

- [ ] Create a chart → View renders inline with PNG preview and Publish button
- [ ] Click Publish → PNG replaced by live interactive embed with tooltips
- [ ] Verify iframe resizes dynamically (test with different chart types: bar, line, scatter)
- [ ] Verify embed load detection timeout fires if embed URL is unreachable (show fallback message)
- [ ] Update the chart (change title, colors, data) → View shows new PNG preview, prompts re-publish
- [ ] After update, click Re-publish → embed refreshes with cache-busted URL, shows updated content
- [ ] Click "Open in editor" → Datawrapper editor opens in browser (or URL displayed if unsupported)
- [ ] Create a chart in a non-Apps host (if available) → PNG preview fallback works in dropdown
- [ ] Verify CSP: Datawrapper embed iframe loads without console errors
- [ ] Verify the View renders correctly in both light and dark host themes
- [ ] Error case: click Publish on a deleted chart → View shows specific error message
- [ ] Error case: Publish fails for any reason → View shows error, stays on PNG preview, doesn't transition to broken embed state

### Step 7: Update documentation

- Update `AGENTS.md` with the MCP Apps capability and the FastMCP 3.x dependency
- Update `server.json` version
- Add a section to the README about the interactive View feature
- Document the `sendOpenLink` sandbox requirement and fallback behavior
- Document the SDK vendoring approach and how to update `vendor/ext-apps.js`

### Step 8: Update Dockerfile and deploy

Update `deployment/requirements.txt`. Verify the Docker build works with `fastmcp>=3.0.0`. No other Dockerfile changes needed.

### Step 9: Ship

Update `pyproject.toml` version. Tag release. Publish to PyPI.

## Open questions to resolve during implementation

1. **Does the Datawrapper embed iframe load inside the sandboxed MCP App iframe?** The CSP `frame_domains` should allow it, but nested iframes with third-party content can be tricky. Needs hands-on testing in Step 6.

2. **Does `app.callServerTool()` work for `publish_chart`?** By default, tools are available to both the model and the app. If permission issues arise, `publish_chart` may need `app=AppConfig(visibility=["model", "app"])`.

3. **Does `app.sendOpenLink()` work in Claude Desktop?** Depends on the host's `allow-popups` sandbox flag. The View includes a URL-text fallback for hosts that don't support it.

4. **Embed URL propagation delay.** A freshly published chart's embed URL may take a few seconds to appear on Datawrapper's CDN. The `datawrapper:height` timeout handles this — if the embed doesn't load within 5 seconds, the View shows a retry/fallback message.

5. **FastMCP 3.x compatibility with `deployment/app.py`.** The `custom_route` decorator and `streamable-http` transport must work under FastMCP 3.x. Validated in Step 1.

## What success looks like

A user asks Claude to create a Datawrapper chart. An interactive panel appears directly in the conversation showing a static preview of the chart with a Publish button and an "Open in editor" link. The user clicks Publish. The static preview is replaced by a live Datawrapper embed — interactive with hover tooltips, automatically sized to fit the content. The user asks Claude to change the colors. Claude calls `update_chart`. The View refreshes with a new preview and prompts re-publishing. After one click the updated chart is live. The user clicks "Open in editor" to fine-tune in Datawrapper's UI. All without leaving the chat.
