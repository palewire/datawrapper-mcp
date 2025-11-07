"""HTTP server entry point for Kubernetes deployment."""

import os

from starlette.requests import Request
from starlette.responses import JSONResponse

from datawrapper_mcp.server import mcp


@mcp.custom_route("/healthz", methods=["GET"])
async def health_check(request: Request):
    """Health check endpoint for Kubernetes liveness/readiness probes."""
    return JSONResponse({"status": "healthy", "service": "datawrapper-mcp"})


if __name__ == "__main__":
    # Get configuration from environment variables
    host = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_SERVER_PORT", "8501"))

    # Configure server settings
    mcp.settings.host = host
    mcp.settings.port = port

    # Log server start information
    print(f"Starting datawrapper-mcp on {host}:{port}")
    print(f"Health check available at http://{host}:{port}/healthz")

    # Run with streamable-http transport
    mcp.run(transport="streamable-http")
