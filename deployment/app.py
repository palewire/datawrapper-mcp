"""HTTP server entry point for Kubernetes deployment."""

import os

from starlette.requests import Request
from starlette.responses import JSONResponse

from datawrapper_mcp.server import mcp


@mcp.custom_route("/healthz", methods=["GET"])
async def health_check(request: Request):
    """Health check endpoint for Kubernetes liveness/readiness probes."""
    return JSONResponse({"status": "healthy", "service": "datawrapper-mcp"})


@mcp.custom_route("/.well-known/mcp.json", methods=["GET"])
async def well_known_mcp(request: Request):
    """MCP server discovery endpoint (SEP-1960)."""
    return JSONResponse(
        {
            "mcp": {
                "versions": ["2025-11-25"],
                "endpoint": "/mcp",
                "name": "datawrapper-mcp",
                "description": "Create Datawrapper charts via MCP",
                "capabilities": {
                    "tools": True,
                    "resources": True,
                    "apps": True,
                },
            }
        }
    )


if __name__ == "__main__":
    # Get configuration from environment variables
    host = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_SERVER_PORT", "8501"))

    # Log server start information
    print(f"Starting datawrapper-mcp on {host}:{port}")
    print(f"Health check available at http://{host}:{port}/healthz")

    # Run with streamable-http transport
    mcp.run(transport="streamable-http", host=host, port=port)
