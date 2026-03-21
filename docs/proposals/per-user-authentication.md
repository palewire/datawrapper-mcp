# Per-User Authentication for datawrapper-mcp

Proposal for enabling individual users to authenticate with their own Datawrapper API
keys, removing the need for shared tokens or manual configuration file editing.

---

## Problem Statement

**Current state:** The datawrapper-mcp server uses a single `DATAWRAPPER_ACCESS_TOKEN`
environment variable. All charts created through the MCP server are owned by whichever
Datawrapper account that token belongs to.

**Limitations:**
- All users share one Datawrapper account's charts and quotas
- Users cannot see their own chart history in their Datawrapper dashboard
- Revoking access requires regenerating the shared token (affects everyone)
- Users must trust the server operator with their charts
- No way to attribute charts to individual users

**Goal:** Allow each user to bring their own Datawrapper API key, so charts are created
in their own Datawrapper accounts. Users should not need to edit MCP client configuration
files or share keys through insecure channels.

---

## Two-Layer Authentication Model

This problem involves two distinct authentication layers:

### Layer 1: MCP Client → datawrapper-mcp Server

How does Claude/ChatGPT/Cursor authenticate to your MCP server?

- **Current:** No authentication (stdio transport) or static Bearer token (HTTP)
- **Future:** MCP OAuth 2.1 for public deployments

This layer is covered by the MCP spec's OAuth 2.1 implementation. See the
[march-2026-upgrades.md](march-2026-upgrades.md) proposal for details on adding this
when needed.

### Layer 2: datawrapper-mcp Server → Datawrapper API

How does your server authenticate to Datawrapper on behalf of each user?

- **Current:** Single shared `DATAWRAPPER_ACCESS_TOKEN` environment variable
- **Goal:** Per-user Datawrapper API tokens

This document focuses on Layer 2—getting per-user Datawrapper tokens into the server.

---

## Architecture Options

### Option A: Per-Session Token Tool (Simplest)

Add a `set_datawrapper_token` tool that users call at the start of each session.

**How it works:**
1. User obtains their Datawrapper API token from https://app.datawrapper.de/account/api-tokens
2. User calls `set_datawrapper_token(token="dw_...")` in chat
3. Server stores token in session memory (not persisted)
4. All subsequent chart operations use that token
5. Token is discarded when session ends

**Implementation:**

```python
# In server.py
from contextvars import ContextVar

# Session-scoped token storage
_session_token: ContextVar[str | None] = ContextVar("datawrapper_token", default=None)

@mcp.tool()
async def set_datawrapper_token(token: str) -> str:
    """Set your Datawrapper API token for this session.

    Get your token from: https://app.datawrapper.de/account/api-tokens

    The token is stored only for this session and not persisted.
    You'll need to set it again in future sessions.
    """
    _session_token.set(token)
    return "Datawrapper token set for this session."

def get_current_token() -> str:
    """Get the current session's Datawrapper token, falling back to env var."""
    session_token = _session_token.get()
    if session_token:
        return session_token

    import os
    env_token = os.environ.get("DATAWRAPPER_ACCESS_TOKEN")
    if env_token:
        return env_token

    raise ValueError(
        "No Datawrapper token available. Either:\n"
        "1. Call set_datawrapper_token(token='your-token') in this session\n"
        "2. Set DATAWRAPPER_ACCESS_TOKEN environment variable"
    )
```

**Pros:**
- Simple to implement (~50 lines of code)
- No backend infrastructure needed
- No persistent storage of user credentials
- Works with stdio and HTTP transports

**Cons:**
- User must provide token every session
- Token transmitted in plaintext through MCP (fine for local stdio, concerning for remote HTTP)
- No token validation until first API call fails

**Best for:** Internal/team use where users are trusted and sessions are short-lived.

---

### Option B: User Accounts with Stored Keys

Build a user account system where users register once and store their Datawrapper token.

**How it works:**
1. User authenticates to your server via OAuth 2.1 (Layer 1)
2. First time: User enters Datawrapper token via a web UI you provide
3. Server encrypts and stores token associated with user's identity
4. Subsequent sessions: Server retrieves token automatically based on OAuth identity

**Architecture:**

```
┌─────────────────┐      ┌──────────────────────────────┐
│  MCP Client     │      │  datawrapper-mcp server      │
│  (Claude, etc.) │      │                              │
│                 │ OAuth│  ┌────────────────────────┐  │
│                 │ 2.1  │  │ User Identity Provider │  │
│                 │─────►│  └───────────┬────────────┘  │
│                 │      │              │               │
│  "create_chart" │ MCP  │              ▼               │
│  ─────────────► │─────►│  ┌────────────────────────┐  │
│                 │      │  │ Token Store (encrypted)│  │
│                 │      │  │ user123 → dw_abc...    │  │
│                 │      │  │ user456 → dw_xyz...    │  │
│                 │      │  └───────────┬────────────┘  │
│                 │      │              │               │
│                 │      │              ▼               │
│                 │      │  ┌────────────────────────┐  │
│                 │      │  │ Datawrapper API        │  │
│                 │      │  └────────────────────────┘  │
└─────────────────┘      └──────────────────────────────┘
```

**Required components:**
1. OAuth 2.1 provider (or integration with existing IdP like Auth0, Clerk)
2. Encrypted token storage (database + encryption key management)
3. Web UI for users to enter/update/revoke their Datawrapper token
4. Token refresh/validation logic

**Implementation complexity:** High. Requires:
- Database (PostgreSQL, SQLite, etc.)
- Encryption key management (environment variable or secrets manager)
- Web frontend for token management
- Session management for the web UI

**Pros:**
- Best UX: users authenticate once and it "just works"
- Tokens encrypted at rest
- Can add features: token rotation, usage analytics, access revocation

**Cons:**
- Significant infrastructure to build and maintain
- You become custodian of users' Datawrapper credentials
- Security responsibility: must protect stored tokens

**Best for:** Public deployment with many users who expect a polished experience.

---

### Option C: Datawrapper OAuth (Ideal Future State)

If Datawrapper implements OAuth 2.0/2.1, your server could be an OAuth client.

**How it works:**
1. User connects to your MCP server
2. Server redirects user to Datawrapper's OAuth authorization page
3. User approves access in Datawrapper's UI
4. Datawrapper redirects back with an authorization code
5. Server exchanges code for access token
6. Server uses token for API calls (with automatic refresh)

**Pros:**
- Users never handle API tokens directly
- Standard OAuth flow with proper scoping
- Datawrapper handles token issuance and revocation
- Users can revoke access from their Datawrapper account

**Cons:**
- Requires Datawrapper to implement OAuth (they currently don't)
- Still need to store refresh tokens (similar to Option B)

**Status:** Not currently possible. Datawrapper only offers static API tokens.
Monitor their changelog for OAuth support.

---

## Recommended Approach

### Short-term: Option A (Per-Session Token)

For your current experimental deployment:

1. Add `set_datawrapper_token` tool
2. Document that users need to provide their token each session
3. Keep `DATAWRAPPER_ACCESS_TOKEN` as fallback for backward compatibility

**Effort:** ~2-4 hours to implement and test.

### Medium-term: Evaluate Need for Option B

If user feedback indicates:
- Users are frustrated re-entering tokens
- You're scaling beyond a small team
- You need audit logs of who created which charts

Then invest in Option B's infrastructure.

### Long-term: Watch for Option C

Monitor Datawrapper's API roadmap. If they add OAuth:
- Migrate to OAuth flow
- Remove stored token infrastructure
- Improve security posture

---

## Implementation Plan for Option A

### Phase 1: Add Session Token Support

**Files to modify:**
- `datawrapper_mcp/server.py` — add `set_datawrapper_token` tool
- `datawrapper_mcp/utils.py` — add `get_current_token()` helper

**Changes:**

```python
# utils.py additions
from contextvars import ContextVar

_session_token: ContextVar[str | None] = ContextVar("datawrapper_token", default=None)

def set_session_token(token: str) -> None:
    """Set the Datawrapper token for the current session."""
    _session_token.set(token)

def get_current_token() -> str:
    """Get the current session's token, falling back to environment variable."""
    token = _session_token.get()
    if token:
        return token

    import os
    token = os.environ.get("DATAWRAPPER_ACCESS_TOKEN")
    if token:
        return token

    raise ValueError(
        "No Datawrapper API token configured.\n\n"
        "Option 1: Call set_datawrapper_token(token='your-token') to set it for this session\n"
        "Option 2: Set the DATAWRAPPER_ACCESS_TOKEN environment variable\n\n"
        "Get your token from: https://app.datawrapper.de/account/api-tokens"
    )
```

### Phase 2: Update Handlers to Use Session Token

The `datawrapper` Python library auto-reads `DATAWRAPPER_ACCESS_TOKEN` from the
environment. To support per-session tokens, handlers need to pass the token explicitly.

Check if the library's Pydantic models accept an `access_token` parameter:
- If yes: Pass `get_current_token()` when constructing chart instances
- If no: Temporarily set the environment variable before API calls (less elegant)

### Phase 3: Add Token Validation Tool (Optional)

```python
@mcp.tool()
async def validate_datawrapper_token() -> str:
    """Check if the current Datawrapper token is valid.

    Returns account information if valid, or an error message if invalid.
    """
    token = get_current_token()
    # Call Datawrapper's /me endpoint to validate
    ...
```

### Phase 4: Document the Workflow

Update README.md with:
1. How to get a Datawrapper API token
2. How to use `set_datawrapper_token` at session start
3. Security considerations for remote deployments

---

## Security Considerations

### Token Transmission

- **stdio transport:** Token stays local—acceptable security for personal use
- **HTTP transport:** Token transmitted over HTTPS—acceptable, but consider:
  - Tokens appear in server logs if request logging is enabled
  - Tokens may be cached by intermediate proxies (ensure no-cache headers)

### Token Storage (Option B only)

If implementing persistent token storage:
- Encrypt tokens at rest using AES-256-GCM or similar
- Store encryption key in a secrets manager (not in code or config files)
- Implement token rotation support
- Provide users a way to revoke their stored token
- Consider compliance requirements (GDPR, SOC 2, etc.)

### Token Scope

When users create Datawrapper tokens, recommend they:
- Create a token specifically for MCP use (not their primary token)
- Use minimal required scopes (if Datawrapper supports scoping)
- Rotate tokens periodically

---

## Relationship to MCP OAuth 2.1

The MCP spec's OAuth 2.1 support (covered in [march-2026-upgrades.md](march-2026-upgrades.md))
handles Layer 1 authentication (MCP client → your server). It does NOT solve the
Datawrapper token problem.

However, if you implement Option B (user accounts), you would use MCP OAuth 2.1 as the
authentication layer for your server. The flow becomes:

1. User connects MCP client to your server
2. MCP OAuth 2.1 authenticates user to your server (Layer 1)
3. Your server looks up user's stored Datawrapper token (Layer 2)
4. API calls to Datawrapper use the per-user token

For Option A (per-session tokens), MCP OAuth 2.1 is not required but could still be
used if you want to identify users for logging/analytics purposes.

---

## Future Considerations

**Datawrapper Team Accounts:** If users belong to a shared Datawrapper team, charts
could be created under the team rather than individual accounts. This might simplify
some use cases but requires understanding Datawrapper's team/folder model.

**Token Caching:** For Option A, consider caching validated tokens briefly to avoid
re-validation overhead on every tool call.

**Multi-Tenant Architecture:** If scaling to many users, consider whether to run
separate MCP server instances per tenant or a shared multi-tenant deployment.
