// Encrypted state between two runs, through Storage. The writer encrypts the state locally with a fresh
// key, stores only the envelope and keeps the key in a file. The reader fetches the envelope by its
// storage_id and decrypts it with that key. Storage holds ciphertext only and is used as it always is.
// Node.js 18 or newer, nothing beyond aisense-api.js.
//   node encrypted-state.mjs write --key-file state.key [--state state.json]
//   node encrypted-state.mjs read --storage-id <uuid> --key-file state.key
import { readFileSync, writeFileSync } from 'node:fs'
import { pathToFileURL } from 'node:url'
import { AISenseAPI, encryptLocally, decryptLocally } from '../../aisense-api.js'

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/

/**
 * Encrypts the state, writes the key to keyFile (which must not exist yet, so a key is never
 * overwritten) and stores the envelope. Resolves to what Storage reported, without the key.
 */
export async function writeState(api, state, keyFile) {
  const { envelope, key } = await encryptLocally(JSON.stringify(state))
  writeFileSync(keyFile, key, { mode: 0o600, flag: 'wx' })
  const stored = await api.storageSet(envelope)
  return { storage_id: stored.storage_id, bytes: stored.bytes, sha256_hash: stored.sha256_hash, expire_datetime: stored.expire_datetime }
}

/** Fetches the envelope by its storage_id and decrypts it with the key in keyFile. */
export async function readState(api, storageId, keyFile) {
  if (typeof storageId !== 'string' || !UUID.test(storageId)) throw new TypeError('storage_id must be a UUID')
  const key = readFileSync(keyFile, 'utf8').trim()
  const envelope = await api.storageGet(storageId)
  return JSON.parse(await decryptLocally(envelope, key))
}

const argument = name => { const at = process.argv.indexOf(name); return at > 0 ? process.argv[at + 1] : undefined }

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const command = process.argv[2]
  const keyFile = argument('--key-file')
  const api = new AISenseAPI()
  if (command === 'write' && keyFile) {
    const stateFile = argument('--state')
    const state = stateFile
      ? JSON.parse(readFileSync(stateFile, 'utf8'))
      : { open_tasks: ['read the morning feed', 'send the briefing'], last_decision: 'wait for the vote', written_at: new Date().toISOString() }
    const stored = await writeState(api, state, keyFile)
    console.log(JSON.stringify(stored, null, 2))
    console.log('The key is in ' + keyFile + ' and nowhere else. Give the next run the storage_id and that file, never the key through the API.')
  } else if (command === 'read' && keyFile && argument('--storage-id')) {
    console.log(JSON.stringify(await readState(api, argument('--storage-id'), keyFile), null, 2))
  } else {
    console.log('Usage: node encrypted-state.mjs write --key-file <file> [--state <json file>]')
    console.log('       node encrypted-state.mjs read --storage-id <uuid> --key-file <file>')
    process.exitCode = 2
  }
}
