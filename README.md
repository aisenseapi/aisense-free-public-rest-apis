# Free Public REST APIs — AI SENSE AS

A curated collection of free, public, no-authentication REST APIs for developers and LLM integrations.  
Provided by [AI SENSE AS](https://www.aisense.no) (Oslo, Norway).

**31 endpoints · 6 categories · No API key · No sign-up · No cost**

---

## API Categories

| Category | Endpoints |
|----------|-----------|
| ⏱ Time | Datetime, Timestamp, Microtimestamp, Timezones, Swatch Internet Time |
| 🎲 Random | Random Number, Random Color, UUID, GUID |
| 🔄 Transform | Base64, Base58, Base32 (encode/decode), JWT (encode/decode), QR Code (encode/decode) |
| 🔐 Hash | MD5, SHA1, SHA256, SHA512 |
| 🌐 Web | Ping, Health, Client IP, IP Lookup, Storage, URL Shortener, Webhook Capture, Webhook Action |
| 🪙 Crypto | Solana, Bitcoin, Ethereum wallet generation |

→ Full reference: [`API.md`](./API.md)

---

## What's included

| File | Who it's for |
|------|-------------|
| [`API.md`](./API.md) | Everyone — full endpoint reference with examples |
| [`aisense_api.py`](./aisense_api.py) | Python developers |
| [`aisense-api.js`](./aisense-api.js) | JavaScript / Node.js developers |
| [`openai-tools.json`](./openai-tools.json) | LLM developers using function calling (OpenAI, Gemini, Mistral, etc.) |
| [`SKILL.md`](./SKILL.md) | Claude users |
| [`test.sh`](./test.sh) | Anyone who wants to verify all endpoints are live |

---

## Quick examples

### curl
```bash
curl https://aisenseapi.com/services/v1/uuid

curl https://aisenseapi.com/services/v1/datetime

curl -X POST https://aisenseapi.com/services/v1/sha256 \
  -H "Content-Type: application/json" \
  -d '{"data": "Hello"}'

curl -X POST https://aisenseapi.com/services/v1/base64_encode \
  -H "Content-Type: application/json" \
  -d '{"data": "Hello, world!"}'
```

### Python
```python
from aisense_api import AISenseAPI
api = AISenseAPI()

print(api.get_uuid())
print(api.hash_sha256("Hello"))
print(api.ip_lookup("8.8.8.8"))
```

### JavaScript
```js
import { AISenseAPI } from './aisense-api.js'
const api = new AISenseAPI()

console.log(await api.getUUID())
console.log(await api.hashSHA256('Hello'))
console.log(await api.ipLookup('8.8.8.8'))
```

### LLM function calling (OpenAI, Gemini, Mistral, etc.)
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

---

## Testing

Verify all 31 endpoints are live:

```bash
chmod +x test.sh
./test.sh
```

Exits with code `1` on any failure — suitable for CI/CD pipelines.

---

## Notes

- All responses are JSON
- POST endpoints accept JSON (`{"data": "..."}`), plain text, or file uploads
- Storage, URL Shortener, Webhook Capture, and Webhook Action data auto-expire after **24 hours**
- Crypto endpoints are for **development and testing only**
- No documented rate limits — please use responsibly

---

## Provider

**AI SENSE AS** · [aisense.no](https://www.aisense.no)  
Postboks 1202 Vika, 0110 Oslo, Norway

---

## License

MIT
