# Integrations: putting the MCP server in front of other agents

Files that list the free MCP server where users of other agents look, kept
here so they can be reviewed and resubmitted. Each ecosystem's documentation
was read on 4 November 2026; formats may have moved since.

| Where | For | What it is | How it is submitted |
| --- | --- | --- | --- |
| [`../agent-plugin/`](../agent-plugin/README.md) | Hermes Agent, OpenClaw, VS Code, Cursor, GitHub Copilot, ChatGPT and Codex, Kiro | A portable [Agent Plugins](https://agent-plugins.org) 1.0.0 package: `plugin.json`, `mcp.json` with the remote server, and one skill | Each client loads it as its documentation says; Hermes lists it through its plugin catalog (below) |
| `hermes-catalog/` | Hermes Agent | `aisense.yaml`, the plugin catalog entry that pins `agent-plugin/` in this repository at an exact commit, and `PULL-REQUEST.md` with the text for the pull request | A pull request that adds `plugin-catalog/aisense.yaml` to `NousResearch/hermes-agent`; a maintainer merges after review and the catalog CI runs `hermes plugins validate` |
| `clawhub-skill/` | OpenClaw | `aisense-free-tools/SKILL.md`, a ClawHub skill that tells the agent how to add the server and which tool fits which need | `clawhub login`, then `clawhub skill publish aisense-free-tools` from this folder, or ClawHub's web importer |

Hermes Agent's MCP catalog (`optional-mcps/`) takes no new entries since
29 October 2026: a maintainer moved a new hosted server to the plugin catalog
"(the MCP catalog takes no new entries)", and hosted servers have since been
listed as portable plugins there. The plugin route is what this folder
prepares.

The server itself needs none of these listings: any MCP client connects to
`https://aisenseapi.com/mcp` with one entry, as `MCP.md` shows.
