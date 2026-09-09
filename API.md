# Free Public REST APIs - AI SENSE AS

> **Base URL:** `https://aisenseapi.com/services/v1`
> **Authentication:** No account or API key. Queue operations require role-specific bearer tokens
> **Cost:** Free
> **Rate limit:** 5000 requests per IP per 24 hours

This document is the REST reference. The same service answers on two further
protocols: the remote MCP server at `https://aisenseapi.com/mcp`, and Agent2Agent
at `https://aisenseapi.com/a2a`. See [`MCP.md`](MCP.md) for the MCP tool list and
client examples, and [Agent2Agent (A2A)](#agent2agent-a2a) below for the five
task-shaped skills that protocol carries.

This reference combines source-checked contracts with dated production checks.
Queue REST checks and 28-tool MCP discovery were verified in production on 9 September 2026.
The response key is
almost never `data` or `result` - it is usually named after the endpoint
(`/md5_hash` returns `md5_hash`, `/random_color` returns `random_color`). Do not
guess it.

---

## Table of Contents

- [Reading this document](#reading-this-document)
- [Time](#time)
- [Random](#random)
- [Transform](#transform)
- [Hash](#hash)
- [Web](#web)
- [Agent Queue](#agent-queue---temporary-work-for-multiple-workers)
- [Crypto](#crypto)
- [Agent2Agent (A2A)](#agent2agent-a2a)
- [Common Conventions](#common-conventions)

---

## Reading this document

Two service-wide behaviours matter more than any single endpoint.

**Errors usually use `{"error": "message"}` with a non-2xx HTTP status.**
Check both the status and the `error` field. The legacy wallet-generation
handlers can return an error object with HTTP 200. Workflow endpoints use
non-2xx statuses, including 409 for conflicts and 410 for an expired record
that has not yet been removed. Once removed, the same ID returns 404. Unknown
routes also return 404. Consult each endpoint for its additional errors.

**Not everything is JSON.** `base64_decode`, `base58_decode` and `base32_decode`
answer with `application/octet-stream` unless you send `Accept: application/json`.

---

## Time

### `GET /datetime[/{offset}]`
Current date and time in ISO 8601.

`offset` is a **four-digit** UTC offset with an optional sign. `+0200`, `-0530`
and `0100` all work. An hour-only value such as `1` does **not** match the route
and falls through to the unknown-path response.

```
GET /datetime
GET /datetime/+0200
GET /datetime/-0530
GET /datetime/0100
```

```json
{ "datetime": "2026-08-16T11:44:35+02:00" }
```

---

### `GET /timestamp`
```json
{ "timestamp": 1786873261 }
```

---

### `GET /microtimestamp`
```json
{ "microtimestamp": 1786873474.745043 }
```

---

### `GET /timezones[/{offset}]`
All timezones, optionally filtered by a four-digit offset. The list contains
**objects, not strings**.

```json
{
  "timezones": [
    { "timezone": "Africa/Abidjan", "offset": "+0000" },
    { "timezone": "Africa/Blantyre", "offset": "+0200" }
  ]
}
```

---

### `GET /swatchinternettime`
Swatch Internet Time. `beat` is a string with a leading `@`, not a number.

```json
{ "beat": "@444", "date": "2026-08-16" }
```

---

### `POST /timestamp_convert`
One time value in, every representation out. Accepts a unix timestamp in
seconds, a unix timestamp in **milliseconds** (13 digits and up - the format
`Date.now()` produces, and the usual source of dates in the year 56000), an
ISO 8601 or RFC 2822 datetime, or the literal `"now"`. Reports which format it
detected. The optional `offset` uses the same four-digit form as `/datetime`.

Unlike the older endpoints, bad input returns a real **HTTP 400**.

```json
// Request
{ "data": "1700000000123", "offset": "+0100" }

// Response
{
  "input": "1700000000123",
  "detected": "unix_ms",
  "timestamp": 1700000000,
  "datetime": "2023-11-14T23:13:20+01:00",
  "rfc2822": "Tue, 14 Nov 2023 23:13:20 +0100",
  "utc_datetime": "2023-11-14T22:13:20+00:00"
}
```

`detected` is one of `unix`, `unix_ms`, `datetime`, `now`.

---

## Random

### `GET /random_number[/{from}[/{to}]]`
Random integer, inclusive. No arguments gives 1-6. A **single** argument is
treated as the upper bound with the lower bound fixed at 1.

```
GET /random_number          -> 1-6
GET /random_number/30       -> 1-30
GET /random_number/10/20    -> 10-20
GET /random_number/-57/-3   -> -57--3
```

```json
{ "random_number": 73, "range": { "from": 1, "to": 100 } }
```

---

### `GET /random_color`
```json
{ "random_color": "#9b6bbf" }
```

---

### `GET /uuid`
```json
{ "uuid": "429151ee-82a1-4438-b2f1-b6b9c9e4a41f" }
```

---

### `GET /guid`
```json
{ "guid": "750dd9a6-a507-4a89-b4ec-8cd71fc115b7" }
```

---

### `GET /password[/{length}]`
Random password, 12 characters by default. Includes punctuation.

```json
{ "password": "jFehS]AKGx9wl[jp", "password_length": 16 }
```

### `GET /passphrase[/{groups}]`
Pronounceable passphrase, 4 hyphen separated groups by default, 2 to 12
allowed. Groups are built from consonant-vowel syllables, so the result can be
read aloud and retyped from memory. One digit and one symbol are always
included, because the complexity rules that demand them are close to universal.

The argument counts **groups, not characters**. That is why this is a separate
endpoint rather than a style on `/password`, where the same number means a
length.

```json
{ "passphrase": "hudil-rosi4-Zerzo-Coze#", "groups": 4, "length": 23, "entropy_bits": 91.4 }
```

`entropy_bits` is accumulated from the random draws that produced this specific
passphrase, not estimated afterwards from the finished string. Counting
characters would overstate it: `Zerzo` looks like five characters from a large
alphabet and is really four uniform choices from small ones.

It is reported per result rather than per setting, so two calls with the same
group count differ depending on how many syllables drew a closing consonant. The
spread is wider than it looks: at the default of 4 groups the observed range
over 4000 generations was 74.6 to 107.9 bits around a mean of 91.4.

| Groups | Mean | Comparable to |
|--------|------|---------------|
| 2 | 48.9 bits | fine against online guessing, weak against an offline crack |
| 4 (default) | 91.4 bits | a 14 character fully random password |
| 6 | 132.7 bits | past the point where the passphrase is the weak link |
| 12 | 255.6 bits | key material, not something a person retypes |

Those are measured over 4000 generations each, and every one lands within 0.2
bits of what the construction predicts analytically.

Two groups is offered because short passphrases have honest uses, throwaway test
fixtures among them. It is not a sensible choice for a credential that will face
a stolen password database, and the number is on every response so that choice is
never made silently.

---

## Transform

### `POST /base64_encode`
```json
// Request
{ "data": "Hello world" }

// Response
{ "base64_encoded_data": "SGVsbG8gd29ybGQ=" }
```

---

### `POST /base64_decode`
Input: JSON with `data`, or plain text with `Content-Type: text/plain`.

**The response format depends on the `Accept` header.** With no `Accept`, you
get the decoded bytes as `application/octet-stream` - the payload and nothing
else. Send `Accept: application/json` to get a typed envelope instead.

```json
// Request                              Accept: application/json
{ "data": "eyJrZXkiOiJ2YWx1ZSJ9" }

// Response - decoded content was JSON
{ "type": "json", "decoded_data": { "key": "value" } }

// Response - decoded content was not JSON
{ "type": "binary", "encoding": "base64", "decoded_data": "iVBORw0KGgo..." }
```

Set `Accept: application/octet-stream` (or send no `Accept`) to stream the raw
bytes.

---

### `POST /base58_encode`
```json
{ "data": "Hello" } -> { "base58_encoded_data": "9Ajdvzr" }
```

---

### `POST /base58_decode`
Same `Accept` behaviour as `base64_decode`. An invalid Base58 character returns
HTTP 400 with `{"error": "Invalid Base58 input."}`.

```json
{ "data": "9Ajdvzr" } -> Hello
```

---

### `POST /base32_encode`
```json
{ "data": "Hello" } -> { "base32_encoded_data": "JBSWY3DP" }
```

---

### `POST /base32_decode`
Same `Accept` behaviour as `base64_decode`.

```json
{ "data": "JBSWY3DP" } -> Hello
```

---

### `POST /slugify`
Text to URL slug, with Scandinavian letters and common Latin diacritics
transliterated by a fixed table so the same input gives the same slug on every
machine. Characters outside the table are dropped; input that leaves nothing
behind returns **HTTP 400** rather than an empty slug.

```json
{ "data": "Blåbærsyltetøy på Ås!" } -> { "slug": "blabaersyltetoy-pa-as" }
{ "data": "Große Übung" }           -> { "slug": "grosse-ubung" }
```

---

### `POST /jwt_encode`
Encodes a payload into an HS256 JWT.

`data` takes the claims as a **JSON object directly**, or as a string
containing JSON - both forms produce the same token. (Before 2026-08-17 only
the string form was accepted, and passing an object was the most-hit trap on
the surface.) A string that does not parse as JSON returns HTTP 400.

```json
// Request - object form
{ "data": { "user": "alice" }, "secret": "your_secret_key" }

// Request - string form, same token
{ "data": "{\"user\":\"alice\"}", "secret": "your_secret_key" }

// Response
{ "jwt": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyIjoiYWxpY2UifQ..." }
```

Also accepts plain text (`Content-Type: text/plain` plus an `X-Secret` header)
or a file upload (`jwt_data` field, `multipart/form-data`).

---

### `POST /jwt_decode`
```json
// Request
{ "data": "eyJ0eXAiOiJKV1Qi...", "secret": "your_secret_key" }

// Response
{ "decoded_payload": { "user": "alice" } }
```

---

### `POST /qrcode_encode`
Generates a QR code. The request field is `payload`, with `data` accepted as an alias since 2026-08-17.

```json
// Request
{ "payload": "https://aisenseapi.com/" }

// Response
{ "qrcode_image": "iVBORw0KGgoAAAANSUhEUg...", "image_type": "png" }
```

---

### `POST /qrcode_decode`
Accepts a Base64 image in the **`payload`** field, or a file upload
(`qrcode_image` field, `multipart/form-data`).

```json
// Request
{ "payload": "iVBORw0KGgoAAAANSUhEUg..." }

// Response
{ "qrcode_content": "https://aisenseapi.com/" }
```

---

## Hash

All hash endpoints accept JSON (`{"data": "..."}`), plain text
(`Content-Type: text/plain`), or a file upload. **Each returns a key named after
the algorithm - not `hash`.**

| Endpoint | Response key | Example value for `"Hello"` |
|----------|--------------|------------------------------|
| `POST /md5_hash` | `md5_hash` | `8b1a9953c4611296a827abf8c47804d7` |
| `POST /sha1_hash` | `sha1_hash` | `f7ff9e8b7bb2e09b70935a5d785e0cc5d9d0abf0` |
| `POST /sha256_hash` | `sha256_hash` | `185f8db32271fe25f561a6fc938b2e26...` |
| `POST /sha512_hash` | `sha512_hash` | `3615f80c9d293ed7402687f94b22d58e...` |
| `POST /crc32_checksum` | `crc32_checksum` | `4157704578` |

`crc32_checksum` is an **integer**, not a hex string.

```json
// POST /sha256_hash
{ "data": "Hello" }
-> { "sha256_hash": "185f8db32271fe25f561a6fc938b2e264306ec304eda518007d1764826381969" }
```

---

### `POST /hash_verify`
Verify data against a hash from any of the endpoints above. JSON only, since
the hash travels alongside the data. The algorithm is recognized from the hash
itself: an integer means crc32 in the form `/crc32_checksum` returns, and hex
strings are mapped by length - 8 is crc32, 32 md5, 40 sha1, 64 sha256,
128 sha512.

A mismatch is a **result**, not an error, and `computed` is always included so
you can see what the data actually hashes to. Unrecognized hash formats return
**HTTP 400**.

```json
// Request
{ "data": "Hello", "hash": "185f8db32271fe25f561a6fc938b2e264306ec304eda518007d1764826381969" }

// Response
{ "match": true, "algorithm": "sha256", "computed": "185f8db32271fe25f561a6fc..." }

// Integer crc32, straight from /crc32_checksum
{ "data": "Hello", "hash": 4157704578 } -> { "match": true, "algorithm": "crc32", "computed": 4157704578 }
```

---

## Web

### `GET /ping`
```json
{ "ping": "pong" }
```

---

### `GET /health`
The second key is `microtimestamp`, not `timestamp`.

```json
{ "status": "ok", "microtimestamp": 1786873258.589068 }
```

---

### `POST /html2pdf`
Renders HTML into a PDF and stores it for 24 hours. The response carries a
link, not the file: the PDF is fetched in a second request.

The markup goes in `data` or `html` - the two names are interchangeable. An
optional `options` object sets the page up.

```json
// Request
{
  "html": "<h1>Invoice 4817</h1><p>Paid</p>",
  "options": { "page-size": "A5", "orientation": "Landscape", "margin-top": "20mm" }
}

// Response
{
  "storage_id": "1c896e41-d5b7-4017-b888-8381d7866088",
  "storage_url": "https://aisenseapi.com/services/v1/storage/1c896e41-d5b7-4017-b888-8381d7866088",
  "expire_timestamp": 1787257796
}
```

Fetching `storage_url` returns the file with `Content-Type: application/pdf`.

`options` accepts `page-size` (A3, A4, A5, Letter, Legal, Tabloid),
`orientation` (Portrait, Landscape) and `margin-top`, `margin-bottom`,
`margin-left`, `margin-right` (up to three digits, optional mm, cm or in
suffix). Values outside those lists are ignored rather than passed on.

The renderer runs sandboxed with no network access and local file access
disabled, so remote images, stylesheets and fonts referenced in the markup
are not fetched - inline everything the document needs. Empty input returns
HTTP 400; a render failure returns HTTP 500 with the reason.

---

### `GET /client_ip`
```json
{ "ip": "203.0.113.42" }
```

---

### `GET /user_agent`
```json
{ "user_agent": "curl/8.5.0" }
```

---

### `GET /ip_reverse_lookup/{ip}`
`city` and `place` are frequently `null`, and coordinates fall back to the
country centroid when the city is unknown.

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

| Field | Type | Description |
|-------|------|-------------|
| `ip` | string | The address that was looked up |
| `country` | string | Country name |
| `city` | string\|null | City name, often null |
| `location.lat` | string | Latitude, as a string |
| `location.lng` | string | Longitude, as a string |
| `place` | string\|null | More specific place name, usually null |
| `timezone` | string\|null | IANA timezone identifier |

---

### `GET /domain_ip_lookup/{domain}`
```json
{ "domain": "example.com", "ip": "104.20.23.154" }
```

---

### `POST /email_validate`
Syntax check, then DNS. `has_mx` means the domain publishes MX records;
`has_address_record` means it resolves at all, which RFC 5321 allows as a
delivery fallback - so a missing MX alone does not prove an address dead.
Neither proves a mailbox exists; only an SMTP conversation could, and this
endpoint deliberately never opens one.

An address that fails validation is a **result** with `valid_syntax: false`,
not an error. 400 is reserved for sending no input at all. DNS resolution uses
the host resolver only - nothing is sent to any third party. Internationalized
domains are not converted to punycode and report `valid_syntax: false`.

```json
// Request
{ "data": "test@gmail.com" }

// Response
{
  "email": "test@gmail.com",
  "valid_syntax": true,
  "domain": "gmail.com",
  "has_mx": true,
  "mx_hosts": ["gmail-smtp-in.l.google.com", "alt1.gmail-smtp-in.l.google.com"],
  "has_address_record": true
}
```

---

### Storage - 24h TTL

**Store:** `POST /storage` - JSON, plain text, or a file upload.

The request body is stored **verbatim**. Whatever you send is exactly what you
get back; no `data` wrapper is added or removed. Post `{"data": {...}}` and you
retrieve `{"data": {...}}`.

```json
// Request body
{ "key1": "value1" }

// Response
{ "storage_id": "123e4567-e89b-12d3-a456-426614174000", "expire_timestamp": 1738457158 }
```

**Retrieve:** `GET /storage/{storage_id}` - returns the stored bytes with
`application/json` if they parse as JSON, otherwise `application/octet-stream`.
An unknown or expired id returns `{"error": "Storage id unknown"}`.

---

### `GET /url_shortener/{url}` - 24h TTL
The target URL goes inline in the path, unencoded.

```
GET /url_shortener/https://developer.mozilla.org/some/long/path
```

```json
{ "short_url": "https://307.fi/KtNshX2B", "expire_timestamp": 1786959715 }
```

---

### Webhook Capture - 24h TTL

**Create:** `POST /webhook_capture`

The JSON body may be empty. Add `notify_url` when you want one completion
signal sent to a public HTTP or HTTPS URL after the first request arrives.

```json
{
  "ok": true,
  "capture_id": "6f8c9e52-3f2c-4e73-9d3b-8d6c3f6d1c91",
  "status": "pending",
  "update_url": "https://aisenseapi.com/services/v1/webhook_capture/6f8c9e52-.../update",
  "read_url": "https://aisenseapi.com/services/v1/webhook_capture/6f8c9e52-...",
  "wait_url": "https://aisenseapi.com/services/v1/webhook_capture/6f8c9e52-.../wait/25",
  "expire_timestamp": 1772893200
}
```

**Send:** any HTTP method to `update_url`.

**Read:** `GET /webhook_capture/{capture_id}`

**Wait:** `GET /webhook_capture/{capture_id}/wait/{seconds}` where `seconds`
is 0 to 25. The response returns early when the first request is captured and
adds `waited_seconds` and `wait_reason`.

```json
{
  "ok": true,
  "capture_id": "6f8c9e52-3f2c-4e73-9d3b-8d6c3f6d1c91",
  "captured_at_timestamp": 1786873316,
  "captured_at_datetime": "2026-08-16T09:41:56Z",
  "request": {
    "method": "POST",
    "uri": "/services/v1/webhook_capture/6f8c9e52-.../update",
    "headers": { "content-type": "application/json" },
    "client_ip": "203.0.113.10",
    "body": { "json": { "event": "payment.created" }, "text": null, "base64": null, "raw_length": 28 }
  }
}
```

The first request to `update_url` wins. Later retries return the stored first
request and cannot replace it or send a second completion signal. Captured
bodies are capped at 256 KB. An unknown ID returns HTTP 404. An expired capture
returns HTTP 410.

---

### Webhook Action - 24h TTL

**Create:** `POST /webhook_action`

`options` accepts either plain strings or `{"value": ..., "label": ...}`
objects. Field types: `radio`, `select`, `text`, `textarea`, `checkbox`.

```json
// Request
{
  "title": "Approval required",
  "description": "Please review and approve this request.",
  "notify_url": "https://example.com/action-ready",
  "fields": [
    {
      "type": "radio",
      "name": "decision",
      "label": "Select decision",
      "required": true,
      "options": [
        { "value": "approve", "label": "Approve" },
        { "value": "reject", "label": "Reject" }
      ]
    },
    { "type": "textarea", "name": "comment", "label": "Comment", "max_length": 500 }
  ]
}

// Response
{
  "ok": true,
  "action_id": "9e0e6d3b-1a45-44c5-9e0b-92f5f3bdb2f1",
  "form_url": "https://aisenseapi.com/services/v1/webhook_action/9e0e6d3b-.../form",
  "result_url": "https://aisenseapi.com/services/v1/webhook_action/9e0e6d3b-...",
  "wait_url": "https://aisenseapi.com/services/v1/webhook_action/9e0e6d3b-.../wait/25",
  "expire_timestamp": 1786959912,
  "expire_datetime": "2026-08-17T09:45:12Z"
}
```

**Open the form:** `GET /webhook_action/{action_id}/form` - returns `text/html`.

**Poll:** `GET /webhook_action/{action_id}`

**Wait:** `GET /webhook_action/{action_id}/wait/{seconds}` where `seconds` is
0 to 25. The response adds `waited_seconds` and `wait_reason`. A group wait
returns when any new answer changes the state.

```json
// Before submission
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

// After submission
{
  "ok": true,
  "action_id": "9e0e6d3b-...",
  "status": "answered",
  "answered_at_datetime": "2026-08-16T15:13:20Z",
  "response": { "decision": "approve", "comment": "Looks good" }
}
```

Set `respondents` to an integer from 2 to 20 to create separate one-use bearer
links for a group. The create response then returns `form_urls` and no
`form_url`. The group status moves from `pending` to `partial` and then
`answered`. Reads include `respondents`, `answered`, `tally` and `responses`.
The tally counts values from the field named `decision`. Only hashes of the
individual bearer tokens are stored.

When `notify_url` is present, the service sends one small signal after a single
answer or the last group answer. The signal names the action, status and result
URL. It does not contain submitted answers. Create bodies are capped at 64 KB,
with at most 20 fields and 50 options per field.

---

### Webhook Schedule - 24h TTL

POST a URL and a payload with either `delay_seconds` or a `fire_at` Unix
timestamp. Add `every` from 60 to 86400 seconds for a recurring job.

The horizon is **one minute to 24 hours** - this is a 24-hour service, and the
scheduler is no exception. The result stays readable for 24 hours after the
final attempt.

Validation accepts anything from 5 seconds out, but that is the input check, not
the resolution. Delivery runs once a minute, so a job fires at the next whole
minute after it falls due, not at the exact second requested. Measured on
2026-08-21: a job due in 5 seconds was delivered 38 seconds later. Schedule in
minutes and treat anything finer as noise.

**Create:** `POST /webhook_schedule`

```json
// Request
{ "url": "https://example.com/hook", "delay_seconds": 1200, "payload": { "job": 42 } }

// Response
{
  "ok": true,
  "schedule_id": "1f1d7b8b-...",
  "status": "scheduled",
  "fire_at_timestamp": 1786990000,
  "fire_at_datetime": "2026-08-17T15:21:37+00:00",
  "result_url": "https://aisenseapi.com/services/v1/webhook_schedule/1f1d7b8b-...",
  "wait_url": "https://aisenseapi.com/services/v1/webhook_schedule/1f1d7b8b-.../wait/25",
  "expire_timestamp": 1787076400
}
```

**Poll:** `GET /webhook_schedule/{schedule_id}`

**Wait:** `GET /webhook_schedule/{schedule_id}/wait/{seconds}` where `seconds`
is 0 to 25.

**Cancel:** `DELETE /webhook_schedule/{schedule_id}` while it is active.

```json
{
  "ok": true,
  "schedule_id": "1f1d7b8b-...",
  "status": "fired",
  "attempts": 1,
  "http_status": 200,
  "response_excerpt": "...",
  "fired_at_datetime": "2026-08-17T15:21:40+00:00"
}
```

One-shot status may be `scheduled`, `retry`, `fired`, `failed` or `cancelled`.
`fired` means the target answered with some HTTP status, recorded in
`http_status`. It does not mean that the target returned 2xx.
**`fired` means a delivery was attempted, not that it succeeded** - a target that
answers 500 is still `fired` with `http_status: 500`.

A recurring job stays on its original time grid. Missed slots are counted and
skipped rather than delivered late. It normally ends as `completed` after its
fixed 24-hour window. Three consecutive transport failures stop it. A creator
address can cause at most 1440 delivery attempts per 24 hours.

The target must be an `http`/`https` URL on port 80 or 443 that resolves to a
**public** address. Private, loopback, link-local and reserved ranges are
refused, at creation and again at delivery time with the connection pinned to
the vetted address; redirects are never followed. Credentials in the URL are
rejected. Payload maximum 32 KB.

---

### Agent Wake - MCP task or REST polling, up to 24h

Agent Wake creates one durable wait state. It completes when a webhook arrives,
a person answers a hosted form or a selected time is reached. The MCP tool uses
the `io.modelcontextprotocol/tasks` extension. The REST interface exposes the
same task state for scripts and services.

**Create:** `POST /agent_wake`

```jsonc
// Webhook event
{ "event_type": "webhook", "timeout_seconds": 3600 }

// Human response
{
  "event_type": "human",
  "title": "Release build 42?",
  "description": "The checks passed.",
  "options": ["Release", "Hold"],
  "allow_note": true,
  "timeout_seconds": 3600
}

// Time event. Use delay_seconds or wake_at.
{ "event_type": "time", "delay_seconds": 600, "timeout_seconds": 900 }
```

```json
{
  "resultType": "task",
  "taskId": "2eb1a08d-759f-4af9-8caa-8b02b7ca17ba",
  "status": "working",
  "statusMessage": "Waiting for an event.",
  "createdAt": "2026-09-01T12:00:00Z",
  "lastUpdatedAt": "2026-09-01T12:00:00Z",
  "ttlMs": 3600000,
  "pollIntervalMs": 2000,
  "_meta": {
    "com.aisenseapi/agentWake": {
      "eventType": "webhook",
      "statusUrl": "https://aisenseapi.com/services/v1/agent_wake/2eb1a08d-...",
      "wakeUrl": "https://aisenseapi.com/services/v1/agent_wake/2eb1a08d-.../wake",
      "expiresAt": "2026-09-01T13:00:00Z"
    }
  }
}
```

**Wake a webhook task:** `POST`, `PUT` or `PATCH` to
`/agent_wake/{task_id}/wake`. The first accepted request completes the task.
Later requests return HTTP 409 and cannot replace the result. The body limit is
256 KB. Authorization, Cookie, X-API-Key and common token or secret headers are
redacted before storage.

**Read:** `GET /agent_wake/{task_id}`

**Wait:** `GET /agent_wake/{task_id}/wait/{seconds}` where `seconds` is 0 to
25. It returns early at a terminal state and adds `waitedSeconds` and
`waitReason`.

The status is `working`, `input_required`, `completed`, `failed` or `cancelled`.
A completed response includes `result`. A human task includes a `formUrl` and a
URL mode elicitation while it waits. A time task becomes complete on the first
read after its wake time.

**Cancel:** `DELETE /agent_wake/{task_id}`

Task IDs are bearer links and there is no list operation. Anyone holding a task
URL can read its result. Do not send secrets, credentials, personal data or
anything that needs more than 24 hours of retention.

---

### Agent Inbox - receive a verification mail, up to 24h

Agent Inbox gives an agent a disposable mail address of its own, to receive a
verification code, a confirmation link or a sign-up mail. No account and no
API key. An inbox lasts at most 24 hours, and that lifetime is fixed and not
extendable.

**Create:** `POST /inbox`

The route takes no arguments and needs no request body. A create answers
HTTP 201.

```
POST /inbox
```

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

**Two identifiers come back, and only one of them is a secret.** The `slug` is
seven characters from `a-z0-9` and it appears in the address. It is public by
construction: it travels in mail headers, bounces and sender logs. Knowing it
lets anyone send mail to the inbox, and nothing more. It never reads the inbox
and it never appears in a URL. The `inbox_id` is a UUID and is the only
credential that reads the inbox. It is a bearer secret, returned once at
creation, and anyone holding it reads the mail. So guessing the address does
not read the inbox. A wrong `inbox_id` and an inbox that never existed both
answer HTTP 404 and never 403, which leaves the two indistinguishable.

**Read:** `GET /inbox/{inbox_id}`

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

The read response does not contain `inbox_id`. The credential is never echoed
back.

`date` is the time the service received the message, not the sender's `Date`
header, because that header is sender controlled. `codes` are standalone 4 to 8
digit numbers. `links` are public http and https links only; private-IP and
localhost links are dropped.

**Wait:** `GET /inbox/{inbox_id}/wait/{seconds}` where `seconds` is 0 to 25.
It returns the same object with `waited_seconds` and `wait_reason` added.
A value above 25 is clamped to 25, the same as every other wait route on this
surface.

`truncated` is worth knowing about. A full inbox refuses new mail rather than
evicting old mail, so the message you are waiting for can be turned away while
everything that arrived earlier is still sitting there. Either cap does it, the
20 message limit or the 256 KiB total. Nothing else in the response would tell
you, since a refused message simply never appears. `truncated` is what says one
was refused. The long poll watches the flag as well as the count, so a refusal
ends the wait rather than leaving you to sit out the full duration for a message
that is never coming.

**Worked example.** Create the inbox and keep both values.

```
POST /inbox
-> address    aisense+ztjqt7n@aisenseapi.com
   inbox_id   a85d0bee-f8f7-4be1-a1b3-8d58f3dbdfc7
```

Give `address` to the site or person that has to send the mail, and keep
`inbox_id` to yourself. Then hold one connection open until the mail lands.

```
GET /inbox/a85d0bee-f8f7-4be1-a1b3-8d58f3dbdfc7/wait/25
```

The call returns as soon as a message arrives. Take the code from the parsed
field rather than parsing `text` yourself.

```
messages[0].codes[0]   -> "481516"
messages[0].links[0]   -> "https://example.com/confirm/abc"
```

If the call returns with `received` still 0, repeat it until the mail arrives
or `expire_timestamp` passes. A read after that answers HTTP 410, and HTTP 404
once the expired record has been pruned.

Limits, all fixed: 20 messages per inbox, 64 KiB of cleaned text per message,
256 KiB of cleaned text per inbox in total, 50 inboxes per client per UTC day
and 5000 active inboxes service wide.

Attachments, raw MIME, arbitrary headers, scripts, styles, private-IP links and
localhost links are stripped before storage. Only the sender address, subject,
received time, cleaned text, codes and public links are kept.

The `inbox_id` is a bearer secret. Anyone holding it reads every message in the
inbox, so do not use the address for anything that needs a real mailbox, and do
not expect any of it to survive the 24 hours.

---

### Heartbeat - alert when check-ins stop

Heartbeat watches a short-lived process that should keep checking in. Create a
monitor with an expected interval, a grace period and one action to run if the
deadline is missed. The monitor has a fixed 24-hour lifetime.

**Create:** `POST /heartbeat`

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

Use an existing, waiting Agent Wake webhook task instead of an outbound URL:

```json
{
  "expect_every_seconds": 300,
  "grace_seconds": 60,
  "on_miss": { "wake_task_id": "2eb1a08d-759f-4af9-8caa-8b02b7ca17ba" }
}
```

The Agent Wake task must exist, use `event_type: "webhook"` and still be in
the `working` state.

```json
{
  "ok": true,
  "heartbeat_id": "58c85e3e8f739edcb73530d14316f2bfae9ae11bf85374b17e4c9ab75bbec5f1",
  "status": "armed",
  "expect_every_seconds": 300,
  "grace_seconds": 60,
  "expires_at_datetime": "2026-09-06T10:00:00Z",
  "next_expected_at_datetime": "2026-09-05T10:05:00Z",
  "miss_due_at_datetime": "2026-09-05T10:06:00Z",
  "ping_count": 0,
  "misses": 0,
  "late": false,
  "on_miss": { "type": "webhook" },
  "ping_url": "https://aisenseapi.com/services/v1/heartbeat/58c85e3e.../ping",
  "status_url": "https://aisenseapi.com/services/v1/heartbeat/58c85e3e..."
}
```

`expect_every_seconds` must be an integer from 60 to 86400.
`grace_seconds` must be zero or more. Their sum cannot exceed 86400.
An optional webhook payload may be at most 32 KB as JSON.

**Check in:** `POST /heartbeat/{heartbeat_id}/ping`

Each accepted check-in updates `last_ping_at_*`, `next_expected_at_*` and
`miss_due_at_*`, and increases `ping_count`. It does not move
`expires_at_*`. A late, missed or expired heartbeat returns HTTP 409 when
pinged.

**Read:** `GET /heartbeat/{heartbeat_id}`

The status is `armed`, `missed`, `fired` or `expired`. The worker checks once
a minute. When a deadline is missed it claims the action before delivery and
never retries it, so the same miss is not sent twice. `fired` means that a
delivery was attempted. Read `delivery.delivered` and `delivery.http_status`
to see whether a webhook accepted it. A failure before an attempt leaves the
status as `missed` with an honest delivery error.

Webhook targets must use HTTP or HTTPS on port 80 or 443 and resolve to a
public address. Credentials and fragments are refused. DNS is checked again
at delivery, the connection is pinned to the checked address, redirects are
disabled and private, loopback, link-local and reserved ranges are blocked.

The 64-character heartbeat ID is a bearer secret. There is no list operation.
The target URL, payload or Agent Wake task ID is removed when the monitor
becomes terminal. Its terminal status remains readable for up to another 24
hours.

---

### Lease - coordinate workers and reuse completed results

Lease gives several workers one anonymous coordination point. The first
worker to acquire a key gets an owner token and a monotonically increasing
fencing token. Other workers receive HTTP 409 while that lease is held.

For short readable keys, mint a private namespace first:

```http
POST /lease/namespace
Content-Type: application/json

{}
```

```json
{
  "ok": true,
  "namespace": "ns_XbO8a6V9e5dMWYqghfPV3ykHTNpR3oZ0fQJm4l7K2nE",
  "entropy_bits": 256
}
```

Treat the namespace as a bearer secret. Without a namespace, `key` itself
must be a high-entropy ASCII value from 32 to 200 characters.

**Acquire:** `POST /lease` or `POST /lease/acquire`

```json
{
  "namespace": "ns_XbO8a6V9e5dMWYqghfPV3ykHTNpR3oZ0fQJm4l7K2nE",
  "key": "invoice:2026-09-05",
  "ttl_seconds": 60,
  "fingerprint": "charge-order-501"
}
```

```json
{
  "ok": true,
  "status": "held",
  "owner_token": "own_lCzWFx9BTqNkKlQJYu8jXdDX7n8h4xTJsU5BzPq3yLk",
  "ttl_seconds": 60,
  "fencing_token": 184,
  "lease_expires_at_timestamp": 1788602460,
  "lease_expires_at": "2026-09-05T10:01:00Z",
  "absolute_expires_at_timestamp": 1788688800,
  "absolute_expires_at": "2026-09-06T10:00:00Z"
}
```

`ttl_seconds` is optional, defaults to 60 and accepts 1 to 86400. A held
lease returns HTTP 409, `status: "held"`, `retry_after_seconds` and a matching
`Retry-After` header. A different fingerprint on the same key returns HTTP
409 with `status: "conflict"`. Use a stable fingerprint when the key must
represent the same input or job.

The owner can change the lease with these POST endpoints:

```json
// POST /lease/renew
{ "namespace": "ns_...", "key": "invoice:2026-09-05", "owner_token": "own_...", "ttl_seconds": 120 }

// POST /lease/release
{ "namespace": "ns_...", "key": "invoice:2026-09-05", "owner_token": "own_..." }

// POST /lease/complete
{ "namespace": "ns_...", "key": "invoice:2026-09-05", "owner_token": "own_...", "result": { "receipt_id": 4817 } }
```

Renew keeps the same fencing token. Release makes the key available at once.
Complete stores up to 32 KB of JSON and changes the status to `completed`.
The next acquire with the same key and fingerprint returns HTTP 200 with that
result and no owner token. Fields with names such as `authorization`,
`password`, `secret`, `token`, `private_key` and `api_key` are replaced with
`[redacted]` before a result is stored. Secrets hidden inside ordinary values
cannot be detected, so keep them out of the result.

An invalid, expired or old owner token receives HTTP 409 with
`status: "lost"`. Send the fencing token to any protected system and reject
writes carrying an older value. This closes the gap where a paused worker
wakes after its lease has been taken over.

Every key lifecycle has a fixed 24-hour absolute expiry. Renewing a lease
cannot extend that boundary. A new acquisition after it starts a new
lifecycle with a higher fencing token. Raw keys, namespaces, owner tokens and
fingerprints are not written to disk. Their hashes and the optional completed
result remain until the absolute expiry.

---

### Validate

Business-number validation by arithmetic. `POST /validate/{type}` where type is
`iban`, `card`, `orgnr`, `kontonummer` or `phone`.

Everything is checked locally - nothing is looked up in any register - so
`valid: true` means **well-formed with a correct check digit**, not that the
account or number exists. An invalid value is a result with `valid: false` and
the failing check named, never an error.

```json
// POST /validate/iban
{ "data": "NO9386011117947" }
-> { "type": "iban", "valid": true, "normalized": "NO9386011117947", "country": "NO",
     "structure_ok": true, "length_ok": true, "checksum_ok": true }

// POST /validate/card  (Luhn; the number is never echoed back)
{ "data": "4111 1111 1111 1111" } -> { "type": "card", "valid": true, "length": 16, ... }

// POST /validate/orgnr  (Norwegian organisasjonsnummer, MOD11)
{ "data": "NO 922 601 151 MVA" } -> { "type": "orgnr", "valid": true, "normalized": "922601151", ... }

// POST /validate/kontonummer  (Norwegian bank account, MOD11)
{ "data": "1234.56.78903" } -> { "type": "kontonummer", "valid": true, ... }

// POST /validate/phone  (E.164 shape only)
{ "data": "004740000000" } -> { "type": "phone", "valid": true, "e164": "+4740000000", ... }
```

IBAN uses the authoritative ISO 13616 mod-97 check; `length_ok` is `null` for
countries outside the built-in length table, where the length cannot be
confirmed but the checksum still can. An unknown `{type}` returns HTTP 400.

---

### Agent Queue - temporary work for multiple workers

Agent Queue lets a producer enqueue JSON jobs and workers claim them for a short
visibility window. Queue REST checks and 28-tool MCP discovery were verified in production on 9 September 2026.
See [AGENT-QUICKSTART.md](AGENT-QUICKSTART.md) for an executable workflow.

**Create:** `POST /queue` with no parameters (an empty JSON object is accepted).
HTTP 201 returns:

```json
{
  "ok": true,
  "queue_id": "0123456789abcdef0123456789abcdef",
  "created_at_timestamp": 1788948000,
  "expire_timestamp": 1789034400,
  "read_token": "<64 lowercase hex characters>",
  "write_token": "<64 lowercase hex characters>",
  "worker_token": "<64 lowercase hex characters>",
  "counts": { "pending": 0, "claimed": 0, "completed": 0, "failed": 0, "total": 0 }
}
```

Values above are placeholders. Save all three tokens from this response: they
are issued only at creation. Queue and job IDs are 32 lowercase hex characters.
Tokens and claim receipts are 64 lowercase hex characters. The queue ID is not
a credential. Each later REST request requires `Authorization: Bearer TOKEN`
with the token for that operation. Never put credentials in paths or query strings.

| Method and path | Bearer token | JSON body |
| --- | --- | --- |
| `GET /queue/{queue_id}` | `read_token` | None |
| `POST /queue/{queue_id}/jobs` | `write_token` | `job_key`, `payload` |
| `GET /queue/{queue_id}/jobs/{job_id}` | `read_token` | None |
| `POST /queue/{queue_id}/claim` | `worker_token` | Optional `visibility_timeout` |
| `POST /queue/{queue_id}/jobs/{job_id}/ack` | `worker_token` | `receipt` |
| `POST /queue/{queue_id}/jobs/{job_id}/release` | `worker_token` | `receipt` |
| `POST /queue/{queue_id}/jobs/{job_id}/renew` | `worker_token` | `receipt`, optional `visibility_timeout` |

**Enqueue:** A producer submits a stable key and a JSON value. The key must
match `^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$`. Payload may be any JSON value,
including `null`, up to 16 KiB (16384 bytes) when encoded.

```bash
curl -X POST https://aisenseapi.com/services/v1/queue/QUEUE_ID/jobs \
  -H "Authorization: Bearer WRITE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"job_key":"report:42","payload":{"report_id":42}}'
```

Replace uppercase placeholders with the creation response values. A new job
returns HTTP 201 and `deduplicated: false`. Sending the same key and payload
again returns the existing job with HTTP 200 and `deduplicated: true`. Changing
the payload for that key returns HTTP 409. Deduplication lasts until the queue
expires, including completed and failed jobs.

**Claim:** `POST /queue/{queue_id}/claim` accepts an integer
`visibility_timeout` from 30 to 900 seconds, default 60. When no job is
available, it returns HTTP 200 with `job: null`. Otherwise it returns:

```json
{
  "ok": true,
  "queue_id": "0123456789abcdef0123456789abcdef",
  "expire_timestamp": 1789034400,
  "job": {
    "job_id": "abcdef0123456789abcdef0123456789",
    "job_key": "report:42",
    "payload": { "report_id": 42 },
    "status": "claimed",
    "attempts": 1,
    "created_at_timestamp": 1788948000,
    "expire_timestamp": 1789034400,
    "claimed_until_timestamp": 1788948060,
    "receipt": "<64 lowercase hex characters>"
  }
}
```

The receipt identifies this claim attempt and appears only in the claim
response. Retain it until the attempt finishes. Job reads, enqueue, ack,
release and renew return the same job envelope without a receipt. A queue
read returns creation and expiry timestamps and the five counts above, without
tokens or a job listing.

**Finish or retry:** Send `{"receipt":"RECEIPT"}` with the worker token to
`ack` after the work succeeds, or to `release` to make it available again.
`renew` accepts the same receipt and an optional `visibility_timeout` and
extends the current visibility window within the queue lifetime. It does not
create another claim attempt. No result or callback URL is accepted by ack.

An expired or superseded receipt returns HTTP 409. Repeating a successful ack
with its receipt is idempotent. Job states are `pending`, `claimed`,
`completed` and `failed`. A claim increments `attempts`. An unacknowledged job
becomes available when its visibility window ends. After five unsuccessful
attempts it becomes `failed` and cannot be claimed again.

Jobs can be delivered again after a claim expires or is released. Queue expiry and the attempt limit may leave jobs unfinished. Initial delivery and exactly-once execution are not guaranteed. A worker can finish an external action and lose its claim before ack,
so another worker may repeat the action. Make side effects idempotent using
the job key or ID.

**Fixed lifetime and limits:** The queue expires exactly 86400 seconds after
creation. Every job, completed record, failed record and deduplication entry
shares that boundary. Enqueue, claim, read, ack, release and renew never move
`expire_timestamp`. There is no expiry or TTL option. No claim can extend
past that timestamp. Expired state becomes unavailable and is cleaned up.

| HTTP status | Queue error |
| --- | --- |
| `400` | Invalid JSON, fields or values. Query parameters are not accepted |
| `401` | Missing or malformed Authorization bearer header |
| `403` | Token is invalid or does not grant the required role |
| `404` | Unknown queue, job or route. Also returned after expired state is cleaned up |
| `405` | Wrong method for the route |
| `409` | Job key conflict, 100-job lifetime capacity reached, or stale claim receipt |
| `410` | Queue expired and its record has not yet been cleaned up |
| `413` | Payload exceeds 16 KiB, enqueue request exceeds 32 KiB, or another request body exceeds 1 KiB |
| `415` | A nonempty POST body did not use `application/json` |
| `429` | Queue creation quota or shared request limit reached |
| `503` | Storage or queue lock unavailable. Stop after an uncertain claim response. Use bounded backoff only for repeat-safe operations |

Queue errors use `{"error":"message"}`. Ordinary reads and successful empty
claims return HTTP 200. Preflight requests use `OPTIONS` and return HTTP 204.

A lost, malformed or 503 claim reply can follow a successful reservation. Do
not blindly claim again when its receipt is unknown. Creation replies can
also be uncertain, and creation-only tokens cannot be recovered. Reads, an
enqueue with the same key and unchanged payload, and an acknowledgement with
the same winning receipt can be repeated within their lifetime. See the
[quickstart retry table](AGENT-QUICKSTART.md#handle-retries-deliberately).

- At most 100 distinct jobs over the entire queue lifetime. Completed and
  failed jobs still count. Idempotent enqueue retries do not add a job.
- At most five claim attempts per job and 16 KiB of encoded JSON per payload.
- At most 20 new queues per client IP per 24 hours, within the shared request limit.

Share the write token with producers, the worker token with workers, and the
read token with observers. Workers necessarily receive job payloads when
claiming. Tokens grant capabilities without verifying a person's identity.
The Queue service writes payload content to its JSON state files without encrypting it. It normalizes object-key ordering and JSON serialization. Keep credentials and sensitive personal data
out of them. Queue processing does not fetch payload URLs, execute jobs,
make callbacks or contact outside services. Your workers perform the work.

The eight MCP equivalents and their argument names are listed in
[`MCP.md`](MCP.md#agent-queue).
The standalone machine-readable Queue contract is
[`queue-openapi.json`](queue-openapi.json). It does not describe other endpoints.

---

## Crypto

> Wallet generation is for **development and testing only**. A key produced
> by a public HTTP endpoint has crossed a network you do not control. Never fund
> one.

### Wallet generation

| Endpoint | Response keys |
|----------|---------------|
| `GET /solana/generate_new_wallet` | `private_key`, `private_key_base58`, `public_address` |
| `GET /bitcoin/generate_new_wallet` | `private_key`, `private_key_wif`, `public_address` |
| `GET /ethereum/generate_new_wallet` | `private_key`, `public_address` |

Bitcoin returns `public_address`, not `address`. Solana returns both
`private_key` as a JSON-array string and `private_key_base58` as a Base58
encoding of the same 64-byte keypair.

### Balance lookup

```json
// GET /bitcoin/balance/{address}
{ "wallet": "1A1zP1...", "final_balance_btc": 107.36719456, "final_balance_sats": 10736719456 }

// GET /solana/balance/{address}
{ "wallet": "So1111...", "balance_sol": 1694.799038633, "balance_lamports": 1694799038633 }

// GET /ethereum/balance/{address}
{ "wallet": "0xd8dA...", "balance_eth": "6.634527787345637061", "balance_wei": "6634527787345637061" }
```

Ethereum returns its two balance fields as **strings**. Wei routinely exceeds
`2^53`, which is the largest integer a JSON number survives in a JavaScript
client, so a number here would be silently wrong. Bitcoin and Solana return
numbers; their smallest units stay well inside the safe range.

---

## Agent2Agent (A2A)

A2A is a protocol for handing work to another agent and following it to
completion. MCP is the protocol for exposing tools. Almost everything on this
page is a tool, so only five capabilities are offered over A2A: the ones where a
long-lived, resumable, human-in-the-loop task is the interesting object, and
where MCP needed an extension to express what A2A has in core.

**MCP is the broader workflow surface.** It publishes schemas through tool
discovery. A2A carries five creation skills, Queue among them. REST
carries the full utility catalog. Only selected capabilities, including time
and UUIDs, also have MCP tools. Hashing, encoding, QR and wallet operations
remain REST-only. See `MCP.md` for the source and deployed tool counts.

**Endpoint:** `POST https://aisenseapi.com/a2a`. JSON-RPC 2.0, protocol revision
`1.0` (specification v1.0.1). No account and no API key, same as everything else
here. Bodies are capped at 256 KB. A protocol error is still HTTP 200 with the
error inside the JSON-RPC envelope; only the transport refuses with a status of
its own, 405 for any method other than POST and 413 for an oversized body.
Batches work. A notification, meaning a request with no `id`, is answered with
HTTP 204 and no body.

**Agent card:** `GET https://aisenseapi.com/.well-known/agent-card.json`. A plain
GET rather than a JSON-RPC method, because the protocol has no method for
fetching the public card. It is cacheable for an hour and carries an ETag. The
endpoint address lives in `supportedInterfaces`, not in a top-level `url`, and
`capabilities` declares `streaming: false`, `pushNotifications: false` and
`extendedAgentCard: false`.

### Naming a skill is a convention here, not a standard field

A2A skills are not addressable. There is no skill id anywhere on the wire and no
`inputSchema` on a skill, so nothing in the protocol says which of the advertised
skills a message is asking for. Look for a standard field and you will not find
one. This service reads the skill from a part carrying structured data:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "SendMessage",
  "params": {
    "message": {
      "messageId": "m1",
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

That shape is documented here and nowhere in the specification. A message with
no such data part is refused with `-32602`: this agent has no language model and
does not interpret free text. An unknown skill id is refused with `-32602` too.
`arguments` are the arguments of the matching MCP tool, checked by the same code,
so bounds and refusals are identical on both surfaces.

### The five skills

| Skill id | Creates | Answers with |
|----------|---------|--------------|
| `agent-wake` | a durable wait for a webhook, a person or a chosen time | a Task |
| `human-approval` | a hosted decision form, for one person or up to 20 | a Message |
| `agent-inbox` | a disposable mail address | a Message |
| `webhook-capture` | a URL that records the first request sent to it | a Message |
| `agent-queue` | a shared pull queue with read, write and worker tokens | a Message |

Each lasts at most 24 hours, the same limit as everywhere else on this service.

`agent-wake` answers with an A2A Task:

```json
{
  "id": "c450a722-cfff-4e81-955b-a4baa566a458",
  "contextId": "c450a722-cfff-4e81-955b-a4baa566a458",
  "status": { "state": "TASK_STATE_WORKING", "timestamp": "2026-09-06T17:11:18Z" }
}
```

The states are `TASK_STATE_WORKING`, `TASK_STATE_INPUT_REQUIRED`,
`TASK_STATE_COMPLETED`, `TASK_STATE_FAILED` and `TASK_STATE_CANCELED`. Note the
single L in `CANCELED`; the REST status for the same task is spelled `cancelled`.
An interrupted task puts the thing a person has to act on, such as a form URL, in
`status.update`.

The other three answer with a Message carrying the created resource:

```json
{
  "messageId": "msg-57925ef67c5f0f8e",
  "role": "ROLE_AGENT",
  "parts": [
    {
      "data": {
        "ok": true,
        "action_id": "f959a9b7-6f92-4f09-8e60-98d452f723b6",
        "status": "pending",
        "form_url": "https://aisenseapi.com/services/v1/webhook_action/f959a9b7-.../form",
        "result_url": "https://aisenseapi.com/services/v1/webhook_action/f959a9b7-...",
        "wait_url": "https://aisenseapi.com/services/v1/webhook_action/f959a9b7-.../wait/25"
      },
      "mediaType": "application/json"
    }
  ]
}
```

Those three create the resource and stop there. Reading a captured request, the
mail in an inbox or a submitted form is not an A2A operation: follow the
`read_url`, `result_url` and `wait_url` in the reply, which are the REST
endpoints documented above, or call the matching MCP tool.

### Methods

Method names are PascalCase, not the slash names from revision 0.x.

| Method | Result |
|--------|--------|
| `SendMessage` | implemented |
| `GetTask` | implemented |
| `CancelTask` | implemented |
| `ListTasks` | implemented, always an empty page |
| `SendStreamingMessage`, `SubscribeToTask` | `-32004` |
| `CreateTaskPushNotificationConfig`, `GetTaskPushNotificationConfig`, `ListTaskPushNotificationConfigs`, `DeleteTaskPushNotificationConfig` | `-32003` |
| `GetExtendedAgentCard` | `-32004` |

The declined methods are not gaps. Once a card declares a capability false,
returning these errors is the conforming behaviour the specification asks for.
**The two families use different codes and are not interchangeable:** streaming
and the extended card answer `-32004`, push notification configuration answers
`-32003`. A client that folds them into one error reports the wrong cause.

`GetTask` and `CancelTask` take the task id in `params.id`, and `params.taskId`
is accepted as well. They address Agent Wake tasks, the only task store this
service has. `CancelTask` returns the task in its new state.

**`ListTasks` always returns an empty page.**

```json
{ "tasks": [], "nextPageToken": "", "pageSize": 50, "totalSize": 0 }
```

The specification requires every operation to scope its results to the
authenticated caller. This service authenticates nobody, so there is no principal
to scope to, and a global list would hand every caller every task id. Those ids
are the only credential there is. An empty page is the conservative reading, not
an unfinished feature. Keep your own task ids.

### Error codes

| Code | Meaning |
|------|---------|
| `-32700` | Parse error. The body was not JSON. |
| `-32600` | Invalid Request. `jsonrpc` was not `"2.0"`, or the envelope was unusable. |
| `-32601` | Method not found. |
| `-32602` | Invalid params. No data part naming a skill, an unknown skill id, a missing task id, or arguments the underlying tool refused. |
| `-32001` | Task not found. |
| `-32003` | Push notification configuration is not supported. |
| `-32004` | Streaming, or the extended card, is not supported. |
| `-32603` | Internal error. |

A wrong task id and a task that never existed both answer `-32001`, with the same
message. Nothing distinguishes them, because the id is the credential and telling
them apart would turn the endpoint into a lookup oracle for task ids.

---

## Common Conventions

### Input formats (POST endpoints)

Formats vary by endpoint. This table summarizes utility inputs, not a promise
that every endpoint accepts every format. Queue and structured workflow
operations use JSON with the fields documented in their own sections.

| Format | Content-Type | Notes |
|--------|-------------|-------|
| JSON | `application/json` | Field name varies - `data` for most, `payload` for QR |
| Plain text | `text/plain` | Pass the secret via `X-Secret` for JWT endpoints |
| File upload | `multipart/form-data` | Field names vary by endpoint |

### Response keys, in full

| Endpoint | Response key(s) |
|----------|-----------------|
| `/datetime` | `datetime` |
| `/timestamp` | `timestamp` |
| `/microtimestamp` | `microtimestamp` |
| `/timezones` | `timezones` (array of objects) |
| `/swatchinternettime` | `beat`, `date` |
| `/timestamp_convert` | `input`, `detected`, `timestamp`, `datetime`, `rfc2822`, `utc_datetime` |
| `/random_number` | `random_number`, `range` |
| `/random_color` | `random_color` |
| `/uuid` | `uuid` |
| `/guid` | `guid` |
| `/password` | `password`, `password_length` |
| `/base64_encode` | `base64_encoded_data` |
| `/base58_encode` | `base58_encoded_data` |
| `/base32_encode` | `base32_encoded_data` |
| `/base64_decode`, `/base58_decode`, `/base32_decode` | raw bytes, or `type` + `decoded_data` with `Accept: application/json` |
| `/jwt_encode` | `jwt` |
| `/jwt_decode` | `decoded_payload` |
| `/qrcode_encode` | `qrcode_image`, `image_type` |
| `/qrcode_decode` | `qrcode_content` |
| `/md5_hash` | `md5_hash` |
| `/sha1_hash` | `sha1_hash` |
| `/sha256_hash` | `sha256_hash` |
| `/sha512_hash` | `sha512_hash` |
| `/crc32_checksum` | `crc32_checksum` (integer) |
| `/ping` | `ping` |
| `/health` | `status`, `microtimestamp` |
| `/client_ip` | `ip` |
| `/html2pdf` | `storage_id`, `storage_url`, `expire_timestamp` |
| `/user_agent` | `user_agent` |
| `/ip_reverse_lookup` | `ip`, `country`, `city`, `location`, `place`, `timezone` |
| `/domain_ip_lookup` | `domain`, `ip` |
| `/email_validate` | `email`, `valid_syntax`, `domain`, `has_mx`, `mx_hosts`, `has_address_record` |
| `/hash_verify` | `match`, `algorithm`, `computed` |
| `/slugify` | `slug` |
| `/storage` (store) | `storage_id`, `expire_timestamp` |
| `/url_shortener` | `short_url`, `expire_timestamp` |
| `/webhook_capture` (create) | `ok`, `capture_id`, `update_url`, `read_url`, `expire_timestamp` |
| `/webhook_action` (create) | `ok`, `action_id`, `form_url`, `result_url`, `expire_timestamp`, `expire_datetime` |
| `/webhook_schedule` (create) | `ok`, `schedule_id`, `status`, `fire_at_timestamp`, `result_url`, `expire_timestamp` |
| `/webhook_schedule/{id}` (poll) | `ok`, `schedule_id`, `status`, `attempts`, `http_status`, `response_excerpt` |
| `/agent_wake` (create) | `taskId`, `status`, `ttlMs`, event URLs in `_meta` |
| `/agent_wake/{id}` (read or cancel) | `status`, `result` or cancellation state |
| `/inbox` (create) | `ok`, `inbox_id`, `slug`, `address`, `read_url`, `wait_url`, `expire_timestamp` |
| `/inbox/{id}` (read or wait) | `ok`, `slug`, `address`, `received`, `truncated`, `messages`, `created_at_timestamp`, `expire_timestamp` |
| `/heartbeat` (create) | `ok`, `heartbeat_id`, `status`, timing fields, `ping_url`, `status_url` |
| `/heartbeat/{id}` (read or ping) | `status`, timing fields, `ping_count`, `misses`, `late`, `delivery` when terminal |
| `/lease/namespace` | `ok`, `namespace`, `entropy_bits` |
| `/lease` or `/lease/acquire` | `status`, `owner_token` for the winner, `fencing_token`, expiry fields, completed `result` when reused |
| `/lease/renew`, `/lease/release`, `/lease/complete` | `status`, `fencing_token`, expiry fields, optional `result` |
| `/queue` (create) | `ok`, `queue_id`, creation and expiry timestamps, `counts`, three role tokens |
| `/queue/{id}` (read) | `ok`, `queue_id`, creation and expiry timestamps, `counts` |
| Queue enqueue, job read, claim, ack, release and renew | `ok`, `queue_id`, `expire_timestamp`, `job`. Enqueue adds `deduplicated`. Claim alone returns a receipt |
| `/validate/{type}` | `type`, `valid`, plus per-check fields (`checksum_ok`, `luhn_ok`, ...) |

### Active lifetimes and retained results

Storage, short links, captures, approvals, Agent Wake, Inbox, Heartbeat, Lease
and Queue have active lifetimes of at most 24 hours. Agent Wake can use a
shorter timeout. Lease expiry is fixed at first acquisition. Queue expiry is
fixed at creation and covers all jobs and deduplication state. Activity cannot
extend either deadline.

Webhook Schedule can schedule work within a 24-hour horizon and retain its
final result for up to another 24 hours. Heartbeat terminal timing and
delivery records can also remain readable for another 24 hours. API expiry
and later scheduled physical cleanup are distinct.

### Rate limit

The shared counter resets at server midnight through the deployed reset job.
This is a calendar-day budget, not a rolling per-request 24-hour window.
Queue creation has a separate fixed 24-hour quota window.


**5000 requests per IP per 24 hours.** Exceeding it returns HTTP 429 in the
same flat error shape as everything else:

```json
{ "error": "Too many requests. The limit is 5000 per IP per 24 hours." }
```

### CORS

`Access-Control-Allow-Origin: *` is sent on every `/services/v1/` response, so
these endpoints are callable directly from a browser.
