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

## Claude (Claude.ai, Desktop, and mobile via a remote connector)

Adding this as a **remote connector** (rather than the local `claude_desktop_config.json`
method above) works identically across Claude.ai, Claude Desktop, and Claude
mobile — they share the same connector infrastructure and account settings. It
requires a running streamable-http deployment (see
[Kubernetes Deployment](#kubernetes-deployment) below, or run `deployment/app.py`
behind any HTTPS-capable host).

**Personal connector, your own Datawrapper account (works today, no admin needed)**

This is the option to reach for when you want each person to create charts
under *their own* Datawrapper account rather than one shared credential, and
you're not relying on an organization admin to provision a single connector for
everyone. Each person does this once, for their own account:

1. Go to **Customize > Connectors** (this is a personal setting, separate from
   anything an organization admin may have already added for you)
2. Click **Add custom connector**
3. Enter a name and your server's `/mcp` URL, e.g. `https://your-domain.example/mcp`
4. Continue to the authentication step and choose **No sign-in**
5. Under **Request headers**, add a header named `Authorization` with the value
   `Bearer <your-datawrapper-api-token>` (get a token from
   [app.datawrapper.de/account/api-tokens](https://app.datawrapper.de/account/api-tokens)) —
   include the word `Bearer` and the space; Claude sends the value exactly as entered
6. Mark the header **Required**, then click **Add**
7. In a chat, click **+** > **Connectors**, and enable it

Claude stores the header value securely and never displays it again. Note: the
**Request headers** option is currently in beta and may not be visible to every
account yet — if you don't see it, only the shared-credential option below is
available to you for now.

**Shared connector, everyone uses the same credential (admin-provisioned)**

If an organization admin is adding this once for the whole org (Team/Enterprise
**Organization Settings > Connectors**), the same **No sign-in** + **Request
headers** flow above works there too — but the credential is shared by
everyone who uses that connector, not per-person. Claude has no way to attach
a different header value per user to a single connector, so if you need
per-person Datawrapper accounts on an admin-provisioned, org-wide connector
instead, see [Linked-Account Mode](#linked-account-mode-org-wide-connectors)
below, which solves this with an OAuth-based per-user token exchange.

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

## Linked-Account Mode (org-wide connectors)

If you're registering this server as a **single, admin-provisioned custom
connector** shared by an entire Claude Team/Enterprise org (rather than each
person adding their own connector with their own header), Claude's connector
model has no way to attach a different credential per user to that one
connector — request-header auth (`static_headers`) is explicitly a single
credential shared by everyone who uses it. If everyone should still create
charts under their *own* Datawrapper account rather than one shared one,
turn on linked-account mode instead.

In this mode the server presents Claude with a small OAuth-shaped
authorization flow: the first time a user calls a tool, Claude redirects
them to a page that asks them to paste their own Datawrapper API token, then
exchanges that for an opaque access token Claude uses from then on. The
server resolves that opaque token back to the real Datawrapper token
internally — see `datawrapper_mcp/oauth/__init__.py` for the full design
rationale. Datawrapper itself has no OAuth server or SSO integration, so
this exists purely to satisfy what an OAuth-based MCP client expects; there
is no actual third-party sign-in step, just a form.

### Enabling it

Set these environment variables (in addition to the usual `MCP_SERVER_HOST`/
`MCP_SERVER_PORT`):

```bash
REQUIRE_LINKED_ACCOUNT=true
TOKEN_ENCRYPTION_KEY=<a Fernet key - see below>
OAUTH_STORE_PATH=/data/oauth_store.db   # must be on persistent storage
```

Generate a key for `TOKEN_ENCRYPTION_KEY` once, and keep it secret and
stable across restarts (rotating it invalidates every linked account):

```bash
python -c "from datawrapper_mcp.oauth.storage import generate_encryption_key as g; print(g())"
```

### Persistent storage is required

`OAUTH_STORE_PATH` points to a SQLite file holding every user's linked
Datawrapper token (encrypted at rest with `TOKEN_ENCRYPTION_KEY`). **This
path must be on a persistent volume.** On a container platform with an
ephemeral filesystem (the default on most, including Fly.io machines without
a mounted volume), every linked account is lost on the next restart or
redeploy, and every user has to re-link.

### Known limitations (v1)

- No refresh-token grant: issued access tokens are long-lived (1 year)
  rather than short-lived-and-refreshed, since a Datawrapper API token
  doesn't expire on its own either. A user who wants to revoke their link
  today needs the operator to delete their row from the store directly;
  there's no self-service revocation UI yet.
- No identity verification beyond "whoever clicks through this specific
  authorization link": the form doesn't verify the person pasting a token is
  who they claim to be beyond the fact that they're the one who initiated
  the Claude connection in the first place. This is adequate as a
  self-service link (the user only ever registers *their own* token, in
  *their own* browser session), but hasn't been hardened against more
  sophisticated identity-spoofing scenarios.
- Storage is a single SQLite file, which is fine for a single-instance
  deployment but doesn't support multiple replicas sharing state.

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
