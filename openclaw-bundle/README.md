# datawrapper-mcp for OpenClaw

Wires the [datawrapper-mcp](https://github.com/palewire/datawrapper-mcp) server
into OpenClaw so an agent can create, update and publish
[Datawrapper](https://www.datawrapper.de/) charts.

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed
  (this bundle launches the server with `uvx`, no manual `pip install` needed)
- A Datawrapper API token, from **Settings > API Tokens** in your Datawrapper
  account

## Install

```bash
openclaw plugins install clawhub:datawrapper-mcp
```

Set your token as an environment variable before starting OpenClaw's gateway:

```bash
export DATAWRAPPER_ACCESS_TOKEN=your-token-here
```

Then restart the gateway so the server is picked up:

```bash
openclaw gateway restart
```

## What this bundle does

This is a thin wrapper, not a reimplementation: it ships a single `.mcp.json`
that tells OpenClaw to launch `datawrapper-mcp` (installed on demand via
`uvx`) as a stdio MCP server, and exposes every tool the server
implements — creating, updating, publishing, exporting and deleting charts.
See the [main repository](https://github.com/palewire/datawrapper-mcp) for
the full tool list and how the server itself works.
