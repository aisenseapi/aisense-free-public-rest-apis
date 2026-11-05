# AI SENSE Free Public Tools: Agent Plugin

A portable [Agent Plugins](https://agent-plugins.org) 1.0.0 package that
connects an agent to the free AI SENSE MCP server and bundles one skill that
tells the agent which of its 77 tools fits which need.

| File | What it is |
| --- | --- |
| `plugin.json` | The manifest: name `aisense`, version, author, license |
| `mcp.json` | One remote server, `aisense`, over Streamable HTTP at `https://aisenseapi.com/mcp`, with no authentication |
| `skills/aisense-tools/SKILL.md` | When to use which tool, the rules on tokens, expiry and quota, and a call with a known answer that proves the connection |

There is no local code: the package declares a hosted server and a skill.

## Install

Any client that loads Agent Plugins can load this directory; the
[compatible clients](https://agent-plugins.org/compatible-clients) page links
each client's own setup instructions. The same package with manifests for
Claude Code, Codex, Gemini CLI and Antigravity sits at the root of
[aisenseapi/aisense-agent-plugin](https://github.com/aisenseapi/aisense-agent-plugin),
which takes each client's one-command install. Without the plugin, the server
alone is one entry in any MCP client:

```bash
hermes mcp add aisense --url https://aisenseapi.com/mcp
claude mcp add --transport http aisense https://aisenseapi.com/mcp
```

## What the tools do

Utilities: time and time zones, hashing and verification, encoding, random
values and UUIDs, QR codes in both directions, HTML to PDF, HTML and Markdown,
JSON checks and JSON to CSV, table matching, image conversion and metadata,
email and value validation, network lookups, short URLs. Workflow tools:
temporary storage and files, webhook capture, human approval, Agent Queue,
Lease, Heartbeat, Agent Inbox, Agent Wake, Agent Handoff, Agent Run, temporary
DNS names, semantic search, one-time secrets, and `decide` for typed decisions
from facts and weighted rules. The full list with arguments is in
[MCP.md](../MCP.md).

## What to know before installing

- **Every tool call goes to AI SENSE's server** at `aisenseapi.com` with the
  arguments the agent passes, and those arguments also reach the user's model
  provider through the session. AI SENSE AS is in Oslo, Norway; request logs
  hold the caller's IP address for the period the
  [privacy policy](https://aisense.no/privacy) gives.
- **No account, no key, no session ID.** Every address has 5000 requests a day
  across all tools; past that the server answers 429 until the daily reset.
- **Bearer tokens.** Tools that create something (queues, inboxes, captures,
  leases, secrets, search collections) return tokens that grant access to it.
  The bundled skill tells the agent to keep them out of messages and logs.
- **Public by id, gone in 24 hours.** Stored data, files and captures are
  readable by anyone holding their id or URL and expire within 24 hours. Do not
  store secrets, credentials or personal data.
- **Outbound calls.** Webhook schedules and notify URLs make the server send a
  request to a URL the agent supplies.
- **Annotated tools.** Each tool carries MCP annotations: 37 are read-only, 32
  write and 8 are destructive (they acknowledge, release, cancel, delete, reveal
  or burn). A client that asks before write-capable calls can use them, for
  example Hermes Agent with `trust: untrusted` on the server entry.
- **The tool list comes from the server at run time**, so a pinned commit of
  this package does not fix it.

## Check it works

Ask the agent to call `decide` with state `{"amount": 30, "tier": "gold"}` and
one `yes_no` question named `refund_now` with bias -2 and the rules amount lte
50 weight 2 and tier eq gold weight 1. The answer is `yes`, probability 0.7311,
confidence 0.4621, action `hold`.

## License and contact

MIT, see [LICENSE](LICENSE). AI SENSE AS, support@aisense.no,
https://aisense.no.
