/** Offline check of examples/encrypted-state against a local Storage stub. No network, no key printed. */
import assert from 'node:assert/strict'
import { createHash, randomUUID } from 'node:crypto'
import { existsSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs'
import { createServer } from 'node:http'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { AISenseAPI, encryptLocally } from '../aisense-api.js'
import { readState, writeState } from '../examples/encrypted-state/encrypted-state.mjs'

let passed = 0
const check = (condition, label) => { assert.ok(condition, label); passed++; console.log(`  ok    ${label}`) }
const objects = new Map()
const requests = []
const server = createServer((request, response) => {
  let body = ''
  request.on('data', chunk => { body += chunk })
  request.on('end', () => {
    requests.push({ method: request.method, url: request.url, body })
    const stored = request.url.match(/^\/services\/v1\/storage\/([0-9a-f-]{36})$/)
    if (request.method === 'POST' && request.url === '/services/v1/storage') {
      const id = randomUUID()
      objects.set(id, body)
      const expire = Math.floor(Date.now() / 1000) + 86400
      response.writeHead(200, { 'Content-Type': 'application/json' })
      response.end(JSON.stringify({ storage_id: id, storage_url: `http://127.0.0.1/services/v1/storage/${id}`, bytes: Buffer.byteLength(body),
        sha256_hash: createHash('sha256').update(body).digest('hex'), expire_timestamp: expire, expire_datetime: new Date(expire * 1000).toISOString() }))
    } else if (request.method === 'GET' && stored && objects.has(stored[1])) {
      response.writeHead(200, { 'Content-Type': 'application/json' })
      response.end(objects.get(stored[1]))
    } else {
      response.writeHead(404, { 'Content-Type': 'application/json' })
      response.end(JSON.stringify({ error: 'not found' }))
    }
  })
})
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
const api = new AISenseAPI(`http://127.0.0.1:${server.address().port}/services/v1`)
const dir = mkdtempSync(join(tmpdir(), 'encrypted-state-'))
try {
  const marker = 'open task: call the bank about account 1234'
  const state = { open_tasks: [marker], last_decision: 'wait', count: 3, note: 'blåbær 🔑' }
  const keyFile = join(dir, 'state.key')
  const stored = await writeState(api, state, keyFile)
  check(/^[0-9a-f-]{36}$/.test(stored.storage_id) && stored.bytes > 0 && /^[0-9a-f]{64}$/.test(stored.sha256_hash), 'write reports the Storage receipt without the key')
  check(!('key' in stored) && !JSON.stringify(stored).includes(readFileSync(keyFile, 'utf8')), 'the key is not in the receipt')
  const posted = requests.filter(r => r.method === 'POST')
  check(posted.length === 1, 'exactly one POST reached Storage')
  const envelope = JSON.parse(posted[0].body)
  check(Object.keys(envelope).sort().join(',') === 'algorithm,ciphertext,nonce,version' && envelope.version === 1 && envelope.algorithm === 'AES-256-GCM', 'Storage received an envelope and nothing else')
  check(!posted[0].body.includes(marker) && !posted[0].body.includes('1234') && !posted[0].body.includes(readFileSync(keyFile, 'utf8')), 'the stored bytes carry neither the state nor the key')
  check(readFileSync(keyFile, 'utf8').length === 43, 'the key file holds one 32-byte key as unpadded base64url')
  if (process.platform !== 'win32') check((statSync(keyFile).mode & 0o777) === 0o600, 'the key file is mode 0600')
  check(JSON.stringify(await readState(api, stored.storage_id, keyFile)) === JSON.stringify(state), 'read returns the same state, UTF-8 intact')
  await assert.rejects(writeState(api, state, keyFile), /EEXIST/)
  check(requests.filter(r => r.method === 'POST').length === 1, 'an existing key file is never overwritten, and nothing was stored')
  const otherKey = join(dir, 'other.key')
  writeFileSync(otherKey, (await encryptLocally('x')).key)
  await assert.rejects(readState(api, stored.storage_id, otherKey))
  passed++
  console.log('  ok    a wrong key fails the decryption')
  const damaged = JSON.parse(objects.get(stored.storage_id))
  const bytes = Buffer.from(damaged.ciphertext, 'base64url')
  bytes[0] ^= 1
  objects.set(stored.storage_id, JSON.stringify({ ...damaged, ciphertext: bytes.toString('base64url') }))
  await assert.rejects(readState(api, stored.storage_id, keyFile))
  passed++
  console.log('  ok    a changed byte fails the decryption')
  await assert.rejects(readState(api, 'not-a-uuid', keyFile), /UUID/)
  passed++
  console.log('  ok    read refuses a storage_id that is not a UUID')
  check(requests.every(r => !r.body.includes(readFileSync(keyFile, 'utf8')) && !r.url.includes(readFileSync(keyFile, 'utf8'))), 'no request carried the key')
} finally {
  server.close()
  rmSync(dir, { recursive: true, force: true })
}
check(!existsSync(dir), 'the temporary key files are gone')
console.log(`check-encrypted-state-example: ${passed} passed`)
