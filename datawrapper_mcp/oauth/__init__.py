"""Minimal OAuth-shaped authorization server for linking Datawrapper accounts.

This lets a single, admin-registered MCP connector (e.g. one Claude Team/
Enterprise custom connector shared by an entire org) still attribute each
user's chart activity to *their own* Datawrapper account, by presenting
Claude with a standard OAuth authorization-code + PKCE flow. Datawrapper
itself has no OAuth server and no SSO tie-in to a company identity
provider, so under the hood the "authorization" step is just a form asking
the user to paste their own Datawrapper API token - everything else
(codes, PKCE, token issuance, protected-resource metadata) exists only to
satisfy what an MCP client like Claude expects from an OAuth-protected
resource.

See datawrapper_mcp/oauth/storage.py for what's persisted and how, and
docs/proposals or INSTALLATION.md for the operational picture (env vars,
persistent storage requirements, and known limitations).
"""
