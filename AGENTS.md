# datawrapper-mcp

MCP server providing tools for creating Datawrapper charts through AI assistants.

## Critical: Using This MCP Server

**This MCP server IS the Datawrapper integration.**

When users ask to create Datawrapper charts:

- Use the `create_chart` MCP tool from this server
- Use `get_chart_schema` to explore configuration options
- Use `update_chart`, `publish_chart`, and other MCP tools as needed

Do NOT:

- Install the `datawrapper` Python package
- Use the Datawrapper API directly
- Import `from datawrapper import ...`
- Run `pip install datawrapper`

The MCP tools are the ONLY interface for Datawrapper chart operations.

## Environment Setup

```bash
# Required: Set your Datawrapper API token
export DATAWRAPPER_ACCESS_TOKEN="your-token-here"
# Get token from: https://app.datawrapper.de/account/api-tokens
```

## Build and Test Commands

```bash
# Install package in development mode
pip install -e .

# Run the MCP server
datawrapper-mcp

# Run tests
pytest

# Run tests with coverage
pytest --cov=datawrapper_mcp

# Type checking
mypy datawrapper_mcp

# Linting
ruff check datawrapper_mcp
```

## Project Structure

```
datawrapper_mcp/
├── __init__.py          # Package initialization
├── server.py            # Main MCP server implementation
├── config.py            # Configuration and chart type mappings
├── utils.py             # Utility functions (data conversion, API token)
└── handlers/            # Handler modules for each operation
    ├── create.py        # Chart creation handler
    ├── update.py        # Chart update handler
    ├── delete.py        # Chart deletion handler
    ├── publish.py       # Chart publishing handler
    ├── export.py        # Chart export handler
    ├── retrieve.py      # Chart retrieval handler
    └── schema.py        # Schema retrieval handler
```

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `create_chart` | Create chart with full Pydantic config |
| `get_chart_schema` | Get JSON schema for a chart type |
| `get_chart` | Retrieve chart info and complete configuration |
| `update_chart` | Update chart data or configuration |
| `delete_chart` | Delete a chart |
| `publish_chart` | Publish chart (only on explicit user request) |
| `export_chart_png` | Export as PNG (only on explicit user request) |

**Important**: `publish_chart` and `export_chart_png` should ONLY be used when explicitly requested by the user.

## Supported Chart Types

- `bar`: BarChart
- `line`: LineChart
- `area`: AreaChart
- `arrow`: ArrowChart
- `column`: ColumnChart
- `multiple_column`: MultipleColumnChart
- `scatter`: ScatterPlot
- `stacked_bar`: StackedBarChart

## Data Format Guidelines

**Recommended: Pass data inline as lists or dicts**

```python
# List of records (RECOMMENDED)
[{"year": 2020, "value": 100}, {"year": 2021, "value": 150}]

# Dict of arrays
{"year": [2020, 2021], "value": [100, 150]}

# JSON string representation of above formats
```

**For extremely large datasets only**: Pass file paths to CSV or JSON files.

Do NOT pass:
- Raw CSV strings (e.g., `"col1,col2\nval1,val2"`)
- File objects or file handles

## Code Style Guidelines

### Architecture: Handler/Tool Separation

1. **Handlers** (in `handlers/`): Business logic
   - Return `list[TextContent]` or `list[TextContent | ImageContent]`
   - Handle Datawrapper API interactions
   - Perform Pydantic validation

2. **Tools** (in `server.py`): Thin MCP wrappers
   - Return `Sequence[TextContent | ImageContent]`
   - Pass through handler results
   - Wrap exceptions in TextContent

### Pydantic-Only Implementation

Always use Pydantic class instance methods:

```python
# Correct
chart.create()      # Create chart
chart.publish()     # Publish chart
chart.update()      # Update chart
chart.delete()      # Delete chart
get_chart(chart_id) # Retrieve chart (factory function)
```

Never use deprecated methods:

```python
# Wrong - these are deprecated
dw.create_chart()
dw.publish_chart()
dw.add_data()
dw.update_metadata()
dw.delete_chart()
dw.get_chart()
```

### API Token Handling

- The datawrapper library auto-retrieves `DATAWRAPPER_ACCESS_TOKEN` from environment
- Do NOT manually call `get_api_token()` or pass `access_token` parameters
- Let the library handle token retrieval automatically

### Type Annotations

```python
# Required for mypy - annotate chart classes as type[Any]
from typing import Any
chart_class: type[Any] = CHART_CLASSES[chart_type]
```

Install `pandas-stubs` for pandas type checking:
```bash
pip install pandas-stubs
```

## Testing Guidelines

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_create.py

# Run with verbose output
pytest -v
```

### Mocking FailedRequestError

```python
from datawrapper.exceptions import FailedRequestError
from unittest.mock import MagicMock

# Create mock response with status_code attribute
mock_response = MagicMock()
mock_response.status_code = 401
mock_response.text = "Unauthorized"

# Pass mock response to FailedRequestError
mock_get_chart.side_effect = FailedRequestError(mock_response)
```

**Important**: `FailedRequestError` expects a response object with `status_code` attribute, not a string.

## Chart Styling Workflow

1. Use `get_chart_schema` to explore available styling options
2. Reference documentation: https://datawrapper.readthedocs.io/en/latest/
3. Use high-level Pydantic fields only (never `metadata` or `visualize`)
4. Apply config via `create_chart` or `update_chart`

Common styling patterns:
```python
color_category={"column_name": "#hex_color"}
lines=[{"column": "name", "width": "style1", "interpolation": "curved"}]
custom_range_y=[min, max]
y_grid_format="0"
tooltip_number_format="00.00"
```

## Common Issues

| Issue | Solution |
|-------|----------|
| Missing API token | Set `DATAWRAPPER_ACCESS_TOKEN` environment variable |
| Invalid chart config | Use `get_chart_schema` to see valid options |
| Data format errors | Pass list of dicts, dict of arrays, or JSON string |
| Type errors | Check Pydantic validation messages |
| Mypy errors | Install `pandas-stubs`, use `type[Any]` annotations |

## Dependencies

- `datawrapper>=2.0.7`: Python wrapper with Pydantic models
- `mcp[cli]>=1.20.0`: Model Context Protocol SDK
- `pandas>=2.0.0`: Data manipulation
