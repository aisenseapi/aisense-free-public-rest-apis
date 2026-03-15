# Free Public REST APIs — AI SENSE AS

> **Base URL:** `https://www.aisense.no/api`  
> **Authentication:** None  
> **Cost:** Free  
> **Format:** JSON (all responses)

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

### `GET /time/datetime[/{offset}]`
Returns the current date and time in ISO 8601 format. Optional timezone offset (e.g. `1` for UTC+1). Defaults to UTC.

```json
{ "datetime": "2025-03-15T14:22:00+01:00" }
```

---

### `GET /time/timestamp`
Returns the current Unix timestamp (seconds since 1970-01-01 UTC).

```json
{ "timestamp": 1741953720 }
```

---

### `GET /time/microtimestamp`
Returns the current Unix timestamp with microsecond precision.

```json
{ "microtimestamp": 1741953720.483921 }
```

---

### `GET /time/timezones[/{offset}]`
Returns all available timezones. Filter by offset if provided.

```json
{ "timezones": ["Europe/Oslo", "Europe/Berlin", "Europe/Paris"] }
```

---

### `GET /time/swatchinternettime`
Returns current time in Swatch Internet Time (.beats). 1000 .beats per day, each = 86.4 seconds. Based on BMT — no time zones.

```json
{ "beats": 623, "date": "2025-03-15" }
```

---

## Random

### `GET /random/number[/{from}/{to}]`
Returns a random integer in the given range. Defaults to 1–6. Swaps values if `to` < `from`.

```json
{ "number": 4 }
```

---

### `GET /random/color`
Returns a random hex color code.

```json
{ "color": "#A3F2C1" }
```

---

### `GET /random/uuid`
Returns a UUID v4.

```json
{ "uuid": "550e8400-e29b-41d4-a716-446655440000" }
```

---

### `GET /random/guid`
Returns a GUID.

```json
{ "guid": "550e8400-e29b-41d4-a716-446655440000" }
```

---

## Transform

All transform endpoints accept input as:
- JSON body: `{ "data": "..." }`
- Plain text: `Content-Type: text/plain`
- File upload: multipart form data

---

### `POST /transform/base64/encode`
Encodes text to Base64.

```json
// Request
{ "data": "Hello, world!" }

// Response
{ "encoded": "SGVsbG8sIHdvcmxkIQ==" }
```

---

### `POST /transform/base64/decode`
Decodes Base64 back to original text.

```json
// Request
{ "data": "SGVsbG8sIHdvcmxkIQ==" }

// Response
{ "decoded": "Hello, world!" }
```

---

### `POST /transform/base58/encode`
Encodes text to Base58.

```json
{ "data": "Hello" }
```

---

### `POST /transform/base58/decode`
Decodes a Base58-encoded string.

```json
{ "data": "9Ajdvzr" }
```

---

### `POST /transform/base32/encode`
Encodes text to Base32.

```json
{ "data": "Hello" }
```

---

### `POST /transform/base32/decode`
Decodes a Base32-encoded string. Response format can be JSON (default) or raw binary via `Accept` header.

```json
{ "data": "JBSWY3DP" }
```

---

### `POST /transform/jwt/encode`
Encodes a JSON payload into a JWT using HS256. Requires a `secret`.

```json
// Request
{ "data": { "user": "alice", "role": "admin" }, "secret": "my-secret" }

// Response
{ "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." }
```

---

### `POST /transform/jwt/decode`
Decodes a JWT and returns its payload. Requires the same `secret` used to sign it.

```json
// Request
{ "data": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", "secret": "my-secret" }
```

---

### `POST /transform/qrcode/encode`
Generates a QR code from text. Returns a Base64-encoded PNG. Supports URLs, plain text, Wi-Fi credentials, contact info, etc.

```json
// Request
{ "data": "https://example.com" }

// Response
{ "qrcode": "iVBORw0KGgoAAAANSUhEUgAA..." }
```

---

### `POST /transform/qrcode/decode`
Decodes a QR code image and returns its text content. Accepts file upload or Base64-encoded image.

```json
// Request
{ "data": "iVBORw0KGgoAAAANSUhEUgAA..." }

// Response
{ "decoded": "https://example.com" }
```

---

## Hash

All hash endpoints accept JSON (`{ "data": "..." }`), plain text, or file uploads.

---

### `POST /hash/md5`
```json
// Request
{ "data": "Hello" }
// Response
{ "hash": "8b1a9953c4611296a827abf8c47804d7" }
```

---

### `POST /hash/sha1`
```json
{ "hash": "f7ff9e8b7bb2e09b70935a5d785e0cc5d9d0abf0" }
```

---

### `POST /hash/sha256`
```json
{ "hash": "185f8db32921bd46d35cc5e1aeea7bab5be96848c1dc7916..." }
```

---

### `POST /hash/sha512`
```json
{ "hash": "3615f80c9d293ed7402687f94b22d58e529b8cc7916f8bca..." }
```

---

## Web

### `GET /web/ping`
Connectivity check. Returns `pong`.

```json
{ "response": "pong" }
```

---

### `GET /web/health`
Health check with microsecond-precision timestamp.

```json
{ "status": "ok", "timestamp": 1741953720.483921 }
```

---

### `GET /web/ip`
Returns the public IP address of the requesting client.

```json
{ "ip": "203.0.113.42" }
```

---

### `GET /web/ip/lookup/{ip}`
Reverse IP lookup. Returns country, city, coordinates, and timezone.

```json
{
  "ip": "8.8.8.8",
  "country": "United States",
  "city": "Mountain View",
  "latitude": 37.386,
  "longitude": -122.0838,
  "timezone": "America/Los_Angeles"
}
```

---

### `POST /web/storage` — Store data
Stores JSON, text, or file data. Returns a UUID. **Expires after 24 hours.**

```json
// Request
{ "data": { "anything": "you want" } }

// Response
{ "uuid": "550e8400-e29b-41d4-a716-446655440000" }
```

### `GET /web/storage/{uuid}` — Retrieve data
Retrieves previously stored data by UUID.

---

### `POST /web/url/shorten`
Shortens a URL. **Expires after 24 hours.**

```json
// Request
{ "url": "https://example.com/some/very/long/path" }

// Response
{ "short_url": "https://www.aisense.no/s/abc123" }
```

---

### `POST /web/webhook/capture`
Captures the full incoming HTTP request (method, headers, query params, body, IP). Useful for testing webhooks and debugging integrations. **Expires after 24 hours.**

```json
{
  "method": "POST",
  "headers": { "content-type": "application/json" },
  "query": {},
  "ip": "203.0.113.42",
  "body": { "event": "user.created" }
}
```

---

### `POST /web/webhook/action`
Creates a human-in-the-loop action with a web form. Returns a form URL for human input and a result URL to poll. Field types: `radio`, `select`, `text`, `textarea`, `checkbox`. **Expires after 24 hours.**

```json
// Request
{
  "title": "Approve deployment?",
  "fields": [
    { "type": "radio", "name": "approval", "label": "Do you approve?", "options": ["Yes", "No"] }
  ]
}

// Response
{
  "action_id": "abc123",
  "form_url": "https://www.aisense.no/action/abc123",
  "result_url": "https://www.aisense.no/api/web/webhook/action/abc123"
}
```

---

## Crypto

> ⚠️ For **development and testing only**. Never use programmatically generated wallets with real funds unless you fully control key storage and security.

---

### `GET /crypto/solana/wallet`
Generates a new Solana wallet.

```json
{
  "private_key": "...",
  "private_key_base58": "...",
  "public_address": "..."
}
```

---

### `GET /crypto/bitcoin/wallet`
Generates a new Bitcoin wallet (secp256k1).

```json
{
  "private_key_hex": "...",
  "private_key_wif": "...",
  "address": "..."
}
```

---

### `GET /crypto/ethereum/wallet`
Generates a new Ethereum wallet.

```json
{
  "private_key": "0x...",
  "public_address": "0x..."
}
```

---

## Common Conventions

### Input formats (POST endpoints)
| Format | Content-Type | Body |
|--------|-------------|------|
| JSON | `application/json` | `{ "data": "..." }` |
| Plain text | `text/plain` | raw string |
| File | `multipart/form-data` | file upload |

### Error responses
```json
{ "error": "Invalid input: data field is required" }
```

### TTL / expiry
These endpoints store temporary data that **auto-deletes after 24 hours**:
- `/web/storage`
- `/web/url/shorten`
- `/web/webhook/capture`
- `/web/webhook/action`

### Rate limits
Not publicly documented. These are free community APIs — use responsibly.
