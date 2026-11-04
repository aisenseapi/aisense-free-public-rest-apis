# Integrations: catalog entries for other agent ecosystems

Files that put the free MCP server in front of users of other agents, kept
here so they can be reviewed and resubmitted. Each ecosystem's own
documentation was read on 4 November 2026; formats may have moved since.

| Folder | For | What it is | How it is submitted |
| --- | --- | --- | --- |
| `hermes-catalog/` | Hermes Agent (Nous Research) | `aisense/manifest.yaml`, a catalog manifest in the shape of the existing remote no-auth entries, and `PULL-REQUEST.md` with the commit, title and body | A pull request that adds `optional-mcps/aisense/manifest.yaml` to `NousResearch/hermes-agent`; Nous merges after review |
| `clawhub-skill/` | OpenClaw | `aisense-free-tools/SKILL.md`, a skill that tells the agent how to add the server and which tool fits which need | `clawhub login`, then `clawhub skill publish aisense-free-tools --changelog "..."` from this folder; the ClawHub account is the publisher's GitHub login |

A ClawHub skill cannot carry an `mcp.servers` entry, so the skill instructs
the agent to add the server once. A ClawHub plugin can declare MCP servers in
its manifest (`mcpServers` in `openclaw.plugin.json`), which would make the
install one step; that route needs the plugin packaging and a capability
review, and is not prepared here.

The server itself needs nothing from either listing: any MCP client connects
to `https://aisenseapi.com/mcp` with one entry, as `MCP.md` shows.
