/**
 * aisense-api.js: JavaScript client for the AI SENSE AS Free Public REST APIs
 * https://aisenseapi.com
 *
 * Works in Node.js (18+) and all modern browsers. No dependencies, native fetch.
 * There is no account. Most requests need nothing beyond the path and, for POST
 * endpoints, the body. Agent Queue calls also carry the queue's role token,
 * which this client sends as an Authorization header and never puts in a URL.
 * The queue answers the browser preflight for that header, so those calls work
 * from a page as well as from Node.
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
 * Three endpoints answer with raw bytes instead of JSON (base64Decode,
 * base58Decode and base32Decode); those resolve to a string when the payload is
 * valid UTF-8 and to a Uint8Array otherwise.
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
    if (method === 'POST') {
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
   * This client sends no `Accept` of its own, so the endpoint answers with
   * `application/octet-stream`: the decoded bytes and nothing else. Send
   * `Accept: application/json` instead and the same endpoint wraps the result
   * as `{ type, decoded_data }`. `type` is `'json'` when the decoded bytes
   * themselves parse as JSON, and `'binary'` otherwise, which adds
   * `encoding: 'base64'` and re-encodes `decoded_data`. Plain text that is not
   * JSON therefore comes back tagged `'binary'`. Raw is the more useful
   * default; use the JSON form when you need the tag.
   *
   * /base64_decode is the only decoder that reads `Accept`. Its Base58 and
   * Base32 siblings always answer raw bytes.
   */
  base64Decode(data) {
    return this.#requestBinary('/base64_decode', { data })
  }

  /** Response key: `base58_encoded_data`. */
  base58Encode(data) {
    return this.#post('/base58_encode', { data })
  }

  /**
   * Decode Base58. Answers with raw bytes, not JSON, and ignores `Accept`.
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

  /** Decode Base32. Answers with raw bytes, not JSON, and ignores `Accept`. */
  base32Decode(data) {
    return this.#requestBinary('/base32_decode', { data })
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
   * The request field is `payload`, and `data` is accepted as well. Anything
   * the decoder cannot read as a QR code answers 400.
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
   * Store data for 24 hours. Response keys: `storage_id`, `expire_timestamp`
   * and `expire_datetime`.
   *
   * The request body is stored verbatim, so whatever you pass here is exactly
   * what {@link storageGet} gives back. No `data` wrapper is added or removed.
   */
  storageSet(data) {
    return this.#post('/storage', data)
  }

  /** Retrieve stored data by its `storage_id`, returned verbatim. */
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
   * The routes are POST /inbox, GET /inbox/{inbox_id} and
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
