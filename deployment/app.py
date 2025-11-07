"""HTTP server entry point for Kubernetes deployment.

This module provides the HTTP transport wrapper for the Datawrapper MCP server,
enabling deployment to Kubernetes with health check support.
"""

import os

from starlette.requests import Request
from starlette.responses import JSONResponse

from datawrapper_mcp.server import mcp


# Add health check endpoint for Kubernetes
@mcp.custom_route("/healthz", methods=["GET"])
async def health_check(request: Request):
    """Health check endpoint for Kubernetes liveness/readiness probes."""
    return JSONResponse({"status": "healthy", "service": "datawrapper-mcp"})


if __name__ == "__main__":
    # Get configuration from environment variables
    host = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_SERVER_PORT", "8501"))
    server_name = os.getenv("MCP_SERVER_NAME", "datawrapper-mcp")

    # Configure server settings
    mcp.settings.host = host
    mcp.settings.port = port

    print(f"Starting {server_name} on {host}:{port}")
    print(f"Health check available at http://{host}:{port}/healthz")

    # Run with streamable-http transport for Kubernetes deployment
    mcp.run(transport="streamable-http")
