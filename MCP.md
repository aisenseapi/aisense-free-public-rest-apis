# AI SENSE Free Public MCP Server

Connect an AI agent to ten workflow tools and one read-only product resource
at the AI SENSE remote MCP endpoint.

**Server URL:** `https://aisenseapi.com/mcp`

No account, API key or OAuth token is required. The limit is 5000 requests per
IP per 24 hours. This limit is shared with the public REST API.

Agents that need only Verifyum can connect to its dedicated stateless endpoint:

```text
https://api.verifyum.com/mcp
```

For Claude Code:

```bash
claude mcp add --transport http verifyum https://api.verifyum.com/mcp
```

The separate Verifyum endpoint exposes exactly `verifyum_anchor_commitment`,
`verifyum_get_proof` and `verifyum_verify_public_proof`. It needs no account,
wallet, payment, API key or npm package. It is listed in the official MCP
registry as `com.verifyum/mcp` version `0.1.0`. The AI SENSE endpoint does not
proxy these tools.

## Available tools

| Tool | What it does |
|------|--------------|
| `get_current_time` | Returns the current time for an IANA timezone or UTC offset |
| `generate_uuid` | Generates a UUID version 4 |
| `shorten_url` | Creates a 307.fi link that expires after 24 hours |
| `store_temporary_data` | Stores a JSON value for 24 hours |
| `read_temporary_data` | Reads a stored JSON value by ID |
| `create_webhook_capture` | Creates a URL that captures an HTTP request |
| `read_webhook_capture` | Reads the captured method, headers and body |
| `create_human_approval` | Creates a hosted approval form for a person |
| `read_human_approval` | Checks the form status and reads the answer |
| `create_agent_wake` | Creates a durable MCP task for a webhook, human response or time event |

The tool list is deliberately small. Each tool has a clear schema and a direct
job in an agent workflow.

## Available resource

| URI | What it contains |
|-----|------------------|
| `https://aisense.no/verifyum` | Public product information for Verifyum, including the local file-processing boundary and current anchoring status |

Call `resources/list` to discover the resource. Call `resources/read` with the
URI above to read it as Markdown. The resource is informational and does not
accept a file.

Verifyum processes the original file locally in the browser or another local
process. The remote MCP server accepts only a completed commitment and
idempotency key for creation, or a public proof ID for reads. It does not expose
a file-processing tool.

## OpenAI Responses API

```python
from openai import OpenAI

client = OpenAI()

response = client.responses.create(
    model="gpt-5.6",
    tools=[
        {
            "type": "mcp",
            "server_label": "aisense",
            "server_description": "Public AI SENSE workflow tools.",
            "server_url": "https://aisenseapi.com/mcp",
            "require_approval": "always",
        }
    ],
    input="Create a human approval request for deployment of build 42.",
)

print(response.output_text)
```

The example asks for approval before every tool call. A client may use a more
specific per-tool policy when it supports one. Several tools create temporary
public URLs or stored records.

## Current MCP request

The server supports MCP revision `2026-07-28`. A current `tools/list` request
looks like this:

```bash
curl -X POST https://aisenseapi.com/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "MCP-Protocol-Version: 2026-07-28" \
  -H "MCP-Method: tools/list" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {
      "_meta": {
        "io.modelcontextprotocol/protocolVersion": "2026-07-28"
      }
    }
  }'
```

Calls to `tools/call` also send `MCP-Name` with the tool name.

## Older MCP clients

The endpoint also accepts the initialize flow used by these revisions:

- `2025-11-25`
- `2025-06-18`
- `2025-03-26`

The transport does not issue an `Mcp-Session-Id`. Agent Wake task state is kept
by task ID for up to 24 hours. Send each request to the same URL.

## Human approval example

Call `create_human_approval` with:

```json
{
  "title": "Deploy build 42?",
  "description": "The tests passed. A person must approve production.",
  "options": ["Approve", "Reject"],
  "allow_note": true
}
```

The result contains a `form_url` for the reviewer and a `result_url` for other
systems. The MCP client can call `read_human_approval` with the returned
`action_id`. Its status changes from `pending` to `answered` after submission.

## Webhook capture example

Call `create_webhook_capture`. Send the returned `update_url` to the service
that emits the webhook. Then call `read_webhook_capture` with the returned
`capture_id`.

The result includes the HTTP method, request URI, headers, client IP and body.
JSON is returned as JSON. Text stays as text. Other bytes are Base64 encoded.

## Agent Wake and MCP Tasks

`create_agent_wake` is available to clients using MCP revision `2026-07-28`
with the `io.modelcontextprotocol/tasks` extension. It creates a durable task
for one of these events:

- `webhook` completes after the first request reaches its wake URL
- `human` completes after a person answers the hosted form
- `time` completes on the first status check after its wake time

The client declares task support on the tool call:

```json
{
  "jsonrpc": "2.0",
  "id": 20,
  "method": "tools/call",
  "params": {
    "name": "create_agent_wake",
    "arguments": {
      "event_type": "webhook",
      "timeout_seconds": 3600
    },
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {
        "extensions": {
          "io.modelcontextprotocol/tasks": {}
        }
      }
    }
  }
}
```

The result has `resultType: "task"` and a `taskId`. Poll with `tasks/get`.
Task requests must repeat the task extension capability and send the task ID in
the `MCP-Name` header. The server supports `tasks/get`, `tasks/update` and
`tasks/cancel`. It does not expose `tasks/list` or `tasks/result`.

A human task reports `input_required` and includes one URL mode
`elicitation/create` request. Opening the URL does not approve anything. The
task completes only when the form is submitted. A decline or cancel response
sent through `tasks/update` cancels the task.

The first webhook wins. Later requests cannot replace its result. Standard
credential headers are redacted before the request is stored. The body may
still contain sensitive data, so keep secrets and personal data out of the
public service.

## Separate Verifyum MCP endpoint

MCP is an additional way to reach Verifyum. The browser flow, public HTTP API
and published protocol remain the main product documentation. The Verifyum MCP
endpoint keeps file hashing, nonce generation and private-manifest construction
on the agent's machine.

The Verifyum endpoint is separate from `https://aisenseapi.com/mcp`:

```text
https://api.verifyum.com/mcp
```

`verifyum_anchor_commitment` accepts exactly two fields:

```json
{
  "commitment": "sha256:<64 lowercase hex characters>",
  "idempotency_key": "one-stable-url-safe-key"
}
```

The commitment must already be calculated locally. Never send the original
file, filename, raw file hash, nonce, private manifest, wallet key, RPC key or
M2M token. The endpoint sends no Authorization header.

This call creates a real public Solana Mainnet transaction. Use it only after
clear user intent. Do not call it during discovery, speculative work, bulk work
or a hidden background task. If the POST times out, its result is unknown. Retry
the same commitment with the same idempotency key. Do not make a new pair.

`verifyum_get_proof` reads the public lifecycle response. It may return queued,
submitted, finalized or failed.

`verifyum_verify_public_proof` performs the full Ed25519 signature check in the
web runtime. The result states that Verifyum is checking its own public data
and returns the exact Solana RPC request for a separate confirmation.

## Agent decision records

An autonomous system can assemble one decision record locally from its system
instructions, exact prompt, model and version, parameters, tool calls and
output. It hashes the document locally and anchors only the commitment. The
record itself stays inside the operator's infrastructure.

A matching proof shows that the exact record existed unchanged no later than
the block time. It does not prove that the agent actually ran with the recorded
parameters. Prefer one record per case or day, or anchor the head of a local
hash chain, instead of anchoring every individual decision.

## Verifyum Witness Layer

Finalized proofs are grouped into hourly and daily Merkle checkpoints. The
Witness Layer adds OpenTimestamps with eventual Bitcoin anchoring, a public
GitHub checkpoint log, the Internet Archive, Certificate Transparency, a
qualified EU timestamp under eIDAS, Software Heritage and a witness-cosigned
Sigsum log with a quorum of two out of three around the primary Solana record
and Verifyum signature - nine evidence records in total for checkpoints
created since 2026-09-01.

Solana and the Verifyum signature remain the primary evidence. The qualified
timestamp's eIDAS legal presumption covers the daily checkpoint root alone. A
Verifyum user proof is not a qualified electronic timestamp, and Verifyum is
not a qualified trust service. A Software Heritage identifier or Internet
Archive capture shows what was stored, never when. The Verifyum signature and
GitHub log are operator records, not independent witnesses. The number of
channels is not a quality score.

External witnesses receive only an aggregate checkpoint root. They do not
receive a file, raw file hash, nonce, private manifest or proof ID. Each
supplemental channel reports `pending`, `confirmed`, `unavailable` or `failed`.
A pending or missing witness does not invalidate the Solana proof.

A proof membership shows inclusion in a Verifyum checkpoint. It does not by
itself show that an external channel confirmed the checkpoint. Read the
separate channel receipt before making that claim.

Public inspection starts at these routes:

```text
GET https://api.verifyum.com/v2/proofs/{proof-id}/witnesses
GET https://verifyum.com/witness/checkpoints/{hourly|daily}/{batch-id}.json
GET https://verifyum.com/witness/receipts/{hourly|daily}/{batch-id}.json
```

The human-readable explanation is at
[verifyum.com/witness](https://verifyum.com/witness).

A finalized proof shows that the commitment existed no later than the estimated
Solana block time. It does not prove authorship, ownership, legal signature
validity, original creation time or whether the file contents are true.

Current policy and limits are published at
[verifyum.com/agents](https://verifyum.com/agents). Public creation is currently
free because AI SENSE AS pays the Solana network fee. This is not a permanent
pricing promise.

## Data and security

- Temporary data, capture records, short links, approval forms and Agent Wake tasks expire after 24 hours.
- The IDs and URLs are unguessable capability links. Share them with the intended recipient.
- Do not store passwords, private keys, health data or long-lived confidential data.
- Requests with a browser `Origin` header are accepted only from approved origins.
- Tool descriptions and annotations are hints. Clients should still apply their own approval policy.
- The Verifyum resource is read-only and contains no user data.
- The Verifyum MCP endpoint is separate from the AI SENSE MCP endpoint.
- Verifyum anchor input is public and permanent. The source file and private proof data stay local.
- MCP logs contain the JSON-RPC method and tool name, not tool arguments or results.

The endpoint is public because the tools operate on short-lived public data and
do not access a user account. Authentication can be added later for private or
account-bound tools.

## Protocol errors

The endpoint returns JSON-RPC 2.0 errors for invalid requests. Tool input
errors are returned as MCP tool results with `isError` set to `true`.

Agent Wake returns JSON-RPC error `-32003` when the current Tasks extension is
missing. Unknown task IDs return `-32602`.

| HTTP status | Meaning |
|-------------|---------|
| `200` | JSON-RPC response |
| `202` | Notification accepted |
| `400` | Invalid JSON-RPC or MCP headers |
| `403` | Origin rejected |
| `405` | Method other than POST or OPTIONS |
| `406` | Current client did not accept JSON and event streams |
| `413` | Request body is larger than 256 KB |
| `415` | Content type is not JSON |
| `429` | Rate limit exceeded |
| `503` | Rate limit storage is unavailable |

## More documentation

- Website: [aisense.no/free-public-mcp-server](https://aisense.no/free-public-mcp-server)
- REST API reference: [`API.md`](API.md)
- Source and tests: [github.com/aisenseapi/aisense-free-public-rest-apis](https://github.com/aisenseapi/aisense-free-public-rest-apis)
