# Free Public REST APIs - AI SENSE AS

No API key | No sign-up | No cost

Provided by **[AI SENSE AS](https://aisenseapi.com)** (Oslo, Norway).
Full endpoint reference: [`API.md`](API.md) | Repo: [github.com/aisenseapi/aisense-free-public-rest-apis](https://github.com/aisenseapi/aisense-free-public-rest-apis)

**Base URL:** `https://aisenseapi.com/services/v1/`

## Free public MCP endpoints

AI agents can connect directly to nine AI SENSE workflow tools at:

`https://aisenseapi.com/mcp`

The AI SENSE MCP server covers human approval, webhook capture, temporary
storage, URL shortening, time and UUIDs. It needs no account or API key. See
[`MCP.md`](MCP.md) for the tool list, data boundary and client examples.

Verifyum has its own dedicated MCP endpoint at
`https://api.verifyum.com/mcp`. It exposes the three Verifyum proof operations
without an account or API key. File hashing still happens on the agent's
machine. The browser flow, public HTTP API and published protocol remain
available. The official MCP registry lists it as `com.verifyum/mcp` version
`0.1.0`.

---

## SpeedUp (.su) - token cost, measured properly

Every serialization format marketed for LLM input ships a token-saving claim
measured against a single tokenizer. Agent traffic crosses vendors, so we
measured instead of assumed: six formats and 33 single-construct probes,
priced by five vocabulary families (OpenAI o200k, DeepSeek, Qwen,
SentencePiece, Tekken), with each provider's own token counter as ground
truth.

- [`SU-PROFILE.md`](SU-PROFILE.md) - the SpeedUp profile: eight writing
  conventions for agent-to-agent text, each citing its measured price tag
- [`speedup/`](speedup/) - the measurement rig (Python, standard library
  only), corpus, probes and raw numbers; rerun everything with your own keys
- [The study](https://aisense.no/tokenizer-cost-study) - what survived
  measurement, what did not, and why we decided against shipping yet another
  format

Headline numbers: plain TSV averages 0.82x minified JSON across the
five-vocabulary union and beats the token-oriented formats on every model;
declaring columns once and sending values positionally is the entire
mechanism (minus 34 percent per key-value pair); base64 costs 3.9-4.6x the
plaintext it encodes; and single-letter key dictionaries lose to full keys
on four of five vocabularies.

---

## Why this exists

Most utility APIs require sign-up, rate limit tiers, or pricing for basic
operations. This collection skips all of that. Drop a URL into curl, Python,
JavaScript, or an LLM tool definition and it just works.

The collection covers two tiers of usefulness:

- **Workflow endpoints** - the ones that solve real problems in pipelines and agent systems
- **Standard utilities** - hashing, encoding, UUIDs, time, crypto - the building blocks

---

## Three things to know before you write a client

These are service-wide and they decide how your error handling has to look.
Every response shape in this repo was verified against production.

**The response key is named after the endpoint.** `/md5_hash` returns
`md5_hash`, `/random_color` returns `random_color`, `/ping` returns `ping`.
There is no generic `data` or `result` wrapper. Do not guess the key -
[`API.md`](API.md) lists every one.

**Errors are `{"error": "message"}` with a real HTTP status.** Uniform since
2026-08-17: 400 is your mistake, 404 an unknown id or endpoint, 429 the rate
limit, 500 our failure, 502/504 an upstream. Branch on the status or on the
`error` key - both are trustworthy, and every error body kept its exact
wording through the change, so older clients keep working.

**There is a rate limit: 5000 requests per IP per 24 hours.** Exceeding it
returns HTTP 429 in the same flat error shape as everything else.

---

## The high-value endpoints

### Webhook Action - human-in-the-loop for agents

The standout endpoint for AI and automation work. When an automated pipeline
needs a human decision before continuing, this handles the whole pattern with
zero backend setup.

**How it works:**

1. `POST` a form definition (radio buttons, dropdowns, text fields, checkboxes)
2. Get back a `form_url` and a `result_url`
3. Send the `form_url` to a human via email or Slack
4. Poll `result_url` until `status` changes from `pending` to `answered`

```bash
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
          { "value": "reject", "label": "Reject" }
        ]
      },
      { "type": "textarea", "name": "comment", "label": "Notes (optional)" }
    ]
  }'
```

```json
{
  "ok": true,
  "action_id": "9e0e6d3b-1a45-44c5-9e0b-92f5f3bdb2f1",
  "form_url": "https://aisenseapi.com/services/v1/webhook_action/9e0e6d3b-.../form",
  "result_url": "https://aisenseapi.com/services/v1/webhook_action/9e0e6d3b-...",
  "expire_timestamp": 1786959912,
  "expire_datetime": "2026-08-17T09:45:12Z"
}
```

Poll for the answer:

```bash
curl https://aisenseapi.com/services/v1/webhook_action/{action_id}
# "status": "pending" -> "answered", with the submission under "response"
```

Field types: `radio`, `select`, `text`, `textarea`, `checkbox`. `options`
accepts plain strings or `{"value": ..., "label": ...}` objects. Expires after
24 hours.

---

### Webhook Capture - inspect any inbound HTTP request

Create a capture session, get a unique URL, point any external service at it
(Stripe, GitHub, Shopify), and read back the full request - method, headers,
query parameters, IP, and parsed body. No ngrok, no local tunnel, no server.

```bash
# 1. Create a session
curl -X POST https://aisenseapi.com/services/v1/webhook_capture
# -> { "ok": true, "capture_id": "...", "update_url": "...", "read_url": "...", "expire_timestamp": ... }

# 2. Point your webhook sender at update_url, with any HTTP method
curl -X POST {update_url} -H "Content-Type: application/json" -d '{"event":"payment.created"}'

# 3. Read it back
curl https://aisenseapi.com/services/v1/webhook_capture/{capture_id}
```

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
    "body": { "json": { "event": "payment.created" }, "text": null, "base64": null, "raw_length": 28 }
  }
}
```

Expires after 24 hours.

---

### Storage - ephemeral key-value store for pipelines

Post any JSON, text, or file. Get back a UUID. Retrieve it from anywhere -
another machine, a different agent call, a downstream pipeline step.

**The body is stored verbatim.** Whatever you send is exactly what comes back;
no wrapper is added or removed.

```bash
curl -X POST https://aisenseapi.com/services/v1/storage \
  -H "Content-Type: application/json" \
  -d '{"result": 42, "status": "complete"}'
# -> { "storage_id": "550e8400-e29b-41d4-a716-446655440000", "expire_timestamp": 1738457158 }

curl https://aisenseapi.com/services/v1/storage/550e8400-e29b-41d4-a716-446655440000
# -> {"result": 42, "status": "complete"}
```

Expires after 24 hours.

---

### URL Shortener

```bash
curl "https://aisenseapi.com/services/v1/url_shortener/https://example.com/very/long/path"
# -> { "short_url": "https://307.fi/KtNshX2B", "expire_timestamp": 1786959715 }
```

Expires after 24 hours.

---

### IP Reverse Lookup

```bash
curl https://aisenseapi.com/services/v1/ip_reverse_lookup/8.8.8.8
```

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

`city` and `place` are frequently `null`, and the coordinates fall back to the
country centroid when the city is unknown. Also available: resolve a domain to
its IP.

```bash
curl https://aisenseapi.com/services/v1/domain_ip_lookup/example.com
# -> { "domain": "example.com", "ip": "104.20.23.154" }
```

---

## Standard utilities

### Hashing - MD5, SHA1, SHA256, SHA512, CRC32

Accepts JSON, plain text (`Content-Type: text/plain`), or a file upload.
**Each returns a key named after the algorithm, not `hash`.**

```bash
curl -X POST https://aisenseapi.com/services/v1/sha256_hash \
  -H "Content-Type: application/json" -d '{"data": "Hello"}'
# -> { "sha256_hash": "185f8db32271fe25f561a6fc938b2e264306ec304eda518007d1764826381969" }
```

`md5_hash` | `sha1_hash` | `sha256_hash` | `sha512_hash` | `crc32_checksum`

`crc32_checksum` returns an integer, not a hex string.

---

### Encoding - Base64, Base58, Base32, JWT, QR Code

```bash
# Encode
curl -X POST https://aisenseapi.com/services/v1/base64_encode \
  -H "Content-Type: application/json" -d '{"data": "Hello world"}'
# -> { "base64_encoded_data": "SGVsbG8gd29ybGQ=" }

# Decode - returns the raw bytes, not JSON
curl -X POST https://aisenseapi.com/services/v1/base64_decode \
  -H "Content-Type: application/json" -d '{"data": "SGVsbG8gd29ybGQ="}'
# -> Hello world

# ...unless you ask for JSON
curl -X POST https://aisenseapi.com/services/v1/base64_decode \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -d '{"data": "eyJrZXkiOiJ2YWx1ZSJ9"}'
# -> { "type": "json", "decoded_data": { "key": "value" } }
```

The three decoders (`base64_decode`, `base58_decode`, `base32_decode`) answer
with `application/octet-stream` unless you send `Accept: application/json`.
This is the one place the API is not JSON.

**JWT - `data` takes the claims as a JSON object, or as a string containing
JSON.** Both forms produce the same token.

```bash
curl -X POST https://aisenseapi.com/services/v1/jwt_encode \
  -H "Content-Type: application/json" \
  -d '{"data": {"user": "alice"}, "secret": "my-secret-key"}'
# -> { "jwt": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." }
```

`jwt_decode` returns `decoded_payload`.

**QR - the request field is `payload`, with `data` accepted as an alias.**

```bash
curl -X POST https://aisenseapi.com/services/v1/qrcode_encode \
  -H "Content-Type: application/json" -d '{"payload": "https://example.com"}'
# -> { "qrcode_image": "iVBORw0KGgoAAAANSUhEUgAA...", "image_type": "png" }
```

`qrcode_decode` takes the same `payload` field (or a file upload) and returns
`qrcode_content`.

---

### Random - UUID, GUID, number, color, password

```bash
curl https://aisenseapi.com/services/v1/uuid            # { "uuid": "..." }
curl https://aisenseapi.com/services/v1/guid            # { "guid": "..." }
curl https://aisenseapi.com/services/v1/random_color    # { "random_color": "#9b6bbf" }
curl https://aisenseapi.com/services/v1/random_number/1/100
# -> { "random_number": 73, "range": { "from": 1, "to": 100 } }
curl https://aisenseapi.com/services/v1/password/16
# -> { "password": "jFehS]AKGx9wl[jp", "password_length": 16 }
```

A single argument to `random_number` is the upper bound, with the lower bound
fixed at 1.

---

### Time - Datetime, Timestamp, Timezones

```bash
curl https://aisenseapi.com/services/v1/datetime            # UTC
curl https://aisenseapi.com/services/v1/datetime/+0200      # with offset
curl https://aisenseapi.com/services/v1/timestamp
curl https://aisenseapi.com/services/v1/microtimestamp
curl https://aisenseapi.com/services/v1/timezones
curl https://aisenseapi.com/services/v1/swatchinternettime
```

The offset must be **four digits** with an optional sign - `+0200`, `-0530`,
`0100`. An hour-only value like `1` is not a valid route.

`/timezones` returns objects, not strings:
`{"timezones": [{"timezone": "Europe/Oslo", "offset": "+0200"}, ...]}`.

---

### Web utilities - Ping, Health, Client IP, User Agent

```bash
curl https://aisenseapi.com/services/v1/ping        # { "ping": "pong" }
curl https://aisenseapi.com/services/v1/health      # { "status": "ok", "microtimestamp": ... }
curl https://aisenseapi.com/services/v1/client_ip   # { "ip": "203.0.113.42" }
curl https://aisenseapi.com/services/v1/user_agent  # { "user_agent": "curl/8.5.0" }
```

---

### Crypto - Wallet generation and balance lookup

```bash
curl https://aisenseapi.com/services/v1/solana/generate_new_wallet
curl https://aisenseapi.com/services/v1/bitcoin/generate_new_wallet
curl https://aisenseapi.com/services/v1/ethereum/generate_new_wallet

curl https://aisenseapi.com/services/v1/solana/balance/{address}
curl https://aisenseapi.com/services/v1/bitcoin/balance/{address}
curl https://aisenseapi.com/services/v1/ethereum/balance/{address}
```

All three generators return `public_address` (Bitcoin also returns
`private_key_wif`). Ethereum balances come back as **strings** -
`{"wallet": "0x...", "balance_eth": "6.634527787345637061", "balance_wei": "6634527787345637061"}`
- because Wei routinely exceeds `2^53`, the largest integer a JSON number
survives in a JavaScript client.

> Wallet generation is for development and testing only. A key produced by a
> public HTTP endpoint has crossed a network you do not control. Never fund one.

---

## Quick start by language

**curl**
```bash
curl https://aisenseapi.com/services/v1/uuid
```

**Python** - zero dependencies, standard library only.
```python
from aisense_api import AISenseAPI
api = AISenseAPI()

print(api.get_uuid()["uuid"])
print(api.hash_sha256("Hello")["sha256_hash"])
print(api.ip_reverse_lookup("8.8.8.8")["country"])
```

**JavaScript** - Node 18+ or any modern browser, native fetch.
```javascript
import { AISenseAPI } from './aisense-api.js'
const api = new AISenseAPI()

console.log((await api.getUUID()).uuid)
console.log((await api.hashSHA256('Hello')).sha256_hash)
console.log((await api.ipReverseLookup('8.8.8.8')).country)
```

Both clients return the parsed response, and every method's docstring names the
exact response key. They also raise a clear error when a path does not exist,
rather than letting the debug echo surface as a JSON parse failure.

**LLM function calling (OpenAI, Gemini, Mistral, ...)**
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

**Claude** - [`SKILL.md`](SKILL.md) is included. Add it to Claude's context and
it will use these APIs as tools automatically.

---

## What's in the repo

| File | Purpose |
|------|---------|
| [`API.md`](API.md) | Full endpoint reference - the verified source of truth |
| [`MCP.md`](MCP.md) | Remote MCP server, tool list and client examples |
| [`server.json`](server.json) | Metadata for the official MCP Registry |
| [`aisense_api.py`](aisense_api.py) | Python client (standard library only) |
| [`aisense-api.js`](aisense-api.js) | JavaScript ESM client |
| [`openai-tools.json`](openai-tools.json) | Tool definitions for any LLM with function calling |
| [`SKILL.md`](SKILL.md) | Claude skill file |
| [`test.sh`](test.sh) | Asserts on response bodies; exits `1` on failure (CI-friendly) |
| [`tools/check-text.php`](tools/check-text.php) | Checks documentation punctuation before commit |

`test.sh` checks response contents, not status codes. Since this API answers 200
for most failures, a status-code-only suite would pass against a completely
broken endpoint.

---

## Endpoint summary

All paths are relative to `https://aisenseapi.com/services/v1/`

| Category | Endpoint | Method | Response key(s) |
|----------|----------|--------|-----------------|
| Time | `/datetime[/{offset}]` | GET | `datetime` |
| Time | `/timestamp` | GET | `timestamp` |
| Time | `/microtimestamp` | GET | `microtimestamp` |
| Time | `/timezones[/{offset}]` | GET | `timezones` |
| Time | `/swatchinternettime` | GET | `beat`, `date` |
| Time | `/timestamp_convert` | POST | `input`, `detected`, `timestamp`, `datetime`, `rfc2822`, `utc_datetime` |
| Random | `/random_number[/{from}[/{to}]]` | GET | `random_number`, `range` |
| Random | `/random_color` | GET | `random_color` |
| Random | `/uuid` | GET | `uuid` |
| Random | `/guid` | GET | `guid` |
| Random | `/password[/{length}]` | GET | `password`, `password_length` |
| Transform | `/base64_encode` | POST | `base64_encoded_data` |
| Transform | `/base64_decode` | POST | raw bytes, or `type` + `decoded_data` |
| Transform | `/base58_encode` | POST | `base58_encoded_data` |
| Transform | `/base58_decode` | POST | raw bytes, or `type` + `decoded_data` |
| Transform | `/base32_encode` | POST | `base32_encoded_data` |
| Transform | `/base32_decode` | POST | raw bytes, or `type` + `decoded_data` |
| Transform | `/slugify` | POST | `slug` |
| Transform | `/jwt_encode` | POST | `jwt` |
| Transform | `/jwt_decode` | POST | `decoded_payload` |
| Transform | `/qrcode_encode` | POST | `qrcode_image`, `image_type` |
| Transform | `/qrcode_decode` | POST | `qrcode_content` |
| Hash | `/md5_hash` | POST | `md5_hash` |
| Hash | `/sha1_hash` | POST | `sha1_hash` |
| Hash | `/sha256_hash` | POST | `sha256_hash` |
| Hash | `/sha512_hash` | POST | `sha512_hash` |
| Hash | `/crc32_checksum` | POST | `crc32_checksum` |
| Hash | `/hash_verify` | POST | `match`, `algorithm`, `computed` |
| Web | `/ping` | GET | `ping` |
| Web | `/health` | GET | `status`, `microtimestamp` |
| Web | `/client_ip` | GET | `ip` |
| Web | `/html2pdf` | POST | `storage_id`, `storage_url`, `expire_timestamp` |
| Web | `/user_agent` | GET | `user_agent` |
| Web | `/ip_reverse_lookup/{ip}` | GET | `ip`, `country`, `city`, `location`, `place`, `timezone` |
| Web | `/domain_ip_lookup/{domain}` | GET | `domain`, `ip` |
| Web | `/email_validate` | POST | `email`, `valid_syntax`, `domain`, `has_mx`, `mx_hosts` |
| Web | `/storage` | POST / GET | `storage_id`, `expire_timestamp` |
| Web | `/url_shortener/{url}` | GET | `short_url`, `expire_timestamp` |
| Web | `/webhook_capture` | POST / GET | `capture_id`, `update_url`, `read_url` |
| Web | `/webhook_action` | POST / GET | `action_id`, `form_url`, `result_url` |
| Web | `/webhook_schedule` | POST / GET | `schedule_id`, `status`, `attempts`, `http_status` |
| Web | `/validate/{type}` | POST | `type`, `valid`, per-check fields |
| Crypto | `/solana/generate_new_wallet` | GET | `private_key`, `public_address` |
| Crypto | `/solana/balance/{address}` | GET | `wallet`, `balance_sol`, `balance_lamports` |
| Crypto | `/bitcoin/generate_new_wallet` | GET | `private_key`, `private_key_wif`, `public_address` |
| Crypto | `/bitcoin/balance/{address}` | GET | `wallet`, `final_balance_btc`, `final_balance_sats` |
| Crypto | `/ethereum/generate_new_wallet` | GET | `private_key`, `public_address` |
| Crypto | `/ethereum/balance/{address}` | GET | `wallet`, `balance_eth`, `balance_wei` |

---

## Notes

- POST endpoints accept JSON, plain text (`Content-Type: text/plain`), or file uploads
- Storage, URL Shortener, Webhook Capture and Webhook Action auto-expire after 24 hours
- `Access-Control-Allow-Origin: *` is set on every response, so these are callable from a browser
- Rate limit: 5000 requests per IP per 24 hours

---

**AI SENSE AS** | [aisenseapi.com](https://aisenseapi.com)
Postboks 1202 Vika, 0110 Oslo, Norway

MIT License
