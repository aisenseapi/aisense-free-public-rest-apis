---
name: free-public-rest-apis
description: "Use this skill whenever the user wants to integrate with, call, test, or learn about the free public REST APIs from AI SENSE AS (aisenseapi.com). Triggers include: requests for current time/datetime/timestamp, random numbers, random colors, passwords, UUIDs, GUIDs, Base64/Base58/Base32 encoding or decoding, JWT encode/decode, QR code generation or decoding, MD5/SHA1/SHA256/SHA512 hashing, CRC32 checksums, ping/health checks, client IP lookup, user agent, IP geolocation/reverse lookup, domain-to-IP resolution, timestamp conversion between unix/ISO/RFC formats, email address validation with MX lookup, hash verification, text slugification, delayed webhook delivery and scheduling, durable Agent Wake tasks for webhooks, human answers or time events, disposable agent email inboxes for verification codes, confirmation links or sign-up mail, heartbeat monitoring for missed agent check-ins, anonymous leases, idempotency claims and fencing tokens, temporary Agent Queue jobs with read/write/worker capabilities, IBAN/card/phone/Norwegian org and account number validation, temporary JSON/text/file storage, URL shortening, webhook capture, webhook action forms for human-in-the-loop approval, or crypto wallet generation and balance lookup (Solana, Bitcoin, Ethereum). Also use when the user asks for a quick utility API without authentication. Do NOT use for paid APIs, account-bound services, or operations requiring persistent storage beyond 24 hours."
license: MIT
---

# Free Public REST APIs - AI SENSE AS

**Base URL:** `https://aisenseapi.com/services/v1`
No account or API key. Queue operations require the role token issued at creation. Hosted by AI SENSE AS, Oslo.

This guide combines source-checked contracts with dated production observations.
Queue deployment has not been verified. Check server discovery before use.

---

## Read this before calling anything

Three service-wide behaviours will bite you if you assume the usual conventions.

**1. The response key is named after the endpoint.** There is no generic `data`
or `result` wrapper. `/md5_hash` returns `md5_hash`. `/ping` returns `ping`.
`/random_color` returns `random_color`. `/health` returns `microtimestamp`, not
`timestamp`. Never guess - the table at the bottom lists every key.

**2. Errors usually use `{"error": "message"}` with a non-2xx HTTP status.**
Check both the status and the `error` field. The legacy wallet-generation
handlers can return an error object with HTTP 200. Workflow endpoints use
non-2xx statuses, including 409 for conflicts and 410 for an expired record
that has not yet been removed. Once removed, the same ID returns 404. Unknown
routes also return 404. Consult each endpoint for its additional errors.

**3. Not everything is JSON.** `base64_decode`, `base58_decode` and
`base32_decode` return `application/octet-stream` unless you send
`Accept: application/json`.

**Rate limit:** 5000 requests per IP per 24 hours, then HTTP 429 in the same
flat error shape.

---

## Agent Queue

Queue is documented for the implementation in this checkout. Check server
availability before use. Production deployment has not been verified.

Create with `POST /queue` and `{}`. Save the returned `queue_id` and separate
`read_token`, `write_token`, `worker_token`. Tokens are issued only at creation.
IDs are 32 lowercase hex characters. Tokens and receipts are 64 lowercase hex.
Every later REST operation requires `Authorization: Bearer TOKEN` with its
role token. Never put credentials in URLs. MCP tools take tokens as arguments.

| REST operation | Token | Body |
| --- | --- | --- |
| `GET /queue/{id}` | Read | None. Returns timing and `counts` |
| `POST /queue/{id}/jobs` | Write | `job_key`, `payload` |
| `GET /queue/{id}/jobs/{job_id}` | Read | None. Returns `job` |
| `POST /queue/{id}/claim` | Worker | Optional `visibility_timeout` |
| `POST /queue/{id}/jobs/{job_id}/ack` | Worker | `receipt` |
| `POST /queue/{id}/jobs/{job_id}/release` | Worker | `receipt` |
| `POST /queue/{id}/jobs/{job_id}/renew` | Worker | `receipt`, optional `visibility_timeout` |

Keys match `^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$`. Payload is any JSON value
up to 16384 encoded bytes, including `null`. Same key and payload returns the
existing job with `deduplicated: true`. Changing that payload returns HTTP 409.
Claims return `job: null` when empty, otherwise a job with its secret `receipt`.
The receipt is disclosed only on claim and is needed for ack, release or renew.
Stale receipts fail with 409. Successful ack can be repeated with its receipt.
Ack takes no result. Visibility accepts integer seconds 30..900, default 60.

All queue state, including payloads, completed/failed jobs and deduplication
entries, expires exactly 24 hours after queue creation. Nothing extends the
returned `expire_timestamp`. There is no TTL parameter. Limits: 100 lifetime
jobs, five claim attempts per job, 20 new queues per client IP per 24 hours.
Jobs can be delivered again after a claim expires or is released. Queue expiry and the attempt limit may leave jobs unfinished. Initial delivery and exactly-once execution are not guaranteed. External
actions must be idempotent. The queue
does not execute jobs, fetch URLs or send callbacks. The Queue service writes payload content to its JSON state files without encrypting it. It normalizes object-key ordering and JSON serialization. Keep secrets and sensitive personal data out of them.

MCP tools: `create_agent_queue`, `read_agent_queue`, `enqueue_agent_queue_job`,
`read_agent_queue_job`, `claim_agent_queue_job`, `ack_agent_queue_job`,
`release_agent_queue_job`, `renew_agent_queue_job`. Use `queue_id` in each
non-create call, plus the matching token name above. Job-specific calls need
`job_id`. See `MCP.md#agent-queue` for full arguments and
`API.md#agent-queue---temporary-work-for-multiple-workers` for response shapes.

## Time

| Endpoint | Returns |
|----------|---------|
| `GET /datetime[/{offset}]` | `{"datetime": "2026-08-16T11:44:35+02:00"}` |
| `GET /timestamp` | `{"timestamp": 1786873261}` |
| `GET /microtimestamp` | `{"microtimestamp": 1786873474.745043}` |
| `GET /timezones[/{offset}]` | `{"timezones": [{"timezone": "Europe/Oslo", "offset": "+0200"}, ...]}` |
| `GET /swatchinternettime` | `{"beat": "@444", "date": "2026-08-16"}` |

`offset` must be **four digits** with an optional sign: `+0200`, `-0530`, `0100`.
An hour-only value like `1` is not a valid route and falls through to the
unknown-path response.

`/timezones` returns objects, not strings. `beat` is a string with a leading `@`.

---

## Random

| Endpoint | Returns |
|----------|---------|
| `GET /random_number[/{from}[/{to}]]` | `{"random_number": 73, "range": {"from": 1, "to": 100}}` |
| `GET /random_color` | `{"random_color": "#9b6bbf"}` |
| `GET /uuid` | `{"uuid": "429151ee-82a1-4438-b2f1-b6b9c9e4a41f"}` |
| `GET /guid` | `{"guid": "..."}` |
| `GET /password[/{length}]` | `{"password": "jFehS]AKGx9wl[jp", "password_length": 16}` |

No arguments to `/random_number` gives 1-6. A **single** argument is the upper
bound, with the lower bound fixed at 1. Passwords default to 12 characters and
include punctuation.

---

## Transform

All POST. Accept JSON, plain text (`Content-Type: text/plain`), or file upload.

### Encoding

| Endpoint | Request | Returns |
|----------|---------|---------|
| `POST /base64_encode` | `{"data": "Hello world"}` | `{"base64_encoded_data": "SGVsbG8gd29ybGQ="}` |
| `POST /base58_encode` | `{"data": "Hello"}` | `{"base58_encoded_data": "9Ajdvzr"}` |
| `POST /base32_encode` | `{"data": "Hello"}` | `{"base32_encoded_data": "JBSWY3DP"}` |

### Decoding

`base64_decode`, `base58_decode` and `base32_decode` all take `{"data": "..."}`
and return **the raw decoded bytes** as `application/octet-stream`.

Send `Accept: application/json` to get a typed envelope instead:

```json
{ "type": "json",   "decoded_data": { "key": "value" } }
{ "type": "binary", "encoding": "base64", "decoded_data": "iVBORw0KGgo..." }
```

An invalid Base58 character returns HTTP 400 with
`{"error": "Invalid Base58 input."}`.

### JWT

```json
// POST /jwt_encode
{ "data": "{\"user\":\"alice\"}", "secret": "my-secret-key" }
-> { "jwt": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." }

// POST /jwt_decode
{ "data": "eyJ0eXAi...", "secret": "my-secret-key" }
-> { "decoded_payload": { "user": "alice" } }
```

`data` takes the claims as a JSON object directly, or as a string containing
JSON - both produce the same token. A string that is not JSON returns 400.
HS256 only.

### QR codes

**The request field is `payload`, with `data` accepted as an alias.**

```json
// POST /qrcode_encode
{ "payload": "https://example.com" }
-> { "qrcode_image": "iVBORw0KGgo...", "image_type": "png" }

// POST /qrcode_decode
{ "payload": "iVBORw0KGgo..." }
-> { "qrcode_content": "https://example.com" }
```

`qrcode_decode` also accepts a file upload in a `qrcode_image` field.

---

## Hash

All POST. Accept JSON, plain text, or file upload. **Each returns a key named
after the algorithm - never `hash`.**

| Endpoint | Response key | Value for `"Hello"` |
|----------|--------------|---------------------|
| `POST /md5_hash` | `md5_hash` | `8b1a9953c4611296a827abf8c47804d7` |
| `POST /sha1_hash` | `sha1_hash` | `f7ff9e8b7bb2e09b70935a5d785e0cc5d9d0abf0` |
| `POST /sha256_hash` | `sha256_hash` | `185f8db32271fe25f561a6fc938b2e26...` |
| `POST /sha512_hash` | `sha512_hash` | `3615f80c9d293ed7402687f94b22d58e...` |
| `POST /crc32_checksum` | `crc32_checksum` | `4157704578` |

`crc32_checksum` is an **integer**, not a hex string.

---

## Web

| Endpoint | Returns |
|----------|---------|
| `GET /ping` | `{"ping": "pong"}` |
| `GET /health` | `{"status": "ok", "microtimestamp": 1786873258.589068}` |
| `GET /client_ip` | `{"ip": "203.0.113.42"}` |
| `GET /user_agent` | `{"user_agent": "curl/8.5.0"}` |
| `GET /domain_ip_lookup/{domain}` | `{"domain": "example.com", "ip": "104.20.23.154"}` |

### IP reverse lookup

`GET /ip_reverse_lookup/{ip}`

```json
{
  "ip": "8.8.8.8",
  "country": "United States",
  "city": null,
  "location": { "lat": "37.751000", "lng": "-97.822000" },
  "place": null,
  "timezone": "America/Chicago"
}
```

`city` and `place` are frequently `null`, and coordinates fall back to the
country centroid when the city is unknown. Latitude and longitude are strings.

### Storage - 24h TTL

`POST /storage` -> `{"storage_id": "...", "expire_timestamp": ...}`
`GET /storage/{storage_id}` -> the stored bytes

The body is stored **verbatim**. Post `{"data": {...}}` and you retrieve
`{"data": {...}}` - no wrapper is added or removed. The response key is
`storage_id`, not `uuid`. An unknown or expired id returns
`{"error": "Storage id unknown"}`.

### URL shortener - 24h TTL

`GET /url_shortener/{url}` -> `{"short_url": "https://307.fi/KtNshX2B", "expire_timestamp": ...}`

The target URL goes inline in the path. This is a GET, not a POST.

### Webhook capture - 24h TTL

`POST /webhook_capture` -> `{"status": "pending", "capture_id": "...", "update_url": "...", "read_url": "...", "wait_url": "...", "expire_timestamp": ...}`

Send any HTTP method to `update_url`, then `GET /webhook_capture/{capture_id}`:

```json
{
  "ok": true,
  "capture_id": "6f8c9e52-...",
  "captured_at_timestamp": 1786873316,
  "captured_at_datetime": "2026-08-16T09:41:56Z",
  "request": {
    "method": "POST",
    "uri": "/services/v1/webhook_capture/6f8c9e52-.../update",
    "headers": { "content-type": "application/json" },
    "client_ip": "203.0.113.10",
    "body": { "json": {...}, "text": null, "base64": null, "raw_length": 28 }
  }
}
```

Use `GET /webhook_capture/{capture_id}/wait/{seconds}` to wait from 0 to 25
seconds for the first request. Add `notify_url` to the create body for one
completion signal. The first inbound request wins, later retries cannot replace
it, and request bodies are capped at 256 KB.

### Webhook action - human-in-the-loop, 24h TTL

The most useful endpoint here for agent work: it pauses an automated pipeline
for a human decision with no backend of your own.

```json
// POST /webhook_action
{
  "title": "Approve deployment?",
  "description": "Optional explanatory text.",
  "fields": [
    {
      "type": "radio", "name": "decision", "label": "Decision", "required": true,
      "options": [
        { "value": "approve", "label": "Approve" },
        { "value": "reject",  "label": "Reject" }
      ]
    },
    { "type": "textarea", "name": "comment", "label": "Notes", "max_length": 500 }
  ]
}

-> {
  "ok": true,
  "action_id": "9e0e6d3b-...",
  "form_url": "https://aisenseapi.com/services/v1/webhook_action/9e0e6d3b-.../form",
  "result_url": "https://aisenseapi.com/services/v1/webhook_action/9e0e6d3b-...",
  "wait_url": "https://aisenseapi.com/services/v1/webhook_action/9e0e6d3b-.../wait/25",
  "expire_timestamp": 1786959912,
  "expire_datetime": "2026-08-17T09:45:12Z"
}
```

Send `form_url` to a human. Poll `GET /webhook_action/{action_id}`:

```json
{
  "ok": true,
  "action_id": "9e0e6d3b-...",
  "status": "pending",
  "created_at_timestamp": 1786873535,
  "created_at_datetime": "2026-08-16T09:45:35Z",
  "expire_timestamp": 1786959935,
  "expire_datetime": "2026-08-17T09:45:35Z",
  "answered_at_timestamp": null,
  "answered_at_datetime": null,
  "response": null
}
```

`status` becomes `answered` and `response` fills with the submission. Field
types: `radio`, `select`, `text`, `textarea`, `checkbox`. `options` accepts
plain strings or `{"value": ..., "label": ...}` objects.

Set `respondents` from 2 to 20 for separate one-use bearer links. The create
response returns `form_urls`. Reads then include `respondents`, `answered`,
`tally` and `responses`, while status moves through `pending`, `partial` and
`answered`. Add `notify_url` for one terminal signal. Use
`GET /webhook_action/{action_id}/wait/{seconds}` to wait for a change for up to
25 seconds.

`GET /webhook_action/{action_id}/form` returns `text/html` - the only
non-JSON-by-default endpoint besides the decoders.

---

### Agent Wake - webhook, human or time, 24h maximum

`POST /agent_wake` creates one durable event task. Send `event_type` as
`webhook`, `human` or `time`. `timeout_seconds` accepts 60 to 86400.

```json
{ "event_type": "webhook", "timeout_seconds": 3600 }
```

The result contains `taskId`, `status`, `ttlMs`, `pollIntervalMs` and metadata
with `statusUrl`. Webhook tasks also return `wakeUrl`. Human tasks return
`formUrl`. Time tasks accept `delay_seconds` or `wake_at`.

Read with `GET /agent_wake/{task_id}`. Cancel with
`DELETE /agent_wake/{task_id}`. The first webhook completes the task and later
requests cannot replace the result. The task ID is a bearer link. Keep secrets
and personal data out of the event body.

Use `GET /agent_wake/{task_id}/wait/{seconds}` to wait from 0 to 25 seconds for
a terminal state. The response adds `waitedSeconds` and `waitReason`.

---

### Agent Inbox - a disposable mail address, 24h maximum

Reach for this when the next step needs an email address the agent controls: a
verification code, a confirmation link, a sign-up mail. Prefer it over asking
the user for a real address for a throwaway flow. Create and read are the whole
surface, so it is for mail arriving at the agent, and it is not a mailbox for
anything that has to outlive the day.

`POST /inbox` takes no arguments and returns the inbox once:

```json
{
  "ok": true,
  "inbox_id": "a85d0bee-f8f7-4be1-a1b3-8d58f3dbdfc7",
  "slug": "ztjqt7n",
  "address": "aisense+ztjqt7n@aisenseapi.com",
  "read_url": "https://aisenseapi.com/services/v1/inbox/a85d0bee-f8f7-4be1-a1b3-8d58f3dbdfc7",
  "wait_url": "https://aisenseapi.com/services/v1/inbox/a85d0bee-f8f7-4be1-a1b3-8d58f3dbdfc7/wait/25",
  "expire_timestamp": 1800086400
}
```

**Two identifiers come back and only one of them is a secret.** The `slug` is
the seven characters `[a-z0-9]` inside the address. It is public by
construction: it travels in mail headers, bounces and sender logs. Knowing it
lets anyone send mail to the inbox. It never lets anyone read the inbox, and it
never appears in a URL. The `inbox_id` is a UUID and the only credential that
reads the inbox. Treat it as a bearer secret, because anyone holding it reads
the mail, and it is returned once, at creation. Guessing the address does not
read the inbox. A wrong `inbox_id` and a missing inbox both answer 404, never
403, so the two are indistinguishable.

Read with `GET /inbox/{inbox_id}`:

```json
{
  "ok": true,
  "slug": "ztjqt7n",
  "address": "aisense+ztjqt7n@aisenseapi.com",
  "received": 1,
  "truncated": false,
  "messages": [
    {
      "from": "noreply@example.com",
      "subject": "Your verification code",
      "date": "2027-01-15T08:00:00Z",
      "text": "Your code is 481516. Confirm at https://example.com/confirm/abc",
      "codes": [ "481516" ],
      "links": [ "https://example.com/confirm/abc" ]
    }
  ],
  "created_at_timestamp": 1800000000,
  "expire_timestamp": 1800086400
}
```

The read response does **not** contain `inbox_id`. The credential is never
echoed back. `GET /inbox/{inbox_id}/wait/{seconds}` waits from 0 to 25 seconds
for a new message and adds `waited_seconds` and `wait_reason` to the same
object. A value above 25 is clamped to 25, the same as every other wait route.

`codes` are standalone 4 to 8 digit numbers. `links` are public http(s) links
only; private-IP and localhost links are dropped. `date` is the time the
service received the message, not the sender's `Date` header, because that
header is sender controlled.

`truncated` is true once a message has been refused, by the message count or
by the total size. A full inbox **refuses new mail
rather than evicting old mail**, so a truncated inbox with no code means the
message was turned away, not lost or still on its way. Both waits, the REST
`/wait/{seconds}` route and the MCP `read_agent_inbox`, watch the flag as well
as the count, so a refusal returns at once instead of running out the clock.

Attachments, raw MIME, arbitrary headers, scripts, styles, private-IP links and
localhost links are stripped before storage. Only the sender address, subject,
received time, cleaned text, codes and public links are kept.

Limits: 20 messages per inbox, 64 KiB of cleaned text per message, 256 KiB per
inbox in total, 50 inboxes per client per UTC day and 5000 active inboxes
service wide. The 24-hour lifetime is fixed and cannot be extended, so read the
code well inside it.

MCP exposes `create_agent_inbox` and `read_agent_inbox`. `read_agent_inbox`
takes `inbox_id` (uuid, required) and `wait_seconds` (integer 0 to 25, default
0).

---

### Heartbeat - fire one action when check-ins stop

Create with `POST /heartbeat`:

```json
{
  "expect_every_seconds": 300,
  "grace_seconds": 60,
  "on_miss": {
    "url": "https://example.com/agent-offline",
    "payload": { "agent": "worker-7" }
  }
}
```

`on_miss` may instead contain `wake_task_id` for an existing, working Agent
Wake webhook task. The response includes a 64-character `heartbeat_id`,
`ping_url`, `status_url`, timing fields and `status: "armed"`.

Check in with `POST /heartbeat/{heartbeat_id}/ping`. Read the state
with `GET /heartbeat/{heartbeat_id}`. A check-in moves the next deadline and
increments `ping_count`. It never extends the fixed 24-hour expiry.

All three of `expect_every_seconds`, `grace_seconds` and `on_miss` are
required; omitting any one is a 400. `expect_every_seconds` accepts 60 to
86400, `grace_seconds` starts at zero, and the two values together cannot
exceed 86400. The status is `armed`, `missed`, `fired` or `expired`. A missed
deadline fires once with no retry.
For a webhook, `delivery.delivered` says whether the target answered with a
2xx status.

The same operations are available through MCP as `create_heartbeat`,
`read_heartbeat` and `ping_heartbeat`.

Webhook URLs may use HTTP or HTTPS on port 80 or 443 and must resolve to a
public address. Private and reserved addresses, redirects, credentials and
fragments are blocked. Treat the heartbeat ID as a bearer secret. The target
is removed at terminal state, which stays readable for up to another 24
hours.

### Lease - one worker wins, later workers reuse the result

Mint a bearer namespace with `POST /lease/namespace` and an empty JSON object.
Then acquire a readable key:

```json
// POST /lease or /lease/acquire
{
  "namespace": "ns_...",
  "key": "invoice:2026-09-05",
  "ttl_seconds": 60,
  "fingerprint": "charge-order-501"
}
```

The first caller gets HTTP 201, `status: "held"`, a secret `owner_token` and
a monotonic `fencing_token`. Another caller gets HTTP 409 while the lease is
held. It can use `retry_after_seconds` or the `Retry-After` header. A
fingerprint mismatch gives `status: "conflict"`.

The winner may call:

- `POST /lease/renew` with namespace, key, owner_token and ttl_seconds
- `POST /lease/release` with namespace, key and owner_token
- `POST /lease/complete` with namespace, key, owner_token and result

An invalid or old owner gets HTTP 409 with `status: "lost"`. Completion keeps
up to 32 KB of JSON. A later acquire with the same key and fingerprint returns
the completed result with HTTP 200. Secret-shaped result fields are stored as
`[redacted]`, but secret values under ordinary field names cannot be detected.

`ttl_seconds` defaults to 60 and accepts 1 to 86400. Renewals stop at the
fixed absolute expiry 24 hours after the first acquisition. Raw namespaces,
keys, owner tokens and fingerprints are not stored. Without a namespace, the
key itself must be a high-entropy ASCII value from 32 to 200 characters.

MCP exposes `create_lease_namespace`, `acquire_lease`, `renew_lease`,
`release_lease` and `complete_lease` for the same flow.

---

## Agent2Agent - a third protocol with four of these capabilities

Everything above is REST. The same service is also on MCP at
`https://aisenseapi.com/mcp`, with schemas published by `tools/list`. This source
version contains 28 tools. Production had 20 when checked on 9 September 2026.
The eight Queue tools are pending deployment verification.

A third protocol runs at its own URL:

```text
POST https://aisenseapi.com/a2a
GET  https://aisenseapi.com/.well-known/agent-card.json
```

It speaks JSON-RPC 2.0 and A2A protocol revision `1.0`, from specification
v1.0.1. The card is a plain GET, because the protocol has no method for
fetching it. No account and no API key, the same as the rest of the service.

**Reach for A2A only when you are already an A2A client, or when the agent
delegating to you is one.** A2A is a protocol for handing work to another
agent, and its Task object earns its place when the work is long-lived,
resumable or waiting on a person. MCP is the richer of the two agent surfaces
and exposes workflow tools with schemas, while A2A carries four creation skills.
REST exposes the utility catalog. Time, UUIDs and short links also have MCP
tools, but hashing, encoding, QR and wallet operations are REST-only. Queue
has REST and MCP interfaces in this source version, not an A2A skill.

Four skills, and they are the same capabilities you already have, not extra
ones:

| A2A skill | MCP tool | REST |
|-----------|----------|------|
| `agent-wake` | `create_agent_wake` | `POST /agent_wake` |
| `human-approval` | `create_human_approval` | `POST /webhook_action` |
| `agent-inbox` | `create_agent_inbox` | `POST /inbox` |
| `webhook-capture` | `create_webhook_capture` | `POST /webhook_capture` |

Each skill runs the same code as its MCP tool, so the arguments, the bounds and
the refusals are identical. There is no read skill. A2A creates the record;
`GetTask` reads an Agent Wake task, and the other three are read with the MCP
read tool or the REST route above.

**Name the skill inside the message.** A2A skills are not addressable: the card
gives each skill an `id`, but no request field in the protocol carries one, and
a skill has no input schema. So this service takes the name from a part
carrying structured data. That convention is this service's own, not something
the protocol defines, which is why looking for a standard field will not turn
one up.

```json
// POST https://aisenseapi.com/a2a
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "SendMessage",
  "params": {
    "message": {
      "messageId": "your-own-id",
      "role": "ROLE_USER",
      "parts": [
        {
          "data": {
            "skill": "human-approval",
            "arguments": {
              "title": "Approve deployment?",
              "options": ["Approve", "Reject"]
            }
          },
          "mediaType": "application/json"
        }
      ]
    }
  }
}
```

`arguments` are the fields of the matching MCP tool. A message with no such
data part is refused with `-32602`. This agent has no language model and will
not read intent out of free text. A bad or missing argument is also `-32602`,
carrying the same message the tool would give.

`agent-wake` answers with a Task, and `GetTask` and `CancelTask` address it by
`id`:

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

States are `TASK_STATE_WORKING`, `TASK_STATE_INPUT_REQUIRED`,
`TASK_STATE_COMPLETED`, `TASK_STATE_FAILED` and `TASK_STATE_CANCELED`, with one
L. The Task carries the ID, a context ID and the state, and nothing more, so
create the task over REST or MCP when you need the wake URL or the form URL.

The other three answer with a Message whose data part is the record the create
call returns, the same JSON as the REST response for that endpoint:

```json
{
  "messageId": "msg-...",
  "role": "ROLE_AGENT",
  "parts": [ { "data": { "ok": true }, "mediaType": "application/json" } ]
}
```

`SendMessage`, `GetTask`, `ListTasks` and `CancelTask` are implemented. The
card declares `streaming` and `pushNotifications` false, so
`SendStreamingMessage` and `SubscribeToTask` answer `-32004` and the four
`TaskPushNotificationConfig` methods answer `-32003`. Those are different
families with different codes, and both are the conforming answer once a
capability is declared false. `GetExtendedAgentCard` answers `-32004` too. Poll
`GetTask` instead of subscribing.

`ListTasks` always returns an empty page:

```json
{ "tasks": [], "nextPageToken": "", "pageSize": 50, "totalSize": 0 }
```

The specification scopes every operation to the authenticated caller, this
service authenticates nobody, and a global list would hand every caller every
task ID, which is the only credential a task has. For the same reason a wrong
ID and an ID that never existed both answer `-32001` and look identical, so do
not read anything into which one you got.

---

## Crypto

> Wallet generation is for **development and testing only**. A private key
> produced by a public HTTP endpoint has crossed a network neither you nor the
> user controls. Never suggest funding one.

| Endpoint | Returns |
|----------|---------|
| `GET /solana/generate_new_wallet` | `{"private_key", "private_key_base58", "public_address"}` |
| `GET /bitcoin/generate_new_wallet` | `{"private_key", "private_key_wif", "public_address"}` |
| `GET /ethereum/generate_new_wallet` | `{"private_key", "public_address"}` |
| `GET /solana/balance/{address}` | `{"wallet", "balance_sol", "balance_lamports"}` |
| `GET /bitcoin/balance/{address}` | `{"wallet", "final_balance_btc", "final_balance_sats"}` |
| `GET /ethereum/balance/{address}` | `{"wallet", "balance_eth", "balance_wei"}` |

Bitcoin returns `public_address`, not `address`. Solana returns both
`private_key` as a JSON-array string and `private_key_base58` as a Base58
encoding of the same 64-byte keypair.

Ethereum returns both balances as **strings**:
`{"balance_eth": "6.634527787345637061", "balance_wei": "6634527787345637061"}`.
Wei routinely exceeds `2^53`, the largest integer a JSON number survives in a
JavaScript client, so a number here would be silently wrong. Bitcoin and Solana
return numbers; their smallest units stay inside the safe range.

---

## Complete response key reference

| Endpoint | Method | Response key(s) |
|----------|--------|-----------------|
| `/datetime[/{offset}]` | GET | `datetime` |
| `/timestamp` | GET | `timestamp` |
| `/microtimestamp` | GET | `microtimestamp` |
| `/timezones[/{offset}]` | GET | `timezones` (array of objects) |
| `/swatchinternettime` | GET | `beat`, `date` |
| `/timestamp_convert` | POST | `input`, `detected`, `timestamp`, `datetime`, `rfc2822`, `utc_datetime` |
| `/random_number[/{from}[/{to}]]` | GET | `random_number`, `range` |
| `/random_color` | GET | `random_color` |
| `/uuid` | GET | `uuid` |
| `/guid` | GET | `guid` |
| `/password[/{length}]` | GET | `password`, `password_length` |
| `/base64_encode` | POST | `base64_encoded_data` |
| `/base58_encode` | POST | `base58_encoded_data` |
| `/base32_encode` | POST | `base32_encoded_data` |
| `/base64_decode` | POST | raw bytes, or `type` + `decoded_data` |
| `/base58_decode` | POST | raw bytes, or `type` + `decoded_data` |
| `/base32_decode` | POST | raw bytes, or `type` + `decoded_data` |
| `/slugify` | POST | `slug` |
| `/jwt_encode` | POST | `jwt` |
| `/jwt_decode` | POST | `decoded_payload` |
| `/qrcode_encode` | POST | `qrcode_image`, `image_type` |
| `/qrcode_decode` | POST | `qrcode_content` |
| `/md5_hash` | POST | `md5_hash` |
| `/sha1_hash` | POST | `sha1_hash` |
| `/sha256_hash` | POST | `sha256_hash` |
| `/sha512_hash` | POST | `sha512_hash` |
| `/crc32_checksum` | POST | `crc32_checksum` (integer) |
| `/hash_verify` | POST | `match`, `algorithm`, `computed` |
| `/ping` | GET | `ping` |
| `/health` | GET | `status`, `microtimestamp` |
| `/client_ip` | GET | `ip` |
| `/user_agent` | GET | `user_agent` |
| `/ip_reverse_lookup/{ip}` | GET | `ip`, `country`, `city`, `location`, `place`, `timezone` |
| `/domain_ip_lookup/{domain}` | GET | `domain`, `ip` |
| `/email_validate` | POST | `email`, `valid_syntax`, `domain`, `has_mx`, `mx_hosts`, `has_address_record` |
| `/storage` | POST | `storage_id`, `expire_timestamp` |
| `/storage/{id}` | GET | the stored body, verbatim |
| `/url_shortener/{url}` | GET | `short_url`, `expire_timestamp` |
| `/webhook_capture` | POST | `capture_id`, update, read and wait URLs, expiry |
| `/webhook_capture/{id}` | GET | pending or captured state, optional wait metadata |
| `/webhook_action` | POST | `action_id`, form URL or URLs, result and wait URLs |
| `/webhook_action/{id}` | GET | single or group answer state, optional wait metadata |
| `/webhook_schedule` | POST | one-shot or recurring schedule and result URLs |
| `/webhook_schedule/{id}` | GET / DELETE | read, wait or cancel schedule state |
| `/agent_wake` | POST | `taskId`, `status`, `ttlMs`, event URLs in `_meta` |
| `/agent_wake/{id}` | GET / DELETE | `status`, `result` or cancellation state |
| `/inbox` | POST | `inbox_id`, `slug`, `address`, `read_url`, `wait_url`, `expire_timestamp` |
| `/inbox/{inbox_id}` | GET | `slug`, `address`, `received`, `truncated`, `messages`, timing fields |
| `/heartbeat` | POST | `heartbeat_id`, `status`, timing fields, `ping_url`, `status_url` |
| `/heartbeat/{id}` | GET | status, timing fields, counters and optional `delivery` |
| `/heartbeat/{id}/ping` | POST | updated status, timing fields and counters |
| `/lease/namespace` | POST | `namespace`, `entropy_bits` |
| `/lease`, `/lease/acquire` | POST | status, owner and fencing tokens, expiry fields, optional completed result |
| `/lease/renew`, `/lease/release`, `/lease/complete` | POST | status, fencing token, expiry fields, optional result |
| `/queue` | POST | `ok`, `queue_id`, creation and expiry timestamps, `counts`, three role tokens |
| `/queue/{id}` | GET | `ok`, `queue_id`, creation and expiry timestamps, `counts` |
| Queue enqueue, job read, claim, ack, release and renew | POST / GET | `ok`, `queue_id`, `expire_timestamp`, `job`. Enqueue adds `deduplicated`. Claim alone returns a receipt |
| `/validate/{type}` | POST | `type`, `valid`, per-check fields |
| `/webhook_action/{id}/form` | GET | `text/html` |
| `/solana/generate_new_wallet` | GET | `private_key`, `private_key_base58`, `public_address` |
| `/bitcoin/generate_new_wallet` | GET | `private_key`, `private_key_wif`, `public_address` |
| `/ethereum/generate_new_wallet` | GET | `private_key`, `public_address` |
| `/solana/balance/{address}` | GET | `wallet`, `balance_sol`, `balance_lamports` |
| `/bitcoin/balance/{address}` | GET | `wallet`, `final_balance_btc`, `final_balance_sats` |
| `/ethereum/balance/{address}` | GET | `wallet`, `balance_eth`, `balance_wei` (strings) |

---

## Input formats for POST endpoints

Check the endpoint before choosing a format. The table summarizes utility
inputs. Queue and structured workflow operations require their documented
JSON fields and do not accept arbitrary plain text or uploads.

| Format | Content-Type | Notes |
|--------|-------------|-------|
| JSON | `application/json` | Field is `data` for most, `payload` for QR |
| Plain text | `text/plain` | JWT endpoints take the secret via an `X-Secret` header |
| File upload | `multipart/form-data` | Field names vary - `jwt_data`, `qrcode_image`, `file` |

## Auto-expiry

`/storage` | `/url_shortener` | `/webhook_capture` | `/webhook_action` |
`/agent_wake` | `/webhook_schedule` | `/inbox` | `/heartbeat` | `/lease` | `/queue`

Active state has a 24-hour ceiling. Heartbeat terminal state and Webhook
Schedule results can remain readable for another 24 hours. Lease renewal
cannot move its fixed absolute expiry. All Queue jobs and deduplication state
expire with the queue, 24 hours after queue creation.

## CORS

`Access-Control-Allow-Origin: *` on every response, so these are callable
directly from browser JavaScript.

---

**AI SENSE AS** | Postboks 1202 Vika, 0110 Oslo, Norway
[aisenseapi.com](https://aisenseapi.com)
