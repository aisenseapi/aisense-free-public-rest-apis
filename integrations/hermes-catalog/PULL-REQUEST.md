# Pull request to NousResearch/hermes-agent: add aisense to optional-mcps

The catalog is the directory `optional-mcps/<name>/manifest.yaml` in the
Hermes Agent repository; presence there means Nous has reviewed and merged
the entry. Their documentation names a pull request as the way in and states
no separate submission form. The manifest beside this file follows the shape
of the existing remote, no-auth entry `deepwiki` as read on 4 November 2026.

## How to open it

1. On GitHub, signed in as `aisenseapi`, fork `NousResearch/hermes-agent`.
2. In the fork, add the file `optional-mcps/aisense/manifest.yaml` with the
   content of `aisense/manifest.yaml` from this folder (the web editor's
   "Add file" does this without a clone).
3. Commit on a branch named `feat/optional-mcps-aisense` with the commit
   message below, then open the pull request against `main` with the title
   and body below. Their contributing rules: one logical change per PR,
   Conventional Commits, rebase onto main before merge.

## Commit message

```text
feat: add aisense remote MCP manifest to optional-mcps
```

## Pull request title

```text
feat: add aisense (AI SENSE Free Public Tools) to optional-mcps
```

## Pull request body

```text
What: a catalog manifest for AI SENSE Free Public Tools, a vendor-hosted
remote MCP server over Streamable HTTP at https://aisenseapi.com/mcp with no
authentication, run by AI SENSE AS (Oslo). It offers 77 tools: utility
endpoints (time and time zones, hashing, encoding, QR codes, HTML to PDF,
JSON and CSV, images) and agent workflow tools (temporary storage, webhook
capture, Agent Queue, Lease, Heartbeat, Agent Inbox, Agent Wake, Decide,
semantic search, one-time secrets). No account, no key, no session ID; 5000
requests per address per day. The server is listed in the official MCP
registry as com.aisenseapi/free-public-tools.

Why: Hermes users get these as a reviewed one-click install instead of a
hand-written mcp_servers entry; the manifest mirrors the existing remote
no-auth entry (deepwiki): transport http, auth none, a post_install note on
the quota and on bearer tokens the create tools answer.

How to test: hermes mcp install aisense; hermes mcp test aisense; then in a
session ask for the decide tool with state {"amount": 30, "tier": "gold"} and
one yes_no question named refund_now with bias -2 and the rules amount lte 50
weight 2, tier eq gold weight 1. The answer is yes with probability 0.7311,
confidence 0.4621 and action hold, so a real call is told from a guess.

Platforms tested: the server was verified live with an anonymous initialize
and tools/list over Streamable HTTP (MCP 2025-11-25) from curl and from Claude
Code; the manifest itself was not run through hermes mcp install by us, since
we do not maintain a Hermes installation. Documentation:
https://aisense.no/free-public-mcp-server and MCP.md in
https://github.com/aisenseapi/aisense-free-public-rest-apis.

Related issues: none.
```
