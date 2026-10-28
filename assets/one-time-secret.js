(function () {
    'use strict';

    // Capture and remove access material before the rest of the page loads.
    // No secret, key, link or token is persisted in browser storage.
    let initialFragment = '';
    let initialError = '';
    if (typeof window !== 'undefined') {
        initialFragment = window.location.hash;
        if (window.location.search) initialError = 'Use the original link with its details after #. Query parameters are not accepted.';
        try {
            if (initialFragment || window.location.search) window.history.replaceState(null, '', window.location.pathname);
        } catch (_) {
            initialError = 'This browser could not clear the access details from the address bar. Open the original link in a supported browser.';
        }
    }

    const API = 'https://aisenseapi.com/services/v1/secret';
    const PAGE = 'https://aisense.no/one-time-secret';
    const MAX_BYTES = 16384;
    const ID_PATTERN = /^[a-f0-9]{32}$/;
    const TOKEN_PATTERN = /^[a-f0-9]{64}$/;

    function encode(bytes) {
        let binary = '';
        for (const byte of bytes) binary += String.fromCharCode(byte);
        return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    }

    function decode(value, minBytes, maxBytes) {
        if (typeof value !== 'string' || !/^[A-Za-z0-9_-]+$/.test(value) || value.length > Math.ceil(maxBytes * 4 / 3)) {
            throw new Error('Invalid encoding.');
        }
        const binary = atob(value.replace(/-/g, '+').replace(/_/g, '/'));
        const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
        if (bytes.length < minBytes || bytes.length > maxBytes || encode(bytes) !== value) throw new Error('Invalid encoding.');
        return bytes;
    }

    function parseFragment(fragment) {
        if (!fragment || fragment === '#') return { mode: 'create' };
        if (!fragment.startsWith('#') || fragment.length > 1024) throw new Error('Invalid link.');
        const params = new URLSearchParams(fragment.slice(1));
        const keys = Array.from(params.keys());
        if (new Set(keys).size !== keys.length || !ID_PATTERN.test(params.get('id') || '')) throw new Error('Invalid link.');
        if (keys.length === 3 && keys.every((key) => ['id', 'token', 'key'].includes(key)) && TOKEN_PATTERN.test(params.get('token') || '')) {
            decode(params.get('key'), 32, 32);
            return { mode: 'receive', id: params.get('id'), token: params.get('token'), key: params.get('key') };
        }
        if (keys.length === 2 && keys.every((key) => ['id', 'receipt'].includes(key)) && TOKEN_PATTERN.test(params.get('receipt') || '')) {
            return { mode: 'receipt', id: params.get('id'), receipt: params.get('receipt') };
        }
        throw new Error('Invalid link.');
    }

    function validateEnvelope(envelope) {
        if (!envelope || Array.isArray(envelope) || Object.keys(envelope).sort().join(',') !== 'algorithm,ciphertext,nonce,version' || envelope.version !== 1 || envelope.algorithm !== 'AES-256-GCM') {
            throw new Error('Unsupported encrypted message.');
        }
        return { nonce: decode(envelope.nonce, 12, 12), ciphertext: decode(envelope.ciphertext, 17, MAX_BYTES + 16) };
    }

    async function encrypt(text, cryptoProvider = globalThis.crypto) {
        const plaintext = new TextEncoder().encode(text);
        if (!plaintext.length || plaintext.length > MAX_BYTES) throw new Error('Enter between 1 and 16384 bytes of text.');
        const key = await cryptoProvider.subtle.generateKey({ name: 'AES-GCM', length: 256 }, true, ['encrypt', 'decrypt']);
        const nonce = cryptoProvider.getRandomValues(new Uint8Array(12));
        const ciphertext = await cryptoProvider.subtle.encrypt({ name: 'AES-GCM', iv: nonce, tagLength: 128 }, key, plaintext);
        plaintext.fill(0);
        return {
            key: encode(new Uint8Array(await cryptoProvider.subtle.exportKey('raw', key))),
            envelope: { version: 1, algorithm: 'AES-256-GCM', nonce: encode(nonce), ciphertext: encode(new Uint8Array(ciphertext)) }
        };
    }

    async function decrypt(envelope, encodedKey, cryptoProvider = globalThis.crypto) {
        const values = validateEnvelope(envelope);
        const rawKey = decode(encodedKey, 32, 32);
        const key = await cryptoProvider.subtle.importKey('raw', rawKey, { name: 'AES-GCM' }, false, ['decrypt']);
        rawKey.fill(0);
        const plaintext = new Uint8Array(await cryptoProvider.subtle.decrypt({ name: 'AES-GCM', iv: values.nonce, tagLength: 128 }, key, values.ciphertext));
        try { return new TextDecoder('utf-8', { fatal: true }).decode(plaintext); }
        finally { plaintext.fill(0); }
    }

    function validateCreated(value) {
        if (!value || Object.keys(value).sort().join(',') !== 'expire_datetime,expire_timestamp,read_token,receipt_token,secret_id' || typeof value.expire_datetime !== 'string' || !ID_PATTERN.test(value.secret_id || '') || !TOKEN_PATTERN.test(value.read_token || '') || !TOKEN_PATTERN.test(value.receipt_token || '') || !Number.isSafeInteger(value.expire_timestamp) || value.expire_timestamp <= 0) {
            throw new Error('Invalid creation response.');
        }
        return value;
    }

    function makeLinks(created, key) {
        validateCreated(created);
        decode(key, 32, 32);
        return {
            share: PAGE + '#' + new URLSearchParams({ id: created.secret_id, token: created.read_token, key }),
            receipt: PAGE + '#' + new URLSearchParams({ id: created.secret_id, receipt: created.receipt_token })
        };
    }

    function start() {
        const byId = (id) => document.getElementById(id);
        const panels = ['create', 'share', 'receive', 'revealed', 'receipt'];
        let state = {};
        let revealAttempted = false;
        let creating = false;
        let receiptBusy = false;
        let inactive = false;

        function notify(message, error = false) {
            byId('notice').textContent = message;
            byId('notice').classList.toggle('error', error);
            byId('notice').hidden = !message;
        }

        function show(panel) {
            panels.forEach((name) => { byId(name + '-panel').hidden = name !== panel; });
        }

        async function request(path, method, token, envelope) {
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 30000);
            const headers = { Accept: 'application/json' };
            if (token) headers.Authorization = 'Bearer ' + token;
            if (envelope) headers['Content-Type'] = 'application/json';
            try {
                const response = await fetch(API + path, {
                    method, headers, body: envelope ? JSON.stringify(envelope) : undefined,
                    credentials: 'omit', cache: 'no-store', redirect: 'error', referrerPolicy: 'no-referrer', signal: controller.signal
                });
                if (!response.ok) throw new Error('Request failed.');
                return await response.json();
            } finally { clearTimeout(timeout); }
        }

        async function copy(value, field) {
            try {
                await navigator.clipboard.writeText(value);
                notify('Copied. Clipboard contents remain until you replace or clear them.');
            } catch (_) {
                if (field) { field.focus(); field.select(); }
                notify('Clipboard access is unavailable. Select the text and copy it manually.');
            }
        }

        function updateSize() {
            const bytes = new TextEncoder().encode(byId('secret-input').value).length;
            byId('byte-count').textContent = bytes + ' / 16384 bytes';
            byId('byte-count').classList.toggle('over-limit', bytes > MAX_BYTES);
            byId('create-button').disabled = creating || !bytes || bytes > MAX_BYTES;
        }

        byId('secret-input').addEventListener('input', updateSize);
        byId('create-form').addEventListener('submit', async (event) => {
            event.preventDefault();
            if (creating || inactive) return;
            const bytes = new TextEncoder().encode(byId('secret-input').value).length;
            if (!bytes || bytes > MAX_BYTES) { notify('Enter between 1 and 16384 bytes of text.', true); return; }
            creating = true;
            updateSize();
            notify('Encrypting in your browser...');
            try {
                const encrypted = await encrypt(byId('secret-input').value);
                const created = validateCreated(await request('', 'POST', null, encrypted.envelope));
                if (inactive) return;
                const links = makeLinks(created, encrypted.key);
                state = { mode: 'receipt', id: created.secret_id, receipt: created.receipt_token };
                byId('share-link').value = links.share;
                byId('receipt-link').value = links.receipt;
                byId('secret-input').value = '';
                byId('expires').textContent = 'Expires ' + new Date(created.expire_timestamp * 1000).toLocaleString() + ' (your local time).';
                show('share');
                notify('Encrypted message stored. Save your links before leaving this page.');
            } catch (_) {
                if (!inactive) notify('A link could not be created. If the response was lost, an inaccessible encrypted record may exist until expiry. No automatic retry was made.', true);
            } finally { creating = false; updateSize(); }
        });

        byId('copy-share').addEventListener('click', () => copy(byId('share-link').value, byId('share-link')));
        byId('copy-receipt').addEventListener('click', () => copy(byId('receipt-link').value, byId('receipt-link')));
        byId('copy-secret').addEventListener('click', () => copy(byId('secret-output').textContent));
        byId('clear-secret').addEventListener('click', () => {
            byId('secret-output').textContent = '';
            byId('copy-secret').disabled = true;
            byId('clear-secret').disabled = true;
            notify('The message has been cleared from this view. Existing copies and clipboard contents are not erased.');
        });

        byId('reveal-button').addEventListener('click', async () => {
            if (revealAttempted || inactive || state.mode !== 'receive') return;
            revealAttempted = true;
            byId('reveal-button').disabled = true;
            notify('Requesting the encrypted message once...');
            try {
                const envelope = await request('/' + state.id + '/reveal', 'POST', state.token);
                const plaintext = await decrypt(envelope, state.key);
                if (inactive) return;
                byId('secret-output').textContent = plaintext;
                show('revealed');
                notify('Decrypted in your browser. The link cannot deliver this message again.');
                byId('secret-output').focus();
            } catch (_) {
                if (!inactive) notify('The secret could not be revealed. It may be expired, revoked, already delivered, or the link or connection may be invalid. The message may have been consumed even if no text appeared. No retry will be made.', true);
            } finally { state = {}; }
        });

        async function checkReceipt() {
            if (receiptBusy || inactive || state.mode !== 'receipt') return;
            receiptBusy = true;
            byId('refresh-receipt').disabled = true;
            byId('burn-secret').hidden = true;
            byId('burn-confirm').hidden = true;
            notify('Checking receipt...');
            try {
                const receipt = await request('/' + state.id + '/receipt', 'GET', state.receipt);
                if (inactive) return;
                if (receipt.secret_id !== state.id || !['pending', 'delivered', 'revoked', 'expired'].includes(receipt.state) || !Number.isSafeInteger(receipt.expire_timestamp)) throw new Error('Invalid receipt.');
                const labels = { pending: 'Pending - available to reveal', delivered: 'Delivered - released once', revoked: 'Revoked - no longer available', expired: 'Expired - no longer available' };
                byId('receipt-state').textContent = labels[receipt.state];
                byId('receipt-detail').textContent = 'Original expiry: ' + new Date(receipt.expire_timestamp * 1000).toLocaleString() + ' (your local time).';
                byId('burn-secret').hidden = receipt.state !== 'pending';
                notify('Receipt checked. This page does not poll automatically.');
            } catch (_) {
                if (!inactive) {
                    byId('receipt-state').textContent = 'Receipt unavailable';
                    byId('receipt-detail').textContent = '';
                    notify('The receipt could not be checked. The link may be invalid, the record may have been cleaned up, or the service may be unavailable.', true);
                }
            } finally { receiptBusy = false; byId('refresh-receipt').disabled = false; }
        }

        byId('open-receipt').addEventListener('click', () => { byId('back-to-links').hidden = false; show('receipt'); checkReceipt(); });
        byId('back-to-links').addEventListener('click', () => { show('share'); notify('Save your links before leaving this page.'); });
        byId('refresh-receipt').addEventListener('click', checkReceipt);
        byId('burn-secret').addEventListener('click', () => { byId('burn-confirm').hidden = false; });
        byId('cancel-burn').addEventListener('click', () => { byId('burn-confirm').hidden = true; });
        byId('confirm-burn').addEventListener('click', async () => {
            if (receiptBusy || inactive || state.mode !== 'receipt') return;
            receiptBusy = true;
            byId('confirm-burn').disabled = true;
            byId('refresh-receipt').disabled = true;
            try {
                await request('/' + state.id + '/burn', 'POST', state.receipt);
                if (!inactive) notify('Revocation request completed. Check status for the current receipt.');
            } catch (_) {
                if (!inactive) notify('Revocation could not be confirmed. Check status before assuming the secret is unavailable.', true);
            } finally {
                receiptBusy = false;
                byId('confirm-burn').disabled = false;
                byId('refresh-receipt').disabled = false;
                byId('burn-confirm').hidden = true;
                byId('burn-secret').hidden = true;
            }
        });

        window.addEventListener('pagehide', () => {
            inactive = true;
            state = {};
            initialFragment = '';
            ['secret-input', 'share-link', 'receipt-link'].forEach((id) => { byId(id).value = ''; });
            byId('secret-output').textContent = '';
            show('none');
            notify('This view was closed. Open the original link again, or create another secret.');
        });

        try {
            if (initialError) throw new Error(initialError);
            state = parseFragment(initialFragment);
            if (!window.isSecureContext || !globalThis.crypto || !globalThis.crypto.subtle) throw new Error('A modern browser with Web Crypto and a secure HTTPS connection is required.');
            show(state.mode);
            updateSize();
        } catch (error) {
            state = {};
            notify(initialError || (error.message === 'Invalid link.' || error.message === 'Invalid encoding.' ? 'This secret link is incomplete or invalid. Ask the sender for the complete original link.' : error.message), true);
        } finally { initialFragment = ''; initialError = ''; }
    }

    // Testable primitives; never expose live browser state.
    if (typeof module !== 'undefined' && module.exports) module.exports = { encode, decode, parseFragment, validateEnvelope, encrypt, decrypt, makeLinks, MAX_BYTES };
    if (typeof document !== 'undefined') document.addEventListener('DOMContentLoaded', start, { once: true });
}());
