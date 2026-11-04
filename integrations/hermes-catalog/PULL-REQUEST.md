# Pull request to NousResearch/hermes-agent: add aisense to plugin-catalog

The plugin catalog lists third-party plugins pinned at an exact commit;
`aisense.yaml` beside this file is the entry. It pins `agent-plugin/` in this
repository (`subdir`) at the commit that added the package. Hermes Agent's MCP
catalog (`optional-mcps/`) takes no new entries, which is why this route.

## How to open it

1. On GitHub, signed in as `aisenseapi`, open
   `https://github.com/NousResearch/hermes-agent/new/main?filename=plugin-catalog/aisense.yaml`,
   which forks the repository on first use.
2. Paste the content of `aisense.yaml`, commit on a new branch with the commit
   message below, and open the pull request against `main` with the title and
   body below.
3. The catalog CI clones this repository at the pinned commit and runs
   `hermes plugins validate`; a maintainer reviews and merges, asks for
   changes, or declines.

## Commit message and title

```text
feat(plugin-catalog): add aisense
```

## Pull request body

```text
What it does: connects Hermes to AI SENSE Free Public Tools, a hosted MCP
server at https://aisenseapi.com/mcp (Streamable HTTP, no authentication) with
77 tools: time and time zones, hashing and encoding, QR codes, HTML to PDF,
JSON and CSV, images, and workflow tools (temporary storage, webhook capture,
human approval, Agent Queue, Lease, Heartbeat, Agent Inbox, typed decisions
from weighted rules, semantic search, one-time secrets). It also bundles one
skill, aisense-tools, that tells the agent which tool fits which need.

Hermes surfaces used: a portable Agent Plugins 1.0.0 package only, with
plugin.json, mcp.json declaring the server `aisense`, and skills/aisense-tools.
There is no Python, no hooks, no middleware, no tools registered by the
plugin, no Desktop or dashboard code, and no environment variables.

Disclosure:
- Network: every tool call goes to AI SENSE's server at aisenseapi.com with
  the arguments the agent passes; request logs hold the caller's IP address
  (https://aisense.no/privacy). Webhook schedules and notify URLs make the
  server send a request to a URL the agent supplies.
- Credentials: none are stored. Tools that create something (queues, inboxes,
  captures, leases, secrets) return bearer tokens; the bundled skill tells the
  agent to keep them out of messages and logs.
- Data: stored data, files and captures are readable by anyone holding their
  id or URL and expire within 24 hours.
- Limits: 5000 requests per address per day across all tools.
- Tools: the list comes from the server at run time, so the pinned commit
  doesn't cover it. Every tool carries MCP annotations (37 read-only, 32 write,
  8 destructive), so `trust: untrusted` on the server entry makes Hermes ask
  before write-capable calls.

Submitter: AI SENSE AS owns the repository and runs the server (rule 5).

Validation: plugin.json and mcp.json validate against the Agent Plugins
1.0.0 schemas, and the server answers initialize and tools/list anonymously
over Streamable HTTP. We did not run `hermes plugins validate` locally; the
package layout follows the merged entries runa and courier-by-autolane, and
the catalog CI runs the check on this PR.
```
