// No runtime capabilities to register. The datawrapper MCP server is wired
// in declaratively through the mcpServers field in openclaw.plugin.json;
// this entrypoint exists only because OpenClaw's package registry requires
// one to be declared.
module.exports = {
  id: "datawrapper-mcp",
  name: "Datawrapper",
  description: "Create, update and publish Datawrapper charts from an AI assistant",
  register() {},
};
