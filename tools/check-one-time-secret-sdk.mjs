/** Offline local cryptography, capability transport and no-retry checks. */
import assert from 'node:assert/strict'
import { createDecipheriv } from 'node:crypto'
import { AISenseAPI, encryptOneTimeSecret, decryptOneTimeSecret } from '../aisense-api.js'

let passed = 0
const check = (condition, label) => { assert.ok(condition, label); passed++; console.log(`  ok    ${label}`) }
const local = await encryptOneTimeSecret('Locally entered: blåbær 🔑')
check(Object.keys(local.envelope).sort().join(',') === 'algorithm,ciphertext,nonce,version', 'encrypted envelope has no key or plaintext field')
check(Buffer.from(local.key, 'base64url').length === 32 && Buffer.from(local.envelope.nonce, 'base64url').length === 12, 'fresh key and nonce have exact AES-GCM sizes')
check(await decryptOneTimeSecret(local.envelope, local.key) === 'Locally entered: blåbær 🔑', 'local UTF-8 round trip')
const encryptedBytes = Buffer.from(local.envelope.ciphertext, 'base64url')
const independent = createDecipheriv('aes-256-gcm', Buffer.from(local.key, 'base64url'), Buffer.from(local.envelope.nonce, 'base64url'))
independent.setAuthTag(encryptedBytes.subarray(-16))
check(Buffer.concat([independent.update(encryptedBytes.subarray(0, -16)), independent.final()]).toString() === 'Locally entered: blåbær 🔑', 'native Node AES-GCM independently decrypts Web Crypto envelope')
const other = await encryptOneTimeSecret('Locally entered: blåbær 🔑')
check(local.key !== other.key && local.envelope.nonce !== other.envelope.nonce, 'each encryption generates a new key and nonce')
await assert.rejects(decryptOneTimeSecret(local.envelope, other.key))
passed++
const corrupt = Buffer.from(encryptedBytes)
corrupt[0] ^= 1
await assert.rejects(decryptOneTimeSecret({ ...local.envelope, ciphertext: corrupt.toString('base64url') }, local.key))
passed++
const maximum = await encryptOneTimeSecret('å'.repeat(8192))
check(Buffer.from(maximum.envelope.ciphertext, 'base64url').length === 16400, '16 KiB UTF-8 boundary includes the 16-byte tag')
await assert.rejects(encryptOneTimeSecret('å'.repeat(8193)), /16 KiB/)
passed++
await assert.rejects(encryptOneTimeSecret(''), /1 byte/)
passed++

const requests = []
globalThis.fetch = async (url, init) => {
  requests.push({ url, init })
  return new Response(JSON.stringify({ ok: true }), { status: 200 })
}
const api = new AISenseAPI('https://example.invalid/services/v1')
await api.createOneTimeSecret(local.envelope)
assert.throws(() => api.createOneTimeSecret({ ...local.envelope, key: local.key }))
assert.throws(() => api.createOneTimeSecret({ ...local.envelope, plaintext: 'private' }))
assert.throws(() => api.revealOneTimeSecret('../secret?token=x', 'b'.repeat(64)))
check(requests.length === 1 && !requests[0].init.body.includes(local.key) && !requests[0].init.body.includes('Locally entered'), 'transport never submits local key or plaintext and rejects injected fields/paths')
await api.revealOneTimeSecret('a'.repeat(32), 'b'.repeat(64))
await api.readOneTimeSecretReceipt('a'.repeat(32), 'c'.repeat(64))
await api.burnOneTimeSecret('a'.repeat(32), 'c'.repeat(64))
check(requests.slice(1).map(r => r.init.method).join(',') === 'POST,GET,POST', 'only explicit POST consumes or burns; receipt uses GET')
check(requests.slice(1).every(r => !r.url.includes('b'.repeat(64)) && !r.url.includes('c'.repeat(64)) && r.init.headers.Authorization.startsWith('Bearer ')), 'role tokens travel only in Authorization headers')
let attempts = 0
globalThis.fetch = async () => { attempts++; throw new Error('Response lost after consumption') }
await assert.rejects(api.revealOneTimeSecret('a'.repeat(32), 'b'.repeat(64)), /Response lost/)
check(attempts === 1, 'lost reveal response is never retried')
console.log(`check-one-time-secret-sdk: ${passed} passed`)
