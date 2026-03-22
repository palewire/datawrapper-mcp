# Deploying datawrapper-mcp on Fly.io for a Conference Demo

## Overview

Host a single shared instance of the Datawrapper MCP server on Fly.io so conference attendees can connect with just a URL — no local installs, no Python, no tokens to manage.

**End result:** Attendees add a 4-line JSON block to their MCP client config and start creating charts immediately.

---

## Prerequisites

- A [Fly.io account](https://fly.io) with the `flyctl` CLI installed
- A [Datawrapper API token](https://app.datawrapper.de/account/api-tokens) (free tier is fine)
- Docker installed locally (the project already has a working Dockerfile)

---

## Step 1: Prepare the Fly App

From the project root, run:

```bash
fly launch --no-deploy
```

When prompted:

- Pick a region close to your conference venue (e.g., `iad` for US East, `lhr` for London)
- Say **no** to provisioning a Postgres database
- Say **no** to provisioning a Redis database

This creates a `fly.toml` file. Edit it to expose the right port:

```toml
[http_service]
  internal_port = 8501
  force_https = true
  auto_stop_machines = "off"        # keep running to preserve MCP sessions
  auto_start_machines = true
  min_machines_running = 1

[checks.health]
  port = 8501
  type = "http"
  path = "/healthz"
  interval = "10s"
  timeout = "2s"
  grace_period = "15s"

[[vm]]
  size = "shared-cpu-1x"
  memory = "512mb"
```

Setting `min_machines_running = 1` prevents cold-start delays during your talk.

## Step 2: Set the Datawrapper Token

Store the API token as a Fly secret (never in the Dockerfile or fly.toml):

```bash
fly secrets set DATAWRAPPER_ACCESS_TOKEN="your-token-here"
```

The `datawrapper` library picks this up automatically from the environment.

## Step 3: Deploy

```bash
fly deploy
```

Fly will build the Docker image remotely using the existing `Dockerfile`, which:

- Installs dependencies from `deployment/requirements.txt`
- Runs `python -m deployment.app` (streamable-http transport on port 8501)

Once deployed, note your app URL — it will be something like:

```
https://your-app-name.fly.dev
```

## Step 4: Verify

Test the health endpoint:

```bash
curl https://your-app-name.fly.dev/healthz
```

Test the MCP endpoint with a quick stdio-over-http probe:

```bash
curl -X POST https://your-app-name.fly.dev/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

You should get back a JSON response listing the available tools.

---

## What to Share with Attendees

### Quick-Start Config

Attendees add this to their MCP client configuration:

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "datawrapper": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://your-app-name.fly.dev/mcp"]
    }
  }
}
```

**Claude Code:**

```bash
claude mcp add datawrapper --transport http https://your-app-name.fly.dev/mcp
```

### Sample Prompts to Try

Give attendees a few copy-paste prompts to get started:

1. "Create a bar chart comparing the GDP of the G7 countries"
2. "Make a line chart showing global temperature anomalies from 1950 to 2020"
3. "Create a column chart of the top 10 programming languages by popularity"

---

## Day-of Checklist

- [ ] Verify the server is running: `fly status`
- [ ] Test chart creation yourself end-to-end
- [ ] Have the attendee config snippet ready to display / share via QR code
- [ ] Open the Datawrapper dashboard so you can show charts appearing in real time
- [ ] Know how to scale up if needed: `fly scale count 2`

## After the Conference

### Clean Up Charts

All attendees' charts land in your Datawrapper account. Bulk-delete from the dashboard, or use the API:

```bash
# List recent charts
curl -H "Authorization: Bearer $DATAWRAPPER_ACCESS_TOKEN" \
  https://api.datawrapper.de/v3/charts?limit=100

# Delete by ID
curl -X DELETE -H "Authorization: Bearer $DATAWRAPPER_ACCESS_TOKEN" \
  https://api.datawrapper.de/v3/charts/CHART_ID
```

### Tear Down the Server

```bash
fly apps destroy your-app-name
```

---

## Cost Estimate

Fly.io's free tier includes 3 shared-CPU VMs. The server needs at least 512 MB RAM (256 MB causes OOM kills). A single `shared-cpu-1x` with 512 MB fits within the free allowance, so the cost is **$0**. If you scale up for a large audience, expect roughly $2–5/mo prorated for the few hours you need it.

---

## Troubleshooting

| Issue                        | Fix                                                                                                              |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Cold start delays            | Set `min_machines_running = 1` in `fly.toml`                                                                     |
| 502 errors on first request  | The app may need 5–10s to boot; retry or add a health check grace period                                         |
| Token not working            | Verify with `fly secrets list` — the name must be exactly `DATAWRAPPER_ACCESS_TOKEN`                             |
| Attendees can't connect      | Confirm `force_https = true` and they're using `https://` in the URL                                             |
| Rate limits from Datawrapper | Free accounts have API limits; upgrade to a paid plan if you expect 50+ attendees creating charts simultaneously |
