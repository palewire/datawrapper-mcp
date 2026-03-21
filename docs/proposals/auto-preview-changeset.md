# Auto-preview PNG on chart create and update

## Problem

When a chart is created or updated via the Datawrapper MCP server, the response only contains a chart ID and an editor URL. The user must leave the chat interface and visit Datawrapper's website to see what the chart looks like. This creates friction in the iterative design loop: create → leave chat → look at chart → come back → request changes → repeat.

## Solution

Modify `create_chart` and `update_chart` to automatically export a PNG preview and return it inline alongside the existing text response. The chart image appears directly in the chat, so the user never has to leave the interface to see the result.

Key design decisions:

- **No publishing required.** The Datawrapper API supports PNG export on unpublished charts, so this feature doesn't change the chart's visibility.
- **Non-blocking.** The PNG export is wrapped in a try/except. If it fails for any reason, the text response (chart ID, URLs) is still returned — the preview is a bonus, not a gate.
- **No new tools or parameters.** The change is internal to the existing handlers. The MCP tool interface is unchanged from the caller's perspective.

## Files changed

| File                                 | Change                                                                                                                         |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| `datawrapper_mcp/handlers/create.py` | Export PNG after `chart.create()`, append `ImageContent` to response                                                           |
| `datawrapper_mcp/handlers/update.py` | Export PNG after `chart.update()`, append `ImageContent` to response                                                           |
| `datawrapper_mcp/server.py`          | Change `create_chart` and `update_chart` wrappers to pass through full response (text + image) instead of extracting only text |

## Step-by-step implementation

### Step 1: Update `datawrapper_mcp/handlers/create.py`

The handler's return type changes from `list[TextContent]` to `list[Union[TextContent, ImageContent]]`. After calling `chart.create()`, it exports a PNG and appends it to the response.

Replace the entire file with:

```python
"""Handler for creating Datawrapper charts."""

import base64
import json
import logging
from typing import Any, Union

from mcp.types import ImageContent, TextContent

from ..config import CHART_CLASSES
from ..types import CreateChartArgs
from ..utils import json_to_dataframe

logger = logging.getLogger(__name__)


async def create_chart(
    arguments: CreateChartArgs,
) -> list[Union[TextContent, ImageContent]]:
    """Create a chart with full Pydantic model configuration."""
    chart_type = arguments["chart_type"]

    # Convert data to DataFrame
    df = json_to_dataframe(arguments["data"])

    # Get chart class and validate config
    chart_class: type[Any] = CHART_CLASSES[chart_type]

    # Validate and create chart using Pydantic model
    try:
        chart = chart_class.model_validate(arguments["chart_config"])
    except Exception as e:
        raise ValueError(
            f"Invalid chart configuration: {str(e)}\n\n"
            f"Use get_chart_schema with chart_type '{chart_type}' "
            f"to see the valid schema."
        )

    # Set data on chart instance
    chart.data = df

    # Create chart using Pydantic instance method
    chart.create()

    result = {
        "chart_id": chart.chart_id,
        "chart_type": chart_type,
        "title": chart.title,
        "edit_url": chart.get_editor_url(),
        "message": (
            f"Chart created successfully! Edit it at: {chart.get_editor_url()}\n"
            f"Use publish_chart with chart_id '{chart.chart_id}' to make it public."
        ),
    }

    response: list[Union[TextContent, ImageContent]] = [
        TextContent(type="text", text=json.dumps(result, indent=2))
    ]

    # Auto-export a PNG preview so the chart is visible inline
    try:
        png_bytes = chart.export_png(zoom=2)
        base64_data = base64.b64encode(png_bytes).decode("utf-8")
        response.append(
            ImageContent(
                type="image",
                data=base64_data,
                mimeType="image/png",
            )
        )
    except Exception as e:
        logger.warning(f"Failed to auto-export PNG preview: {e}")

    return response
```

### Step 2: Update `datawrapper_mcp/handlers/update.py`

Same pattern — change the return type and append a PNG export after `chart.update()`.

Replace the entire file with:

```python
"""Handler for updating Datawrapper charts."""

import base64
import json
import logging
from typing import Union

from mcp.types import ImageContent, TextContent
from datawrapper import get_chart

from ..types import UpdateChartArgs
from ..utils import json_to_dataframe

logger = logging.getLogger(__name__)


async def update_chart(
    arguments: UpdateChartArgs,
) -> list[Union[TextContent, ImageContent]]:
    """Update an existing chart's data or configuration."""
    chart_id = arguments["chart_id"]

    # Get chart using factory function - returns correct Pydantic class instance
    chart = get_chart(chart_id)

    # Update data if provided
    if "data" in arguments:
        df = json_to_dataframe(arguments["data"])
        chart.data = df

    # Update config if provided
    if "chart_config" in arguments:
        # Directly set attributes on the chart instance
        # Pydantic will validate each assignment automatically due to validate_assignment=True
        try:
            # Build a mapping of aliases to field names
            alias_to_field = {}
            for field_name, field_info in chart.model_fields.items():
                # Add the field name itself
                alias_to_field[field_name] = field_name
                # Add any aliases
                if field_info.alias:
                    alias_to_field[field_info.alias] = field_name

            for key, value in arguments["chart_config"].items():
                # Convert alias to field name if needed
                field_name = alias_to_field.get(key, key)
                setattr(chart, field_name, value)

        except Exception as e:
            raise ValueError(
                f"Invalid chart configuration: {str(e)}\n\n"
                f"Use get_chart_schema to see the valid schema for this chart type. "
                f"Only high-level Pydantic fields are accepted."
            )

    # Update using Pydantic instance method
    chart.update()

    result = {
        "chart_id": chart.chart_id,
        "message": "Chart updated successfully!",
        "edit_url": chart.get_editor_url(),
    }

    response: list[Union[TextContent, ImageContent]] = [
        TextContent(type="text", text=json.dumps(result, indent=2))
    ]

    # Auto-export a PNG preview so the updated chart is visible inline
    try:
        png_bytes = chart.export_png(zoom=2)
        base64_data = base64.b64encode(png_bytes).decode("utf-8")
        response.append(
            ImageContent(
                type="image",
                data=base64_data,
                mimeType="image/png",
            )
        )
    except Exception as e:
        logger.warning(f"Failed to auto-export PNG preview: {e}")

    return response
```

### Step 3: Update `datawrapper_mcp/server.py`

The tool wrappers for `create_chart` and `update_chart` previously returned `-> str` and extracted only the first text element from the handler response:

```python
result = await create_chart_handler(arguments)
return result[0].text  # discards any ImageContent
```

This must change so the wrappers pass through the full handler response, including both `TextContent` and `ImageContent`.

#### 3a. Change the `create_chart` wrapper

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

#### 3b. Change the `update_chart` wrapper

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

## Open question

The MCP image content may still render inside a collapsible dropdown in the Claude chat UI rather than directly inline. This is a client-side rendering decision in claude.ai, not something the MCP server controls. If the dropdown behavior persists after this change, it would need to be addressed on the client side separately.
