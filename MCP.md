# AI SENSE Free Public MCP Server

Connect an AI agent to nine public tools and one read-only product resource at
one remote MCP endpoint.

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

The tool list is deliberately small. Each tool has a clear schema and a direct
job in an agent workflow.

## Available resource

| URI | What it contains |
|-----|------------------|
| `https://aisense.no/verifyum` | Public product information for Verifyum, including the local file-processing boundary and current anchoring status |

Call `resources/list` to discover the resource. Call `resources/read` with the
URI above to read it as Markdown. The resource is informational. It does not
accept a file and cannot create a proof.

Verifyum processes the original file locally in the browser. Adding a remote
file-processing tool here would break that boundary, so MCP exposes product
context only.

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
            "server_description": "Public tools for webhooks, approvals, storage, time and IDs.",
            "server_url": "https://aisenseapi.com/mcp",
            "require_approval": "never",
        }
    ],
    input="Create a human approval request for deployment of build 42.",
)

print(response.output_text)
```

Use your normal approval policy if calls should pause for confirmation. The
tools do not send messages, charge money or modify outside accounts. Several
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

## Data and security

- Temporary data, capture records, short links and approval forms expire after 24 hours.
- The IDs and URLs are unguessable capability links. Share them with the intended recipient.
- Do not store passwords, private keys, health data or long-lived confidential data.
- Requests with a browser `Origin` header are accepted only from approved origins.
- Tool descriptions and annotations are hints. Clients should still apply their own approval policy.
- The Verifyum resource is read-only and contains no user data.

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
