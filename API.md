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

```json
{
  "ok": true,
  "capture_id": "6f8c9e52-3f2c-4e73-9d3b-8d6c3f6d1c91",
  "update_url": "https://aisenseapi.com/services/v1/webhook_capture/6f8c9e52-.../update",
  "read_url": "https://aisenseapi.com/services/v1/webhook_capture/6f8c9e52-...",
  "expire_timestamp": 1772893200
}
```

**Send:** any HTTP method to `update_url`.

**Read:** `GET /webhook_capture/{capture_id}`

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
  "expire_timestamp": 1786959912,
  "expire_datetime": "2026-08-17T09:45:12Z"
}
```

**Open the form:** `GET /webhook_action/{action_id}/form` - returns `text/html`.

**Poll:** `GET /webhook_action/{action_id}`

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

---

### Webhook Schedule - 24h TTL

The timer an agent does not have. POST a URL and a payload with either
`delay_seconds` or a `fire_at` unix timestamp, and the service POSTs the payload
to that URL at that time, with one retry on transport failure.

The horizon is **5 seconds to 24 hours** - this is a 24-hour service, and the
scheduler is no exception. The result stays readable for 24 hours after the
final attempt.

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
  "expire_timestamp": 1787076400
}
```

**Poll:** `GET /webhook_schedule/{schedule_id}`

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

`status` moves `scheduled` -> `fired` (the target answered with any HTTP status,
recorded in `http_status`) or `failed` (no response after the retry).
**`fired` means a delivery was attempted, not that it succeeded** - a target that
answers 500 is still `fired` with `http_status: 500`.

The target must be an `http`/`https` URL on port 80 or 443 that resolves to a
**public** address. Private, loopback, link-local and reserved ranges are
refused, at creation and again at delivery time with the connection pinned to
the vetted address; redirects are never followed. Credentials in the URL are
rejected. Payload maximum 32 KB.

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
| `/validate/{type}` | `type`, `valid`, plus per-check fields (`checksum_ok`, `luhn_ok`, ...) |

### TTL - deleted automatically after 24 hours

`/storage` | `/url_shortener` | `/webhook_capture` | `/webhook_action`

### Rate limit

**5000 requests per IP per 24 hours.** Exceeding it returns HTTP 429 in the
same flat error shape as everything else:

```json
{ "error": "Too many requests. The limit is 5000 per IP per 24 hours." }
```

### CORS

`Access-Control-Allow-Origin: *` is sent on every `/services/v1/` response, so
these endpoints are callable directly from a browser.
