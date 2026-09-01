---
name: free-public-rest-apis
description: "Use this skill whenever the user wants to integrate with, call, test, or learn about the free public REST APIs from AI SENSE AS (aisenseapi.com). Triggers include: requests for current time/datetime/timestamp, random numbers, random colors, passwords, UUIDs, GUIDs, Base64/Base58/Base32 encoding or decoding, JWT encode/decode, QR code generation or decoding, MD5/SHA1/SHA256/SHA512 hashing, CRC32 checksums, ping/health checks, client IP lookup, user agent, IP geolocation/reverse lookup, domain-to-IP resolution, timestamp conversion between unix/ISO/RFC formats, email address validation with MX lookup, hash verification, text slugification, delayed webhook delivery and scheduling, durable Agent Wake tasks for webhooks, human answers or time events, IBAN/card/phone/Norwegian org and account number validation, temporary JSON/text/file storage, URL shortening, webhook capture, webhook action forms for human-in-the-loop approval, or crypto wallet generation and balance lookup (Solana, Bitcoin, Ethereum). Also use when the user asks for a quick utility API without authentication. Do NOT use for paid APIs, authenticated services, or operations requiring persistent storage beyond 24 hours."
license: Public documentation - no authentication required for any endpoint
---

# Free Public REST APIs - AI SENSE AS

**Base URL:** `https://aisenseapi.com/services/v1`
No authentication. No sign-up. Hosted by AI SENSE AS, Oslo.

Every shape below was verified against production.

---

## Read this before calling anything

Three service-wide behaviours will bite you if you assume the usual conventions.

**1. The response key is named after the endpoint.** There is no generic `data`
or `result` wrapper. `/md5_hash` returns `md5_hash`. `/ping` returns `ping`.
`/random_color` returns `random_color`. `/health` returns `microtimestamp`, not
`timestamp`. Never guess - the table at the bottom lists every key.

**2. Errors are `{"error": "message"}` with a real HTTP status.** Uniform since
2026-08-17: 400 caller mistake, 404 unknown id or endpoint, 429 rate limit,
500 our failure, 502/504 upstream. Branch on either the status or the `error`
key - both are trustworthy, and a path matching no route is a plain 404 in the
same shape.

**3. Not everything is JSON.** `base64_decode`, `base58_decode` and
`base32_decode` return `application/octet-stream` unless you send
`Accept: application/json`.

**Rate limit:** 5000 requests per IP per 24 hours, then HTTP 429 in the same
flat error shape.

---

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

`POST /webhook_capture` -> `{"ok": true, "capture_id": "...", "update_url": "...", "read_url": "...", "expire_timestamp": ...}`

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

---

## Crypto

> Wallet generation is for **development and testing only**. A private key
> produced by a public HTTP endpoint has crossed a network neither you nor the
> user controls. Never suggest funding one.

| Endpoint | Returns |
|----------|---------|
| `GET /solana/generate_new_wallet` | `{"private_key", "public_address"}` |
| `GET /bitcoin/generate_new_wallet` | `{"private_key", "private_key_wif", "public_address"}` |
| `GET /ethereum/generate_new_wallet` | `{"private_key", "public_address"}` |
| `GET /solana/balance/{address}` | `{"wallet", "balance_sol", "balance_lamports"}` |
| `GET /bitcoin/balance/{address}` | `{"wallet", "final_balance_btc", "final_balance_sats"}` |
| `GET /ethereum/balance/{address}` | `{"wallet", "balance_eth", "balance_wei"}` |

Bitcoin returns `public_address`, not `address`. Solana has no
`private_key_base58` field.

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
| `/webhook_capture` | POST | `ok`, `capture_id`, `update_url`, `read_url`, `expire_timestamp` |
| `/webhook_capture/{id}` | GET | `ok`, `capture_id`, `captured_at_*`, `request` |
| `/webhook_action` | POST | `ok`, `action_id`, `form_url`, `result_url`, `expire_*` |
| `/webhook_action/{id}` | GET | `ok`, `action_id`, `status`, `response`, timestamps |
| `/webhook_schedule` | POST | `ok`, `schedule_id`, `status`, `fire_at_timestamp`, `result_url` |
| `/webhook_schedule/{id}` | GET | `ok`, `schedule_id`, `status`, `attempts`, `http_status` |
| `/agent_wake` | POST | `taskId`, `status`, `ttlMs`, event URLs in `_meta` |
| `/agent_wake/{id}` | GET / DELETE | `status`, `result` or cancellation state |
| `/validate/{type}` | POST | `type`, `valid`, per-check fields |
| `/webhook_action/{id}/form` | GET | `text/html` |
| `/solana/generate_new_wallet` | GET | `private_key`, `public_address` |
| `/bitcoin/generate_new_wallet` | GET | `private_key`, `private_key_wif`, `public_address` |
| `/ethereum/generate_new_wallet` | GET | `private_key`, `public_address` |
| `/solana/balance/{address}` | GET | `wallet`, `balance_sol`, `balance_lamports` |
| `/bitcoin/balance/{address}` | GET | `wallet`, `final_balance_btc`, `final_balance_sats` |
| `/ethereum/balance/{address}` | GET | `wallet`, `balance_eth`, `balance_wei` (strings) |

---

## Input formats for POST endpoints

| Format | Content-Type | Notes |
|--------|-------------|-------|
| JSON | `application/json` | Field is `data` for most, `payload` for QR |
| Plain text | `text/plain` | JWT endpoints take the secret via an `X-Secret` header |
| File upload | `multipart/form-data` | Field names vary - `jwt_data`, `qrcode_image`, `file` |

## Auto-expiry

`/storage` | `/url_shortener` | `/webhook_capture` | `/webhook_action` - all
deleted after 24 hours.

## CORS

`Access-Control-Allow-Origin: *` on every response, so these are callable
directly from browser JavaScript.

---

**AI SENSE AS** | Postboks 1202 Vika, 0110 Oslo, Norway
[aisenseapi.com](https://aisenseapi.com)
