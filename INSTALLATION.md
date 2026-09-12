# Installation Guide

Detailed setup instructions for each supported MCP client, plus Docker and Kubernetes deployment.

## Claude Desktop

**Using uvx (recommended)**

Open Settings > Developer > Edit Config, which opens (or creates) `claude_desktop_config.json`:

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

**Using pip**

First install the package:

```bash
pip install datawrapper-mcp
```

Then add this to `claude_desktop_config.json`:

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

Restart Claude Desktop after editing the file.

## Claude.ai

Claude.ai only connects to servers reachable over HTTPS, so this requires a running
streamable-http deployment (see [Kubernetes Deployment](#kubernetes-deployment) below,
or run `deployment/app.py` behind any HTTPS-capable host).

1. Go to Settings > Connectors (or, for Team/Enterprise plans, Organization Settings > Connectors)
2. Click **Add custom connector**
3. Enter a name and your server's `/mcp` URL, e.g. `https://your-domain.example/mcp`
4. Click **Add**
5. In a chat, click the **+** button, choose **Connectors**, and enable `datawrapper`

To use your own Datawrapper account rather than the server operator's, see
[Using Your Own Token](README.md#using-your-own-token-hosted-deployments) for the
`Authorization: Bearer` header pattern — Claude.ai's Advanced settings let you set
custom headers when adding the connector.

## Claude Code

**Using uvx (recommended)**

Add this to `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "datawrapper": {
      "type": "stdio",
      "command": "uvx",
      "args": ["datawrapper-mcp"],
      "env": {
        "DATAWRAPPER_ACCESS_TOKEN": "your-token-here"
      }
    }
  }
}
```

**Using pip**

First install the package:

```bash
pip install datawrapper-mcp
```

Then add this to `.mcp.json`:

```json
{
  "mcpServers": {
    "datawrapper": {
      "type": "stdio",
      "command": "datawrapper-mcp",
      "env": {
        "DATAWRAPPER_ACCESS_TOKEN": "your-token-here"
      }
    }
  }
}
```

**Secure secrets**

Claude Code expands `${VAR}` in `.mcp.json`, so you can reference an environment
variable already set in your shell instead of writing the token into a file that
might get committed:

```json
{
  "mcpServers": {
    "datawrapper": {
      "type": "stdio",
      "command": "uvx",
      "args": ["datawrapper-mcp"],
      "env": {
        "DATAWRAPPER_ACCESS_TOKEN": "${DATAWRAPPER_ACCESS_TOKEN}"
      }
    }
  }
}
```

Verify with `claude mcp list` after adding the server; the first use requires
interactive approval.

## VS Code Copilot

Add this to `.vscode/mcp.json` in your workspace (or run **MCP: Open User
Configuration** to add it for every workspace):

```json
{
  "inputs": [
    {
      "type": "promptString",
      "id": "datawrapper-token",
      "description": "Datawrapper API token",
      "password": true
    }
  ],
  "servers": {
    "datawrapper": {
      "type": "stdio",
      "command": "uvx",
      "args": ["datawrapper-mcp"],
      "env": {
        "DATAWRAPPER_ACCESS_TOKEN": "${input:datawrapper-token}"
      }
    }
  }
}
```

The `inputs` block prompts for your token the first time the server starts and
keeps it out of version control instead of hardcoding it in `env`.

## Cursor

Add this to `.cursor/mcp.json`:

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

Cursor doesn't expand environment variables in `mcp.json`, so the token has to be
a literal value here — consider adding `.cursor/mcp.json` to `.gitignore` if the
file will hold a real token.

## ChatGPT

ChatGPT's MCP support (Developer Mode) only speaks HTTP, not stdio, so this
requires a running streamable-http deployment (see
[Kubernetes Deployment](#kubernetes-deployment) below).

1. Go to Settings > Apps & Connectors > Advanced Settings and toggle **Developer mode** on
2. Go to Settings > Connectors, click **Add custom connector**
3. Enter a name, description, and your server's `/mcp` URL, e.g. `https://your-domain.example/mcp`
4. Choose an auth method (OAuth, API key, or none) and click **Save**
5. In a chat, click **+** > **More** > **Developer Mode** and select the connector

## OpenAI Codex

**CLI with uvx**

Add this to `~/.codex/config.toml`:

```toml
[mcp_servers.datawrapper]
args = ["datawrapper-mcp"]
command = "uvx"
startup_timeout_sec = 30

[mcp_servers.datawrapper.env]
DATAWRAPPER_ACCESS_TOKEN = "your-token-here"
```

**CLI with pip**

First install the package:

```bash
pip install datawrapper-mcp
```

Then add this to `~/.codex/config.toml`:

```toml
[mcp_servers.datawrapper]
command = "datawrapper-mcp"
startup_timeout_sec = 30

[mcp_servers.datawrapper.env]
DATAWRAPPER_ACCESS_TOKEN = "your-token-here"
```

**Secure secrets**

For enhanced security, you can configure a pass-through environment variable by ensuring that `DATAWRAPPER_ACCESS_TOKEN` is set in your environment, and replacing this in your `config.toml`:

```toml
[mcp_servers.datawrapper.env]
DATAWRAPPER_ACCESS_TOKEN = "your-token-here"
```

With this:

```toml
env_vars = ["DATAWRAPPER_ACCESS_TOKEN"]
```

This ensures that the value set for `DATAWRAPPER_ACCESS_TOKEN` in your environment is passed through to Codex without having to store the secret as text in a config file.

**Desktop application**

If you're using the [Codex Desktop Application](https://openai.com/codex/), you can set up the MCP in your settings under `MCP servers`:

1. Under Custom servers, click `Add server`
2. Under Name, enter `datawrapper-mcp`
3. Select STDIO
4. Under Command to launch, type `uvx` ([you must have uv installed](https://docs.astral.sh/uv/getting-started/installation/))
5. Under Arguments, add `datawrapper-mcp`
6. Under Environment variables, add `DATAWRAPPER_ACCESS_TOKEN` as the key and your token as the value
7. Click Save

## OpenClaw

Add this to `openclaw.json`:

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

## Kubernetes Deployment

For enterprise deployments, this server can be deployed to Kubernetes using HTTP transport.

### Building the Docker Image

```bash
docker build -t datawrapper-mcp:latest .
```

### Running with Docker

```bash
docker run -p 8501:8501 \
  -e DATAWRAPPER_ACCESS_TOKEN=your-token-here \
  -e MCP_SERVER_HOST=0.0.0.0 \
  -e MCP_SERVER_PORT=8501 \
  datawrapper-mcp:latest
```

### Environment Variables

- `DATAWRAPPER_ACCESS_TOKEN`: Your Datawrapper API token (required)
- `MCP_SERVER_HOST`: Server host (default: `0.0.0.0`)
- `MCP_SERVER_PORT`: Server port (default: `8501`)
- `MCP_SERVER_NAME`: Server name (default: `datawrapper-mcp`)

### Health Check Endpoint

The HTTP server includes a `/healthz` endpoint for Kubernetes liveness and readiness probes:

```bash
curl http://localhost:8501/healthz
# Returns: {"status": "healthy", "service": "datawrapper-mcp"}
```

### Discovery Endpoint

The HTTP server serves a `/.well-known/mcp.json` endpoint for MCP client auto-discovery:

```bash
curl http://localhost:8501/.well-known/mcp.json
```

### Kubernetes Configuration Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: datawrapper-mcp
spec:
  replicas: 1
  selector:
    matchLabels:
      app: datawrapper-mcp
  template:
    metadata:
      labels:
        app: datawrapper-mcp
    spec:
      containers:
        - name: datawrapper-mcp
          image: datawrapper-mcp:latest
          ports:
            - containerPort: 8501
          env:
            - name: DATAWRAPPER_ACCESS_TOKEN
              valueFrom:
                secretKeyRef:
                  name: datawrapper-secrets
                  key: access-token
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8501
            initialDelaySeconds: 5
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /healthz
              port: 8501
            initialDelaySeconds: 5
            periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: datawrapper-mcp
spec:
  selector:
    app: datawrapper-mcp
  ports:
    - protocol: TCP
      port: 8501
      targetPort: 8501
```
