/**
 * aisense-api.js — JavaScript client for the AI SENSE AS Free Public REST APIs
 * https://aisenseapi.com
 *
 * Works in Node.js (18+) and all modern browsers. No dependencies — native fetch.
 *
 * Usage (ESM):
 *   import { AISenseAPI } from './aisense-api.js'
 *   const api = new AISenseAPI()
 *   console.log((await api.getUUID()).uuid)
 *   console.log((await api.hashSHA256('Hello')).sha256_hash)
 *
 * Every method resolves to the parsed JSON response, and each JSDoc block names
 * the exact response key. The upstream API is not consistent about naming —
 * /md5_hash returns `md5_hash`, /ping returns `ping`, /random_color returns
 * `random_color` — so do not guess the key.
 *
 * Two endpoints answer with raw bytes instead of JSON (base64Decode and
 * base32Decode); those resolve to a string when the payload is valid UTF-8 and
 * to a Uint8Array otherwise.
 *
 * Known upstream bugs, verified against production:
 *   - /base58_decode always fails with "Invalid Base32 input." — it cannot
 *     decode the output of /base58_encode. base58Decode() rejects until fixed.
 *   - /qrcode_encode prepends a PHP warning to its JSON body. This client
 *     strips it and records it in `lastServerNotice`.
 *   - /ethereum/balance returns "Failed to retrieve balance data."
 *   - Unknown paths return HTTP 200 with a debug echo instead of 404. This
 *     client detects that and rejects with a clear message.
 */

const BASE_URL = 'https://aisenseapi.com/services/v1'

// Unknown paths do not 404 — they return HTTP 200 with a body shaped like
//   ["<your-ip>",1786873281]["\/services\/v1\/random","1","random"]
// Detecting it turns a confusing JSON parse error into a clear message.
const DEBUG_ECHO = /^\[".*?",\d+\]\["/

export class AISenseAPIError extends Error {
  constructor(message, { status, body } = {}) {
    super(message)
    this.name = 'AISenseAPIError'
    this.status = status
    this.body = body
  }
}

export class AISenseAPI {
  constructor(baseUrl = BASE_URL) {
    this.baseUrl = baseUrl.replace(/\/$/, '')
    /**
     * Set when the server prepends a PHP warning to a JSON response
     * (currently /qrcode_encode). Null when the last call was clean.
     * @type {string|null}
     */
    this.lastServerNotice = null
  }

  // ── Internal helpers ───────────────────────────────────────────────────────

  async #fetch(path, method, body) {
    const init = { method }
    if (method === 'POST') {
      init.headers = { 'Content-Type': 'application/json' }
      init.body = JSON.stringify(body)
    }
    return fetch(`${this.baseUrl}${path}`, init)
  }

  async #request(path, method = 'GET', body) {
    const res = await this.#fetch(path, method, body)
    const text = await res.text()

    if (DEBUG_ECHO.test(text)) {
      throw new AISenseAPIError(
        `${method} ${path} is not a known endpoint — the API answered with its ` +
          `debug echo instead of a 404. Check the path against API.md.`,
        { status: res.status, body: text.slice(0, 200) }
      )
    }

    const { json, notice } = stripServerNotice(text)
    this.lastServerNotice = notice

    let parsed
    try {
      parsed = JSON.parse(json)
    } catch (err) {
      throw new AISenseAPIError(
        `${method} ${path} returned a body that is not JSON: ${json.slice(0, 200)}`,
        { status: res.status, body: text.slice(0, 500) }
      )
    }

    if (parsed && typeof parsed === 'object' && 'error' in parsed) {
      throw new AISenseAPIError(`${method} ${path} failed: ${parsed.error}`, {
        status: res.status,
        body: text.slice(0, 500),
      })
    }
    if (!res.ok) {
      throw new AISenseAPIError(`${method} ${path} failed with HTTP ${res.status}`, {
        status: res.status,
        body: text.slice(0, 500),
      })
    }

    return parsed
  }

  /** For endpoints that answer with application/octet-stream, not JSON. */
  async #requestBinary(path, body) {
    const res = await this.#fetch(path, 'POST', body)
    const buffer = new Uint8Array(await res.arrayBuffer())
    const text = new TextDecoder('utf-8', { fatal: false }).decode(buffer)

    if (DEBUG_ECHO.test(text)) {
      throw new AISenseAPIError(`POST ${path} is not a known endpoint.`, {
        status: res.status,
        body: text.slice(0, 200),
      })
    }

    // Errors still come back as JSON even though success is raw bytes.
    if (text.trimStart().startsWith('{')) {
      let parsed
      try {
        parsed = JSON.parse(text)
      } catch {
        parsed = null
      }
      if (parsed && typeof parsed === 'object' && 'error' in parsed) {
        throw new AISenseAPIError(`POST ${path} failed: ${parsed.error}`, {
          status: res.status,
          body: text.slice(0, 500),
        })
      }
    }

    if (!res.ok) {
      throw new AISenseAPIError(`POST ${path} failed with HTTP ${res.status}`, {
        status: res.status,
        body: text.slice(0, 500),
      })
    }

    try {
      return new TextDecoder('utf-8', { fatal: true }).decode(buffer)
    } catch {
      return buffer
    }
  }

  #get(path) {
    return this.#request(path, 'GET')
  }

  #post(path, body) {
    return this.#request(path, 'POST', body)
  }

  // ── Time ──────────────────────────────────────────────────────────────────

  /**
   * Current datetime in ISO 8601. Response key: `datetime`.
   *
   * `offset` must be a four-digit UTC offset such as `'+0200'`, `'-0530'` or
   * `'0100'`. Hour-only values like `'1'` are NOT accepted by the API and
   * resolve to an unknown path.
   */
  getDatetime(offset) {
    return this.#get(offset !== undefined ? `/datetime/${offset}` : '/datetime')
  }

  /** Current Unix timestamp in seconds. Response key: `timestamp`. */
  getTimestamp() {
    return this.#get('/timestamp')
  }

  /** Unix timestamp with microsecond precision. Response key: `microtimestamp`. */
  getMicrotimestamp() {
    return this.#get('/microtimestamp')
  }

  /**
   * All timezones, optionally filtered by a four-digit offset (`'+0200'`).
   * Response key: `timezones` — a list of `{ timezone, offset }` objects, not
   * a list of strings.
   */
  getTimezones(offset) {
    return this.#get(offset !== undefined ? `/timezones/${offset}` : '/timezones')
  }

  /** Swatch Internet Time. Response keys: `beat` (e.g. `'@444'`) and `date`. */
  getSwatchTime() {
    return this.#get('/swatchinternettime')
  }

  // ── Random ────────────────────────────────────────────────────────────────

  /**
   * Random integer. Response keys: `random_number` and `range`.
   *
   * No arguments defaults to 1–6. A single argument is treated by the API as
   * the upper bound, with the lower bound fixed at 1.
   */
  getRandomNumber(from, to) {
    if (from === undefined) return this.#get('/random_number')
    if (to === undefined) return this.#get(`/random_number/${from}`)
    return this.#get(`/random_number/${from}/${to}`)
  }

  /** Random hex colour. Response key: `random_color`. */
  getRandomColor() {
    return this.#get('/random_color')
  }

  /** Generate a UUID v4. Response key: `uuid`. */
  getUUID() {
    return this.#get('/uuid')
  }

  /** Generate a GUID. Response key: `guid`. */
  getGUID() {
    return this.#get('/guid')
  }

  /** Random password, 12 characters by default. Response keys: `password`, `password_length`. */
  getPassword(length) {
    return this.#get(length !== undefined ? `/password/${length}` : '/password')
  }

  // ── Transform ─────────────────────────────────────────────────────────────

  /** Response key: `base64_encoded_data`. */
  base64Encode(data) {
    return this.#post('/base64_encode', { data })
  }

  /**
   * Decode Base64, resolving to a string (UTF-8) or a Uint8Array.
   *
   * This client deliberately sends no `Accept` header, which makes the endpoint
   * answer with `application/octet-stream` — the decoded bytes and nothing else.
   * Send `Accept: application/json` instead and the same endpoint wraps the
   * result as `{ type: 'json'|'binary', decoded_data }`, base64-re-encoding the
   * payload in the binary case. Raw is the more useful default; use the JSON
   * form when you need the type tag.
   */
  base64Decode(data) {
    return this.#requestBinary('/base64_decode', { data })
  }

  /** Response key: `base58_encoded_data`. */
  base58Encode(data) {
    return this.#post('/base58_encode', { data })
  }

  /**
   * Decode Base58.
   *
   * BROKEN UPSTREAM: the server validates the input with its Base32 decoder and
   * rejects everything with "Invalid Base32 input." — including strings produced
   * by {@link base58Encode}. This rejects with AISenseAPIError until the server
   * is fixed. Kept here so the bug stays visible.
   */
  base58Decode(data) {
    return this.#requestBinary('/base58_decode', { data })
  }

  /** Response key: `base32_encoded_data`. */
  base32Encode(data) {
    return this.#post('/base32_encode', { data })
  }

  /** Decode Base32. Answers with raw bytes, not JSON — see {@link base64Decode}. */
  base32Decode(data) {
    return this.#requestBinary('/base32_decode', { data })
  }

  /**
   * Encode a payload into an HS256 JWT. Response key: `jwt`.
   *
   * The API requires `data` to be a *string*. An object is serialised to JSON
   * here; passing an object straight through returns
   * "Invalid data provided. Expected a string."
   */
  jwtEncode(payload, secret) {
    const data = typeof payload === 'string' ? payload : JSON.stringify(payload)
    return this.#post('/jwt_encode', { data, secret })
  }

  /** Decode a JWT. Response key: `decoded_payload`. */
  jwtDecode(token, secret) {
    return this.#post('/jwt_decode', { data: token, secret })
  }

  /**
   * Generate a QR code. Response keys: `qrcode_image` (Base64 PNG) and `image_type`.
   *
   * The request field is `payload`, not `data`.
   *
   * The server currently prepends a PHP warning to the JSON body because it
   * cannot write a temp file. This client strips it; inspect `lastServerNotice`
   * to see whether it fired.
   */
  qrcodeEncode(payload) {
    return this.#post('/qrcode_encode', { payload })
  }

  /**
   * Decode a Base64-encoded QR code image. Response key: `qrcode_content`.
   * The request field is `payload`, not `data`.
   */
  qrcodeDecode(imageBase64) {
    return this.#post('/qrcode_decode', { payload: imageBase64 })
  }

  // ── Hash ──────────────────────────────────────────────────────────────────

  /** Response key: `md5_hash`. */
  hashMD5(data) {
    return this.#post('/md5_hash', { data })
  }

  /** Response key: `sha1_hash`. */
  hashSHA1(data) {
    return this.#post('/sha1_hash', { data })
  }

  /** Response key: `sha256_hash`. */
  hashSHA256(data) {
    return this.#post('/sha256_hash', { data })
  }

  /** Response key: `sha512_hash`. */
  hashSHA512(data) {
    return this.#post('/sha512_hash', { data })
  }

  /** CRC32 checksum. Response key: `crc32_checksum` — an integer, not a hex string. */
  crc32Checksum(data) {
    return this.#post('/crc32_checksum', { data })
  }

  // ── Web ───────────────────────────────────────────────────────────────────

  /** Connectivity check. Response key: `ping` (value `'pong'`). */
  ping() {
    return this.#get('/ping')
  }

  /** Health check. Response keys: `status` and `microtimestamp`. */
  health() {
    return this.#get('/health')
  }

  /** Your public IP address. Response key: `ip`. */
  getClientIP() {
    return this.#get('/client_ip')
  }

  /** The User-Agent string the API saw. Response key: `user_agent`. */
  getUserAgent() {
    return this.#get('/user_agent')
  }

  /**
   * Reverse IP lookup. Response keys: `ip`, `country`, `city`, `location`
   * (`lat`/`lng`), `place`, `timezone`. `city` and `place` are often null.
   */
  ipReverseLookup(ip) {
    return this.#get(`/ip_reverse_lookup/${ip}`)
  }

  /** Resolve a domain to an IP. Response keys: `domain` and `ip`. */
  domainIPLookup(domain) {
    return this.#get(`/domain_ip_lookup/${domain}`)
  }

  /**
   * Store data for 24 hours. Response keys: `storage_id` and `expire_timestamp`.
   *
   * The request body is stored verbatim, so whatever you pass here is exactly
   * what {@link storageGet} gives back — no `data` wrapper is added or removed.
   */
  storageSet(data) {
    return this.#post('/storage', data)
  }

  /** Retrieve stored data by its `storage_id`, returned verbatim. */
  storageGet(storageId) {
    return this.#get(`/storage/${storageId}`)
  }

  /**
   * Shorten a URL for 24 hours. Response keys: `short_url` and `expire_timestamp`.
   * This is a GET with the target URL inline in the path — not a POST.
   */
  shortenURL(url) {
    return this.#get(`/url_shortener/${url}`)
  }

  /**
   * Open a capture session. Response keys: `ok`, `capture_id`, `update_url`,
   * `read_url`, `expire_timestamp`. Point any HTTP client at `update_url`, then
   * read it back with {@link webhookCaptureRead}.
   */
  webhookCaptureCreate() {
    return this.#post('/webhook_capture', {})
  }

  /**
   * Read a captured request. Response keys: `ok`, `capture_id`,
   * `captured_at_timestamp`, `captured_at_datetime`, `request`.
   */
  webhookCaptureRead(captureId) {
    return this.#get(`/webhook_capture/${captureId}`)
  }

  /**
   * Create a human-in-the-loop action form. Response keys: `ok`, `action_id`,
   * `form_url`, `result_url`, `expire_timestamp`, `expire_datetime`.
   *
   * `options` accepts either plain strings or `{ value, label }` objects:
   *
   *   [{ type: 'radio', name: 'decision', label: 'Approve?', required: true,
   *      options: [{ value: 'yes', label: 'Yes' }, { value: 'no', label: 'No' }] }]
   *
   * Field types: radio, select, text, textarea, checkbox.
   */
  webhookActionCreate(title, fields, description) {
    const body = { title, fields }
    if (description !== undefined) body.description = description
    return this.#post('/webhook_action', body)
  }

  /**
   * Poll for the answer to an action. Response keys: `ok`, `action_id`,
   * `status` (`'pending'` or `'answered'`), `created_at_timestamp`,
   * `created_at_datetime`, `expire_timestamp`, `expire_datetime`,
   * `answered_at_timestamp`, `answered_at_datetime`, `response`.
   */
  webhookActionResult(actionId) {
    return this.#get(`/webhook_action/${actionId}`)
  }

  // ── Crypto ────────────────────────────────────────────────────────────────

  /**
   * New Solana wallet. Response keys: `private_key`, `public_address`.
   * FOR DEVELOPMENT ONLY — never fund a wallet generated over a public API.
   */
  generateSolanaWallet() {
    return this.#get('/solana/generate_new_wallet')
  }

  /**
   * New Bitcoin wallet. Response keys: `private_key`, `private_key_wif`, `public_address`.
   * FOR DEVELOPMENT ONLY.
   */
  generateBitcoinWallet() {
    return this.#get('/bitcoin/generate_new_wallet')
  }

  /**
   * New Ethereum wallet. Response keys: `private_key`, `public_address`.
   * FOR DEVELOPMENT ONLY.
   */
  generateEthereumWallet() {
    return this.#get('/ethereum/generate_new_wallet')
  }

  /** Response keys: `wallet`, `balance_sol`, `balance_lamports`. */
  solanaBalance(address) {
    return this.#get(`/solana/balance/${address}`)
  }

  /** Response keys: `wallet`, `final_balance_btc`, `final_balance_sats`. */
  bitcoinBalance(address) {
    return this.#get(`/bitcoin/balance/${address}`)
  }

  /**
   * Ethereum balance.
   *
   * BROKEN UPSTREAM: currently answers "Failed to retrieve balance data." for
   * every address, so this rejects with AISenseAPIError.
   */
  ethereumBalance(address) {
    return this.#get(`/ethereum/balance/${address}`)
  }
}

/**
 * Split a leading PHP warning off a JSON body.
 *
 * /qrcode_encode emits a `Warning: file_put_contents(...)` line before its JSON
 * because the QR library cannot write its temp file.
 */
function stripServerNotice(text) {
  const trimmed = text.trimStart()
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
    return { json: trimmed, notice: null }
  }
  const brace = text.indexOf('{')
  if (brace === -1) return { json: trimmed, notice: null }
  return { json: text.slice(brace), notice: text.slice(0, brace).trim() }
}

// ── Example usage ─────────────────────────────────────────────────────────────

// Uncomment to run: node aisense-api.js

/*
const api = new AISenseAPI()

// Time
console.log((await api.getDatetime('+0200')).datetime)
console.log((await api.getTimestamp()).timestamp)

// Random
console.log((await api.getUUID()).uuid)
console.log((await api.getRandomColor()).random_color)
console.log((await api.getRandomNumber(1, 100)).random_number)
console.log((await api.getPassword(16)).password)

// Transform
const { base64_encoded_data } = await api.base64Encode('Hello, world!')
console.log('Base64:', base64_encoded_data)
console.log('Decoded:', await api.base64Decode(base64_encoded_data))

const { jwt } = await api.jwtEncode({ user: 'alice' }, 'my-secret')
console.log('JWT:', jwt)
console.log('Decoded:', (await api.jwtDecode(jwt, 'my-secret')).decoded_payload)

// Hash
console.log((await api.hashSHA256('Hello')).sha256_hash)
console.log((await api.crc32Checksum('Hello')).crc32_checksum)

// Web
console.log((await api.ping()).ping)
console.log((await api.getClientIP()).ip)
console.log((await api.ipReverseLookup('8.8.8.8')).country)

const stored = await api.storageSet({ hello: 'world' })
console.log('Stored:', stored.storage_id)
console.log('Retrieved:', await api.storageGet(stored.storage_id))

// Crypto (dev only)
console.log((await api.generateEthereumWallet()).public_address)

// Known upstream bugs
try {
  const { base58_encoded_data } = await api.base58Encode('Hello')
  await api.base58Decode(base58_encoded_data)
} catch (err) {
  console.log('base58Decode still broken:', err.message)
}

await api.qrcodeEncode('https://aisenseapi.com/')
if (api.lastServerNotice) {
  console.log('qrcodeEncode still leaking a PHP warning:', api.lastServerNotice.slice(0, 80), '...')
}
*/
