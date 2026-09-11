-# BYOK Implementation Plan: Per-Request Datawrapper Token Support

## Background

When the MCP server is deployed centrally (e.g. on fly.io), all charts are created
under the server operator's Datawrapper account. This means users can't view or edit
the charts they create, because ownership lives in the wrong account.

The fix is to let callers optionally supply their own Datawrapper API token via an
MCP tool argument. The `datawrapper` Python library already supports this — every
method on `BaseChart` accepts an `access_token: str | None = None` parameter, with
`None` falling back to the `DATAWRAPPER_ACCESS_TOKEN` environment variable. No
monkey-patching or concurrency hacks are required.

---

## Scope

| File          | Change type                                                       |
| ------------- | ----------------------------------------------------------------- |
| `types.py`    | Add optional `access_token` field to all `TypedDict` args         |
| `create.py`   | Pass `access_token` to `chart.create()`                           |
| `update.py`   | Pass `access_token` to `chart.update()` and `get_chart()`         |
| `publish.py`  | Pass `access_token` to `get_chart()` and `chart.publish()`        |
| `delete.py`   | Pass `access_token` to `get_chart()` and `chart.delete()`         |
| `export.py`   | Pass `access_token` to `get_chart()` and `chart.export_png()`     |
| `retrieve.py` | Pass `access_token` to `get_chart()`                              |
| `preview.py`  | Accept and forward `access_token` to `chart.export_png()`         |
| `server.py`   | Add `access_token` param to all tools; thread through to handlers |
| `AGENTS.md`   | Document the new parameter                                        |

`schema.py` does not need changes (no API calls).

---

## Step 1 — `types.py`: Add `access_token` to all TypedDicts

Add `access_token: NotRequired[str]` to every args TypedDict that maps to a
handler that makes API calls.

```python
class CreateChartArgs(TypedDict):
    data: str | list[dict] | dict[str, list]
    chart_type: str
    chart_config: dict[str, Any]
    access_token: NotRequired[str]  # ← add


class UpdateChartArgs(TypedDict):
    chart_id: str
    data: NotRequired[str | list[dict] | dict[str, list]]
    chart_config: NotRequired[dict[str, Any]]
    access_token: NotRequired[str]  # ← add


class PublishChartArgs(TypedDict):
    chart_id: str
    access_token: NotRequired[str]  # ← add


class GetChartArgs(TypedDict):
    chart_id: str
    access_token: NotRequired[str]  # ← add


class DeleteChartArgs(TypedDict):
    chart_id: str
    access_token: NotRequired[str]  # ← add


class ExportChartPngArgs(TypedDict):
    chart_id: str
    width: NotRequired[int]
    height: NotRequired[int]
    plain: NotRequired[bool]
    zoom: NotRequired[int]
    transparent: NotRequired[bool]
    border_width: NotRequired[int]
    border_color: NotRequired[str]
    access_token: NotRequired[str]  # ← add
```

`GetChartSchemaArgs` is read-only (no API calls), so leave it unchanged.

---

## Step 2 — Handler files

In each handler, extract `access_token` from `arguments` with `.get()` so it
remains `None` when absent — which causes the library to fall back to the
environment variable automatically.

### `create.py`

> **Note:** `create_chart` does not go through `chart_factory.get_chart()`, so it
> does not benefit from the library's built-in `access_token or os.getenv(...)`
> normalization. Normalize the token here so that an empty string `""` falls back
> to the env var rather than causing a 401.

```python
async def create_chart(arguments: CreateChartArgs) -> list[TextContent]:
    chart_type = arguments["chart_type"]
    token = arguments.get("access_token") or None  # ← add; normalize "" → None

    df = json_to_dataframe(arguments["data"])
    chart_class: type[Any] = CHART_CLASSES[chart_type]

    try:
        chart = chart_class.model_validate(arguments["chart_config"])
    except Exception as e:
        raise ValueError(...)

    chart.data = df
    chart.create(access_token=token)  # ← pass token
    ...
```

### `update.py`

```python
async def update_chart(arguments: UpdateChartArgs) -> list[TextContent]:
    chart_id = arguments["chart_id"]
    token = arguments.get("access_token")  # ← add

    chart = get_chart(chart_id, access_token=token)  # ← pass token

    if "data" in arguments:
        ...

    if "chart_config" in arguments:
        ...

    chart.update(access_token=token)  # ← pass token
    ...
```

### `publish.py`

```python
async def publish_chart(arguments: PublishChartArgs) -> list[TextContent]:
    chart_id = arguments["chart_id"]
    token = arguments.get("access_token")  # ← add

    chart = get_chart(chart_id, access_token=token)  # ← pass token
    chart.publish(access_token=token)  # ← pass token
    ...
```

### `delete.py`

```python
async def delete_chart(arguments: DeleteChartArgs) -> list[TextContent]:
    chart_id = arguments["chart_id"]
    token = arguments.get("access_token")  # ← add

    chart = get_chart(chart_id, access_token=token)  # ← pass token
    chart.delete(access_token=token)  # ← pass token
    ...
```

### `retrieve.py`

```python
async def get_chart_info(arguments: GetChartArgs) -> list[TextContent]:
    chart_id = arguments["chart_id"]
    token = arguments.get("access_token")  # ← add

    chart = get_chart(chart_id, access_token=token)  # ← pass token
    ...
```

### `export.py`

```python
async def export_chart_png(arguments: ExportChartPngArgs) -> list[ImageContent]:
    chart_id = arguments["chart_id"]
    token = arguments.get("access_token")  # ← add

    chart = get_chart(chart_id, access_token=token)  # ← pass token

    export_params: dict[str, Any] = {}
    ...  # existing param extraction unchanged

    png_bytes = chart.export_png(
        **cast(dict[str, Any], export_params),
        access_token=token,  # ← pass token
    )
    ...
```

### `preview.py`

`try_export_preview()` is called internally by `create.py`, `update.py`, and
`publish.py` after mutating a chart. It calls `chart.export_png()`, which is a
separate API call that needs the token. Update the signature to accept and
forward it:

```python
def try_export_preview(
    chart: BaseChart, access_token: str | None = None
) -> ImageContent | None:
    try:
        png_bytes = chart.export_png(zoom=1, access_token=access_token)  # ← pass token
        ...
```

Callers in `create.py`, `update.py`, and `publish.py` must pass `token` through:

```python
preview = try_export_preview(chart, access_token=token)
```

> **`get_chart()` confirmed:** `chart_factory.get_chart(chart_id, access_token=...)`
> accepts `access_token`, threads it to both `Datawrapper.get_chart()` (metadata
> lookup) and `chart_class.get()` (typed instance), and normalizes `""` → `None`
> via `access_token = access_token or os.getenv(...) or None`. No workaround needed.

---

## Step 3 — `server.py`: Add parameter to all tools

Add `access_token: str | None = None` to each tool's signature and include it
when building the `arguments` dict passed to the handler.

```python
@mcp.tool()
async def create_chart(
    data: str | list | dict,
    chart_type: str,
    chart_config: dict,
    access_token: str | None = None,  # ← add
) -> str:
    """
    ...existing docstring...

    Args:
        ...
        access_token: Optional Datawrapper API token. When provided, charts are
                      created in the caller's account (recommended). When omitted,
                      falls back to the server's DATAWRAPPER_ACCESS_TOKEN env var.
    """
    try:
        arguments = cast(
            CreateChartArgs,
            {
                "data": data,
                "chart_type": chart_type,
                "chart_config": chart_config,
                **({"access_token": access_token} if access_token else {}),
            },
        )
        result = await create_chart_handler(arguments)
        return result[0].text
    except Exception as e:
        return f"Error creating chart of type '{chart_type}': {str(e)}"
```

Apply the same pattern to `publish_chart`, `get_chart`, `update_chart`,
`delete_chart`, and `export_chart_png`. Each tool's docstring should include the
`access_token` parameter description shown above.

---

## Step 4 — `AGENTS.md`: Document the new parameter

Add a section under **Available MCP Tools** describing the optional argument:

```markdown
### Optional: Using your own Datawrapper token

All tools accept an optional `access_token` parameter. When provided, the tool
uses that token to authenticate with the Datawrapper API, meaning all charts are
created and owned by the token holder's account.

When omitted, the server falls back to its `DATAWRAPPER_ACCESS_TOKEN` environment
variable (the server operator's account).

**Recommended for hosted deployments**: pass your own token so you can view and
edit charts directly in Datawrapper after creation.
```

---

## Security: token handling

- **Never log or include tokens in error messages.** The `except` blocks in
  `server.py` must not interpolate `access_token` into the error string returned
  to callers. Stick to the existing pattern of including only the chart ID and
  the exception message.
- **Middleware awareness.** `ErrorHandlingMiddleware` in `middleware.py` logs
  full tracebacks via `logger.exception()` and re-raises with
  `f"Error in {tool_name}: {e}"`. If the upstream Datawrapper library ever
  includes the token in an exception message (e.g. a failed auth URL), it could
  leak through these paths. No code change is required now — the library does not
  currently do this — but keep it in mind if upgrading the library.
- **No persistence.** Tokens are used for the duration of a single request and
  are not stored on the server. They exist only as function arguments in memory.
- **MCP transport visibility.** Callers should be aware that `access_token` is
  transmitted as a plain tool argument. Over stdio this stays local; over SSE/HTTP
  the transport should use TLS. This is a caller responsibility, not something the
  server needs to enforce, but worth noting in `AGENTS.md`.

---

## HTTP Authorization header injection

For HTTP deployments (streamable-http on Fly.io), callers can pass their
Datawrapper token via the standard HTTP `Authorization` header instead of
including `access_token` in every tool call:

```
Authorization: Bearer <datawrapper-api-token>
```

`BearerTokenMiddleware` in `middleware.py` reads the header via FastMCP's
`get_http_headers(include={"authorization"})` and injects it as `access_token`
into tool arguments using `setdefault`. This means:

- **Explicit `access_token` tool argument always wins** (via `setdefault`)
- **Stdio callers are unaffected** (`get_http_headers()` returns `{}`)
- **No handler changes needed** — handlers already read `arguments.get("access_token")`

### Token precedence (highest to lowest)

1. `access_token` passed as a tool argument
2. `Authorization: Bearer <token>` HTTP header
3. `DATAWRAPPER_ACCESS_TOKEN` env var (library fallback)

---

## What this does NOT change

- **No concurrency risk.** There is no mutation of `os.environ`. Each call to
  `chart_factory.get_chart()` instantiates a fresh `Datawrapper` client internally,
  and `create_chart` passes the token directly to `chart.create()`.
- **No breaking changes.** `access_token` is `NotRequired` in all TypedDicts and
  defaults to `None` in all tool signatures. Existing callers that don't supply a
  token continue to work exactly as before.
- **No changes to the deployment layer.** `deployment/app.py` and the Dockerfile
  do not need to change.
- **No schema or MCP protocol changes.** The parameter shows up as a standard
  optional tool argument, visible to any MCP client that inspects the tool schema.

---

## Tests

### Existing tests

There are 8 test files under `tests/` plus `conftest.py`. The `mock_get_chart`
fixture in `conftest.py` patches `get_chart` across all handler modules. Existing
tests do not pass `access_token`, so they exercise the env-var fallback path.

**All existing tests must continue to pass unchanged** — this validates backwards
compatibility.

### New test coverage

Add tests that verify `access_token` is forwarded correctly:

- **`conftest.py`**: No new fixtures needed. The existing `mock_get_chart` fixture
  already returns a `MagicMock`; callers can assert `get_chart` was called with
  `access_token=...` via `mock_get_chart.assert_called_with(...)`.
- **Handler tests** (one per handler): Call the handler with
  `access_token="user_token_xyz"` and assert:
  - `get_chart()` was called with `access_token="user_token_xyz"` (for handlers
    that use it)
  - `chart.create()` / `.update()` / `.publish()` / `.delete()` / `.export_png()`
    was called with `access_token="user_token_xyz"`
  - `try_export_preview()` was called with `access_token="user_token_xyz"` (for
    `create`, `update`, `publish`)
- **Edge case**: Call `create_chart` with `access_token=""` and verify it
  normalizes to `None` (env-var fallback).

### Manual testing checklist

- [ ] Call each tool without `access_token` — should use env var as before
- [ ] Call `create_chart` with a valid personal token — chart should appear in the
      token holder's Datawrapper account
- [ ] Call `get_chart` / `update_chart` / `publish_chart` with a token for a chart
      owned by that token's account — should succeed
- [ ] Call `get_chart` with a token for a chart _not_ owned by that account —
      should return a clear 403/404 error from the library, not a crash
- [ ] Confirm `export_chart_png` forwards `access_token` to `chart.export_png()`
      correctly (the `export_params` dict currently uses `**cast` unpacking, so
      `access_token` must be passed as a separate keyword arg, not inside that dict)
