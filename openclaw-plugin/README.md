# Datawrapper

[Datawrapper](https://www.datawrapper.de/) is a tool for creating charts,
maps and tables that look good on any website, used by newsrooms around the world.

This plugin lets your AI assistant build, update and publish Datawrapper charts for you, right from a chat.

## What you need

- A Datawrapper account
- An API token from **Settings > API Tokens** in your Datawrapper account
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed,
  with `uvx` on `PATH`, before you install this plugin — if it's missing,
  the server currently fails with a generic "Connection closed" error
  instead of a clear one

## Configuration

After installing the plugin in the Control UI:

1. Go to **Settings > Secrets** and add a new entry named
   `DATAWRAPPER_ACCESS_TOKEN` with your API token as the value
2. Restart the gateway when prompted
3. Run `openclaw doctor --fix` to confirm the server actually started —
   see the known issue below before assuming "enabled" means it's running

## Known issue: may not load on restart

This plugin only declares a static `mcpServers` entry, which can get
silently excluded from OpenClaw's gateway startup plan
([openclaw/openclaw#117243](https://github.com/openclaw/openclaw/issues/117243)).
If `openclaw doctor --fix` shows the server isn't running, use the manual
`mcp.servers` configuration in
[INSTALLATION.md](https://github.com/palewire/datawrapper-mcp/blob/main/INSTALLATION.md#openclaw)
instead, which bypasses the plugin loader and isn't affected.
