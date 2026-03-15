# Free Public REST APIs — AI SENSE AS

> **Base URL:** `https://aisenseapi.com/services/v1`  
> **Authentication:** None  
> **Cost:** Free  
> **Format:** JSON (all responses unless noted)

---

## Table of Contents

- [Time](#time)
- [Random](#random)
- [Transform](#transform)
- [Hash](#hash)
- [Web](#web)
- [Crypto](#crypto)
- [Common Conventions](#common-conventions)

---

## Time

### `GET /datetime[/{offset}]`
Returns the current date and time in ISO 8601 format. Optional 4-digit timezone offset (`+0200`, `-0530`, `0100`).

```
GET https://aisenseapi.com/services/v1/datetime
GET https://aisenseapi.com/services/v1/datetime/+0200
GET https://aisenseapi.com/services/v1/datetime/-0530
GET https://aisenseapi.com/services/v1/datetime/0100
```

```json
{ "datetime": "2025-01-27T14:53:22+00:00" }
```

---

### `GET /timestamp`
Returns the current Unix timestamp (seconds since 1970-01-01 UTC).

```json
{ "timestamp": 1741953720 }
```

---

### `GET /microtimestamp`
Returns the current Unix timestamp with microsecond precision.

```json
{ "microtimestamp": 1741953720.483921 }
```

---

### `GET /timezones[/{offset}]`
Returns all available timezones. Optionally filter by UTC offset.

```json
{ "timezones": ["Europe/Oslo", "Europe/Berlin", "Europe/Paris"] }
```

---

### `GET /swatchinternettime`
Returns current time in Swatch Internet Time (.beats) and today's date. Based on BMT (GMT-1). No time zones.

```json
{ "beat": "@582", "date": "2025-01-27" }
```

---

## Random

### `GET /random_number[/{from}/{to}]`
Returns a random integer in the given range. Defaults to 1–6. Auto-swaps if `to` < `from`. Single value sets `from=1`.

```
GET https://aisenseapi.com/services/v1/random_number
GET https://aisenseapi.com/services/v1/random_number/10/20
GET https://aisenseapi.com/services/v1/random_number/-57/-3
GET https://aisenseapi.com/services/v1/random_number/30
```

```json
{ "random_number": 4, "range": { "from": 1, "to": 6 } }
```

---

### `GET /random_color`
Returns a random hex color code.

```json
{ "color": "#A3F2C1" }
```

---

### `GET /uuid`
Returns a UUID v4.

```json
{ "uuid": "809edbbe-1626-4c16-b4a1-73847546e22b" }
```

---

### `GET /guid`
Returns a GUID.

```json
{ "guid": "809edbbe-1626-4c16-b4a1-73847546e22b" }
```

---

## Transform

### `POST /base64_encode`
Encodes text to Base64. Input: JSON with `data` field.

```json
// Request
{ "data": "Hello world" }

// Response
{ "base64_encoded_data": "SGVsbG8gd29ybGQ=" }
```

---

### `POST /base64_decode`
Decodes Base64. Input: JSON with `data` field or plain text (`Content-Type: text/plain`).
If decoded result is JSON, returns it directly. If binary/non-JSON, stores it and returns a storage URL.
Set `Accept: application/octet-stream` to stream raw binary.

```json
// Request
{ "data": "SGVsbG8gd29ybGQ=" }

// Response — JSON data
{ "type": "json", "decoded_data": { "key": "value" } }

// Response — binary data
{
  "type": "binary",
  "decoded_data_storage_url": "https://aisenseapi.com/services/v1/storage/123e4567-e89b-12d3-a456-426614174000",
  "expire_timestamp": 1738457158
}
```

---

### `POST /base58_encode`
Encodes text to Base58. Input: JSON with `data` field.

```json
// Request
{ "data": "Hello" }
// Response
{ "base58_encoded_data": "9Ajdvzr" }
```

---

### `POST /base58_decode`
Decodes Base58. Input: JSON with `data` field or plain text.

```json
// Request
{ "data": "9Ajdvzr" }
// Response
{ "decoded_data": "Hello" }
```

---

### `POST /base32_encode`
Encodes text to Base32. Input: JSON with `data` field.

```json
// Request
{ "data": "Hello" }
// Response
{ "base32_encoded_data": "JBSWY3DP" }
```

---

### `POST /base32_decode`
Decodes Base32. Input: JSON with `data` field or plain text. Set `Accept: application/octet-stream` for binary output.

```json
// Request
{ "data": "JBSWY3DP" }
// Response
{ "decoded_data": "Hello" }
```

---

### `POST /jwt_encode`
Encodes a JSON payload into a JWT using HS256. Accepts JSON, plain text (`Content-Type: text/plain` + `X-Secret` header), or file upload (`jwt_data` field, `multipart/form-data`).

```json
// Request
{ "data": "{\"user\":\"john\",\"iat\":1627123456}", "secret": "your_secret_key" }

// Response
{ "jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjoiam9obiIsImlhdCI6MTYyNzEyMzQ1Nn0..." }
```

---

### `POST /jwt_decode`
Decodes a JWT and returns its payload. Accepts JSON, plain text (`Content-Type: text/plain` + `X-Secret` header), or file upload (`jwt_data` field, `multipart/form-data`).

```json
// Request
{ "data": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", "secret": "your_secret_key" }

// Response
{ "decoded_payload": { "sub": "1234567890", "name": "John Doe", "iat": 1516239022 } }
```

---

### `POST /qrcode_encode`
Generates a QR code from text. Input: JSON with `payload` field. Returns Base64-encoded PNG.
Supports URLs, plain text, vCards, Wi-Fi credentials, calendar events, and more.

```json
// Request
{ "payload": "https://aisenseapi.com/" }

// Response
{ "qrcode_image": "iVBORw0KGgoAAAANSUhEUg...", "image_type": "png" }
```

---

### `POST /qrcode_decode`
Decodes a QR code image. Accepts file upload (`qrcode_image` field, `multipart/form-data`) or Base64 JSON (`payload` field).

```json
// Request
{ "payload": "iVBORw0KGgoAAAANSUhEUg..." }

// Response
{ "qrcode_content": "https://aisenseapi.com/" }
```

---

## Hash

All hash endpoints accept JSON (`{ "data": "..." }`), plain text (`Content-Type: text/plain`), or file uploads.

### `POST /md5`
```json
{ "data": "Hello" } → { "hash": "8b1a9953c4611296a827abf8c47804d7" }
```

### `POST /sha1`
```json
{ "data": "Hello" } → { "hash": "f7ff9e8b7bb2e09b70935a5d785e0cc5d9d0abf0" }
```

### `POST /sha256`
```json
{ "data": "Hello" } → { "hash": "185f8db32921bd46d35cc5e1aeea7bab5be96848c1dc7..." }
```

### `POST /sha512`
```json
{ "data": "Hello" } → { "hash": "3615f80c9d293ed7402687f94b22d58e529b8cc7916f8..." }
```

---

## Web

### `GET /ping`
```json
{ "response": "pong" }
```

---

### `GET /health`
```json
{ "status": "ok", "timestamp": 1741953720.483921 }
```

---

### `GET /client_ip`
```json
{ "ip": "203.0.113.42" }
```

---

### `GET /ip_reverse_lookup/{ip}`
```
GET https://aisenseapi.com/services/v1/ip_reverse_lookup/151.101.65.195
```
```json
{
  "ip": "151.101.65.195",
  "country": "United States",
  "city": "San Francisco",
  "location": { "lat": "37.764200", "lng": "-122.399300" },
  "place": null,
  "timezone": "America/Los_Angeles"
}
```

---

### Storage

**Store:** `POST /storage` — JSON, plain text, or file. Returns `storage_id` + `expire_timestamp`. **24h TTL.**

```json
// Request
{ "key1": "value1" }

// Response
{ "storage_id": "123e4567-e89b-12d3-a456-426614174000", "expire_timestamp": 1738457158 }
```

**Retrieve:** `GET /storage/{storage_id}` — returns stored JSON, text, or binary.

---

### `GET /url_shortener/{url}`
Shortens a URL. **24h TTL.**

```
GET https://aisenseapi.com/services/v1/url_shortener/https://developer.mozilla.org/
```

---

### Webhook Capture

**Create session:** `POST /webhook_capture`

```json
{
  "ok": true,
  "capture_id": "6f8c9e52-3f2c-4e73-9d3b-8d6c3f6d1c91",
  "update_url": "https://aisenseapi.com/services/v1/webhook_capture/6f8c9e52-3f2c-4e73-9d3b-8d6c3f6d1c91/update",
  "read_url": "https://aisenseapi.com/services/v1/webhook_capture/6f8c9e52-3f2c-4e73-9d3b-8d6c3f6d1c91",
  "expire_timestamp": 1772893200
}
```

**Send webhook:** Any HTTP method → `update_url`

**Read result:** `GET /webhook_capture/{capture_id}`

```json
{
  "ok": true,
  "capture_id": "6f8c9e52-3f2c-4e73-9d3b-8d6c3f6d1c91",
  "captured_at_datetime": "2026-03-06T14:20:00Z",
  "request": {
    "method": "POST",
    "headers": { "content-type": "application/json" },
    "client_ip": "203.0.113.10",
    "body": {
      "json": { "event": "payment.created", "amount": 499 },
      "text": null, "base64": null, "raw_length": 38
    }
  }
}
```

---

### Webhook Action

**Create session:** `POST /webhook_action`

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
    {
      "type": "textarea",
      "name": "comment",
      "label": "Comment",
      "placeholder": "Optional comment",
      "max_length": 500
    }
  ]
}

// Response
{
  "ok": true,
  "action_id": "9e0e6d3b-1a45-44c5-9e0b-92f5f3bdb2f1",
  "form_url": "https://aisenseapi.com/services/v1/webhook_action/9e0e6d3b-1a45-44c5-9e0b-92f5f3bdb2f1/form",
  "result_url": "https://aisenseapi.com/services/v1/webhook_action/9e0e6d3b-1a45-44c5-9e0b-92f5f3bdb2f1",
  "expire_timestamp": 1772893200,
  "expire_datetime": "2026-03-07T14:20:00Z"
}
```

**Open form:** `GET /webhook_action/{action_id}/form`

**Get result:** `GET /webhook_action/{action_id}`

```json
// After submission
{
  "ok": true,
  "action_id": "9e0e6d3b-1a45-44c5-9e0b-92f5f3bdb2f1",
  "status": "answered",
  "answered_at_datetime": "2026-03-06T15:13:20Z",
  "response": { "decision": "approve", "comment": "Looks good" }
}
```

**Supported field types:** `radio`, `select`, `text`, `textarea`, `checkbox`

---

## Crypto

> ⚠️ For **development and testing only**. Never use with real funds.

### `GET /solana/generate_new_wallet`
```json
{ "private_key": "...", "private_key_base58": "...", "public_address": "..." }
```

### `GET /bitcoin/generate_new_wallet`
```json
{ "private_key": "...", "private_key_wif": "...", "address": "..." }
```

### `GET /ethereum/generate_new_wallet`
```json
{ "private_key": "0x...", "public_address": "0x..." }
```

---

## Common Conventions

### Input formats (POST endpoints)
| Format | Content-Type | Notes |
|--------|-------------|-------|
| JSON | `application/json` | Most common — see each endpoint for field names |
| Plain text | `text/plain` | Pass secret via `X-Secret` header for JWT endpoints |
| File upload | `multipart/form-data` | Field names vary by endpoint |

### Response field names (key reference)
| Endpoint | Response key |
|----------|-------------|
| `/base64_encode` | `base64_encoded_data` |
| `/base64_decode` | `decoded_data` or `decoded_data_storage_url` |
| `/base58_encode` | `base58_encoded_data` |
| `/base32_encode` | `base32_encoded_data` |
| `/jwt_encode` | `jwt` |
| `/jwt_decode` | `decoded_payload` |
| `/qrcode_encode` | `qrcode_image` + `image_type` |
| `/qrcode_decode` | `qrcode_content` |
| `/random_number` | `random_number` + `range` |
| `/swatchinternettime` | `beat` + `date` |
| `/storage` (store) | `storage_id` + `expire_timestamp` |

### TTL — auto-deletes after 24 hours
`/storage` · `/url_shortener` · `/webhook_capture` · `/webhook_action`

### Rate limits
Not publicly documented. Free community APIs — use responsibly.
