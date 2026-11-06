'use strict';
// No microphone, API call or production data is used by this test.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const base = path.join(__dirname, '../web');
const source = fs.readFileSync(path.join(base, 'assets/audio-data.js'), 'utf8');
const core = require(path.join(base, 'assets/audio-data.js'));

test('UTF-8 and strict Base64 preserve binary bytes', () => {
  assert.equal(core.inputBytes('\u00e6'.repeat(64), 'utf8').length, 128);
  assert.deepEqual([...core.inputBytes('AAECA/8=', 'base64')], [0, 1, 2, 3, 255]);
  for (const bad of ['A', 'YQ', 'YR==', 'YQ==\n', '!!!!', 'YQ--']) assert.throws(() => core.inputBytes(bad, 'base64'));
});

test('WAV has exact PCM16 samples, little-endian headers and correct size', () => {
  for (const rate of [44100, 48000]) {
    const bytes = Buffer.from(core.wavFromChunks([new Int16Array([-32768, -1]), new Int16Array([0, 1, 32767])], rate));
    assert.equal(bytes.toString('ascii', 0, 4), 'RIFF');
    assert.equal(bytes.toString('ascii', 8, 12), 'WAVE');
    assert.equal(bytes.readUInt32LE(4), bytes.length - 8);
    assert.equal(bytes.readUInt32LE(24), rate);
    assert.equal(bytes.readUInt16LE(22), 1);
    assert.equal(bytes.readUInt16LE(34), 16);
    assert.equal(bytes.readUInt32LE(40), 10);
    assert.deepEqual(Array.from({ length: 5 }, (_, i) => bytes.readInt16LE(44 + 2 * i)), [-32768, -1, 0, 1, 32767]);
  }
  assert.throws(() => core.wavFromChunks([], 48000));
  assert.throws(() => core.wavFromChunks([new Int16Array(1)], 96000));
  assert.throws(() => core.wavFromChunks([new Int16Array(48000 * 40 + 1)], 48000));
  assert.throws(() => core.validateFile({ size: 8 * 1024 * 1024 + 1 }));
  assert.throws(() => core.validateFile(null));
});

test('worklet preserves opposite-phase stereo, clips samples, sends the tail and stops', () => {
  let Processor;
  const posts = [];
  vm.runInNewContext(fs.readFileSync(path.join(base, 'assets/audio-capture-worklet.js'), 'utf8'), {
    AudioWorkletProcessor: class { constructor() { this.port = { postMessage: value => posts.push(value) }; } },
    registerProcessor(name, value) { assert.equal(name, 'audio-data-capture'); Processor = value; },
    Int16Array, Math, sampleRate: 48000
  });
  const processor = new Processor();
  processor.process([[Float32Array.from([1, -1, .5]), Float32Array.from([-1, 1, -.5])]]);
  assert.equal(posts.length, 0);
  processor.port.onmessage({ data: 'stop' });
  assert.deepEqual([...posts[0].pcm], [32767, -32768, 16384]);
  assert.equal(posts[0].level, 1);
  assert.equal(posts[1].stopped, true);
  assert.equal(processor.process([]), false);
});

test('worklet enforces its own sample ceiling when the main thread does not respond', () => {
  let Processor;
  const posts = [];
  vm.runInNewContext(fs.readFileSync(path.join(base, 'assets/audio-capture-worklet.js'), 'utf8'), {
    AudioWorkletProcessor: class { constructor() { this.port = { postMessage: value => posts.push(value) }; } },
    registerProcessor(name, value) { Processor = value; }, Int16Array, Math, sampleRate: 48000
  });
  const processor = new Processor();
  assert.equal(processor.maxSamples, 48000 * 40);
  processor.maxSamples = 130;
  assert.equal(processor.process([[new Float32Array(128)]]), true);
  assert.equal(processor.process([[new Float32Array(128)]]), false);
  assert.equal(posts[0].pcm.length, 130);
  assert.equal(posts[1].limit, true);
  assert.equal(processor.process([[new Float32Array(128)]]), false);
});

test('worklet detects actual data tones for automatic stop, not silence', () => {
  let Processor;
  vm.runInNewContext(fs.readFileSync(path.join(base, 'assets/audio-capture-worklet.js'), 'utf8'), {
    AudioWorkletProcessor: class { constructor() { this.port = { postMessage() {} }; } },
    registerProcessor(name, value) { Processor = value; }, Int16Array, Math, sampleRate: 48000
  });
  for (const frequency of [1400, 1800, 2200, 2600, 14800, 15200, 15600, 16000]) {
    const processor = new Processor();
    for (let block = 0; block < 400; block++) processor.process([[Float32Array.from({ length: 128 }, (_, i) => .25 * Math.sin(2 * Math.PI * frequency * (block * 128 + i) / 48000))]]);
    assert.ok(processor.toneSamples >= 48000);
    const last = processor.lastToneSample;
    for (let i = 0; i < 40; i++) processor.process([[new Float32Array(128)]]);
    assert.equal(processor.lastToneSample, last);
  }
});

test('worklet hears a weak high tone under louder low room noise, and the noise alone is not a tone', () => {
  let Processor;
  vm.runInNewContext(fs.readFileSync(path.join(base, 'assets/audio-capture-worklet.js'), 'utf8'), {
    AudioWorkletProcessor: class { constructor() { this.port = { postMessage() {} }; } },
    registerProcessor(name, value) { Processor = value; }, Int16Array, Math, sampleRate: 48000
  });
  // Speakers reproduce 15 kHz far weaker than 2 kHz, so the tone sits 23 dB
  // under brown noise and 50 Hz hum, as a microphone hears a room.
  let seed = 7919, walk = 0;
  const room = n => {
    seed = (seed * 48271) % 2147483647;
    walk = 0.995 * walk + (seed / 1073741823.5 - 1);
    return 0.1 * (walk / 5.78 + 0.5 * Math.sin(2 * Math.PI * 50 * n / 48000));
  };
  for (const frequency of [14800, 15200, 15600, 16000]) {
    const processor = new Processor();
    for (let block = 0; block < 400; block++) processor.process([[Float32Array.from({ length: 128 }, (_, i) => {
      const n = block * 128 + i;
      return room(n) + .01 * Math.sin(2 * Math.PI * frequency * n / 48000);
    })]]);
    assert.ok(processor.toneSamples >= 48000);
  }
  const quiet = new Processor();
  for (let block = 0; block < 400; block++) quiet.process([[Float32Array.from({ length: 128 }, (_, i) => room(block * 128 + i))]]);
  assert.ok(quiet.toneSamples < 4800);
});

function browser(direction, fetcher, options = {}) {
  const html = fs.readFileSync(path.join(base, `free-public-api-audio-${direction}-api-endpoint.html`), 'utf8');
  const elements = {};
  for (const match of html.matchAll(/\bid="([^"]+)"/g)) {
    elements[match[1]] = { value: '', textContent: '', dataset: {}, hidden: true, disabled: false, files: [], listeners: {},
      pause() {}, load() {}, removeAttribute() {}, addEventListener(name, fn) { this.listeners[name] = fn; } };
  }
  const idle = [...html.matchAll(/<[^>]*\bid="([^"]+)"[^>]*data-idle-control[^>]*>/g)].map(m => elements[m[1]]);
  const lab = { dataset: { audioTool: direction }, querySelectorAll: () => idle };
  elements['audio-mode'].value = direction === 'encode' ? 'audible' : 'auto';
  if (elements['audio-data']) elements['audio-data'].value = 'Hello';
  if (elements['audio-input-encoding']) elements['audio-input-encoding'].value = 'utf8';
  const listeners = {};
  const calls = [];
  const nodes = [];
  const contexts = [];
  const revoked = [];
  const timers = new Map();
  let serial = 0;
  let stopped = 0;
  let micCalls = 0;
  const stream = { getTracks: () => [{ stop() { stopped++; }, addEventListener() {} }] };
  class Context {
    constructor() { this.sampleRate = 48000; this.state = 'suspended'; this.destination = {}; this.audioWorklet = { addModule: async url => assert.match(url, /audio-capture-worklet/) }; contexts.push(this); }
    async resume() { this.state = 'running'; }
    async close() { this.state = 'closed'; }
    createMediaStreamSource() { return { connect() {}, disconnect() {} }; }
    createGain() { return { gain: { value: 1 }, connect() {}, disconnect() {} }; }
  }
  class Worklet {
    constructor() {
      this.port = { onmessage: null, postMessage: message => { if (message === 'stop' && this.port.onmessage) this.port.onmessage({ data: { stopped: true } }); }, close() {} };
      nodes.push(this);
    }
    connect() {}
    disconnect() {}
  }
  const window = { AudioContext: Context, AudioWorkletNode: Worklet, isSecureContext: options.secure !== false,
    addEventListener(name, fn) { (listeners[name] ||= []).push(fn); } };
  vm.runInNewContext(source, {
    window, AudioWorkletNode: Worklet, document: { querySelector: () => lab, getElementById: id => elements[id] },
    navigator: { mediaDevices: { getUserMedia: async settings => { micCalls++; assert.equal(settings.audio.echoCancellation, false); return options.permission ? options.permission() : stream; } } },
    fetch: async (url, settings) => { calls.push({ url, settings }); if (!fetcher) throw new Error('Unexpected network'); return fetcher(url, settings); },
    URL: { createObjectURL: () => 'blob:test-' + (++serial), revokeObjectURL: url => revoked.push(url) },
    TextEncoder, Uint8Array, Int16Array, ArrayBuffer, DataView, Blob, AbortController, atob, btoa,
    setTimeout(fn, delay) { const id = ++serial; timers.set(id, { fn, delay }); return id; }, clearTimeout(id) { timers.delete(id); },
    console
  });
  return { elements, calls, contexts, nodes, revoked, timers, stream,
    get stopped() { return stopped; }, get micCalls() { return micCalls; },
    fire(id, name = 'click') { return elements[id].listeners[name]({ preventDefault() {} }); },
    async event(name, arg = {}) { for (const listener of listeners[name] || []) await listener(arg); },
    emit(samples) { nodes[0].port.onmessage({ data: { pcm: samples, level: .25 } }); }
  };
}
const json = body => ({ ok: true, json: async () => body });
const wav = () => ({ ok: true, headers: { get: () => 'audio/wav' }, blob: async () => new Blob([core.wavFromChunks([new Int16Array(16)], 48000)], { type: 'audio/wav' }) });

test('sender requires action, counts bytes, uses JSON and never auto-plays', async () => {
  const page = browser('encode', wav);
  assert.equal(page.calls.length, 0);
  let plays = 0;
  page.elements['audio-player'].play = () => plays++;
  await page.fire('audio-encode-form', 'submit');
  assert.equal(page.calls[0].url, 'https://aisenseapi.com/services/v1/audio_encode');
  assert.deepEqual(JSON.parse(page.calls[0].settings.body), { data: 'Hello', input_encoding: 'utf8', mode: 'audible' });
  assert.equal(page.elements['audio-output'].hidden, false);
  assert.equal(plays, 0);
  page.elements['audio-data'].value = '\u00e6'.repeat(65);
  await page.fire('audio-encode-form', 'submit');
  assert.equal(page.calls.length, 1);
  assert.match(page.elements['audio-status'].textContent, /128 bytes/);
  await page.event('pagehide');
  assert.equal(page.revoked.length, 1);
});

test('recording starts on click, stops tracks before upload and writes safe text', async () => {
  let page;
  page = browser('decode', (url, request) => {
    assert.ok(page.stopped > 0);
    assert.equal(url, 'https://aisenseapi.com/services/v1/audio_decode/auto');
    assert.equal(request.headers['Content-Type'], 'audio/wav');
    assert.equal(request.body.size, 44 + 8);
    const text = '<script>alert(1)</script>';
    return json({ data_base64: btoa(text), byte_length: text.length, text, mode: 'audible' });
  });
  assert.equal(page.micCalls, 0);
  await page.fire('audio-listen');
  assert.equal(page.micCalls, 1);
  page.emit(new Int16Array([1, 2, 3, 4]));
  await page.fire('audio-stop');
  assert.equal(page.calls.length, 1);
  assert.equal(page.contexts[0].state, 'closed');
  assert.equal(page.elements['audio-result-text'].textContent, '<script>alert(1)</script>');
  assert.equal(page.elements['audio-output'].hidden, false);
});

test('editing the sender invalidates the previous sound instead of sending stale data', async () => {
  const page = browser('encode', wav);
  await page.fire('audio-encode-form', 'submit');
  page.elements['audio-data'].value = 'Changed';
  page.fire('audio-data', 'input');
  assert.equal(page.elements['audio-output'].hidden, true);
  assert.equal(page.revoked.length, 1);
  assert.match(page.elements['audio-status'].textContent, /Create a new sound/);
});

test('cancel discards recording without calling decode', async () => {
  const page = browser('decode');
  await page.fire('audio-listen');
  page.emit(new Int16Array([1, 2, 3]));
  await page.fire('audio-cancel');
  assert.equal(page.calls.length, 0);
  assert.ok(page.stopped > 0);
  assert.equal(page.contexts[0].state, 'closed');
});

test('permission rejection closes context and restores controls', async () => {
  const page = browser('decode', null, { permission: () => { throw Object.assign(new Error('denied'), { name: 'NotAllowedError' }); } });
  await page.fire('audio-listen');
  assert.equal(page.contexts[0].state, 'closed');
  assert.equal(page.elements['audio-listen'].disabled, false);
  assert.match(page.elements['audio-status'].textContent, /denied/);
});

test('cancellation during the permission prompt closes a late-arriving stream', async () => {
  let resolvePermission;
  const page = browser('decode', null, { permission: () => new Promise(resolve => { resolvePermission = resolve; }) });
  const pending = page.fire('audio-listen');
  for (let i = 0; i < 6; i++) await Promise.resolve();
  assert.equal(typeof resolvePermission, 'function');
  await page.fire('audio-cancel');
  resolvePermission(page.stream);
  await pending;
  assert.ok(page.stopped > 0);
  assert.equal(page.calls.length, 0);
  assert.equal(page.contexts[0].state, 'closed');
});

test('navigation stops microphone and invalid oversized uploads never leave browser', async () => {
  const page = browser('decode');
  await page.fire('audio-listen');
  await page.event('pagehide');
  assert.ok(page.stopped > 0);
  await page.event('pageshow', { persisted: true });
  assert.equal(page.elements['audio-stop'].disabled, true);
  page.elements['audio-file'].files = [{ size: core.MAX_WAV_BYTES + 1 }];
  await page.fire('audio-file-form', 'submit');
  assert.equal(page.calls.length, 0);
  assert.match(page.elements['audio-status'].textContent, /8 MiB/);
});

test('API failures are shown and controls remain usable', async () => {
  const page = browser('encode', () => ({ ok: false, status: 429, json: async () => ({ error: 'Please wait before trying again.' }) }));
  await page.fire('audio-encode-form', 'submit');
  assert.match(page.elements['audio-status'].textContent, /Please wait/);
  assert.equal(page.elements['audio-data'].disabled, false);
  assert.equal(page.timers.size, 0);
});
