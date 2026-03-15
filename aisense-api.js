/**
 * aisense-api.js — JavaScript client for the AI SENSE AS Free Public REST APIs
 * https://www.aisense.no
 *
 * Works in Node.js (18+) and all modern browsers.
 * No dependencies — uses native fetch.
 *
 * Usage (ESM):
 *   import { AISenseAPI } from './aisense-api.js'
 *   const api = new AISenseAPI()
 *   console.log(await api.getUUID())
 *   console.log(await api.hashSHA256('Hello'))
 *
 * Usage (CommonJS / Node < 18):
 *   Replace fetch with node-fetch or undici.
 */

const BASE_URL = 'https://aisenseapi.com/services/v1'

export class AISenseAPI {
  constructor(baseUrl = BASE_URL) {
    this.baseUrl = baseUrl.replace(/\/$/, '')
  }

  // ── Internal helpers ───────────────────────────────────────────────────────

  async #get(path) {
    const res = await fetch(`${this.baseUrl}${path}`)
    if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
    return res.json()
  }

  async #post(path, body) {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`)
    return res.json()
  }

  // ── Time ──────────────────────────────────────────────────────────────────

  /** Current datetime in ISO 8601. Optional UTC offset (e.g. 1 for UTC+1). */
  getDatetime(offset) {
    const path = offset !== undefined ? `/time/datetime/${offset}` : '/time/datetime'
    return this.#get(path)
  }

  /** Current Unix timestamp (seconds). */
  getTimestamp() {
    return this.#get('/time/timestamp')
  }

  /** Current Unix timestamp with microsecond precision. */
  getMicrotimestamp() {
    return this.#get('/time/microtimestamp')
  }

  /** All timezones, optionally filtered by UTC offset. */
  getTimezones(offset) {
    const path = offset !== undefined ? `/time/timezones/${offset}` : '/time/timezones'
    return this.#get(path)
  }

  /** Current time in Swatch Internet Time (.beats). */
  getSwatchTime() {
    return this.#get('/time/swatchinternettime')
  }

  // ── Random ────────────────────────────────────────────────────────────────

  /** Random integer in [from, to]. Defaults to 1–6. */
  getRandomNumber(from = 1, to = 6) {
    return this.#get(`/random/number/${from}/${to}`)
  }

  /** Random hex color code. */
  getRandomColor() {
    return this.#get('/random/color')
  }

  /** Generate a UUID v4. */
  getUUID() {
    return this.#get('/random/uuid')
  }

  /** Generate a GUID. */
  getGUID() {
    return this.#get('/random/guid')
  }

  // ── Transform ─────────────────────────────────────────────────────────────

  base64Encode(data) {
    return this.#post('/transform/base64_encode', { data })
  }

  base64Decode(data) {
    return this.#post('/transform/base64_decode', { data })
  }

  base58Encode(data) {
    return this.#post('/transform/base58_encode', { data })
  }

  base58Decode(data) {
    return this.#post('/transform/base58_decode', { data })
  }

  base32Encode(data) {
    return this.#post('/transform/base32_encode', { data })
  }

  base32Decode(data) {
    return this.#post('/transform/base32_decode', { data })
  }

  /** Encode a JSON payload into a JWT (HS256). */
  jwtEncode(payload, secret) {
    return this.#post('/transform/jwt_encode', { data: payload, secret })
  }

  /** Decode a JWT and return its payload. */
  jwtDecode(token, secret) {
    return this.#post('/transform/jwt_decode', { data: token, secret })
  }

  /** Generate a QR code from text. Returns Base64-encoded PNG. */
  qrcodeEncode(data) {
    return this.#post('/transform/qrcode_encode', { data })
  }

  /** Decode a Base64-encoded QR code image. */
  qrcodeDecode(imageBase64) {
    return this.#post('/transform/qrcode_decode', { data: imageBase64 })
  }

  // ── Hash ──────────────────────────────────────────────────────────────────

  hashMD5(data) {
    return this.#post('/hash/md5', { data })
  }

  hashSHA1(data) {
    return this.#post('/hash/sha1', { data })
  }

  hashSHA256(data) {
    return this.#post('/hash/sha256', { data })
  }

  hashSHA512(data) {
    return this.#post('/hash/sha512', { data })
  }

  // ── Web ───────────────────────────────────────────────────────────────────

  /** Verify API connectivity. */
  ping() {
    return this.#get('/web/ping')
  }

  /** API health check with microsecond timestamp. */
  health() {
    return this.#get('/web/health')
  }

  /** Returns your public IP address. */
  getClientIP() {
    return this.#get('/web/ip')
  }

  /** Reverse IP lookup: country, city, coordinates, timezone. */
  ipLookup(ip) {
    return this.#get(`/web/ip_reverse_lookup/${ip}`)
  }

  /** Store data temporarily (24h TTL). Returns a UUID. */
  storageSet(data) {
    return this.#post('/web/storage', { data })
  }

  /** Retrieve stored data by UUID. */
  storageGet(uuid) {
    return this.#get(`/web/storage/${uuid}`)
  }

  /** Shorten a URL (24h TTL). */
  shortenURL(url) {
    return this.#post('/web/url_shortener', { url })
  }

  /** Capture and return the full incoming HTTP request (24h TTL). */
  webhookCapture(body = {}) {
    return this.#post('/web/webhook_capture', body)
  }

  /**
   * Create a human-in-the-loop action form (24h TTL).
   *
   * @param {string} title - Title shown on the form
   * @param {Array}  fields - Form fields, e.g.:
   *   [{ type: 'radio', name: 'approval', label: 'Approve?', options: ['Yes', 'No'] }]
   * @returns {{ action_id, form_url, result_url }}
   */
  webhookAction(title, fields) {
    return this.#post('/web/webhook_action', { title, fields })
  }

  // ── Crypto ────────────────────────────────────────────────────────────────

  /** Generate a new Solana wallet. FOR DEVELOPMENT ONLY. */
  generateSolanaWallet() {
    return this.#get('/crypto/solana/generate_new_wallet')
  }

  /** Generate a new Bitcoin wallet. FOR DEVELOPMENT ONLY. */
  generateBitcoinWallet() {
    return this.#get('/crypto/bitcoin/generate_new_wallet')
  }

  /** Generate a new Ethereum wallet. FOR DEVELOPMENT ONLY. */
  generateEthereumWallet() {
    return this.#get('/crypto/ethereum/generate_new_wallet')
  }
}

// ── Example usage ─────────────────────────────────────────────────────────────

// Uncomment to run: node aisense-api.js

/*
const api = new AISenseAPI()

// Time
console.log(await api.getDatetime(1))
console.log(await api.getTimestamp())

// Random
console.log(await api.getUUID())
console.log(await api.getRandomColor())
console.log(await api.getRandomNumber(1, 100))

// Transform
const encoded = await api.base64Encode('Hello, world!')
console.log('Base64:', encoded)
console.log('Decoded:', await api.base64Decode(encoded.base64_encoded_data))

const token = await api.jwtEncode({ user: 'alice' }, 'my-secret')
console.log('JWT:', token)
console.log('Decoded:', await api.jwtDecode(token.jwt, 'my-secret'))

// Hash
console.log(await api.hashSHA256('Hello'))

// Web
console.log(await api.ping())
console.log(await api.getClientIP())
console.log(await api.ipLookup('8.8.8.8'))

const stored = await api.storageSet({ hello: 'world' })
console.log('Stored:', stored)
console.log('Retrieved:', await api.storageGet(stored.uuid))

// Crypto (dev only)
console.log(await api.generateEthereumWallet())
*/
