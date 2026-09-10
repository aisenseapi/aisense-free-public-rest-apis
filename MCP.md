# AI SENSE Free Public MCP Server

Production MCP discovery returned 28 workflow tools and two read-only resources
on 9 September 2026. The deployed Queue REST smoke test passed 21 checks.
Use `tools/list` to inspect the server you connect to.

Start with [AGENT-GUIDE.md](AGENT-GUIDE.md) to choose tools, then
[AGENT-QUICKSTART.md](AGENT-QUICKSTART.md) for a complete Queue workflow and
retry decisions.

**Server URL:** `https://aisenseapi.com/mcp`

The official MCP Registry lists `com.aisenseapi/free-public-tools` version
`1.8.0` as active, verified on 9 September 2026. This is the server release
version, separate from the agent guide resource version.

No account, API key or OAuth token is required. The limit is 5000 requests per
IP per 24 hours. This limit is shared with the public REST API and A2A.
The counter resets at server midnight, not on a rolling per-request window.

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
| `create_heartbeat` | Creates a 24-hour deadline monitor with one on-miss action |
| `read_heartbeat` | Reads a Heartbeat monitor by its bearer ID |
| `ping_heartbeat` | Records a check-in without extending the fixed lifetime |
| `create_lease_namespace` | Creates a private namespace for short Lease keys |
| `acquire_lease` | Claims work and returns an owner token and fencing token |
| `renew_lease` | Extends a held Lease within its fixed lifetime |
| `release_lease` | Releases a held Lease for another worker |
| `complete_lease` | Stores a small reusable result for the same work identity |
| `create_agent_inbox` | Creates a disposable mail inbox that lasts at most 24 hours |
| `read_agent_inbox` | Reads the received mail, extracted codes and public links |
| `create_agent_queue` | Creates a queue with a fixed 24-hour expiry and separate role tokens |
| `read_agent_queue` | Reads queue timing and pending, claimed, completed and failed counts |
| `enqueue_agent_queue_job` | Adds a JSON job using a stable deduplication key |
| `read_agent_queue_job` | Reads one job's payload, status and attempts |
| `claim_agent_queue_job` | Claims one available job and returns its receipt |
| `ack_agent_queue_job` | Marks a currently claimed job completed |
| `release_agent_queue_job` | Makes a claimed job available for another attempt |
| `renew_agent_queue_job` | Extends claim visibility within the queue's original expiry |

Each MCP tool has a schema returned by discovery. The REST function-calling
catalog is a separate integration surface, not a copy of this list.

## Available resources

| URI | What it contains |
|-----|------------------|
| `https://aisense.no/verifyum` | Public product information for Verifyum, including the local file-processing boundary and current anchoring status |
| `skill://com.aisenseapi/free-public-tools` | A compact agent guide to the public tools, safety limits and workflow patterns |

Call `resources/list` to discover both resources. Call `resources/read` with a
URI above to read it as Markdown. The resources are informational and do not
accept a file.

The refreshed canonical guide is [AGENT-GUIDE.md](AGENT-GUIDE.md). The initial
resource read after the Queue deployment on 9 September 2026 still returned
the older 18-tool guide. Deployment of the refreshed embedded copy requires a
separate `resources/read` check. Use the repository guide until that check
confirms the Queue and Inbox sections.

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
systems. Set `respondents` from 2 to 20 to create a separate bearer link for
each person. Group status moves from `pending` to `partial`, then `answered`.
The result includes the answer count, individual responses and a decision
tally. The server stores only hashes of group form tokens.

Add `notify_url` when another public HTTP service should receive a small signal
after the final answer. The signal contains the action ID, status, result URL
and group counts. It does not contain the answers. The target is checked for
private and reserved addresses before it is queued and again before delivery.

`read_human_approval` accepts `wait_seconds` from 0 to 25. It returns when the
state changes, the action finishes or the wait ends.

## Webhook capture example

Call `create_webhook_capture`. Send the returned `update_url` to the service
that emits the webhook. Then call `read_webhook_capture` with the returned
`capture_id`. The read tool accepts `wait_seconds` from 0 to 25.

`create_webhook_capture` accepts an optional `notify_url`. After the first
request is captured, that public URL receives a small signal with the capture
ID and result URL. The captured method, headers and body are not copied into
the signal. Delivery has one transport retry.

The result includes the HTTP method, request URI, headers, client IP and body.
JSON is returned as JSON. Text stays as text. Other bytes are Base64 encoded.
The first request wins. A sender retry returns the stored first request and
cannot replace it or create a second notification.

## Heartbeat and Lease

Heartbeat is a short-lived dead-man switch. `create_heartbeat` sets the
expected check-in interval, a grace period and one on-miss action. The action
can call a public webhook or wake an active Agent Wake webhook task. Each
`ping_heartbeat` moves the next deadline. It never extends the absolute
24-hour lifetime. A missed action is attempted once.

The Heartbeat ID is a 256-bit bearer secret used for both status and ping. The
public result names the action type but does not return its target or payload.
There is no Heartbeat listing tool.

Lease gives several agents one coordination point for the same unit of work.
The first `acquire_lease` call receives an owner token and a monotonic fencing
token. Other callers receive `held` while the lease is active. Holding a lease
cannot stop a paused worker from waking up and acting, which is what the
fencing token is for: send it to the protected system and have that system
reject writes carrying an older value. A fingerprint can bind the key to one
exact kind of work.

Use `complete_lease` to store a reusable JSON result up to 32 KB. A later
acquire for the same namespace, key and fingerprint returns that result.
Renewal stays inside the original 24-hour lifetime. Raw keys, namespaces,
owner tokens and fingerprints are not stored. There is no Lease listing tool.

## Agent Queue

Create a queue with `create_agent_queue` and `{}`. Keep its `queue_id`,
`read_token`, `write_token` and `worker_token`. The three 64-character hex
tokens are issued only by creation. The 32-character queue ID is not a secret
capability on its own. Queue tool calls supply the appropriate token in their
arguments, as listed below. REST calls use `Authorization: Bearer TOKEN`.
Never place these credentials in a URL.

| Tool | Required arguments | Optional arguments |
| --- | --- | --- |
| `create_agent_queue` | None | None |
| `read_agent_queue` | `queue_id`, `read_token` | None |
| `enqueue_agent_queue_job` | `queue_id`, `write_token`, `job_key`, `payload` | None |
| `read_agent_queue_job` | `queue_id`, `job_id`, `read_token` | None |
| `claim_agent_queue_job` | `queue_id`, `worker_token` | `visibility_timeout` |
| `ack_agent_queue_job` | `queue_id`, `job_id`, `worker_token`, `receipt` | None |
| `release_agent_queue_job` | `queue_id`, `job_id`, `worker_token`, `receipt` | None |
| `renew_agent_queue_job` | `queue_id`, `job_id`, `worker_token`, `receipt` | `visibility_timeout` |

Enqueue a job such as `job_key: "report:42"` with
`payload: {"report_id":42}`. Keys match
`^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$`. Payload accepts any JSON value up to
16384 encoded bytes, including `null`. Repeating a key and payload returns the
existing job with `deduplicated: true`. Reusing the key for different payload
returns a conflict.

Claim returns `job: null` when nothing is available. Otherwise `job` contains
the ID, key, payload, status, attempts, timing and a secret `receipt` for this
claim only. Other operations never disclose a receipt. `visibility_timeout`
accepts integer seconds from 30 to 900 and defaults to 60. Complete work and
ack with the receipt, release to retry, or renew while the same claim remains
valid. A stale receipt fails. A successful ack can be repeated with its
receipt. Ack does not accept a result.

Queue tool failures set `isError: true` and include `error` and `status_code`
in the structured result. These status codes describe the Queue operation.
The MCP transport can still return HTTP 200 for the JSON-RPC tool result.

An unacknowledged job becomes available after visibility expires, until five
unsuccessful claim attempts change it to `failed`. Jobs can be delivered again after a claim expires or is released. Queue expiry and the attempt limit may leave jobs unfinished. Initial delivery and exactly-once execution are not guaranteed. External
actions must be idempotent: a worker may lose its claim after an action
succeeds but before ack.

The queue and all its jobs, deduplication entries, completed records and failed
records expire exactly 24 hours after creation. No operation extends the
returned `expire_timestamp`. There is no TTL setting. At most 100 distinct jobs
can be added over that lifetime, including completed and failed jobs. Creation
is limited to 20 queues per client IP per 24 hours within the shared limit.

Queue reads return `counts` with `pending`, `claimed`, `completed`, `failed`
and `total`, without listing jobs. Share the read token with observers, the
write token with producers, and the worker token with workers. Claiming workers
receive the payload. The Queue service writes payload content to its JSON state files without encrypting it. It normalizes object-key ordering and JSON serialization. Keep secrets and sensitive
personal data out of them. The queue never runs code, fetches payload URLs,
makes callbacks or contacts another service. Your worker does the work.

See [`API.md`](API.md#agent-queue---temporary-work-for-multiple-workers) for
the REST paths and response envelopes.

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

## Agent Inbox

`create_agent_inbox` takes no arguments. It returns a disposable mail address
an agent can use to receive a verification code, a confirmation link or a
sign-up mail. The inbox lasts at most 24 hours. The lifetime is fixed and is
not extendable.

Creation returns two identifiers with different jobs:

- `slug` is seven characters from `a-z0-9` and appears in the mail address. It
  is public by construction, because it travels in mail headers, bounces and
  sender logs. Knowing it lets anyone send mail to the inbox. It never reads
  the inbox and it never appears in a URL.
- `inbox_id` is a UUID and is the only credential that reads the inbox. It is
  a bearer secret, returned once, at creation.

Guessing the address does not read the inbox. A wrong `inbox_id` and a missing
inbox both answer 404, never 403, so the two cases are indistinguishable.

`read_agent_inbox` accepts `inbox_id` and `wait_seconds` from 0 to 25. The wait
defaults to 0. The long poll returns when a message arrives, when a refused
message first turns `truncated` true, or when the wait ends. It adds
`waited_seconds` and `wait_reason` to the result.

The result contains the slug, the address, the message count, a `truncated`
flag, the messages and the creation and expiry timestamps. It does not contain
`inbox_id`. The credential is never echoed back.

Each message has the sender address, subject, received time, cleaned text,
`codes` and `links`. The `date` field is the time the service received the
message, not the sender's `Date` header, because that header is sender
controlled. `codes` are standalone 4 to 8 digit numbers. `links` are public
http and https links only. Private-IP links and localhost links are dropped.

An inbox that has hit a cap refuses new mail rather than evicting old mail.
`truncated` turns true once a message has been refused, by the 20 message cap
or by the 256 KiB total, so an agent waiting for a code sees the reason
instead of a quiet inbox. The flag is part of the long poll signature, so the first refusal
wakes a waiter instead of leaving it to time out.

Attachments, raw MIME, arbitrary headers, scripts and styles are stripped
before storage. Only the sender address, subject, received time, cleaned text,
codes and public links are kept.

| Limit | Value |
|-------|-------|
| Messages per inbox | 20 |
| Cleaned text per message | 64 KiB |
| Cleaned text per inbox | 256 KiB |
| Inboxes per client per UTC day | 50 |
| Active inboxes service wide | 5000 |
| Lifetime | 24 hours, fixed |

## Agent2Agent, a third protocol

A2A runs beside this endpoint at its own URL. It is a smaller surface, not a
second copy of the tool list.

```text
POST https://aisenseapi.com/a2a
GET  https://aisenseapi.com/.well-known/agent-card.json
```

The endpoint speaks JSON-RPC 2.0 and A2A protocol revision `1.0`, from
specification v1.0.1. The agent card is a plain GET, because the protocol has
no method for fetching it. No account, API key or token is needed, the same as
here.

A2A is a protocol for one agent to delegate work to another. MCP is the
protocol for exposing tools. Most of this service is tools, so only five
capabilities are offered over A2A:

| A2A skill | Same capability on this endpoint |
|-----------|----------------------------------|
| `agent-wake` | `create_agent_wake` |
| `human-approval` | `create_human_approval` |
| `agent-inbox` | `create_agent_inbox` |
| `webhook-capture` | `create_webhook_capture` |
| `agent-queue` | `create_agent_queue` |

Those five are the cases where the interesting object is a long-lived,
resumable task, often waiting on a person or on another agent. A2A carries
that in core, while MCP needed
the `io.modelcontextprotocol/tasks` extension to say the same thing. Each skill
calls the tool in the right-hand column, so arguments, bounds and refusals are
identical on the two surfaces.

The other MCP tools in the table above are not reachable over A2A, and neither are the REST-only
utilities: hashing, encoding, JWT, QR codes, validation and the wallets. The
schemas of the tools are published in band by `tools/list`, and a task
lifecycle would add nothing to a hash or a UUID. **MCP is the broader workflow
surface. Use REST for utilities that are absent from MCP discovery.** A2A has no read
skills either. It creates a record, and `read_human_approval`,
`read_agent_inbox` and `read_webhook_capture` here, or the REST routes in
[`API.md`](API.md), read it back.

A2A skills are not addressable. The card gives each skill an `id`, but no
request field in the protocol carries one, and a skill has no `inputSchema`, so
the card can describe a skill without saying how to call it. This service
therefore takes the name inside the message, in a part carrying structured
data:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "SendMessage",
  "params": {
    "message": {
      "messageId": "caller-generated",
      "role": "ROLE_USER",
      "parts": [
        {
          "data": {
            "skill": "agent-wake",
            "arguments": { "event_type": "webhook", "timeout_seconds": 3600 }
          },
          "mediaType": "application/json"
        }
      ]
    }
  }
}
```

`arguments` are the fields of the matching tool. The convention is this
service's own and not something A2A defines, so a reader looking for a standard
field will not find one. A message with no such data part is refused with
`-32602`. The agent has no language model and does not interpret free text.

`SendMessage`, `GetTask`, `ListTasks` and `CancelTask` are implemented.
`SendStreamingMessage` and `SubscribeToTask` answer `-32004`, and the four
`TaskPushNotificationConfig` methods answer `-32003`. The card declares
`streaming` false and `pushNotifications` false, and returning those errors is
the conforming behaviour once a capability is declared false rather than a gap.
The two families keep different codes on purpose. `GetExtendedAgentCard` also
answers `-32004`. An unknown method is `-32601`, a request that does not say
`"jsonrpc": "2.0"` is `-32600`, and a bad or missing argument is `-32602`
carrying the tool's own message instead of the `isError` tool result MCP
returns.

`agent-wake` answers with a Task:

```json
{
  "id": "...",
  "contextId": "...",
  "status": {
    "state": "TASK_STATE_WORKING",
    "timestamp": "2026-09-06T16:44:45Z"
  }
}
```

The states are `TASK_STATE_WORKING`, `TASK_STATE_INPUT_REQUIRED`,
`TASK_STATE_COMPLETED`, `TASK_STATE_FAILED` and `TASK_STATE_CANCELED`, spelled
with one L. `GetTask` and `CancelTask` address a task by this `id`. The Task
carries the ID, a context ID and the state, and not the wake URL or the form
URL, so create the task through MCP or REST when the caller needs one of those.

The other three skills answer with a Message whose data part is the created
record, the same JSON the matching tool returns:

```json
{
  "messageId": "msg-...",
  "role": "ROLE_AGENT",
  "parts": [ { "data": { "ok": true }, "mediaType": "application/json" } ]
}
```

`ListTasks` always returns an empty page:

```json
{ "tasks": [], "nextPageToken": "", "pageSize": 50, "totalSize": 0 }
```

The specification requires every operation to scope results to the
authenticated caller. This service authenticates nobody, so there is no
principal to scope to, and a global list would hand every caller every task ID.
Those IDs are the only credential there is. For the same reason a wrong task ID
and a task that never existed both answer `-32001` with nothing to tell them
apart, because a difference would make the endpoint a lookup oracle.

A request with no `id` is a notification and gets HTTP 204 with no body. A
batch array is accepted and answers with the replies its non-notification
entries produce.

## Separate Verifyum MCP endpoint

MCP is an additional way to reach Verifyum. The browser flow, public HTTP API
and published protocol remain the main product documentation. The Verifyum MCP
endpoint keeps file hashing, nonce generation and private-manifest construction
on the agent's machine.

The Verifyum endpoint is separate from `https://aisenseapi.com/mcp`:

```text
https://api.verifyum.com/mcp
```

The public HTTP API uses `POST https://api.verifyum.com/v2/anchor` and
`GET https://api.verifyum.com/v2/proofs/{proof-id}`. It also needs no API key.

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

Finalized proofs are grouped into hourly and daily Merkle checkpoints. Nine
records surround each finalized proof.

| Tier | Records |
| --- | --- |
| Primary evidence | One finalized Solana Mainnet Memo transaction per proof |
| Independent corroboration | Hourly OpenTimestamps on Bitcoin, daily qualified EU timestamp, daily witness-cosigned Sigsum and daily Certificate Transparency certificate |
| Operator records and availability redundancy | Verifyum Ed25519 signature, GitHub checkpoint log, Software Heritage and Internet Archive |

The Solana transaction is the primary evidence. Deep Solana history generally
requires an archival provider. The qualified timestamp's eIDAS legal
presumption covers the daily checkpoint root alone. A Verifyum user proof is
not a qualified electronic timestamp. Verifyum is not a qualified trust
service. Software Heritage and Internet Archive show what was stored. They do
not establish when the original file existed. The number of channels is not a
quality score.

The Sigsum digest is cosigned by Glasklar, Mullvad and Tillitis with a quorum
of two out of three. The qualified timestamp uses RFC 3161. Its eIDAS Article
41(2) presumption applies only to the daily checkpoint root.

External witnesses receive only an aggregate checkpoint root. They do not
receive a file, raw file hash, nonce, private manifest or proof ID. Each
channel reports `pending`, `confirmed`, `unavailable` or `failed`.
A pending or missing witness does not invalidate the Solana proof or Verifyum
signature.

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

Every finalized proof is also announced on
[Telegram](https://t.me/verifyum) and in the
[Atom feed](https://verifyum.com/feed.xml). These posts help people and agents
find new proofs. They are announcement channels and are excluded from the nine
evidence records. Their timestamps date the announcement. They say nothing
about the original file date.

A finalized proof shows that the commitment existed no later than the estimated
Solana block time. It does not prove authorship, ownership, legal signature
validity, original creation time or whether the file contents are true.

Current policy and limits are published at
[verifyum.com/agents](https://verifyum.com/agents). Public creation is currently
free because AI SENSE AS pays the Solana network fee. This is not a permanent
pricing promise.

## Data and security

- Temporary data, capture records, short links, approval forms, Agent Wake tasks, Heartbeats, Leases and Agent Inboxes have fixed short lifetimes.
- The IDs and URLs are unguessable capability links. Share them with the intended recipient.
- Group approval links, Heartbeat IDs, Lease namespaces, owner tokens and inbox IDs are bearer secrets.
- An Agent Inbox address is public by construction. The inbox ID is the only credential that reads the mail, so share the address and keep the ID.
- Queue read, write and worker tokens are separate bearer secrets. Receipts identify one claim. All Queue state expires 24 hours after creation.
- Do not store passwords, private keys, health data or long-lived confidential data.
- Requests with a browser `Origin` header are accepted only from approved origins.
- Tool descriptions and annotations are hints. Clients should still apply their own approval policy.
- The Verifyum resource is read-only and contains no user data.
- The Verifyum MCP endpoint is separate from the AI SENSE MCP endpoint.
- Verifyum anchor input is public and permanent. The source file and private proof data stay local.
- MCP logs contain the JSON-RPC method and tool name, not tool arguments or results.

The endpoint is public because the tools create short-lived records that are
not bound to a user account. What a record holds is reached by the bearer
secret or capability link its create call returned, not by the endpoint being
open. Authentication can be added later for private or account-bound tools.

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

`openai-tools.json` is a separate REST function-calling catalog. It is not the
MCP tool list and its function count and names need not match MCP discovery.

## More documentation

- Website: [aisense.no/free-public-mcp-server](https://aisense.no/free-public-mcp-server)
- REST API reference: [`API.md`](API.md)
- A2A agent card: [aisenseapi.com/.well-known/agent-card.json](https://aisenseapi.com/.well-known/agent-card.json)
- Source and tests: [github.com/aisenseapi/aisense-free-public-rest-apis](https://github.com/aisenseapi/aisense-free-public-rest-apis)
