---
name: free-public-rest-apis
description: "Use this skill whenever the user wants to integrate with, call, test, or learn about the free public REST APIs from AI SENSE AS (aisense.no). Triggers include: requests for current time/datetime, random numbers, random colors, UUIDs, GUIDs, Base64/Base58/Base32 encoding or decoding, JWT encode/decode, QR code generation or decoding, MD5/SHA1/SHA256/SHA512 hashing, ping/health checks, client IP lookup, IP geolocation/reverse lookup, temporary JSON/text/file storage, URL shortening, webhook capture, webhook action forms, or crypto wallet generation (Solana, Bitcoin, Ethereum). Also use when the user asks for a quick utility API without authentication. Do NOT use for paid APIs, authenticated services, or operations requiring persistent storage beyond 24 hours."
license: Public documentation — no authentication required for any endpoint
---

# Free Public REST APIs — AI SENSE AS

## Overview

All APIs listed here are **free**, **public**, and require **no authentication**. They are hosted by AI SENSE AS (Oslo, Norway). Base URL patterns follow each endpoint description below.

All endpoints return JSON unless otherwise noted. No API keys are needed.

---

## Categories

- [Time](#time)
- [Random](#random)
- [Transform](#transform)
- [Hash](#hash)
- [Web](#web)
- [Crypto](#crypto)

---

## Time

### Datetime
**Description:** Returns the current date and time in ISO 8601 format, adjusted for an optional timezone offset. If no valid timezone offset is provided, defaults to UTC.

**Endpoint:** `GET https://aisenseapi.com/services/v1/datetime[/{offset}]`

**Example response:**
```json
{
  "datetime": "2025-03-15T14:22:00+01:00"
}
```

---

### Timestamp
**Description:** Returns the current Unix timestamp — the number of seconds since January 1, 1970 (UTC).

**Endpoint:** `GET https://aisenseapi.com/services/v1/timestamp`

**Example response:**
```json
{
  "timestamp": 1741953720
}
```

---

### Microtimestamp
**Description:** Returns the current Unix timestamp with microsecond precision as a floating-point value. Ideal for high-resolution time measurements.

**Endpoint:** `GET https://aisenseapi.com/services/v1/microtimestamp`

**Example response:**
```json
{
  "microtimestamp": 1741953720.483921
}
```

---

### Timezones
**Description:** Returns a list of all available timezones. Optionally filter by timezone offset.

**Endpoint:** `GET https://aisenseapi.com/services/v1/timezones[/{offset}]`

**Example response:**
```json
{
  "timezones": ["Europe/Oslo", "Europe/Berlin", "Europe/Paris"]
}
```

---

### Swatch Internet Time
**Description:** Returns the current time in Swatch Internet Time (.beats) and the current date in YYYY-MM-DD format. The day is divided into 1000 .beats (each = 86.4 seconds). Based on BMT (Biel Meantime) — no time zones involved.

**Endpoint:** `GET https://aisenseapi.com/services/v1/swatchinternettime`

**Example response:**
```json
{
  "beats": 623,
  "date": "2025-03-15"
}
```

---

## Random

### Random Number
**Description:** Generates a random integer within a specified range using optional `from` and `to` parameters. Defaults to 1–6 if no parameters are given. Automatically swaps values if `to` < `from`.

**Endpoint:** `GET https://aisenseapi.com/services/v1/random_number[/{from}/{to}]`

**Example response:**
```json
{
  "number": 4
}
```

---

### Random Color
**Description:** Generates a random hex color code between `#000000` and `#FFFFFF`.

**Endpoint:** `GET https://aisenseapi.com/services/v1/random_color`

**Example response:**
```json
{
  "color": "#A3F2C1"
}
```

---

### UUID
**Description:** Generates a universally unique identifier (UUID v4).

**Endpoint:** `GET https://aisenseapi.com/services/v1/uuid`

**Example response:**
```json
{
  "uuid": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### GUID
**Description:** Generates a globally unique identifier (GUID).

**Endpoint:** `GET https://aisenseapi.com/services/v1/guid`

**Example response:**
```json
{
  "guid": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## Transform

### Base64 Encode
**Description:** Encodes text into Base64 format. Input must be JSON with a `data` field.

**Endpoint:** `POST https://aisenseapi.com/services/v1/base64_encode`

**Request:**
```json
{
  "data": "Hello, world!"
}
```

**Response:**
```json
{
  "encoded": "SGVsbG8sIHdvcmxkIQ=="
}
```

---

### Base64 Decode
**Description:** Decodes a Base64-encoded string back to its original format. Input must be JSON with a `data` field.

**Endpoint:** `POST https://aisenseapi.com/services/v1/base64_decode`

**Request:**
```json
{
  "data": "SGVsbG8sIHdvcmxkIQ=="
}
```

**Response:**
```json
{
  "decoded": "Hello, world!"
}
```

---

### Base58 Encode
**Description:** Encodes text into Base58 format. Input must be JSON with a `data` field.

**Endpoint:** `POST https://aisenseapi.com/services/v1/base58_encode`

**Request:**
```json
{
  "data": "Hello"
}
```

---

### Base58 Decode
**Description:** Decodes a Base58-encoded string. Input must be JSON with a `data` field.

**Endpoint:** `POST https://aisenseapi.com/services/v1/base58_decode`

---

### Base32 Encode
**Description:** Encodes text into Base32 format. Input must be JSON with a `data` field.

**Endpoint:** `POST https://aisenseapi.com/services/v1/base32_encode`

---

### Base32 Decode
**Description:** Decodes a Base32-encoded string. Accepts JSON with a `data` field or plain text. Response can be JSON (default) or raw binary based on the `Accept` header.

**Endpoint:** `POST https://aisenseapi.com/services/v1/base32_decode`

---

### JWT Encode
**Description:** Encodes a JSON payload into a JWT using the HS256 algorithm. Accepts JSON, plain text (`Content-Type: text/plain`), or file upload. A secret key is required to sign the token.

**Endpoint:** `POST https://aisenseapi.com/services/v1/jwt_encode`

**Request:**
```json
{
  "data": { "user": "alice", "role": "admin" },
  "secret": "my-secret-key"
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

### JWT Decode
**Description:** Decodes a JWT and returns its payload. Accepts JSON with a `data` field, plain text, or file upload. A secret key must be provided.

**Endpoint:** `POST https://aisenseapi.com/services/v1/jwt_decode`

**Request:**
```json
{
  "data": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "secret": "my-secret-key"
}
```

---

### QR Code Encode
**Description:** Generates a QR code from text input. Returns the QR code as a Base64-encoded PNG. Can encode URLs, plain text, contact info, Wi-Fi credentials, event details, etc.

**Endpoint:** `POST https://aisenseapi.com/services/v1/qrcode_encode`

**Request:**
```json
{
  "data": "https://example.com"
}
```

**Response:**
```json
{
  "qrcode": "iVBORw0KGgoAAAANSUhEUgAA..."
}
```

---

### QR Code Decode
**Description:** Decodes a QR code image and returns the embedded content. Accepts a file upload or a Base64-encoded image in JSON format.

**Endpoint:** `POST https://aisenseapi.com/services/v1/qrcode_decode`

**Request (Base64):**
```json
{
  "data": "iVBORw0KGgoAAAANSUhEUgAA..."
}
```

**Response:**
```json
{
  "decoded": "https://example.com"
}
```

---

## Hash

All hash endpoints accept JSON, plain text (`Content-Type: text/plain`), or file uploads.

### MD5
**Endpoint:** `POST https://aisenseapi.com/services/v1/md5`

**Request:**
```json
{ "data": "Hello" }
```
**Response:**
```json
{ "hash": "8b1a9953c4611296a827abf8c47804d7" }
```

---

### SHA1
**Endpoint:** `POST https://aisenseapi.com/services/v1/sha1`

**Request:**
```json
{ "data": "Hello" }
```
**Response:**
```json
{ "hash": "f7ff9e8b7bb2e09b70935a5d785e0cc5d9d0abf0" }
```

---

### SHA256
**Endpoint:** `POST https://aisenseapi.com/services/v1/sha256`

**Request:**
```json
{ "data": "Hello" }
```
**Response:**
```json
{ "hash": "185f8db32921bd46d35cc5e1aeea7bab5be96848c1dc7..." }
```

---

### SHA512
**Endpoint:** `POST https://aisenseapi.com/services/v1/sha512`

**Request:**
```json
{ "data": "Hello" }
```
**Response:**
```json
{ "hash": "3615f80c9d293ed7402687f94b22d58e529b8cc7916f8..." }
```

---

## Web

### Ping
**Description:** Returns a `pong` response. Used to verify connectivity or confirm the API is reachable.

**Endpoint:** `GET https://aisenseapi.com/services/v1/ping`

**Response:**
```json
{ "response": "pong" }
```

---

### Health
**Description:** Returns a health check status and a high-precision ISO 8601 timestamp (microsecond float). Useful for monitoring server uptime and response times.

**Endpoint:** `GET https://aisenseapi.com/services/v1/health`

**Response:**
```json
{
  "status": "ok",
  "timestamp": 1741953720.483921
}
```

---

### Client IP
**Description:** Returns the public IP address of the client making the request. Useful for access control, analytics, or request tracking. No parameters required.

**Endpoint:** `GET https://aisenseapi.com/services/v1/client_ip

**Response:**
```json
{ "ip": "203.0.113.42" }
```

---

### IP Reverse Lookup
**Description:** Performs a reverse IP lookup. Returns country, city, latitude, longitude, and time zone for a given IP address. Useful for location-based services, analytics, or security checks.

**Endpoint:** `GET https://aisenseapi.com/services/v1/ip_reverse_lookup/{ip}`

**Response:**
```json
{
  "ip": "203.0.113.42",
  "country": "Norway",
  "city": "Oslo",
  "latitude": 59.9139,
  "longitude": 10.7522,
  "timezone": "Europe/Oslo"
}
```

---

### Storage
**Description:** Temporary key-value storage for JSON, text, or file data. Store new data and receive a UUID, or retrieve previously stored data using a UUID. **All data is automatically deleted after 24 hours.**

**Store data:**
`POST https://aisenseapi.com/services/v1/storage`
```json
{ "data": { "key": "value" } }
```
Response:
```json
{ "uuid": "550e8400-e29b-41d4-a716-446655440000" }
```

**Retrieve data:**
`GET https://aisenseapi.com/services/v1/storage/{uuid}`

---

### URL Shortener
**Description:** Generates a shortened URL for any full-length link. Returns a short redirect URL. **Links expire automatically after 24 hours.**

**Endpoint:** `POST https://aisenseapi.com/services/v1/url_shortener`

**Request:**
```json
{ "url": "https://example.com/some/very/long/path?with=params" }
```

**Response:**
```json
{ "short_url": "https://www.aisense.no/s/abc123" }
```

---

### Webhook Capture
**Description:** Captures and returns the full HTTP request received by the server. Records method, headers, query parameters, client IP, and body. JSON bodies are automatically parsed. **Data expires after 24 hours.** Primarily used to test webhooks and debug integrations.

**Endpoint:** `POST https://aisenseapi.com/services/v1/webhook_capture`

**Response:**
```json
{
  "method": "POST",
  "headers": { "Content-Type": "application/json" },
  "query": {},
  "ip": "203.0.113.42",
  "body": { "event": "user.created" }
}
```

---

### Webhook Action
**Description:** Creates an interactive action requiring human input before an automated process continues. Generates a unique action ID, a form URL for user submission, and a result URL to poll for the response. Form fields can include radio buttons, select menus, text inputs, textareas, and checkboxes. Status changes to `answered` once submitted. **All stored actions expire after 24 hours.**

**Endpoint:** `POST https://aisenseapi.com/services/v1/webhook_action`

**Request:**
```json
{
  "title": "Approve deployment?",
  "fields": [
    {
      "type": "radio",
      "name": "approval",
      "label": "Do you approve?",
      "options": ["Yes", "No"]
    }
  ]
}
```

**Response:**
```json
{
  "ok": true,
  "action_id": "9e0e6d3b-1a45-44c5-9e0b-92f5f3bdb2f1",
  "form_url": "https://aisenseapi.com/services/v1/webhook_action/9e0e6d3b-1a45-44c5-9e0b-92f5f3bdb2f1/form",
  "result_url": "https://aisenseapi.com/services/v1/webhook_action/9e0e6d3b-1a45-44c5-9e0b-92f5f3bdb2f1",
  "expire_timestamp": 1772893200,
  "expire_datetime": "2026-03-07T14:20:00Z"
}
```

---

## Crypto

> ⚠️ **Warning:** These endpoints generate wallets for **development and testing purposes**. Never use programmatically generated wallets with real funds unless you fully control key storage and security.

---

### Solana — Generate New Wallet
**Description:** Generates a new Solana wallet including a private key, a Base58-encoded private key, and a public address.

**Endpoint:** `GET https://aisenseapi.com/services/v1/solana_wallet`

**Response:**
```json
{
  "private_key": "...",
  "private_key_base58": "...",
  "public_address": "..."
}
```

---

### Bitcoin — Generate New Wallet
**Description:** Generates a Bitcoin wallet with a private key (hexadecimal and WIF format) and a Base58Check-encoded Bitcoin address. Adheres to Bitcoin's secp256k1 standards.

**Endpoint:** `GET https://aisenseapi.com/services/v1/bitcoin_wallet`

**Response:**
```json
{
  "private_key_hex": "...",
  "private_key_wif": "...",
  "address": "..."
}
```

---

### Ethereum — Generate New Wallet
**Description:** Generates a new Ethereum wallet including a private key and a public address.

**Endpoint:** `GET https://aisenseapi.com/services/v1/ethereum_wallet`

**Response:**
```json
{
  "private_key": "0x...",
  "public_address": "0x..."
}
```

---

## Quick Reference Table

| Category | Endpoint | Method | Description |
|----------|----------|--------|-------------|
| Time | `/api/time/datetime` | GET | Current datetime (ISO 8601) |
| Time | `/api/time/timestamp` | GET | Unix timestamp |
| Time | `/api/time/microtimestamp` | GET | Microsecond Unix timestamp |
| Time | `/api/time/timezones` | GET | List of timezones |
| Time | `/api/time/swatchinternettime` | GET | Swatch .beats time |
| Random | `/api/random/number` | GET | Random integer in range |
| Random | `/api/random/color` | GET | Random hex color |
| Random | `/api/random/uuid` | GET | UUID v4 |
| Random | `/api/random/guid` | GET | GUID |
| Transform | `/api/transform/base64_encode` | POST | Base64 encode |
| Transform | `/api/transform/base64_decode` | POST | Base64 decode |
| Transform | `/api/transform/base58_encode` | POST | Base58 encode |
| Transform | `/api/transform/base58_decode` | POST | Base58 decode |
| Transform | `/api/transform/base32_encode` | POST | Base32 encode |
| Transform | `/api/transform/base32_decode` | POST | Base32 decode |
| Transform | `/api/transform/jwt_encode` | POST | JWT encode (HS256) |
| Transform | `/api/transform/jwt_decode` | POST | JWT decode |
| Transform | `/api/transform/qrcode_encode` | POST | QR code → Base64 PNG |
| Transform | `/api/transform/qrcode_decode` | POST | QR code image → text |
| Hash | `/api/hash/md5` | POST | MD5 hash |
| Hash | `/api/hash/sha1` | POST | SHA1 hash |
| Hash | `/api/hash/sha256` | POST | SHA256 hash |
| Hash | `/api/hash/sha512` | POST | SHA512 hash |
| Web | `/api/web/ping` | GET | Ping / connectivity check |
| Web | `/api/web/health` | GET | Health check + timestamp |
| Web | `/api/web/ip` | GET | Client public IP |
| Web | `/api/web/ip_reverse_lookup/{ip}` | GET | IP geolocation lookup |
| Web | `/api/web/storage` | POST/GET | Temp JSON/text storage (24h TTL) |
| Web | `/api/web/url_shortener` | POST | URL shortener (24h TTL) |
| Web | `/api/web/webhook_capture` | POST | Webhook request capture (24h TTL) |
| Web | `/api/web/webhook_action` | POST | Human-in-the-loop action form (24h TTL) |
| Crypto | `/api/crypto/solana_wallet` | GET | New Solana wallet |
| Crypto | `/api/crypto/bitcoin_wallet` | GET | New Bitcoin wallet |
| Crypto | `/api/crypto/ethereum_wallet` | GET | New Ethereum wallet |

---

## Common Patterns

### POST endpoints — accepted input formats
Most POST endpoints accept input in three ways:
1. **JSON body** with a `data` field: `{ "data": "your input" }`
2. **Plain text** with header `Content-Type: text/plain`
3. **File upload** (multipart form data)

### Error handling
If input is invalid or missing, endpoints return an appropriate error message in JSON format:
```json
{ "error": "Invalid input: data field is required" }
```

### 24-hour TTL endpoints
The following endpoints store data that **automatically expires after 24 hours**:
- Storage
- URL Shortener
- Webhook Capture
- Webhook Action

---

## Provider Information

**AI SENSE AS**
Postboks 1202 Vika
0110 Oslo, Norway

Website: [aisense.no](https://www.aisense.no)
