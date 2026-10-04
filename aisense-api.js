/**
 * aisense-api.js: JavaScript client for the AI SENSE AS Free Public REST APIs
 * https://aisenseapi.com
 *
 * Works in Node.js (18+) and all modern browsers. No dependencies, native fetch.
 * There is no account. Most requests need nothing beyond the path and, for POST
 * endpoints, the body. Agent Queue and semantic search calls also carry a role
 * token, which this client sends as an Authorization header and never puts in
 * a URL. Both answer the browser preflight for that header, so those calls
 * work from a page as well as from Node.
 *
 * Usage (ESM):
 *   import { AISenseAPI } from './aisense-api.js'
 *   const api = new AISenseAPI()
 *   console.log((await api.getUUID()).uuid)
 *   console.log((await api.hashSHA256('Hello')).sha256_hash)
 *
 * Every method resolves to the parsed JSON response, and each JSDoc block names
 * the exact response key. The upstream API is not consistent about naming.
 * /md5_hash returns `md5_hash`, /ping returns `ping` and /random_color returns
 * `random_color`, so do not guess the key.
 *
 * The image methods take a Blob, File, ArrayBuffer or Uint8Array and upload it
 * as multipart/form-data. simulateFailure resolves to what the API sent,
 * status and body as text, instead of rejecting on the failure it asked for.
 *
 * Five endpoints answer with raw bytes instead of JSON (base64Decode,
 * base58Decode, base32Decode, hexDecode and base64urlDecode); those resolve to a
 * string when the payload is valid UTF-8 and to a Uint8Array otherwise.
 *
 * Failures arrive as `{"error": "message"}` with a real HTTP status, and this
 * client rejects with an AISenseAPIError carrying both.
 *
 * Older deployments answered differently, and this client still handles two of
 * those shapes so that the same code works against either:
 *   - a plain-text warning line in front of a JSON body, which it strips and
 *     records in `lastServerNotice`;
 *   - an unknown path answering HTTP 200 with a debug echo instead of a 404,
 *     which it turns into a clear rejection.
 * Neither shape appeared when this client was last checked against production,
 * on 2026-09-06.
 */

const BASE_URL = 'https://aisenseapi.com/services/v1'

// An unknown path answers a real 404 with the usual `{"error": ...}` body.
// Older deployments answered HTTP 200 with a body shaped like
//   ["<your-ip>",1786873281]["\/services\/v1\/random","1","random"]
// Detecting that turns a confusing JSON parse error into a clear message.
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
     * Set when the server prepends a plain-text warning line to a JSON
     * response, which an older deployment of /qrcode_encode did. Null when the
     * last call was clean, which is every call against production today.
     * @type {string|null}
     */
    this.lastServerNotice = null
  }

  // ── Internal helpers ───────────────────────────────────────────────────────

  async #fetch(path, method, body, token) {
    const init = { method, headers: {} }
    if (method === 'POST' && body instanceof FormData) {
      init.body = body
    } else if (method === 'POST') {
      init.headers['Content-Type'] = 'application/json'
      init.body = JSON.stringify(body)
    }
    if (token !== undefined) init.headers.Authorization = `Bearer ${token}`
    return fetch(`${this.baseUrl}${path}`, init)
  }

  async #request(path, method = 'GET', body, token) {
    const res = await this.#fetch(path, method, body, token)
    const text = await res.text()

    if (DEBUG_ECHO.test(text)) {
      throw new AISenseAPIError(
        `${method} ${path} is not a known endpoint. The API answered with the ` +
          `debug echo an older deployment sent instead of a 404. Check the ` +
          `path against API.md.`,
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

  #get(path, token) {
    return this.#request(path, 'GET', undefined, token)
  }

  #post(path, body, token) {
    return this.#request(path, 'POST', body, token)
  }

  #delete(path) {
    return this.#request(path, 'DELETE')
  }

  /**
   * One image as the multipart field `file`, with the other fields as text.
   * Fields left undefined or null are not sent.
   */
  #upload(path, file, fields = {}) {
    const form = new FormData()
    const blob = file instanceof Blob ? file : new Blob([file])
    form.append('file', blob, typeof file.name === 'string' && file.name ? file.name : 'image')
    for (const [key, value] of Object.entries(fields)) {
      if (value !== undefined && value !== null) form.append(key, String(value))
    }
    return this.#request(path, 'POST', form)
  }

  // ── Time ──────────────────────────────────────────────────────────────────

  /**
   * Current datetime in ISO 8601. Response key: `datetime`.
   *
   * `offset` must be a four-digit UTC offset such as `'+0200'`, `'-0530'` or
   * `'0100'`. Hour-only values like `'1'` are NOT accepted by the API: they
   * form a path that matches no route, so they answer 404.
   */
  getDatetime(offset) {
    return this.#get(offset !== undefined ? `/datetime/${offset}` : '/datetime')
  }

  /**
   * Current datetime in an IANA time zone such as `europe/oslo`, in any case, summer time
   * included. Keys: `datetime`, `timezone`, `abbreviation`, `utc_offset`,
   * `dst`, `unixtime`, `raw_offset`, `dst_offset`, `dst_from`, `dst_until`,
   * `day_of_week`, `day_of_year`, `week_number`, `utc_datetime`. An unknown
   * name is a 400.
   */
  getDatetimeInZone(timezone) {
    return this.#get(`/datetime/${timezone}`)
  }

  /**
   * The time where an IPv4 or IPv6 address is, or the caller's own without
   * one. Keys: `ip`, then the same as `getDatetimeInZone`. An address with no
   * zone in the lookup, such as a private one, is a 404.
   */
  getIpDatetime(ip) {
    return this.#get(ip !== undefined ? `/ip_datetime/${ip}` : '/ip_datetime')
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
   * Response key: `timezones`, a list of `{ timezone, offset }` objects, not
   * a list of strings.
   */
  getTimezones(offset) {
    return this.#get(offset !== undefined ? `/timezones/${offset}` : '/timezones')
  }

  /** Swatch Internet Time. Response keys: `beat` (e.g. `'@444'`) and `date`. */
  getSwatchTime() {
    return this.#get('/swatchinternettime')
  }

  /**
   * One time value in every form: unix seconds or milliseconds, ISO 8601,
   * RFC 2822 or `'now'`. Response keys: `input`, `detected`, `timestamp`,
   * `datetime`, `rfc2822`, `utc_datetime`. `offset` is a four-digit UTC offset
   * as for getDatetime. Bad input is a 400.
   */
  timestampConvert(data, offset) {
    const body = { data }
    if (offset !== undefined) body.offset = offset
    return this.#post('/timestamp_convert', body)
  }

  // ── Random ────────────────────────────────────────────────────────────────

  /**
   * Random integer. Response keys: `random_number` and `range`.
   *
   * No arguments defaults to 1 to 6. A single argument is treated by the API as
   * the upper bound, with the lower bound fixed at 1.
   */
  getRandomNumber(from, to) {
    if (from === undefined) return this.#get('/random_number')
    if (to === undefined) return this.#get(`/random_number/${from}`)
    return this.#get(`/random_number/${from}/${to}`)
  }

  /** Random hex color. Response key: `random_color`. */
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

  /**
   * Pronounceable passphrase of `groups` hyphenated groups, 4 by default and
   * 2 to 12. Response keys: `passphrase`, `groups`, `length`, `entropy_bits`.
   */
  getPassphrase(groups) {
    return this.#get(groups !== undefined ? `/passphrase/${groups}` : '/passphrase')
  }

  // ── Transform ─────────────────────────────────────────────────────────────

  /** Response key: `base64_encoded_data`. */
  base64Encode(data) {
    return this.#post('/base64_encode', { data })
  }

  /**
   * Decode Base64, resolving to a string (UTF-8) or a Uint8Array.
   *
   * This client sends no `Accept` of its own, so the endpoint answers with
   * `application/octet-stream`: the decoded bytes and nothing else. Send
   * `Accept: application/json` instead and the same endpoint wraps the result
   * as `{ type, decoded_data }`. `type` is `'json'` when the decoded bytes
   * themselves parse as JSON, and `'binary'` otherwise, which adds
   * `encoding: 'base64'` and re-encodes `decoded_data`. Plain text that is not
   * JSON therefore comes back tagged `'binary'`. Raw is the more useful
   * default; use the JSON form when you need the tag.
   *
   * The hex and base64url decoders read `Accept` exactly as this one does. The
   * Base58 and Base32 decoders answer JSON on `Accept: application/json` too,
   * but have no text mode and no 406.
   */
  base64Decode(data) {
    return this.#requestBinary('/base64_decode', { data })
  }

  /** Response key: `base58_encoded_data`. */
  base58Encode(data) {
    return this.#post('/base58_encode', { data })
  }

  /**
   * Decode Base58 and return the raw bytes. The service answers JSON when asked
   * with `Accept: application/json`; this method does not ask.
   *
   * This endpoint used to validate its input with the Base32 decoder and reject
   * everything with "Invalid Base32 input.", including strings produced by
   * {@link base58Encode}. It round-trips against {@link base58Encode} as of
   * 2026-09-06; bad input now answers 400 with "Invalid Base58 input."
   */
  base58Decode(data) {
    return this.#requestBinary('/base58_decode', { data })
  }

  /** Response key: `base32_encoded_data`. */
  base32Encode(data) {
    return this.#post('/base32_encode', { data })
  }

  /**
   * Decode Base32 and return the raw bytes. The service answers JSON when asked
   * with `Accept: application/json`; this method does not ask.
   */
  base32Decode(data) {
    return this.#requestBinary('/base32_decode', { data })
  }

  /** Response key: `hex_encoded_data`, in lower case. */
  hexEncode(data) {
    return this.#post('/hex_encode', { data })
  }

  /**
   * Decode hex in either case, with an optional `0x` and spaces, and return the
   * raw bytes, as {@link base64Decode} does.
   */
  hexDecode(data) {
    return this.#requestBinary('/hex_decode', { data })
  }

  /**
   * Response key: `base64url_encoded_data`: the URL-safe alphabet, `-` and `_`,
   * without padding, as JWT writes it.
   */
  base64urlEncode(data) {
    return this.#post('/base64url_encode', { data })
  }

  /**
   * Decode base64url, with or without padding, and return the raw bytes, as
   * {@link base64Decode} does. `+` and `/` belong to base64Decode and answer 400.
   */
  base64urlDecode(data) {
    return this.#requestBinary('/base64url_decode', { data })
  }

  /**
   * Response key: `url_encoded_data`. RFC 3986 percent-encoding: a space is
   * `%20` and only `A-Z a-z 0-9 - _ . ~` are left as they are.
   */
  urlEncode(data) {
    return this.#post('/url_encode', { data })
  }

  /** Response key: `url_decoded_data`. A `+` stays a `+`, and the result has to be UTF-8 text. */
  urlDecode(data) {
    return this.#post('/url_decode', { data })
  }

  /** Response key: `html_encoded_data`. `& < > " '` become `&amp; &lt; &gt; &quot; &#039;`. */
  htmlEncode(data) {
    return this.#post('/html_encode', { data })
  }

  /** Response key: `html_decoded_data`. Every named HTML5 entity and every numeric one back to its character. */
  htmlDecode(data) {
    return this.#post('/html_decode', { data })
  }

  /** Response keys: `markdown` and `title`. HTML to CommonMark, without scripts, styles or forms. */
  htmlToMarkdown(data) {
    return this.#post('/html_to_markdown', { data })
  }

  /** Response key: `html`. Markdown to HTML that is safe to put in a page: raw HTML is shown as text. */
  markdownToHtml(data) {
    return this.#post('/markdown_to_html', { data })
  }

  /** Response key: `slug`. Scandinavian letters and Latin diacritics are transliterated; text with nothing to slug is a 400. */
  slugify(data) {
    return this.#post('/slugify', { data })
  }

  /**
   * Encode a payload into an HS256 JWT. Response key: `jwt`.
   *
   * The API takes `data` as either a JSON object or a string containing JSON,
   * and both produce the same token. An object is serialised here so the
   * behaviour is the same whichever deployment answers. An empty `data` or an
   * empty `secret` answers 400.
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
   * The request field is `payload`. `data` is accepted as well, so the QR pair
   * is no longer the one endpoint with a field name of its own.
   */
  qrcodeEncode(payload) {
    return this.#post('/qrcode_encode', { payload })
  }

  /**
   * Decode a Base64-encoded QR code image. Response key: `qrcode_content`.
   * The request field is `payload`, and `data` is accepted as well. The image
   * is a PNG, JPEG, GIF or WebP of at most 10 MB; anything else answers 415.
   * An image with no readable code answers 400.
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

  /** CRC32 checksum. Response key: `crc32_checksum`, an integer, not a hex string. */
  crc32Checksum(data) {
    return this.#post('/crc32_checksum', { data })
  }

  /** Response key: `whirlpool_hash`, 128 hex characters. */
  hashWhirlpool(data) {
    return this.#post('/whirlpool_hash', { data })
  }

  /** Response key: `sha3_256_hash`. */
  hashSHA3_256(data) {
    return this.#post('/sha3_256_hash', { data })
  }

  /** Response key: `sha3_512_hash`. */
  hashSHA3_512(data) {
    return this.#post('/sha3_512_hash', { data })
  }

  /** BLAKE2b-256. Response key: `blake2b_hash`. */
  hashBLAKE2b(data) {
    return this.#post('/blake2b_hash', { data })
  }

  /** BLAKE3, input at most 1 MiB. Response key: `blake3_hash`. */
  hashBLAKE3(data) {
    return this.#post('/blake3_hash', { data })
  }

  /** Argon2id password hash, 64 MiB, 3 passes; a new salted PHC string every call. For test data: 200 operations per IP per day. Response key: `argon2id_hash`. */
  hashArgon2id(password) {
    return this.#post('/argon2id_hash', { password })
  }

  /** bcrypt password hash, cost 12, input at most 72 bytes. Response key: `bcrypt_hash`. */
  hashBcrypt(password) {
    return this.#post('/bcrypt_hash', { password })
  }

  /** scrypt password hash, N 2^17, r 8, p 1; a PHC string. Response key: `scrypt_hash`. */
  hashScrypt(password) {
    return this.#post('/scrypt_hash', { password })
  }

  /** Verify a password against an Argon2id, bcrypt or scrypt string; the algorithm is read from the string. Answers match, algorithm and params. */
  passwordVerify(password, hash) {
    return this.#post('/password_verify', { password, hash })
  }

  /**
   * Verify data against a digest. Response keys: `match`, `algorithm` and
   * `computed`; a mismatch is a result, not an error. Name the `algorithm`
   * when you know it, and always for whirlpool, sha3_256, sha3_512, blake2b
   * and blake3. A CRC32 can be the integer crc32Checksum answers.
   */
  hashVerify(data, hash, algorithm) {
    const body = { data, hash }
    if (algorithm !== undefined) body.algorithm = algorithm
    return this.#post('/hash_verify', body)
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
   * Store data for 24 hours. Response keys: `storage_id`, `storage_url`,
   * `sha256_hash`, `bytes`, `expire_timestamp`
   * and `expire_datetime`.
   *
   * The request body is stored verbatim, so whatever you pass here is exactly
   * what {@link storageGet} gives back. No `data` wrapper is added or removed.
   */
  storageSet(data) {
    return this.#post('/storage', data)
  }

  /**
   * Retrieve stored data by its `storage_id`, returned verbatim. The answer
   * carries an `ETag` that is `sha256_hash` in quotes, so what came back can
   * be checked against what {@link storageSet} reported.
   */
  storageGet(storageId) {
    return this.#get(`/storage/${storageId}`)
  }

  /**
   * Shorten a URL for 24 hours. Response keys: `short_url`, `expire_timestamp`
   * and `expire_datetime`. This is a GET with the target URL inline in the
   * path, not a POST.
   */
  shortenURL(url) {
    return this.#get(`/url_shortener/${url}`)
  }

  /**
   * Create a URL that records the next request sent to it. Response keys: `ok`,
   * `capture_id`, `status`, `update_url`, `read_url`, `wait_url`,
   * `expire_timestamp`, `expire_datetime`. Point any HTTP client at
   * `update_url`, then read it back with {@link webhookCaptureRead}.
   */
  webhookCaptureCreate(notifyUrl) {
    const body = {}
    if (notifyUrl !== undefined) body.notify_url = notifyUrl
    return this.#post('/webhook_capture', body)
  }

  /**
   * Read a captured request. Response keys: `ok`, `capture_id`, `status`
   * (`'pending'` or `'captured'`), `created_at_timestamp`,
   * `created_at_datetime`, `expire_timestamp`, `expire_datetime`. Once
   * something has arrived it also carries `captured_at_timestamp`,
   * `captured_at_datetime` and `request`. Branch on `status`, not on the
   * presence of `request`.
   */
  webhookCaptureRead(captureId, waitSeconds) {
    const suffix = waitSeconds === undefined ? '' : `/wait/${waitSeconds}`
    return this.#get(`/webhook_capture/${captureId}${suffix}`)
  }

  /**
   * Create a human-in-the-loop action form. Response keys: `ok`, `action_id`,
   * `form_url`, `result_url`, `wait_url`, `expire_timestamp`,
   * `expire_datetime`.
   *
   * With `respondents` above 1 the shape changes: there is no `form_url`, and
   * `form_urls` carries one link per respondent, alongside `respondents`,
   * `answered`, `tally` and `responses`. Hand each respondent their own link.
   *
   * `options` accepts either plain strings or `{ value, label }` objects:
   *
   *   [{ type: 'radio', name: 'decision', label: 'Approve?', required: true,
   *      options: [{ value: 'yes', label: 'Yes' }, { value: 'no', label: 'No' }] }]
   *
   * Field types: radio, select, text, textarea, checkbox.
   */
  webhookActionCreate(title, fields, description, options = {}) {
    if (description && typeof description === 'object') {
      options = description
      description = undefined
    }
    const body = { title, fields }
    if (description !== undefined) body.description = description
    if (options.respondents !== undefined) body.respondents = options.respondents
    if (options.notifyUrl !== undefined) body.notify_url = options.notifyUrl
    return this.#post('/webhook_action', body)
  }

  /**
   * Poll for the answer to an action. Response keys: `ok`, `action_id`,
   * `status`, `created_at_timestamp`, `created_at_datetime`,
   * `expire_timestamp`, `expire_datetime`, `answered_at_timestamp`,
   * `answered_at_datetime`, `response`.
   *
   * `status` is `'pending'`, `'answered'`, or `'partial'` when an action with
   * several respondents has some answers but not all. A multi-respondent action
   * also returns `respondents`, `answered`, `tally` and `responses`.
   */
  webhookActionResult(actionId, waitSeconds) {
    const suffix = waitSeconds === undefined ? '' : `/wait/${waitSeconds}`
    return this.#get(`/webhook_action/${actionId}${suffix}`)
  }

  /** Create a one-shot or recurring webhook schedule. */
  webhookScheduleCreate(url, options = {}) {
    const body = { url }
    for (const key of ['delay_seconds', 'fire_at', 'payload', 'every']) {
      if (options[key] !== undefined) body[key] = options[key]
    }
    return this.#post('/webhook_schedule', body)
  }

  /** Read a schedule, or wait up to 25 seconds for a state change. */
  webhookScheduleRead(scheduleId, waitSeconds) {
    const suffix = waitSeconds === undefined ? '' : `/wait/${waitSeconds}`
    return this.#get(`/webhook_schedule/${scheduleId}${suffix}`)
  }

  /** Cancel a schedule that has not reached a terminal state. */
  webhookScheduleCancel(scheduleId) {
    return this.#delete(`/webhook_schedule/${scheduleId}`)
  }

  /** Create a durable webhook, human or time Agent Wake task. */
  agentWakeCreate(eventType, options = {}) {
    return this.#post('/agent_wake', { event_type: eventType, ...options })
  }

  /** Read an Agent Wake task, or wait up to 25 seconds for completion. */
  agentWakeRead(taskId, waitSeconds) {
    const suffix = waitSeconds === undefined ? '' : `/wait/${waitSeconds}`
    return this.#get(`/agent_wake/${taskId}${suffix}`)
  }

  /** Cancel a waiting Agent Wake task. */
  agentWakeCancel(taskId) {
    return this.#delete(`/agent_wake/${taskId}`)
  }

  /** Create a Heartbeat that fires once when check-ins stop. */
  heartbeatCreate(expectEverySeconds, onMiss, graceSeconds = 0) {
    return this.#post('/heartbeat', {
      expect_every_seconds: expectEverySeconds,
      grace_seconds: graceSeconds,
      on_miss: onMiss,
    })
  }

  /** Read Heartbeat state. */
  heartbeatRead(heartbeatId) {
    return this.#get(`/heartbeat/${heartbeatId}`)
  }

  /** Check in with a Heartbeat. */
  heartbeatPing(heartbeatId) {
    return this.#post(`/heartbeat/${heartbeatId}/ping`, {})
  }

  /** Mint a bearer namespace for readable lease keys. */
  leaseCreateNamespace() {
    return this.#post('/lease/namespace', {})
  }

  /** Acquire a lease. The returned owner token is required for owner actions. */
  leaseAcquire(options) {
    return this.#post('/lease/acquire', options)
  }

  leaseRenew(namespace, key, ownerToken, ttlSeconds) {
    return this.#post('/lease/renew', {
      namespace,
      key,
      owner_token: ownerToken,
      ttl_seconds: ttlSeconds,
    })
  }

  leaseRelease(namespace, key, ownerToken) {
    return this.#post('/lease/release', { namespace, key, owner_token: ownerToken })
  }

  leaseComplete(namespace, key, ownerToken, result) {
    return this.#post('/lease/complete', {
      namespace,
      key,
      owner_token: ownerToken,
      result,
    })
  }

  /**
   * Create a disposable mail inbox for a verification code, a confirmation link
   * or a sign-up mail. Takes no arguments. Response keys: `ok`, `inbox_id`,
   * `slug`, `address`, `read_url`, `wait_url`, `expire_timestamp`.
   *
   * The two identifiers are not interchangeable. `slug` is the seven characters
   * `[a-z0-9]` inside `address`, and it is public by construction: it travels in
   * mail headers, bounces and sender logs. Knowing it lets anyone send mail to
   * the inbox, and nothing else; it never appears in a URL. `inbox_id` is the
   * only credential that reads the inbox. It is a bearer secret, anyone holding
   * it reads the mail, and it is returned once, here. Guessing the address does
   * not read the inbox. A wrong `inbox_id` and a missing inbox both answer 404,
   * and nothing here answers 403, so the two cannot be told apart. An inbox
   * that has passed its expiry answers 410 until the pruner removes it, and
   * 404 after that.
   *
   * Caps: 20 messages per inbox, 64 KiB of cleaned text per message, 256 KiB
   * per inbox, 50 inboxes per client per UTC day, 5000 active inboxes service
   * wide. The 24 hour lifetime is fixed and cannot be extended.
   *
   * The routes are GET or POST /inbox, GET /inbox/{inbox_id} and
   * GET /inbox/{inbox_id}/wait/{0..25}. A wait outside 0 to 25 answers 404,
   * which is where this differs from the other long poll routes.
   */
  agentInboxCreate() {
    return this.#post('/inbox', {})
  }

  /**
   * Read an inbox, or wait up to 25 seconds for it to change. Response keys:
   * `ok`, `slug`, `address`, `received`, `truncated`, `messages`,
   * `created_at_timestamp`, `expire_timestamp`. The wait form adds
   * `waited_seconds` and `wait_reason`. `inbox_id` is not echoed back; the
   * credential never travels in a response.
   *
   * Each entry in `messages` has `from`, `subject`, `date`, `text`, `codes` and
   * `links`. `date` is when the service received the message, not the sender's
   * Date header, because that header is sender controlled. `codes` are
   * standalone 4 to 8 digit numbers. `links` are public http(s) links only:
   * private-IP and localhost links are dropped. Attachments, raw MIME,
   * arbitrary headers, scripts and styles are stripped before storage.
   *
   * `truncated` is true once at least one message has been refused, either by
   * the 20 message cap or by the 256 KiB total. A full inbox refuses new mail
   * rather than evicting old mail, so without the flag a reader would see a
   * full inbox, no code and no reason. It carries no count, and it says nothing
   * about text cut short inside a message at the 64 KiB per-message cap, which
   * the parser does silently.
   *
   * The wait watches `truncated` as well as `received`, so a message the cap
   * turns away ends the wait instead of leaving the caller to run out the
   * clock on one that will never arrive.
   */
  agentInboxRead(inboxId, waitSeconds) {
    const suffix = waitSeconds === undefined ? '' : `/wait/${waitSeconds}`
    return this.#get(`/inbox/${inboxId}${suffix}`)
  }

  /**
   * Create a pull queue that cooperating agents share for at most 24 hours.
   * Takes no arguments. Response keys: `ok`, `queue_id`,
   * `created_at_timestamp`, `expire_timestamp`, `counts`, `read_token`,
   * `write_token`, `worker_token`.
   *
   * The three tokens are separate capabilities, and each is returned once,
   * here. `read_token` reads counts and single jobs, `write_token` adds jobs,
   * and `worker_token` claims, acknowledges, releases and renews them. A token
   * used for another role answers 403, so each agent can be given only the
   * token its role needs. Every queue method below takes the queue ID first,
   * then the token, then the job details, and sends the token as an
   * Authorization header.
   *
   * The whole queue expires 24 hours after creation, and activity never
   * extends it. Caps: 100 jobs over the queue's lifetime, 16 KiB of encoded
   * JSON per payload, 5 claims per job and 20 new queues per client IP per 24
   * hours. The service stores jobs and hands them out; it never runs them.
   */
  createAgentQueue() {
    return this.#post('/queue', {})
  }

  /**
   * Read queue counts with the read token. Response keys: `ok`, `queue_id`,
   * `created_at_timestamp`, `expire_timestamp`, `counts`. `counts` has
   * `pending`, `claimed`, `completed`, `failed` and `total`. Payloads and
   * tokens are never listed.
   */
  readAgentQueue(queueId, readToken) {
    return this.#get(`/queue/${queueId}`, readToken)
  }

  /**
   * Add a job with the write token. Response keys: `ok`, `queue_id`,
   * `expire_timestamp`, `job`, `deduplicated`. `job` has `job_id`, `job_key`,
   * `payload`, `status`, `attempts`, `created_at_timestamp`,
   * `expire_timestamp` and `claimed_until_timestamp`.
   *
   * `jobKey` makes a resend harmless. The same key with the same payload
   * returns the existing job with `deduplicated` true. The same key with a
   * different payload answers 409, so a retry can never quietly change a job.
   * A key is 1 to 64 characters of `[A-Za-z0-9._:-]` and starts with a letter
   * or digit.
   *
   * `payload` is any JSON value, `null` included, up to 16 KiB encoded.
   * `undefined` is not a JSON value: it is dropped from the request body, and
   * the server answers 400 `payload is required`.
   */
  enqueueAgentQueueJob(queueId, writeToken, jobKey, payload) {
    return this.#post(`/queue/${queueId}/jobs`, { job_key: jobKey, payload }, writeToken)
  }

  /**
   * Read one job with the read token. Response keys: `ok`, `queue_id`,
   * `expire_timestamp`, `job`, with the same `job` fields as
   * {@link enqueueAgentQueueJob}. A claim receipt is never shown here. The
   * server keeps only its hash, so the worker that claimed the job is the one
   * party that holds it.
   */
  readAgentQueueJob(queueId, readToken, jobId) {
    return this.#get(`/queue/${queueId}/jobs/${jobId}`, readToken)
  }

  /**
   * Claim the next pending job with the worker token. Response keys: `ok`,
   * `queue_id`, `expire_timestamp`, `job`. `job` is `null` when nothing is
   * waiting, which is the normal answer from an idle queue and not an error.
   * Otherwise it is the job with `status` `'claimed'`, a
   * `claimed_until_timestamp` and a secret `receipt`. Keep the receipt:
   * acknowledging, releasing and renewing all need it.
   *
   * `visibilityTimeout` is how long the claim holds, 30 to 900 seconds, 60 by
   * default, and never past the queue's expiry. A job whose claim runs out goes
   * back to pending for another worker. Each claim counts one attempt, and a
   * job fails after 5 unsuccessful ones.
   *
   * A job can be handed out more than once, so make the work itself
   * idempotent. A claim reply that is lost can still have reserved a job; the
   * Agent Queue section of API.md describes how to recover without taking a
   * second job.
   */
  claimAgentQueueJob(queueId, workerToken, visibilityTimeout) {
    const body = visibilityTimeout === undefined ? {} : { visibility_timeout: visibilityTimeout }
    return this.#post(`/queue/${queueId}/claim`, body, workerToken)
  }

  /**
   * Mark a claimed job completed with the worker token and its receipt.
   * Response keys: `ok`, `queue_id`, `expire_timestamp`, `job`, with `status`
   * `'completed'`. Repeating the acknowledgement with the same receipt
   * succeeds again, so a worker whose reply was lost can retry it. A receipt
   * from an earlier claim of the same job answers 409. Completing a job does
   * not free room under the 100 job cap.
   */
  ackAgentQueueJob(queueId, workerToken, jobId, receipt) {
    return this.#post(`/queue/${queueId}/jobs/${jobId}/ack`, { receipt }, workerToken)
  }

  /**
   * Give a claimed job back to the queue with the worker token and its
   * receipt. Response keys: `ok`, `queue_id`, `expire_timestamp`, `job`, with
   * `status` `'pending'` again. The attempt the claim used still counts toward
   * the limit of 5.
   */
  releaseAgentQueueJob(queueId, workerToken, jobId, receipt) {
    return this.#post(`/queue/${queueId}/jobs/${jobId}/release`, { receipt }, workerToken)
  }

  /**
   * Extend a claim with the worker token and its receipt. Response keys: `ok`,
   * `queue_id`, `expire_timestamp`, `job`, with a later
   * `claimed_until_timestamp`. No new receipt is issued, and the one from the
   * claim stays valid. Renewing adds no attempt. `visibilityTimeout` is 30 to
   * 900 seconds, 60 by default, and never past the queue's expiry.
   */
  renewAgentQueueJob(queueId, workerToken, jobId, receipt, visibilityTimeout) {
    const body = { receipt }
    if (visibilityTimeout !== undefined) body.visibility_timeout = visibilityTimeout
    return this.#post(`/queue/${queueId}/jobs/${jobId}/renew`, body, workerToken)
  }

  /**
   * Create a semantic search collection: short notes that agents find by
   * meaning, across wording and between languages, for a fixed 24 hours.
   * `model` is 'bge-m3' (the default when omitted) or 'qwen3-embedding-4b',
   * fixed for the collection. Response keys: `ok`, `collection_id`, `model`,
   * `created_at_timestamp`, `expire_timestamp`, `notes`, `notes_added`,
   * `notes_max`, `read_token`, `write_token`. The two tokens appear only in
   * this response: the read token reads and searches, the write token adds and
   * deletes notes. At most 500 notes over the lifetime and 20 new collections
   * per client IP per 24 hours.
   */
  createSemanticSearch(model) {
    return this.#post('/semantic_search', model === undefined ? {} : { model })
  }

  /**
   * Read a collection with the read token. Response keys: `ok`,
   * `collection_id`, `model`, `created_at_timestamp`, `expire_timestamp`,
   * `notes`, `notes_added`, `notes_max`. Notes are found by searching.
   */
  readSemanticSearch(collectionId, readToken) {
    return this.#get(`/semantic_search/${collectionId}`, readToken)
  }

  /**
   * Add 1 to 32 notes with the write token. Each note is `{ text, key }`:
   * `text` holds 1 to 2000 characters and `key` is optional. Response keys:
   * `ok`, `collection_id`, `added` (each new `note_id` and `key`, in order),
   * `notes`, `notes_added`, `expire_timestamp`. Never add secrets or sensitive
   * personal data. Adding and searching share a usage limit of 60 per minute
   * and 1000 per UTC day per IP.
   */
  addSemanticSearchNotes(collectionId, writeToken, notes) {
    return this.#post(`/semantic_search/${collectionId}/notes`, { notes }, writeToken)
  }

  /**
   * Search the notes by meaning with the read token. `limit` is 1 to 10, 3 by
   * default. Response keys: `ok`, `collection_id`, `model`, `results` (each
   * with `note_id`, `key`, `text` and `score`, best first), `notes`,
   * `expire_timestamp`. The score is cosine similarity plus 0.1 for each
   * identifier the search and the note share, kind by kind, and is not a
   * probability. The results are ranked suggestions, not a decision that a
   * match exists.
   */
  querySemanticSearch(collectionId, readToken, query, limit) {
    const body = { query }
    if (limit !== undefined) body.limit = limit
    return this.#post(`/semantic_search/${collectionId}/search`, body, readToken)
  }

  /**
   * Delete one note with the write token. Response keys: `ok`,
   * `collection_id`, `deleted`, `notes`, `notes_added`. The text and the
   * vector are removed at once, and the place in the 500-note lifetime limit
   * stays used.
   */
  deleteSemanticSearchNote(collectionId, writeToken, noteId) {
    return this.#post(`/semantic_search/${collectionId}/notes/${noteId}/delete`, {}, writeToken)
  }

  /**
   * Check an email address: syntax, then DNS. Response keys: `email`,
   * `valid_syntax`, `domain`, `has_mx`, `mx_hosts`, `has_address_record`. A
   * failing address is a result with `valid_syntax` false. The mailbox itself
   * is never contacted.
   */
  emailValidate(data) {
    return this.#post('/email_validate', { data })
  }

  /**
   * Check a business number by arithmetic: `type` is 'iban', 'card', 'orgnr',
   * 'kontonummer' or 'phone'. Response keys: `type`, `valid` and the checks
   * for that type. An invalid value is a result with `valid` false; nothing is
   * looked up in a register, and a card number is never echoed back.
   */
  validate(type, data) {
    return this.#post(`/validate/${type}`, { data })
  }

  /**
   * A public DNS name for `ip` for 24 hours, `aisense-<slug>.53for24h.com`.
   * Response keys: `name`, `slug`, `ip`, `record`, `ttl`, `nameservers`,
   * `expire_at` and `dns_token`, shown once. `ip` must be a public address.
   */
  dnsCreate(ip) {
    return this.#get(`/dns/${ip}`)
  }

  /** Read a DNS name by its `slug`: its address and expiry, all public in DNS anyway. */
  dnsRead(slug) {
    return this.#get(`/dns/${slug}`)
  }

  /** Move a DNS name to another public `ip`. The expiry does not move. `dnsToken` goes in the Authorization header. */
  dnsUpdate(slug, ip, dnsToken) {
    return this.#post(`/dns/${slug}/update/${ip}`, {}, dnsToken)
  }

  /** Remove a DNS name before it expires. `dnsToken` goes in the Authorization header. */
  dnsDelete(slug, dnsToken) {
    return this.#post(`/dns/${slug}/delete`, {}, dnsToken)
  }

  /**
   * Render HTML to a PDF stored for 24 hours. Response keys: the Storage
   * fields `storage_id`, `storage_url`, `sha256_hash`, `bytes` and
   * `expire_timestamp`; a GET on `storage_url` returns the PDF. `options` may
   * set `page-size`, `orientation` and the four margins such as
   * `margin-top`. The renderer has no network, so inline images, styles and
   * fonts.
   */
  htmlToPdf(html, options) {
    const body = { html }
    if (options !== undefined) body.options = options
    return this.#post('/html2pdf', body)
  }

  // ── Convert ───────────────────────────────────────────────────────────────

  // These store their result for 24 hours and answer with the Storage fields
  // (`storage_id`, `storage_url`, `sha256_hash`, `bytes`, `expire_timestamp`,
  // `expire_datetime`) plus `content_type`, `filename` and `operation`. Read
  // the result with storageGet or a GET on `storage_url`.

  /**
   * JSON rows to CSV, stored as result.csv. `columns` names the columns and
   * their order. `options`: `delimiter` (`','`, `';'` or `'\t'`) and
   * `spreadsheetSafe`, which guards cells a spreadsheet would run as formulas.
   */
  jsonToCsv(columns, rows, options = {}) {
    const body = { columns, rows }
    if (options.delimiter !== undefined) body.delimiter = options.delimiter
    if (options.spreadsheetSafe !== undefined) body.spreadsheet_safe = options.spreadsheetSafe
    return this.#post('/json_to_csv', body)
  }

  /** CSV text to `{columns, rows}`, stored as result.json. Every cell stays a string. */
  csvToJson(data, delimiter) {
    const body = { data }
    if (delimiter !== undefined) body.delimiter = delimiter
    return this.#post('/csv_to_json', body)
  }

  /**
   * Match two lists of rows on `keys`, pairs such as
   * `{ left: 'id', right: 'customer_id' }`. Stored as matches.json with
   * `matched`, `only_left`, `only_right` and `ambiguous`, positions only.
   */
  tableMatch(left, right, keys) {
    return this.#post('/table_match', { left, right, keys })
  }

  /** Pretty-print or compact JSON text, stored as result.json; only whitespace changes. `mode` 'pretty' or 'compact', `indent` 2 or 4. */
  jsonFormat(data, mode, indent) {
    const body = { data }
    if (mode !== undefined) body.mode = mode
    if (indent !== undefined) body.indent = indent
    return this.#post('/json_format', body)
  }

  /** Check that JSON text parses. Adds `valid` to the Storage fields; invalid JSON is a result, and validation.json holds the parser's message. */
  jsonValidate(data) {
    return this.#post('/json_validate', { data })
  }

  // ── Images ────────────────────────────────────────────────────────────────

  // Each takes one JPEG, PNG or WebP of at most 10 MB as `file`: a Blob or
  // File, or the bytes as an ArrayBuffer or Uint8Array (a Node Buffer is one).
  // It is sent as multipart/form-data. The result is stored for 24 hours, and
  // the answer has the Storage fields plus `operation` and what the result is.

  /**
   * Convert to `format` 'jpeg', 'png' or 'webp'; reads HEIC too. `options`:
   * `quality` 40 to 95 and, for WebP, `lossless`. Adds `format`, `width`,
   * `height`, `input_format` and `input_bytes`.
   */
  imageConvert(file, format, options = {}) {
    return this.#upload('/image_convert', file, { format, quality: options.quality, lossless: options.lossless })
  }

  /** Save again in its own format: JPEG and WebP at `quality` 40 to 95, PNG losslessly. Compare `bytes` with `input_bytes`. */
  imageCompress(file, quality) {
    return this.#upload('/image_compress', file, { quality })
  }

  /**
   * A new size inside a box of `width` and/or `height`, aspect ratio kept;
   * reads HEIC too. `options`: `width`, `height`, `fit` ('contain', or 'cover'
   * with both sides), `upscale`, `format`, `quality`, `lossless`. Adds
   * `input_width`, `input_height`, `fit` and `upscaled`.
   */
  imageResize(file, options = {}) {
    const { width, height, fit, upscale, format, quality, lossless } = options
    return this.#upload('/image_resize', file, { width, height, fit, upscale, format, quality, lossless })
  }

  /** What the image carries besides its pixels, with a privacy list, stored as metadata.json. Adds `format`, `width`, `height`, `gps` and `findings`. */
  imageMetadata(file) {
    return this.#upload('/image_metadata', file)
  }

  /** Remove EXIF, XMP, IPTC and comments without saving the image again. Adds `format`, `width`, `height`, `input_bytes`, `removed` and `kept`. */
  imageStrip(file) {
    return this.#upload('/image_strip', file)
  }

  /** The dominant colors, `count` 2 to 16 and 8 by default, stored as colors.json. Adds `average`, `dominant` and `count`. */
  imageColors(file, count) {
    return this.#upload('/image_colors', file, { count })
  }

  /** A favicon set as favicon.zip. `options`: `crop` 'fit', 'trim' or 'center', and `name` for the manifest. Adds `files`, `crop` and `upscaled`. */
  imageFavicon(file, options = {}) {
    return this.#upload('/image_favicon', file, { crop: options.crop, name: options.name })
  }

  // ── Logic ─────────────────────────────────────────────────────────────────

  /**
   * Typed answers about `state`. Without `model`, or with 'rules', each
   * question is yes_no, choice or scale with weighted rules, and its answer
   * carries `probability`, `confidence`, `action` and `because`. With 'clef',
   * 'nimble' or 'tev1' the questions are noul, choice or score with
   * `instructions` and `criteria`, and the answer is the model's own. tev1 is
   * the smallest and fastest, tested in English only, for short, direct
   * questions. Response key: `answers`, with `model` and `model_version` for a
   * model. The format: https://aisense.no/free-public-api-decide-api-endpoint
   */
  decide(state, questions, model) {
    const body = { state, questions }
    if (model !== undefined) body.model = model
    return this.#post('/decide', body)
  }

  /**
   * A failure on purpose, to test a client: `outcome` is a status from 200 to
   * 504, or 'html', 'empty' or 'wrongtype', after `delayMs` of 0 to 10000.
   * Unlike the other methods this one does not reject on the answer it asked
   * for. It resolves to `{ status, contentType, retryAfter, chaos, body }`,
   * with the body as text, so the handling under test sees what came back.
   */
  async simulateFailure(outcome, delayMs) {
    const path = delayMs !== undefined ? `/chaos/${outcome}/${delayMs}` : `/chaos/${outcome}`
    const res = await fetch(`${this.baseUrl}${path}`)
    return {
      status: res.status,
      contentType: res.headers.get('content-type'),
      retryAfter: res.headers.get('retry-after'),
      chaos: res.headers.get('x-chaos'),
      body: await res.text(),
    }
  }

  // ── Crypto ────────────────────────────────────────────────────────────────

  /**
   * New Solana wallet. Response keys: `private_key`, `public_address`.
   * FOR DEVELOPMENT ONLY. Do not fund a wallet whose private key was generated
   * on a server and sent back over the wire.
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
   * Ethereum balance. Response keys: `wallet`, `balance_eth`, `balance_wei`.
   *
   * This used to answer "Failed to retrieve balance data." for every address.
   * It returns a balance as of 2026-09-06.
   */
  ethereumBalance(address) {
    return this.#get(`/ethereum/balance/${address}`)
  }
}

/**
 * Split a leading plain-text warning line off a JSON body.
 *
 * An older deployment of /qrcode_encode emitted one in front of its JSON.
 * Production does not, so this is a guard for callers pointed at an older
 * deployment rather than a workaround for current behaviour.
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

// Base58, which used to reject its own encoder's output
const { base58_encoded_data } = await api.base58Encode('Hello')
console.log('Base58:', base58_encoded_data, '->', await api.base58Decode(base58_encoded_data))

// An unknown path rejects with the server's own error message
try {
  await api.getDatetime('1')
} catch (err) {
  console.log(err.message)
}

await api.qrcodeEncode('https://aisenseapi.com/')
if (api.lastServerNotice) {
  console.log('Server sent a warning line before its JSON:', api.lastServerNotice.slice(0, 80), '...')
}
*/
