# AI SENSE Free Public MCP Server

Connect an AI agent to nine workflow tools, three Verifyum proof tools and one
read-only product resource at one remote MCP endpoint.

**Server URL:** `https://aisenseapi.com/mcp`

No account, API key or OAuth token is required. The limit is 5000 requests per
IP per 24 hours. This limit is shared with the public REST API.

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
| `verifyum_anchor_commitment` | Creates a public Solana Mainnet proof from a completed Verifyum commitment |
| `verifyum_get_proof` | Reads the public lifecycle state for a Verifyum proof ID |
| `verifyum_verify_public_proof` | Verifies public metadata and the finalized Solana transaction |

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
            "server_description": "Public workflow tools and Verifyum public proof tools.",
            "server_url": "https://aisenseapi.com/mcp",
            "require_approval": "always",
        }
    ],
    input="Create a human approval request for deployment of build 42.",
)

print(response.output_text)
```

The example asks for approval before tool calls because
`verifyum_anchor_commitment` creates a real public Solana transaction. A client
may use a more specific per-tool policy when it supports one. Several other
tools create temporary public URLs.

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

The server is stateless. It does not issue an `Mcp-Session-Id`. Send each
request to the same URL.

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

## Verifyum public proof tools

`verifyum_anchor_commitment` accepts exactly two fields:

```json
{
  "commitment": "sha256:<64 lowercase hex characters>",
  "idempotency_key": "one-stable-url-safe-key"
}
```

The commitment must already be calculated locally. Never send the original
file, filename, raw file hash, nonce, private manifest, wallet key, RPC key or
M2M token. The anchor call checks the live Verifyum health response and OpenAPI
contract before it submits the pair unchanged. It sends no Authorization
header.

This call creates a real public Solana Mainnet transaction. Use it only after
clear user intent. Do not call it during discovery, speculative work, bulk work
or a hidden background task. If the POST times out, its result is unknown. Retry
the same commitment with the same idempotency key. Do not make a new pair.

`verifyum_get_proof` reads the public lifecycle response. It may return queued,
submitted, finalized or failed.

`verifyum_verify_public_proof` verifies the public metadata signature against
the published Verifyum key registry. It also checks finalized status, signer,
Memo program, exact memo, transaction signature, slot and block time through
public Solana RPC.

A finalized proof shows that the commitment existed no later than the estimated
Solana block time. It does not prove authorship, ownership, legal signature
validity, original creation time or whether the file contents are true.

Current policy and limits are published at
[verifyum.com/agents](https://verifyum.com/agents). Public creation is currently
free because AI SENSE AS pays the Solana network fee. This is not a permanent
pricing promise.

## Data and security

- Temporary data, capture records, short links and approval forms expire after 24 hours.
- The IDs and URLs are unguessable capability links. Share them with the intended recipient.
- Do not store passwords, private keys, health data or long-lived confidential data.
- Requests with a browser `Origin` header are accepted only from approved origins.
- Tool descriptions and annotations are hints. Clients should still apply their own approval policy.
- The Verifyum resource is read-only and contains no user data.
- Verifyum anchor input is public and permanent. The source file and private proof data stay local.
- MCP logs contain the JSON-RPC method and tool name, not tool arguments or results.

The endpoint is public because the tools operate on short-lived public data and
do not access a user account. Authentication can be added later for private or
account-bound tools.

## Protocol errors

The endpoint returns JSON-RPC 2.0 errors for invalid requests. Tool input
errors are returned as MCP tool results with `isError` set to `true`.

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
