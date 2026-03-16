# Free Public REST APIs — AI SENSE AS

No API key · No sign-up · No cost · No rate limit

Provided by **[AI SENSE AS](https://aisenseapi.com)** (Oslo, Norway).  
Full endpoint reference: [`API.md`](API.md) · Repo: [github.com/aisenseapi/aisense-free-public-rest-apis](https://github.com/aisenseapi/aisense-free-public-rest-apis)

**Base URL:** `https://aisenseapi.com/services/v1/`

---

## Why this exists

Most utility APIs require sign-up, rate limit tiers, or pricing for basic operations. This collection skips all of that. Drop a URL into curl, Python, JavaScript, or an LLM tool definition and it just works.

The collection covers two tiers of usefulness:

- **Workflow endpoints** — the ones that solve real problems in pipelines and agent systems
- **Standard utilities** — hashing, encoding, UUIDs, time, crypto — the building blocks

---

## The high-value endpoints

### 🔁 Webhook Action — human-in-the-loop for agents

The standout endpoint for AI and automation work. When an automated pipeline needs a human decision before continuing, this handles the whole pattern with zero backend setup.

**How it works:**

1. `POST` a form definition (radio buttons, dropdowns, text fields, checkboxes)
2. Get back a `form_url` and a `result_url`
3. Send the `form_url` to a human via email or Slack
4. Poll `result_url` until `status` changes to `answered`

```bash
# Create the action
curl -X POST https://aisenseapi.com/services/v1/webhook_action \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Approve deployment to production?",
    "fields": [
      {
        "type": "radio",
        "name": "decision",
        "label": "Decision",
        "required": true,
        "options": [
          { "value": "approve", "label": "Approve" },
          { "value": "reject", "label": "Reject" },
          { "value": "defer", "label": "Defer" }
        ]
      },
      {
        "type": "textarea",
        "name": "comment",
        "label": "Notes (optional)"
      }
    ]
  }'

# Response:
# {
#   "ok": true,
#   "action_id": "9e0e6d3b-1a45-44c5-9e0b-92f5f3bdb2f1",
#   "form_url": "https://aisenseapi.com/services/v1/webhook_action/9e0e6d3b-.../form",
#   "result_url": "https://aisenseapi.com/services/v1/webhook_action/9e0e6d3b-...",
#   "expire_datetime": "2026-03-07T14:20:00Z"
# }

# Poll for the result
curl https://aisenseapi.com/services/v1/webhook_action/{action_id}
# "status": "pending"  →  "answered" once the form is submitted
```

Supported field types: `radio`, `select`, `text`, `textarea`, `checkbox`

All stored actions expire after 24 hours.

---

### 📡 Webhook Capture — inspect any inbound HTTP request

Create a capture session, get a unique URL, point any external service at it (Stripe, GitHub, Shopify), and read back the full captured request — method, headers, query parameters, IP, and parsed body. No ngrok, no local tunnel, no server setup.

```bash
# Create a capture session
curl -X POST https://aisenseapi.com/services/v1/webhook_capture

# Point your webhook sender at the returned capture_url, then read back what was sent:
curl https://aisenseapi.com/services/v1/webhook_capture/{capture_id}
# Returns method, headers, query params, IP, and auto-parsed JSON body
```

Data expires after 24 hours.

---

### 🗄️ Storage — ephemeral key-value store for pipelines

Post any JSON, text, or file. Get back a UUID. Retrieve it from anywhere — another machine, a different agent call, a downstream pipeline step. No database, no credentials.

```bash
# Store data
curl -X POST https://aisenseapi.com/services/v1/storage \
  -H "Content-Type: application/json" \
  -d '{"data": {"result": 42, "status": "complete"}}'
# { "uuid": "550e8400-e29b-41d4-a716-446655440000" }

# Retrieve it later, from anywhere
curl https://aisenseapi.com/services/v1/storage/550e8400-e29b-41d4-a716-446655440000
```

Expires after 24 hours.

---

### 🔗 URL Shortener

Shorten any URL by passing it directly in the path. Links expire after 24 hours.

```bash
curl https://aisenseapi.com/services/v1/url_shortener/https://example.com/very/long/path?with=params
```

---

### 🌍 IP Reverse Lookup

Resolve any IP address to country, city, coordinates, and timezone.

```bash
curl https://aisenseapi.com/services/v1/ip_reverse_lookup/8.8.8.8
# {
#   "ip": "8.8.8.8",
#   "country": "United States",
#   "city": "Mountain View",
#   "latitude": 37.386,
#   "longitude": -122.0838,
#   "timezone": "America/Los_Angeles"
# }
```

Also available: resolve a domain name to its IP address.

```bash
curl https://aisenseapi.com/services/v1/domain_ip_lookup/example.com
```

---

## Standard utilities

### 🔐 Hashing — MD5, SHA1, SHA256, SHA512, CRC32

All hash endpoints accept JSON, plain text, or file uploads.

```bash
curl -X POST https://aisenseapi.com/services/v1/sha256_hash \
  -H "Content-Type: application/json" \
  -d '{"data": "Hello"}'
# { "hash": "185f8db32921bd46d35cc5e1aeea7bab..." }
```

Available: `md5_hash`, `sha1_hash`, `sha256_hash`, `sha512_hash`, `crc32_checksum`

---

### 🔄 Encoding — Base64, Base58, Base32, JWT, QR Code

Encode and decode in either direction. JWT endpoints use HS256 and require a secret. QR encode returns a Base64 PNG; QR decode accepts a file upload or Base64 image.

```bash
# Base64 encode
curl -X POST https://aisenseapi.com/services/v1/base64_encode \
  -H "Content-Type: application/json" \
  -d '{"data": "Hello, world!"}'
# { "encoded": "SGVsbG8sIHdvcmxkIQ==" }

# QR code from text
curl -X POST https://aisenseapi.com/services/v1/qrcode_encode \
  -H "Content-Type: application/json" \
  -d '{"data": "https://example.com"}'
# { "qrcode": "iVBORw0KGgoAAAANSUhEUgAA..." }
```

Available: `base64_encode`, `base64_decode`, `base58_encode`, `base58_decode`, `base32_encode`, `base32_decode`, `jwt_encode`, `jwt_decode`, `qrcode_encode`, `qrcode_decode`

---

### 🎲 Random — UUID, GUID, number, color, password

```bash
curl https://aisenseapi.com/services/v1/uuid
curl https://aisenseapi.com/services/v1/guid
curl https://aisenseapi.com/services/v1/random_color
curl https://aisenseapi.com/services/v1/random_number/1/100
curl https://aisenseapi.com/services/v1/password/16        # random password, optional length
```

---

### ⏱ Time — Datetime, Timestamp, Timezones

```bash
curl https://aisenseapi.com/services/v1/datetime            # UTC
curl https://aisenseapi.com/services/v1/datetime/+0200      # with offset
curl https://aisenseapi.com/services/v1/timestamp
curl https://aisenseapi.com/services/v1/microtimestamp
curl https://aisenseapi.com/services/v1/timezones
curl https://aisenseapi.com/services/v1/swatchinternettime
```

---

### 🌐 Web utilities — Ping, Health, Client IP, User Agent

```bash
curl https://aisenseapi.com/services/v1/ping          # { "response": "pong" }
curl https://aisenseapi.com/services/v1/health        # { "status": "ok", "timestamp": ... }
curl https://aisenseapi.com/services/v1/client_ip     # { "ip": "203.0.113.42" }
curl https://aisenseapi.com/services/v1/user_agent    # returns your User-Agent string
```

---

### 🪙 Crypto — Wallet generation and balance lookup

Wallet generation for Solana, Bitcoin, and Ethereum. Balance lookup also available for each chain.

```bash
# Generate wallets
curl https://aisenseapi.com/services/v1/solana/generate_new_wallet
curl https://aisenseapi.com/services/v1/bitcoin/generate_new_wallet
curl https://aisenseapi.com/services/v1/ethereum/generate_new_wallet

# Check balances
curl https://aisenseapi.com/services/v1/solana/balance/{address}
curl https://aisenseapi.com/services/v1/bitcoin/balance/{address}
curl https://aisenseapi.com/services/v1/ethereum/balance/{address}
```

> ⚠️ Wallet generation is for development and testing only. Never use programmatically generated wallets with real funds unless you fully control key storage.

---

## Quick start by language

**curl**
```bash
curl https://aisenseapi.com/services/v1/uuid
```

**Python**
```python
from aisense_api import AISenseAPI
api = AISenseAPI()

print(api.get_uuid())
print(api.hash_sha256("Hello"))
print(api.ip_reverse_lookup("8.8.8.8"))
```

**JavaScript**
```javascript
import { AISenseAPI } from './aisense-api.js'
const api = new AISenseAPI()

console.log(await api.getUUID())
console.log(await api.hashSHA256('Hello'))
console.log(await api.ipReverseLookup('8.8.8.8'))
```

**LLM function calling (OpenAI, Gemini, Mistral, etc.)**
```python
import json
from openai import OpenAI

with open("openai-tools.json") as f:
    tools = json.load(f)

client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o",
    tools=tools,
    messages=[{"role": "user", "content": "Generate a UUID and hash the word Hello with SHA256"}]
)
```

**Claude** — a `SKILL.md` is included in the repo. Add it to Claude's context and it will use these APIs as tools automatically.

---

## What's in the repo

| File | Purpose |
|------|---------|
| `API.md` | Full endpoint reference with examples |
| `aisense_api.py` | Python client (zero dependencies) |
| `aisense-api.js` | JavaScript ESM client |
| `openai-tools.json` | Tool definitions for any LLM with function calling |
| `SKILL.md` | Claude skill file |
| `test.sh` | Smoke-tests all endpoints; exits `1` on failure (CI-friendly) |

---

## Endpoint summary

All paths are relative to `https://aisenseapi.com/services/v1/`

| Category | Endpoint | Method |
|----------|----------|--------|
| Time | `/datetime[/{offset}]` | GET |
| Time | `/timestamp` | GET |
| Time | `/microtimestamp` | GET |
| Time | `/timezones[/{offset}]` | GET |
| Time | `/swatchinternettime` | GET |
| Random | `/random_number[/{from}/{to}]` | GET |
| Random | `/random_color` | GET |
| Random | `/uuid` | GET |
| Random | `/guid` | GET |
| Random | `/password[/{length}]` | GET |
| Transform | `/base64_encode` | POST |
| Transform | `/base64_decode` | POST |
| Transform | `/base58_encode` | POST |
| Transform | `/base58_decode` | POST |
| Transform | `/base32_encode` | POST |
| Transform | `/base32_decode` | POST |
| Transform | `/jwt_encode` | POST |
| Transform | `/jwt_decode` | POST |
| Transform | `/qrcode_encode` | POST |
| Transform | `/qrcode_decode` | POST |
| Hash | `/md5_hash` | POST |
| Hash | `/sha1_hash` | POST |
| Hash | `/sha256_hash` | POST |
| Hash | `/sha512_hash` | POST |
| Hash | `/crc32_checksum` | POST |
| Web | `/ping` | GET |
| Web | `/health` | GET |
| Web | `/client_ip` | GET |
| Web | `/user_agent` | GET |
| Web | `/ip_reverse_lookup/{ip}` | GET |
| Web | `/domain_ip_lookup/{domain}` | GET |
| Web | `/storage` | POST / GET |
| Web | `/url_shortener/{url}` | GET |
| Web | `/webhook_capture` | POST / GET |
| Web | `/webhook_action` | POST / GET |
| Crypto | `/solana/generate_new_wallet` | GET |
| Crypto | `/solana/balance/{address}` | GET |
| Crypto | `/bitcoin/generate_new_wallet` | GET |
| Crypto | `/bitcoin/balance/{address}` | GET |
| Crypto | `/ethereum/generate_new_wallet` | GET |
| Crypto | `/ethereum/balance/{address}` | GET |

---

## Notes

- All responses are JSON
- POST endpoints accept JSON `{"data": "..."}`, plain text (`Content-Type: text/plain`), or file uploads
- Storage, URL Shortener, Webhook Capture, and Webhook Action data auto-expire after 24 hours
- No rate limit — please use responsibly

---

**AI SENSE AS** · [aisenseapi.com](https://aisenseapi.com)  
Postboks 1202 Vika, 0110 Oslo, Norway

MIT License
