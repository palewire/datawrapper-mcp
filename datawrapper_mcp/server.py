"""Main MCP server implementation for Datawrapper chart creation."""

import json
from typing import Any, Sequence

from mcp.server import Server
from mcp.types import ImageContent, Resource, TextContent
from pydantic import AnyUrl

from .config import CHART_CLASSES
from .handlers import (
    create_chart,
    delete_chart,
    export_chart_png,
    get_chart_info,
    get_chart_schema,
    publish_chart,
    update_chart,
)
from .tools import list_tools as get_tool_list

# Initialize the MCP server
app = Server("datawrapper-mcp")


@app.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources."""
    return [
        Resource(
            uri=AnyUrl("datawrapper://chart-types"),
            name="Available Chart Types",
            mimeType="application/json",
            description="List of available Datawrapper chart types and their Pydantic schemas",
        )
    ]


@app.read_resource()
async def read_resource(uri: AnyUrl) -> str:
    """Read a resource by URI."""
    if str(uri) == "datawrapper://chart-types":
        chart_info = {}
        for name, chart_class in CHART_CLASSES.items():
            chart_info[name] = {
                "class_name": chart_class.__name__,
                "schema": chart_class.model_json_schema(),
            }
        return json.dumps(chart_info, indent=2)

    raise ValueError(f"Unknown resource URI: {uri}")


@app.list_tools()
async def list_tools():
    """List available tools."""
    return await get_tool_list()


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent]:
    """Handle tool calls."""
    try:
        if name == "create_chart":
            return await create_chart(arguments)
        elif name == "get_chart_schema":
            return await get_chart_schema(arguments)
        elif name == "publish_chart":
            return await publish_chart(arguments)
        elif name == "get_chart":
            return await get_chart_info(arguments)
        elif name == "update_chart":
            return await update_chart(arguments)
        elif name == "delete_chart":
            return await delete_chart(arguments)
        elif name == "export_chart_png":
            return await export_chart_png(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


def main():
    """Run the MCP server."""
    import asyncio
    from mcp.server.stdio import stdio_server

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options(),
            )

    asyncio.run(run())


if __name__ == "__main__":
    main()
