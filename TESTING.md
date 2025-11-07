# Testing Guide

This guide covers how to test the datawrapper-mcp server in different deployment modes.

## Table of Contents

- [Local Testing (stdio)](#local-testing-stdio)
- [Local Testing (HTTP)](#local-testing-http)
- [Docker Testing](#docker-testing)
- [Testing HTTP Transport](#testing-http-transport-with-claude-desktop)
- [Integration Testing](#integration-testing)

## Local Testing (stdio)

Test the server with stdio transport (the default mode for MCP clients like Claude Desktop):

```bash
# Install in development mode
pip install -e .

# Set your API token
export DATAWRAPPER_ACCESS_TOKEN=your-token-here

# Run the server
python -m datawrapper_mcp
```

The server will start and wait for MCP protocol messages on stdin. You can test it by configuring your MCP client (Claude Desktop, etc.) to use this command.

## Local Testing (HTTP)

Test the server with HTTP transport (for Kubernetes deployments):

```bash
# Set your API token
export DATAWRAPPER_ACCESS_TOKEN=your-token-here

# Optional: Configure host and port
export MCP_SERVER_HOST=0.0.0.0
export MCP_SERVER_PORT=8501

# Run the HTTP server
python -m deployment.app
```

The server will start on http://0.0.0.0:8501. You can verify it's running:

```bash
# Test health check endpoint
curl http://localhost:8501/healthz

# Expected response:
# {"status": "healthy", "service": "datawrapper-mcp"}
```

## Docker Testing

### Build the Image

```bash
docker build -t datawrapper-mcp:latest .
```

### Run the Container

```bash
docker run -p 8501:8501 \
  -e DATAWRAPPER_ACCESS_TOKEN=your-token-here \
  -e MCP_SERVER_HOST=0.0.0.0 \
  -e MCP_SERVER_PORT=8501 \
  datawrapper-mcp:latest
```

### Verify the Container

```bash
# Check health endpoint
curl http://localhost:8501/healthz

# Check container logs
docker ps  # Get container ID
docker logs <container-id>
```

## Testing HTTP Transport with Claude Desktop

The HTTP transport is primarily designed for Kubernetes deployments. For local testing, the stdio transport (default) is recommended as it integrates directly with Claude Desktop and other MCP clients.

**Note:** MCP Inspector does not currently support the streamable-http transport used by this server. HTTP transport testing requires custom client code or integration testing via the automated test suite.

## Integration Testing

### Manual Integration Test

Run through this complete workflow to verify stdio transport functionality:

```bash
# 1. Install in development mode
pip install -e .

# 2. Set your API token
export DATAWRAPPER_ACCESS_TOKEN=your-token-here

# 3. Configure Claude Desktop to use the server
# Add to your Claude Desktop MCP settings:
# {
#   "mcpServers": {
#     "datawrapper": {
#       "command": "python",
#       "args": ["-m", "datawrapper_mcp"],
#       "env": {
#         "DATAWRAPPER_ACCESS_TOKEN": "your-token-here"
#       }
#     }
#   }
# }

# 4. Test in Claude Desktop:
#    - Ask Claude to get the schema for a line chart
#    - Ask Claude to create a chart with sample data
#    - Ask Claude to update the chart
#    - Ask Claude to get chart details
#    - Ask Claude to delete the chart

# 5. Verify all operations succeeded
```

### Automated Integration Tests

The repository includes pytest-based integration tests:

```bash
# Install test dependencies
pip install -e ".[test]"

# Run all tests
pytest

# Run specific test files
pytest tests/test_schema.py
pytest tests/test_update.py

# Run with coverage
pytest --cov=datawrapper_mcp
```
