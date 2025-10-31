# datawrapper-mcp

A Model Context Protocol (MCP) server for creating Datawrapper charts using AI assistants. This server provides tools that allow AI assistants like Claude to create, manage, and publish data visualizations through the Datawrapper API.

## Features

- **Three-tier tool architecture** for flexible chart creation:
  - **Simple tool** (`create_chart`): Quick chart creation with minimal configuration
  - **Advanced tool** (`create_chart_advanced`): Full control using Pydantic models
  - **Schema discovery** (`get_chart_schema`): Explore available chart options
- **Pydantic-powered validation**: Leverages datawrapper library's Pydantic models for type safety
- **Chart management**: Create, update, publish, retrieve, and delete charts
- **Flexible data input**: Supports JSON strings, lists of dicts, or dicts of arrays
- **MCP resources**: Access chart type schemas as resources

## Supported Chart Types

- Bar charts (`bar`)
- Line charts (`line`)
- Area charts (`area`)
- Arrow charts (`arrow`)
- Column charts (`column`)
- Multiple column charts (`multiple_column`)
- Scatter plots (`scatter`)
- Stacked bar charts (`stacked_bar`)

## Installation

```bash
pip install datawrapper-mcp
```

Or install from source:

```bash
git clone https://github.com/palewire/datawrapper-mcp.git
cd datawrapper-mcp
pip install -e .
```

## Configuration

### 1. Get a Datawrapper API Token

1. Go to https://app.datawrapper.de/account/api-tokens
2. Create a new API token
3. Set it as an environment variable:

```bash
export DATAWRAPPER_API_TOKEN="your-token-here"
```

### 2. Configure MCP Client

Add the server to your MCP client configuration. For Claude Desktop, edit your config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "datawrapper": {
      "command": "datawrapper-mcp",
      "env": {
        "DATAWRAPPER_API_TOKEN": "your-token-here"
      }
    }
  }
}
```

Or use `uvx` to run without installation:

```json
{
  "mcpServers": {
    "datawrapper": {
      "command": "uvx",
      "args": ["datawrapper-mcp"],
      "env": {
        "DATAWRAPPER_API_TOKEN": "your-token-here"
      }
    }
  }
}
```

## Usage

Once configured, you can ask your AI assistant to create charts. Here are some examples:

### Simple Chart Creation

```
Create a line chart showing temperature trends:
- 2020: 15°C
- 2021: 16°C
- 2022: 17°C
- 2023: 18°C
Title: "Global Temperature Rise"
```

The AI will use the `create_chart` tool with minimal configuration.

### Advanced Chart Creation

```
Create a bar chart with custom colors and axis labels showing sales data.
Use blue bars and add a subtitle explaining the data source.
```

The AI can use `get_chart_schema` to explore options, then use `create_chart_advanced` with full Pydantic model configuration.

### Chart Management

```
Update chart abc123 with new data for 2024: 19°C
```

```
Publish chart abc123 and give me the public URL
```

```
Delete chart abc123
```

## Available Tools

### create_chart

Create a chart with minimal configuration. Requires:
- `data`: Chart data (JSON string, list of dicts, or dict of arrays)
- `chart_type`: Type of chart (bar, line, area, etc.)
- `title`: Chart title
- `description`: Optional subtitle/description

### create_chart_advanced

Create a chart with full control using Pydantic models. Requires:
- `data`: Chart data
- `chart_type`: Type of chart
- `chart_config`: Complete Pydantic model dict with all chart properties

### get_chart_schema

Get the Pydantic JSON schema for a chart type. Shows all available properties, types, and descriptions.

### publish_chart

Publish a chart to make it publicly accessible. Returns the public URL.

### get_chart

Get information about an existing chart, including metadata and URLs.

### update_chart

Update a chart's data or configuration. Can update data, metadata, or both.

### delete_chart

Permanently delete a chart.

## Data Format Examples

### List of Records (Recommended)

```json
[
  {"year": 2020, "value": 100},
  {"year": 2021, "value": 150},
  {"year": 2022, "value": 200}
]
```

### Dict of Arrays

```json
{
  "year": [2020, 2021, 2022],
  "value": [100, 150, 200]
}
```

### JSON String

```json
"[{\"year\": 2020, \"value\": 100}, {\"year\": 2021, \"value\": 150}]"
```

## Architecture

The server leverages the Pydantic models from the `datawrapper` library:

1. **Automatic validation**: Chart configurations are validated using Pydantic's `model_validate()`
2. **Schema generation**: JSON schemas are generated using `model_json_schema()`
3. **Type safety**: All chart properties are type-checked and validated
4. **Helpful errors**: Pydantic provides clear error messages for invalid configurations

This design allows AI assistants to:
- Discover available chart options dynamically
- Construct valid chart configurations
- Receive helpful validation errors
- Have full control over chart appearance

## Development

```bash
# Clone the repository
git clone https://github.com/palewire/datawrapper-mcp.git
cd datawrapper-mcp

# Install in development mode
pip install -e ".[dev,test]"

# Run tests
pytest

# Run pre-commit hooks
pre-commit install
pre-commit run --all-files
```

## Resources

- [Datawrapper API Documentation](https://developer.datawrapper.de/docs)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [datawrapper Python Library](https://github.com/chekos/datawrapper)

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please see CONTRIBUTING.md for guidelines.
