# Encrypted state in Storage

`encrypted-state.mjs` passes private state from one run to the next through
Storage without Storage ever seeing it. The writer encrypts the state locally
with a fresh AES-256-GCM key, stores only the envelope and keeps the key in a
file. The reader fetches the envelope by its `storage_id` and decrypts it with
that key. Node.js 18 or newer, nothing beyond [aisense-api.js](../../aisense-api.js).

Storage is unchanged by this. It stores what it is given for 24 hours, and the
link alone gives the object to whoever holds it. Storing plaintext remains the
default and is the right choice for state that is not private, such as a
briefing that is meant to be shared. Encrypt when the next run must be the
only reader.

```sh
node examples/encrypted-state/encrypted-state.mjs write --key-file state.key
node examples/encrypted-state/encrypted-state.mjs read --storage-id <uuid> --key-file state.key
```

`write` encrypts a small sample state, or the JSON file named with `--state`,
and prints what Storage reported: `storage_id`, `bytes`, `sha256_hash` and
`expire_datetime`. The key goes into the file named with `--key-file` and
nowhere else; the file must not exist yet, so a key is never overwritten. On
POSIX the file is created with mode 0600. `read` needs the `storage_id` and the
same key file and prints the state. A wrong key, or a changed byte in the
envelope, fails the decryption instead of producing wrong state.

What travels to the next run is the `storage_id` and the key file, for example
through the next worker's own configuration or a Webhook Schedule payload that
carries the `storage_id` only. The key never goes into an API call, an MCP
argument, a plan, a model conversation or a log. To hand the key to someone else
exactly once, with a receipt that says whether it was taken, use
[One-time Secret](../../API.md#one-time-secret---client-encrypted-single-reveal);
the browser tool and `encryptOneTimeSecret` use the same envelope format.

The helpers are part of the JavaScript client. `encryptLocally(text)` returns
`{ envelope, key }`, where the envelope is `{ version: 1, algorithm:
"AES-256-GCM", nonce, ciphertext }` with unpadded base64url values, and
`decryptLocally(envelope, key)` returns the text. The envelope is what
`storageSet` stores and `storageGet` returns. The Python client transports the
same envelope but does not encrypt; a Python reader needs an AES-GCM library
and this envelope layout, with the 16-byte tag at the end of the ciphertext.

Limits are Storage's own: 80 MB stored per IP address per day, 5000 requests
per IP address per day across the services, and 24 hours per object. What the
model is given to read in a managed run is plaintext to the model provider
regardless of how it was stored; this example protects state between runs, not
input to a model.

Run the offline check, which uses a local Storage stub and no network:

```sh
node tools/check-encrypted-state-example.mjs
```
