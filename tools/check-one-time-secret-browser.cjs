'use strict';

// Offline checks only. No request is made to the public service.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { webcrypto } = require('node:crypto');
const sourcePath = path.join(__dirname, '../web/assets/one-time-secret.js');
const source = fs.readFileSync(sourcePath, 'utf8');
const html = fs.readFileSync(path.join(__dirname, '../web/one-time-secret.html'), 'utf8');
const secret = require(sourcePath);
const id = 'a'.repeat(32);
const readToken = 'b'.repeat(64);
const receiptToken = 'c'.repeat(64);
const created = { secret_id: id, read_token: readToken, receipt_token: receiptToken, expire_timestamp: 1793275200, expire_datetime: '2026-10-29T12:00:00Z' };
const response = (body) => ({ ok: true, json: async () => body });

function browser(fragment = '', fetcher = () => { throw new Error('Unexpected network request'); }, options = {}) {
    const elements = {};
    for (const match of html.matchAll(/\bid="([^"]+)"/g)) {
        elements[match[1]] = {
            value: '', textContent: '', hidden: true, disabled: false, listeners: {},
            classList: { toggle() {} }, focus() {}, select() {},
            addEventListener(event, callback) { this.listeners[event] = callback; }
        };
    }
    const windowListeners = {};
    const calls = [];
    let ready;
    let cleared = false;
    const window = {
        location: { hash: fragment, search: options.search || '', pathname: '/one-time-secret' },
        history: { replaceState(state, unused, url) { assert.equal(state, null); assert.equal(url, '/one-time-secret'); cleared = true; } },
        isSecureContext: options.secure !== false,
        addEventListener(event, callback) { windowListeners[event] = callback; }
    };
    vm.runInNewContext(source, {
        window, document: { getElementById: (name) => elements[name], addEventListener(event, callback) { assert.equal(event, 'DOMContentLoaded'); ready = callback; } },
        crypto: webcrypto, TextEncoder, TextDecoder, Uint8Array, URLSearchParams, btoa, atob, AbortController, setTimeout, clearTimeout,
        navigator: { clipboard: { writeText: async () => {} } },
        fetch: async (url, config) => { calls.push({ url, config }); return fetcher(url, config); }
    });
    assert.equal(cleared, !!(fragment || options.search), 'fragment must clear before DOMContentLoaded');
    ready();
    return {
        elements, calls,
        fire: (name, event = 'click') => elements[name].listeners[event]({ preventDefault() {} }),
        pagehide: () => windowListeners.pagehide()
    };
}

test('AES-256-GCM interoperates with Web Crypto and preserves literal UTF-8 text', async () => {
    const text = 'A literal <script>alert(1)</script> and \u00e6\u00f8\u00e5\nSecond line.';
    const result = await secret.encrypt(text, webcrypto);
    assert.equal(secret.decode(result.key, 32, 32).length, 32);
    assert.equal(secret.decode(result.envelope.nonce, 12, 12).length, 12);
    assert.equal(secret.decode(result.envelope.ciphertext, 17, 16400).length, Buffer.byteLength(text) + 16);
    assert.equal(await secret.decrypt(result.envelope, result.key, webcrypto), text);
    const key = await webcrypto.subtle.importKey('raw', secret.decode(result.key, 32, 32), 'AES-GCM', false, ['decrypt']);
    const raw = await webcrypto.subtle.decrypt({ name: 'AES-GCM', iv: secret.decode(result.envelope.nonce, 12, 12), tagLength: 128 }, key, secret.decode(result.envelope.ciphertext, 17, 16400));
    assert.equal(new TextDecoder().decode(raw), text);
    const other = await secret.encrypt(text, webcrypto);
    assert.notEqual(other.key, result.key);
    assert.notEqual(other.envelope.nonce, result.envelope.nonce);
});

test('UTF-8 byte limits include the 16 KiB boundary', async () => {
    const text = '\u00e6'.repeat(8192);
    const result = await secret.encrypt(text, webcrypto);
    assert.equal(await secret.decrypt(result.envelope, result.key, webcrypto), text);
    await assert.rejects(secret.encrypt(text + 'x', webcrypto));
    await assert.rejects(secret.encrypt('', webcrypto));
});

test('authentication rejects tampering and a wrong key', async () => {
    const result = await secret.encrypt('message', webcrypto);
    const wrong = await secret.encrypt('other', webcrypto);
    await assert.rejects(secret.decrypt(result.envelope, wrong.key, webcrypto));
    const bytes = secret.decode(result.envelope.ciphertext, 17, 16400);
    bytes[0] ^= 1;
    await assert.rejects(secret.decrypt({ ...result.envelope, ciphertext: secret.encode(bytes) }, result.key, webcrypto));
});

test('rejects noncanonical encodings and unknown envelope fields', async () => {
    const result = await secret.encrypt('message', webcrypto);
    assert.throws(() => secret.decode('AQ=', 1, 1));
    assert.throws(() => secret.decode('AR', 1, 1));
    assert.throws(() => secret.decode('a'.repeat(22000), 1, 16400));
    assert.throws(() => secret.validateEnvelope({ ...result.envelope, plaintext: 'message' }));
    assert.throws(() => secret.validateEnvelope({ ...result.envelope, version: 2 }));
    assert.throws(() => secret.validateEnvelope({ ...result.envelope, nonce: 'AA' }));
});

test('share and receipt capabilities remain separate and links use fragments', async () => {
    const result = await secret.encrypt('message', webcrypto);
    const links = secret.makeLinks(created, result.key);
    const share = new URL(links.share);
    assert.equal(share.origin, 'https://aisense.no');
    assert.equal(share.search, '');
    assert.equal(secret.parseFragment(share.hash).key, result.key);
    assert.equal(secret.parseFragment(new URL(links.receipt).hash).receipt, receiptToken);
    assert.ok(!links.receipt.includes(result.key));
    assert.ok(!links.receipt.includes(readToken));
    assert.throws(() => secret.makeLinks({ ...created, key: result.key }, result.key));
    for (const fragment of [share.hash + '&id=' + id, share.hash + '&unknown=1', share.hash + '&receipt=' + receiptToken, '#id=' + id, '#id=' + id + '&token=' + readToken + '&key=AA', '#id=' + id.toUpperCase() + '&receipt=' + receiptToken]) assert.throws(() => secret.parseFragment(fragment));
});

test('browser creation sends only ciphertext and clears input after success', async () => {
    const app = browser('', async (url, config) => {
        assert.equal(url, 'https://aisenseapi.com/services/v1/secret');
        assert.equal(config.method, 'POST');
        assert.equal(config.credentials, 'omit');
        assert.equal(config.cache, 'no-store');
        assert.equal(config.redirect, 'error');
        assert.equal(config.referrerPolicy, 'no-referrer');
        const envelope = JSON.parse(config.body);
        assert.deepEqual(Object.keys(envelope).sort(), ['algorithm', 'ciphertext', 'nonce', 'version']);
        secret.validateEnvelope(envelope);
        assert.ok(!config.body.includes('example private message'));
        return response(created);
    });
    app.elements['secret-input'].value = 'example private message';
    await app.fire('create-form', 'submit');
    assert.equal(app.calls.length, 1);
    assert.equal(app.elements['secret-input'].value, '');
    assert.equal(app.elements['share-panel'].hidden, false);
    const share = secret.parseFragment(new URL(app.elements['share-link'].value).hash);
    assert.equal(await secret.decrypt(JSON.parse(app.calls[0].config.body), share.key, webcrypto), 'example private message');
    app.pagehide();
    assert.equal(app.elements['share-link'].value, '');
    assert.equal(app.elements['receipt-link'].value, '');
});

test('opening a link does not fetch; explicit reveal sends the read token once', async () => {
    const encrypted = await secret.encrypt('<img src=x onerror=alert(1)>', webcrypto);
    const links = secret.makeLinks(created, encrypted.key);
    const app = browser(new URL(links.share).hash, async (url, config) => {
        assert.equal(url, 'https://aisenseapi.com/services/v1/secret/' + id + '/reveal');
        assert.equal(config.method, 'POST');
        assert.equal(config.headers.Authorization, 'Bearer ' + readToken);
        assert.equal(config.body, undefined);
        assert.ok(!JSON.stringify({ url, config }).includes(encrypted.key));
        return response(encrypted.envelope);
    });
    assert.equal(app.calls.length, 0);
    await Promise.all([app.fire('reveal-button'), app.fire('reveal-button')]);
    assert.equal(app.calls.length, 1);
    assert.equal(app.elements['secret-output'].textContent, '<img src=x onerror=alert(1)>');
    assert.equal(app.elements['revealed-panel'].hidden, false);
    await app.fire('clear-secret');
    assert.equal(app.elements['secret-output'].textContent, '');
});

test('failed consume response leaves reveal disabled and never retries', async () => {
    const encrypted = await secret.encrypt('message', webcrypto);
    const app = browser(new URL(secret.makeLinks(created, encrypted.key).share).hash, async () => { throw new Error('Lost response'); });
    await app.fire('reveal-button');
    await app.fire('reveal-button');
    assert.equal(app.calls.length, 1);
    assert.equal(app.elements['reveal-button'].disabled, true);
    assert.match(app.elements.notice.textContent, /may have been consumed/);
    assert.equal(app.elements['secret-output'].textContent, '');
});

test('receipt requires an explicit check and separate confirmation for revocation', async () => {
    const app = browser('#id=' + id + '&receipt=' + receiptToken, async (url, config) => {
        assert.equal(config.headers.Authorization, 'Bearer ' + receiptToken);
        return response({ secret_id: id, state: config.method === 'GET' ? 'pending' : 'revoked', expire_timestamp: created.expire_timestamp });
    });
    assert.equal(app.calls.length, 0);
    await app.fire('refresh-receipt');
    assert.equal(app.calls[0].config.method, 'GET');
    await app.fire('burn-secret');
    assert.equal(app.calls.length, 1);
    await app.fire('confirm-burn');
    assert.equal(app.calls.length, 2);
    assert.equal(app.calls[1].config.method, 'POST');
    assert.ok(app.calls[1].url.endsWith('/burn'));
});

test('invalid links, query parameters and insecure contexts fail closed', () => {
    for (const app of [browser('#unexpected=1'), browser('', undefined, { search: '?key=do-not-use-query' }), browser('', undefined, { secure: false })]) {
        assert.equal(app.calls.length, 0);
        assert.equal(app.elements['create-panel'].hidden, true);
        assert.equal(app.elements['receive-panel'].hidden, true);
        assert.equal(app.elements.notice.hidden, false);
    }
});

test('tool has only its dedicated script and privacy restrictions', () => {
    assert.equal([...html.matchAll(/<script\b/g)].length, 1);
    assert.match(html, /script src="\/assets\/one-time-secret\.js/);
    assert.match(html, /connect-src https:\/\/aisenseapi\.com/);
    assert.match(html, /name="referrer" content="no-referrer"/);
    assert.match(html, /name="robots" content="noindex, nofollow, noarchive"/);
    assert.ok(!/\b(?:localStorage|sessionStorage|console\.|innerHTML)\b/.test(source));
    assert.ok(!/\bon(?:click|submit|load)\s*=/.test(html));
});
