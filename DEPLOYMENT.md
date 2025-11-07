# Kubernetes Deployment Guide

This guide explains how to deploy the datawrapper-mcp server to Kubernetes using the FastMCP framework with HTTP transport.

## Architecture Overview

The datawrapper-mcp server has been refactored to support two deployment modes:

1. **stdio transport** (default): For local MCP client usage (Claude Desktop, etc.)
2. **streamable-http transport**: For Kubernetes deployment with health checks

Both modes use the same FastMCP server implementation, ensuring consistent behavior across deployments.

## Project Structure

```
datawrapper-mcp/
├── datawrapper_mcp/          # Main package (stdio transport)
│   ├── __init__.py
│   ├── __main__.py           # Entry point for `python -m datawrapper_mcp`
│   ├── server.py             # FastMCP server with tools and resources
│   ├── config.py
│   ├── tools.py
│   ├── utils.py
│   └── handlers/             # Tool implementation handlers
├── deployment/               # Kubernetes deployment files
│   ├── __init__.py
│   ├── __main__.py           # Entry point for `python -m deployment`
│   ├── app.py                # HTTP server with health check
│   └── requirements.txt      # Production dependencies
├── Dockerfile                # Container image definition
└── README.md                 # User documentation
```

## Key Implementation Details

### FastMCP Server (datawrapper_mcp/server.py)

The server uses FastMCP decorators for clean, declarative tool and resource definitions:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("datawrapper-mcp")


@mcp.tool()
async def create_chart(
    data: str | list | dict, chart_type: str, chart_config: dict
) -> str:
    """Create a Datawrapper chart."""
    # Implementation...


@mcp.resource("datawrapper://chart-types")
async def chart_types_resource() -> str:
    """Get schemas for all chart types."""
    # Implementation...


def main():
    """Run with stdio transport (backwards compatible)."""
    mcp.run(transport="stdio")
```

### HTTP Server (deployment/app.py)

The HTTP server adds a health check endpoint and configures the server for Kubernetes:

```python
from starlette.requests import Request
from starlette.responses import JSONResponse
from datawrapper_mcp.server import mcp


@mcp.custom_route("/healthz", methods=["GET"])
async def health_check(request: Request):
    """Health check endpoint for Kubernetes probes."""
    return JSONResponse({"status": "healthy", "service": "datawrapper-mcp"})


if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_SERVER_PORT", "8501"))

    mcp.settings.host = host
    mcp.settings.port = port

    mcp.run(transport="streamable-http")
```

## Building and Testing

### Local Testing

1. **Test stdio transport** (backwards compatibility):
   ```bash
   python -m datawrapper_mcp
   ```

2. **Test HTTP transport**:
   ```bash
   export DATAWRAPPER_ACCESS_TOKEN=your-token-here
   python -m deployment.app
   ```

3. **Test health check**:
   ```bash
   curl http://localhost:8501/healthz
   ```

### Docker Build

```bash
docker build -t datawrapper-mcp:latest .
```

### Docker Run

```bash
docker run -p 8501:8501 \
  -e DATAWRAPPER_ACCESS_TOKEN=your-token-here \
  -e MCP_SERVER_HOST=0.0.0.0 \
  -e MCP_SERVER_PORT=8501 \
  datawrapper-mcp:latest
```

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATAWRAPPER_ACCESS_TOKEN` | Datawrapper API token | - | Yes |
| `MCP_SERVER_HOST` | Server bind address | `0.0.0.0` | No |
| `MCP_SERVER_PORT` | Server port | `8501` | No |
| `MCP_SERVER_NAME` | Server name | `datawrapper-mcp` | No |

## Kubernetes Deployment

### Prerequisites

1. Docker image built and pushed to registry
2. Kubernetes cluster access
3. Datawrapper API token stored as secret

### Create Secret

```bash
kubectl create secret generic datawrapper-secrets \
  --from-literal=access-token=your-token-here
```

### Deploy to Kubernetes

Apply the configuration from README.md or create your own deployment YAML.

### Verify Deployment

```bash
# Check pod status
kubectl get pods -l app=datawrapper-mcp

# Check logs
kubectl logs -l app=datawrapper-mcp

# Test health check
kubectl port-forward svc/datawrapper-mcp 8501:8501
curl http://localhost:8501/healthz
```

## Backwards Compatibility

The refactoring maintains full backwards compatibility:

- ✅ Same entry point: `datawrapper-mcp` command
- ✅ Same tools: All 7 tools preserved
- ✅ Same resource: `datawrapper://chart-types`
- ✅ Same protocol: MCP stdio transport
- ✅ Same configuration: Environment variables

Existing users can continue using the server with their current MCP client configurations without any changes.

## Troubleshooting

### Server Won't Start

1. Check API token is set: `echo $DATAWRAPPER_ACCESS_TOKEN`
2. Check port availability: `lsof -i :8501`
3. Check logs for errors

### Health Check Fails

1. Verify server is running: `curl http://localhost:8501/healthz`
2. Check firewall rules
3. Verify Kubernetes service configuration

### Tools Not Working

1. Verify API token is valid
2. Check Datawrapper API status
3. Review server logs for errors

## Migration from Previous Version

If you're upgrading from a previous version:

1. No changes needed for stdio transport users
2. For HTTP deployment, use the new `deployment/` directory structure
3. Update any custom deployment scripts to use FastMCP configuration

## Additional Resources

- [FastMCP Documentation](https://github.com/modelcontextprotocol/python-sdk)
- [Datawrapper API Documentation](https://developer.datawrapper.de/)
- [MCP Protocol Specification](https://spec.modelcontextprotocol.io/)
