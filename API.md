# Free Public REST APIs - AI SENSE AS

> **Base URL:** `https://aisenseapi.com/services/v1`
> **Authentication:** None
> **Cost:** Free
> **Rate limit:** 5000 requests per IP per 24 hours

AI agents can also use the remote MCP server at `https://aisenseapi.com/mcp`.
See [`MCP.md`](MCP.md) for its tool list and client examples.

Every response shape below was verified against production. The response key is
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
- [Crypto](#crypto)
- [Common Conventions](#common-conventions)

---

## Reading this document

Two service-wide behaviours matter more than any single endpoint.

**Errors are `{"error": "message"}` with a real HTTP status.** One rule across
the whole surface, uniform since 2026-08-17: 400 is your mistake, 404 is an
unknown id or endpoint, 429 is the rate limit, 500 is our failure, 502 and 504
are an upstream refusing or timing out. Branch on the status or on the `error`
key - both are trustworthy, and the body shape is the same everywhere. A path
that matches no route is a plain 404 with the same error shape. (Before
2026-08-17 most failures arrived as HTTP 200 and unknown paths returned an
unparseable debug echo; clients written against that era keep working, since
every error body is unchanged.)

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

## Crypto

> Wallet generation is for **development and testing only**. A key produced
> by a public HTTP endpoint has crossed a network you do not control. Never fund
> one.

### Wallet generation

| Endpoint | Response keys |
|----------|---------------|
| `GET /solana/generate_new_wallet` | `private_key`, `public_address` |
| `GET /bitcoin/generate_new_wallet` | `private_key`, `private_key_wif`, `public_address` |
| `GET /ethereum/generate_new_wallet` | `private_key`, `public_address` |

Bitcoin returns `public_address`, not `address`. Solana does not return a
`private_key_base58` field.

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

## Common Conventions

### Input formats (POST endpoints)

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
| `/heartbeat` (create) | `ok`, `heartbeat_id`, `status`, timing fields, `ping_url`, `status_url` |
| `/heartbeat/{id}` (read or ping) | `status`, timing fields, `ping_count`, `misses`, `late`, `delivery` when terminal |
| `/lease/namespace` | `ok`, `namespace`, `entropy_bits` |
| `/lease` or `/lease/acquire` | `status`, `owner_token` for the winner, `fencing_token`, expiry fields, completed `result` when reused |
| `/lease/renew`, `/lease/release`, `/lease/complete` | `status`, `fencing_token`, expiry fields, optional `result` |
| `/validate/{type}` | `type`, `valid`, plus per-check fields (`checksum_ok`, `luhn_ok`, ...) |

### TTL - deleted automatically after 24 hours

`/storage` | `/url_shortener` | `/webhook_capture` | `/webhook_action` |
`/agent_wake` | `/webhook_schedule` | `/heartbeat` | `/lease`

Heartbeat terminal records can remain readable for another 24 hours after the
monitor fires, misses or expires. Lease records use a fixed 24-hour absolute
lifecycle that renewals cannot extend.

### Rate limit

**5000 requests per IP per 24 hours.** Exceeding it returns HTTP 429 in the
same flat error shape as everything else:

```json
{ "error": "Too many requests. The limit is 5000 per IP per 24 hours." }
```

### CORS

`Access-Control-Allow-Origin: *` is sent on every `/services/v1/` response, so
these endpoints are callable directly from a browser.
