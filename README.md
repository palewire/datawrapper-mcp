A Model Context Protocol (MCP) server that enables AI assistants to create Datawrapper charts. Built on the [datawrapper Python library](https://github.com/chekos/datawrapper) with Pydantic validation.

## Getting Started

### Get Your API Token

1. Go to https://app.datawrapper.de/account/api-tokens
2. Create a new API token
3. Add it to your MCP configuration as shown above

### Installation

#### Using uvx (Recommended)

Configure your MCP client to run the server with `uvx` in `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "datawrapper": {
      "command": "uvx",
      "args": ["datawrapper-mcp"],
      "env": {
        "DATAWRAPPER_ACCESS_TOKEN": "your-token-here"
      }
    }
  }
}
```

#### Using pip

```bash
pip install datawrapper-mcp
```

Then configure your MCP client:

```json
{
  "mcpServers": {
    "datawrapper": {
      "command": "datawrapper-mcp",
      "env": {
        "DATAWRAPPER_ACCESS_TOKEN": "your-token-here"
      }
    }
  }
}
```

## Example Usage

Here's a complete example showing how to create, publish, update, and display a chart by chatting with the assistant:

```
"Create a datawrapper line chart showing temperature trends with this data:
2020, 15.5
2021, 16.0
2022, 16.5
2023, 17.0"
# The assistant creates the chart and returns the chart ID, e.g., "abc123"

"Publish it."
# The assistant publishes it and returns the public URL

"Update chart with new data for 2024: 17.2°C"
# The assistant updates the chart with the new data point

"Make the line color dodger blue."
# The assistant updates the chart configuration to set the line color

"Show me the editor URL."
# The assistant returns the Datawrapper editor URL where you can view/edit the chart

"Show me the PNG."
# The assistant embeds the PNG image of the chart in its contained response.

"Suggest five ways to improve the chart."
# See what happens!
```
