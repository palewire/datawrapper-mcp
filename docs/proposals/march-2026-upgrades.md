# datawrapper-mcp upgrade plan

Implementation plan for adopting recent MCP ecosystem improvements. Organized into
four phases, roughly ordered by impact-to-effort ratio. Each phase can ship as an
independent PR.

**Related:** See [per-user-authentication.md](per-user-authentication.md) for the
separate proposal on enabling individual users to bring their own Datawrapper API keys.

---

## Phase 1 — Add tool annotations to every tool

**Why now:** Tool annotations are stable since March 2025, supported across all major
clients, and zero-risk to add. ChatGPT displays tools as "read" or "write" based on
annotations — without them every tool shows as a write operation. Claude, Cursor, and
VS Code Copilot also use annotations for confirmation prompting and safety UI. This is
the single highest-payoff, lowest-effort change available.

**What to do:**

Add `annotations` to each `@mcp.tool()` decorator. The relevant properties are
`readOnlyHint`, `destructiveHint`, `idempotentHint`, and `openWorldHint`.

| Tool               | readOnly | destructive | idempotent | openWorld | Rationale                                      |
| ------------------ | -------- | ----------- | ---------- | --------- | ---------------------------------------------- |
| `list_chart_types` | `true`   | `false`     | `true`     | `false`   | Pure local lookup, no side effects             |
| `get_chart_schema` | `true`   | `false`     | `true`     | `false`   | Pure local lookup                              |
| `get_chart`        | `true`   | `false`     | `true`     | `true`    | Reads from Datawrapper API                     |
| `create_chart`     | `false`  | `false`     | `false`    | `true`    | Creates new resource, additive not destructive |
| `update_chart`     | `false`  | `false`     | `true`     | `true`    | Overwrites existing, same input → same result  |
| `publish_chart`    | `false`  | `false`     | `true`     | `true`    | Idempotent publish                             |
| `delete_chart`     | `false`  | `true`      | `true`     | `true`    | Permanent deletion                             |
| `export_chart_png` | `true`   | `false`     | `true`     | `true`    | Read-only export                               |

Example for `server.py`:

```python
from mcp.types import ToolAnnotations

@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
async def list_chart_types() -> Sequence[TextContent | ImageContent]:
    ...

@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=True,
        openWorldHint=True,
    )
)
async def delete_chart(chart_id: str) -> str:
    ...
```

If FastMCP 3.x wraps this differently (e.g. via its own decorator kwargs), use its
syntax — but the underlying MCP `ToolAnnotations` dict is what matters on the wire.

**Files changed:** `server.py` only.

**Testing:** Run the MCP Inspector (`npx @modelcontextprotocol/inspector`) against the
server and verify annotations appear in each tool's listing. Test in ChatGPT dev mode
to confirm read-only tools no longer show a "write" badge.

**Risk:** None. Annotations are advisory hints and do not change tool behavior.

---

## Phase 2 — Add FastMCP middleware for production hardening

**Why now:** FastMCP 3.x ships battle-tested middleware for error handling, rate
limiting, timing, and logging. Adding these to your server closes operational gaps
with minimal code — each is ~3 lines of config.

**What to do:**

### 2a. Error handling middleware

Catches unhandled exceptions in tool handlers and returns structured error messages
instead of crashing the connection:

```python
from fastmcp.server.middleware import ErrorHandlingMiddleware

mcp = FastMCP(
    "datawrapper-mcp",
    middleware=[ErrorHandlingMiddleware()],
)
```

This replaces the manual `try/except` wrappers in each tool function in `server.py`.
You can simplify tool functions to let exceptions propagate naturally.

### 2b. Rate limiting middleware

Protects against runaway LLM loops that hammer the Datawrapper API:

```python
from fastmcp.server.middleware import RateLimitingMiddleware

mcp = FastMCP(
    "datawrapper-mcp",
    middleware=[
        RateLimitingMiddleware(max_calls=60, period=60),  # 60 calls/min
        ErrorHandlingMiddleware(),
    ],
)
```

### 2c. Timing middleware

Logs execution time for each tool call — essential for identifying slow Datawrapper
API responses vs. local overhead:

```python
from fastmcp.server.middleware import TimingMiddleware

# Add to middleware list
TimingMiddleware()
```

### 2d. Custom audit middleware (optional)

If you want structured logging of every tool invocation for debugging or analytics:

```python
import logging
from fastmcp.server.middleware import Middleware, MiddlewareContext

logger = logging.getLogger("datawrapper_mcp.audit")

class AuditMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        tool_name = context.message.params.name
        logger.info("tool_call", extra={"tool": tool_name})
        result = await call_next(context)
        logger.info("tool_complete", extra={"tool": tool_name})
        return result
```

**Files changed:** `server.py`, optionally new `middleware.py`.

**Testing:** Trigger each tool and verify middleware fires (check logs for timing
output, trigger rate limit by rapid-fire calls).

**Risk:** Low. Middleware is additive and doesn't change tool logic. Order matters —
ErrorHandlingMiddleware should be outermost (last in list, first to catch).

---

## Phase 3 — Add `.well-known/mcp.json` discovery and registry metadata

**Why now:** Server discovery is converging on the `.well-known/mcp.json` format
(SEP-1960), targeted for the next MCP spec release (~June 2026). Early adopters like
Shopify and Replicate already serve it. Adding it now makes your remote deployment
auto-discoverable by clients that support it, and costs almost nothing. You also
already have a `server.json` for the official MCP registry — this phase updates it
and adds multi-registry support.

**What to do:**

### 3a. Serve `.well-known/mcp.json` from the HTTP deployment

Add a route to `deployment/app.py` that returns your server's MCP endpoint metadata:

```python
@mcp.custom_route("/.well-known/mcp.json", methods=["GET"])
async def well_known_mcp(request):
    return JSONResponse({
        "mcp": {
            "versions": ["2025-11-25"],
            "endpoint": "/mcp",
            "name": "datawrapper-mcp",
            "description": "Create Datawrapper charts via MCP",
            "capabilities": {
                "tools": True,
                "resources": True,
                "apps": True
            }
        }
    })
```

### 3b. Update `server.json` for the official MCP Registry

The current `server.json` references version `0.0.16` (package) but the server is at
`0.0.19`. Keep these in sync. Also add a `"docker"` package entry for your Kubernetes
deployment:

```json
{
  "packages": [
    {
      "registryType": "pypi",
      "registryBaseUrl": "https://pypi.org",
      "identifier": "datawrapper-mcp",
      "version": "0.0.19",
      "runtimeHint": "uvx",
      "transport": { "type": "stdio" },
      "environmentVariables": [...]
    },
    {
      "registryType": "docker",
      "registryBaseUrl": "https://hub.docker.com",
      "identifier": "palewire/datawrapper-mcp",
      "version": "latest",
      "transport": { "type": "streamable-http" },
      "environmentVariables": [...]
    }
  ]
}
```

### 3c. Submit to additional registries

Beyond the official MCP registry (registry.modelcontextprotocol.io), consider:

- **GitHub MCP Registry** (github.com/mcp) — integrates directly into VS Code's
  Extensions view. Submission is via a `server.json` in your repo root.
- **Docker MCP Catalog** — if you publish Docker images to Docker Hub.
- **Smithery** (smithery.ai) — largest third-party catalog, 6,000+ servers.

### 3d. Document multi-client config files

Add a `CLIENTS.md` or section in README showing config snippets for each client:

| Client          | Config file                  | Transport                |
| --------------- | ---------------------------- | ------------------------ |
| Claude Desktop  | `claude_desktop_config.json` | stdio or streamable-http |
| Claude.ai       | Managed connector            | streamable-http          |
| VS Code Copilot | `.vscode/mcp.json`           | stdio                    |
| Cursor          | `.cursor/mcp.json`           | stdio or streamable-http |
| ChatGPT         | Dev Mode settings            | streamable-http only     |
| Claude Code     | `.claude/settings.json`      | stdio                    |

**Files changed:** `deployment/app.py`, `server.json`, `README.md` or new
`CLIENTS.md`.

**Testing:** `curl https://your-host/.well-known/mcp.json` returns valid JSON.
Validate `server.json` against the schema at
`https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json`.

**Risk:** None. Purely additive metadata.

---

## Phase 4 — Adopt FastMCP in-memory testing and improve test infrastructure

**Why now:** FastMCP 3.x's in-memory test transport eliminates the need for subprocess
spawning or network mocking in tests. Combined with the existing pytest + VCR setup,
this gives you fast, deterministic tests that actually exercise the full MCP protocol
stack.

**What to do:**

### 4a. Use FastMCP's `Client` with in-memory transport

```python
import pytest
from fastmcp import Client
from datawrapper_mcp.server import mcp

@pytest.fixture
async def client():
    async with Client(transport=mcp) as c:
        yield c

async def test_list_chart_types(client):
    result = await client.call_tool("list_chart_types", {})
    assert not result.isError
    assert "bar" in result.content[0].text

async def test_create_chart_returns_chart_id(client):
    result = await client.call_tool("create_chart", {
        "data": [{"year": 2020, "value": 100}],
        "chart_type": "bar",
        "chart_config": {"title": "Test Chart"},
    })
    assert not result.isError
    # VCR cassette handles the Datawrapper API call
```

### 4b. Add MCP Inspector to CI

```yaml
# In GitHub Actions workflow
- name: Smoke-test with MCP Inspector
  run: |
    npx @modelcontextprotocol/inspector \
      --server "uvx datawrapper-mcp" \
      --check tools
```

### 4c. Add integration tests for MCP Apps rendering

Test that `create_chart`, `publish_chart`, and `update_chart` return both text content
and structured content:

```python
async def test_create_chart_returns_structured_content(client):
    result = await client.call_tool("create_chart", {
        "data": [{"year": 2020, "value": 100}],
        "chart_type": "bar",
        "chart_config": {"title": "Test"},
    })
    # Text fallback exists
    text_items = [c for c in result.content if c.type == "text"]
    assert len(text_items) >= 1
    # Structured content exists for Apps-capable clients
    assert result.structured_content is not None
```

### 4d. Consider `pytest-mcp` for structured assertions

The `pytest-mcp` package on PyPI provides fixtures and matchers purpose-built for MCP
server testing, including performance benchmarks.

**Files changed:** `tests/` directory, `pyproject.toml` (test deps), CI config.

**Testing:** The tests test themselves. Run the full suite and verify coverage.

**Risk:** Low. Test infrastructure changes don't affect production code.

---

## Future considerations (not yet actionable)

These items are worth tracking but not ready for implementation:

**Tasks (experimental):** The async Tasks primitive could enable long-running chart
generation (e.g. generating a series of 20 charts from a large dataset). However,
Tasks is still experimental in the November 2025 spec and client support is minimal.
Monitor for stabilization in the ~June 2026 spec release.

**Elicitation:** Server-initiated prompts to request user input mid-tool-execution
(e.g. "Which column should be the X axis?"). Only 11% of clients support it today.
Worth adding once Claude Desktop and Cursor ship support.

**Per-user Datawrapper authentication:** Allowing individual users to bring their own
Datawrapper API keys (rather than sharing a single server-wide token). See
[per-user-authentication.md](per-user-authentication.md) for detailed options and
implementation plans.

**MCP OAuth 2.1 for public deployment:** If you eventually need public access where
users connect without pre-shared credentials, the MCP spec's OAuth 2.1 support
(with FastMCP's `MultiAuth`) would be the appropriate solution. This is separate from
the per-user Datawrapper authentication problem — OAuth 2.1 authenticates users to
your MCP server, while per-user auth handles the Datawrapper API credentials.

**Resource subscriptions:** Clients subscribing to chart state changes. Not relevant
until your server maintains persistent state beyond the Datawrapper API.

**FastMCP Code Mode:** For servers with many tools, this uses BM25 search + sandboxed
execution instead of listing all tools in context. Not needed at your current tool
count (8 tools), but relevant if you expand significantly.

**`.well-known/mcp.json` standardization:** Currently a proposal (SEP-1960). Phase 4
implements an early version. Update to match the final spec once ratified.

---

## Priority matrix

| Phase                   | Impact | Effort   | Risk | Ship independently? |
| ----------------------- | ------ | -------- | ---- | ------------------- |
| 1. Tool annotations     | High   | Very low | None | Yes                 |
| 2. Middleware           | Medium | Low      | Low  | Yes                 |
| 3. Discovery & registry | Medium | Low      | None | Yes                 |
| 4. Test infrastructure  | Medium | Medium   | None | Yes                 |

Recommended shipping order: **1 → 2 → 4 → 3**.
