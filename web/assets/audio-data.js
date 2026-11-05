/* Audio Data Try pages. Microphone access starts only after an explicit click. */
(function () {
  'use strict';
  const API = 'https://aisenseapi.com/services/v1/';
  const MAX_BYTES = 128;
  const MAX_SECONDS = 40;
  const MAX_WAV_BYTES = 8 * 1024 * 1024;

  function inputBytes(value, encoding) {
    if (encoding === 'utf8') return new TextEncoder().encode(value);
    if (encoding !== 'base64' || !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(value)) {
      throw new Error('Enter standard Base64 with its padding, without spaces or line breaks.');
    }
    const binary = atob(value);
    if (btoa(binary) !== value) throw new Error('The Base64 padding bits are invalid.');
    return Uint8Array.from(binary, character => character.charCodeAt(0));
  }

  function wavFromChunks(chunks, sampleRate) {
    if (sampleRate !== 44100 && sampleRate !== 48000) throw new Error('The microphone must provide 44.1 or 48 kHz audio.');
    const length = chunks.reduce((total, chunk) => total + chunk.length, 0);
    if (!length || length > sampleRate * MAX_SECONDS) throw new Error('Record between a moment and 40 seconds of audio.');
    const result = new ArrayBuffer(44 + length * 2);
    const view = new DataView(result);
    const text = (offset, value) => { for (let i = 0; i < value.length; i++) view.setUint8(offset + i, value.charCodeAt(i)); };
    text(0, 'RIFF'); view.setUint32(4, 36 + length * 2, true); text(8, 'WAVE'); text(12, 'fmt ');
    view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true); view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true); view.setUint16(34, 16, true); text(36, 'data'); view.setUint32(40, length * 2, true);
    let offset = 44;
    for (const chunk of chunks) for (const sample of chunk) { view.setInt16(offset, sample, true); offset += 2; }
    return result;
  }

  function validateFile(file) {
    if (!file || !file.size) throw new Error('Choose a PCM16 WAV recording first.');
    if (file.size > MAX_WAV_BYTES) throw new Error('The WAV file must be 8 MiB or smaller.');
  }

  // Export the byte and WAV contract for offline tests without touching a browser.
  if (typeof module === 'object' && module.exports) {
    module.exports = { inputBytes, wavFromChunks, validateFile, MAX_BYTES, MAX_SECONDS, MAX_WAV_BYTES };
    return;
  }

  const lab = document.querySelector('[data-audio-tool]');
  if (!lab) return;
  const byId = id => document.getElementById(id);
  const status = byId('audio-status');
  const mode = byId('audio-mode');
  const output = byId('audio-output');
  const urls = new Set();
  const controllers = new Set();
  let disposed = false;
  let busy = false;
  let recorder = null;
  let cancelEpoch = 0;

  function say(message, error) {
    status.textContent = message;
    status.dataset.error = error ? 'true' : 'false';
  }
  function revokeUrls() { for (const url of urls) URL.revokeObjectURL(url); urls.clear(); }
  function blobUrl(blob) { const url = URL.createObjectURL(blob); urls.add(url); return url; }
  function setBusy(value) {
    busy = value;
    for (const control of lab.querySelectorAll('[data-idle-control]')) control.disabled = value;
  }
  function errorText(error) {
    if (error.name === 'NotAllowedError') return 'Microphone access was denied. Allow it in your browser settings or upload a WAV recording.';
    if (error.name === 'NotFoundError') return 'No microphone was found. Connect one or upload a WAV recording.';
    if (error.name === 'NotReadableError') return 'The microphone could not start. Close other apps using it, then try again.';
    if (error.name === 'AbortError') return 'The request timed out or was cancelled. Try again.';
    return error.message || 'Something went wrong. Try again.';
  }
  async function request(path, options, kind) {
    const controller = new AbortController();
    controllers.add(controller);
    const timeout = setTimeout(() => controller.abort(), 60000);
    try {
      const response = await fetch(API + path, { ...options, signal: controller.signal, credentials: 'omit', cache: 'no-store', referrerPolicy: 'no-referrer' });
      if (!response.ok) {
        let message = 'Request failed (HTTP ' + response.status + ').';
        try {
          const answer = await response.json();
          if (typeof answer.error === 'string') message = answer.error;
        } catch (_) { /* Keep the HTTP status if the response was not JSON. */ }
        throw new Error(message);
      }
      if (kind === 'wav') {
        if (!/audio\/(?:x-)?wav/i.test(response.headers.get('Content-Type') || '')) throw new Error('The service did not return a WAV response.');
        const blob = await response.blob();
        if (!blob.size || blob.size > MAX_WAV_BYTES) throw new Error('The service returned an empty or oversized WAV response.');
        return blob;
      }
      return await response.json();
    } finally { clearTimeout(timeout); controllers.delete(controller); }
  }

  function updateModeNote() {
    byId('audio-mode-note').textContent = mode.value === 'ultrasound'
      ? '18.5-19.7 kHz. This experimental band may still be audible, and many microphones filter it out. Try audible mode first.'
      : mode.value === 'auto'
        ? 'Detect either mode. Start with audible tones for the first test on a new pair of devices.'
        : 'A short sequence of digital tones. Start at moderate volume with the devices close together.';
  }
  mode.addEventListener('change', updateModeNote);
  updateModeNote();

  if (lab.dataset.audioTool === 'encode') {
    const form = byId('audio-encode-form');
    const data = byId('audio-data');
    const encoding = byId('audio-input-encoding');
    const count = byId('audio-byte-count');
    const player = byId('audio-player');
    function updateCount() {
      try {
        const length = inputBytes(data.value, encoding.value).length;
        count.textContent = length + ' / ' + MAX_BYTES + ' bytes';
        count.dataset.invalid = length < 1 || length > MAX_BYTES ? 'true' : 'false';
      } catch (_) { count.textContent = 'Invalid Base64'; count.dataset.invalid = 'true'; }
    }
    function inputChanged() {
      updateCount();
      if (output.hidden) return;
      player.pause(); player.removeAttribute('src'); player.load();
      lab.dataset.playing = 'false'; output.hidden = true; revokeUrls();
      say('The input changed. Create a new sound before sending it.');
    }
    data.addEventListener('input', inputChanged);
    encoding.addEventListener('change', inputChanged);
    mode.addEventListener('change', inputChanged);
    updateCount();
    player.addEventListener('play', () => { lab.dataset.playing = 'true'; });
    for (const event of ['pause', 'ended', 'error']) player.addEventListener(event, () => { lab.dataset.playing = 'false'; });
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (busy) return;
      try {
        const length = inputBytes(data.value, encoding.value).length;
        if (!length || length > MAX_BYTES) throw new Error('Enter 1 to 128 bytes. Accented letters and emoji can use more than one byte.');
        setBusy(true); player.pause(); output.hidden = true; revokeUrls();
        say('Turning ' + length + ' bytes into sound...');
        const blob = await request('audio_encode', { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'audio/wav' }, body: JSON.stringify({ data: data.value, input_encoding: encoding.value, mode: mode.value }) }, 'wav');
        if (disposed) return;
        const url = blobUrl(blob);
        player.src = url;
        byId('audio-download').href = url;
        byId('audio-result-meta').textContent = length + ' bytes encoded. ' + (mode.value === 'ultrasound' ? 'High-frequency mode.' : 'Audible mode.');
        output.hidden = false;
        say('Sound ready. Start listening on the receiving device, then press Play below.');
      } catch (error) { if (!disposed) say(errorText(error), true); }
      finally { if (!disposed) setBusy(false); }
    });
  } else {
    const start = byId('audio-listen');
    const stop = byId('audio-stop');
    const cancel = byId('audio-cancel');
    const meter = byId('audio-level');
    const progress = byId('audio-progress');
    const elapsed = byId('audio-elapsed');
    const file = byId('audio-file');

    async function closeCapture(capture) {
      if (!capture) return;
      clearTimeout(capture.timer);
      clearTimeout(capture.flushTimeout);
      if (capture.finish) capture.finish();
      if (capture.stream) for (const track of capture.stream.getTracks()) track.stop();
      if (capture.source) capture.source.disconnect();
      if (capture.node) { capture.node.onprocessorerror = null; capture.node.port.onmessage = null; capture.node.disconnect(); capture.node.port.close(); }
      if (capture.mute) capture.mute.disconnect();
      if (capture.context && capture.context.state !== 'closed') await capture.context.close().catch(() => {});
    }
    function idleCapture() {
      stop.disabled = true;
      cancel.disabled = true;
      lab.dataset.playing = 'false';
      meter.value = 0;
      setBusy(false);
    }
    async function cancelCapture() {
      cancelEpoch++;
      const capture = recorder;
      recorder = null;
      await closeCapture(capture);
      if (capture) capture.chunks.length = 0;
      if (!disposed) { idleCapture(); say('Recording cancelled. Nothing was uploaded.'); }
    }
    async function decode(blob) {
      const epoch = cancelEpoch;
      output.hidden = true;
      revokeUrls();
      setBusy(true);
      say('Checking the recording for a complete message...');
      try {
        validateFile(blob);
        const result = await request('audio_decode/' + mode.value, { method: 'POST', headers: { 'Content-Type': 'audio/wav', Accept: 'application/json' }, body: blob });
        if (disposed || epoch !== cancelEpoch) return;
        if (typeof result.data_base64 !== 'string' || !Number.isInteger(result.byte_length) || result.byte_length < 1 || result.byte_length > MAX_BYTES) throw new Error('The service returned an unexpected decode result.');
        const bytes = inputBytes(result.data_base64, 'base64');
        if (bytes.length !== result.byte_length) throw new Error('The decoded byte count does not match the result.');
        byId('audio-result-text').textContent = typeof result.text === 'string' ? result.text : 'Binary data received. Download the bytes or copy the Base64 below.';
        byId('audio-result-base64').textContent = result.data_base64;
        byId('audio-result-meta').textContent = bytes.length + ' bytes received. Mode: ' + String(result.mode || 'unknown') + '. Integrity check passed.';
        byId('audio-bytes-download').href = blobUrl(new Blob([bytes], { type: 'application/octet-stream' }));
        output.hidden = false;
        say('Message received. The text below came from the sound.');
      } catch (error) { if (!disposed && epoch === cancelEpoch) say(errorText(error), true); }
      finally { if (!disposed && epoch === cancelEpoch) setBusy(false); }
    }
    async function finishCapture() {
      const capture = recorder;
      if (!capture || capture.stopping || !capture.node) return;
      capture.stopping = true;
      stop.disabled = true;
      cancel.disabled = true;
      clearTimeout(capture.timer);
      say('Finishing the recording...');
      if (!capture.limitReached) {
        await new Promise(resolve => {
          capture.finish = resolve;
          capture.flushTimeout = setTimeout(resolve, 1000);
          capture.node.port.postMessage('stop');
        });
      }
      clearTimeout(capture.flushTimeout);
      if (recorder !== capture || disposed) return;
      recorder = null;
      await closeCapture(capture);
      idleCapture();
      try {
        const wav = wavFromChunks(capture.chunks, capture.context.sampleRate);
        capture.chunks.length = 0;
        await decode(new Blob([wav], { type: 'audio/wav' }));
      } catch (error) { say(errorText(error), true); }
    }
    cancel.addEventListener('click', cancelCapture);
    stop.addEventListener('click', finishCapture);
    start.addEventListener('click', async () => {
      if (busy) return;
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (!window.isSecureContext || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { say('Microphone capture needs HTTPS and a browser with microphone access. You can still upload a WAV file.', true); return; }
      if (!AudioContextClass || !window.AudioWorkletNode) { say('This browser cannot capture PCM audio here. Use a current browser or upload a WAV file.', true); return; }
      const epoch = ++cancelEpoch;
      const capture = { context: null, stream: null, source: null, node: null, mute: null, chunks: [], samples: 0, stopping: false, autoStop: byId('audio-auto-stop').checked };
      recorder = capture;
      setBusy(true); cancel.disabled = false; output.hidden = true; progress.value = 0; elapsed.textContent = '0.0 / 40 s';
      say('Allow microphone access. The recording starts when the browser is ready.');
      try {
        // Resume from the button gesture before the permission prompt (needed on mobile).
        try { capture.context = new AudioContextClass({ sampleRate: 48000 }); }
        catch (_) { capture.context = new AudioContextClass(); }
        await capture.context.resume();
        if (!capture.context.audioWorklet) throw new Error('AudioWorklet is unavailable. Use a current browser or upload a WAV file.');
        await capture.context.audioWorklet.addModule('/assets/audio-capture-worklet.js?v=20261105a');
        if (disposed || epoch !== cancelEpoch) { await closeCapture(capture); return; }
        capture.stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: false, noiseSuppression: false, autoGainControl: false }, video: false });
        if (disposed || epoch !== cancelEpoch) { await closeCapture(capture); return; }
        if (![44100, 48000].includes(capture.context.sampleRate)) throw new Error('This audio device does not provide 44.1 or 48 kHz. Upload a compatible WAV file instead.');
        capture.node = new AudioWorkletNode(capture.context, 'audio-data-capture', { numberOfInputs: 1, numberOfOutputs: 1, outputChannelCount: [1] });
        capture.node.port.onmessage = event => {
          if (event.data.stopped) { if (capture.finish) capture.finish(); return; }
          if (event.data.limit) { capture.limitReached = true; if (recorder === capture) finishCapture(); return; }
          if (recorder !== capture || disposed || !event.data.pcm) return;
          const available = capture.context.sampleRate * MAX_SECONDS - capture.samples;
          const chunk = event.data.pcm.subarray(0, Math.max(0, available));
          if (chunk.length) { capture.chunks.push(chunk); capture.samples += chunk.length; }
          const seconds = capture.samples / capture.context.sampleRate;
          meter.value = Math.min(1, Math.max(0, event.data.level || 0));
          progress.value = seconds;
          elapsed.textContent = seconds.toFixed(1) + ' / 40 s';
          if (seconds >= MAX_SECONDS) finishCapture();
          else if (capture.autoStop && event.data.toneSamples >= capture.context.sampleRate &&
            capture.samples - event.data.lastToneSample >= capture.context.sampleRate * 1.2) finishCapture();
        };
        capture.node.onprocessorerror = () => { cancelCapture().then(() => say('Audio capture stopped unexpectedly. Try again or upload a WAV file.', true)); };
        capture.source = capture.context.createMediaStreamSource(capture.stream);
        capture.mute = capture.context.createGain(); capture.mute.gain.value = 0;
        capture.source.connect(capture.node); capture.node.connect(capture.mute); capture.mute.connect(capture.context.destination);
        for (const track of capture.stream.getTracks()) track.addEventListener('ended', () => { if (recorder === capture && !capture.stopping) finishCapture(); });
        capture.timer = setTimeout(finishCapture, MAX_SECONDS * 1000);
        stop.disabled = false;
        lab.dataset.playing = 'true';
        say(capture.autoStop ? 'Listening. Play the sound on the other device now. Decoding starts after the tones end, or choose Stop and decode.' : 'Listening. Play the sound on the other device now. When it ends, press Stop and decode.');
      } catch (error) {
        await closeCapture(capture);
        if (disposed || epoch !== cancelEpoch) return;
        recorder = null;
        idleCapture();
        say(errorText(error), true);
      }
    });
    byId('audio-file-form').addEventListener('submit', async event => {
      event.preventDefault();
      if (busy) return;
      try { validateFile(file.files[0]); await decode(file.files[0]); }
      catch (error) { say(errorText(error), true); }
    });
    window.addEventListener('pagehide', () => { cancelEpoch++; closeCapture(recorder); recorder = null; });
  }

  window.addEventListener('pagehide', () => {
    disposed = true;
    for (const controller of controllers) controller.abort();
    const player = byId('audio-player');
    if (player) { player.pause(); player.removeAttribute('src'); player.load(); }
    revokeUrls();
  });
  window.addEventListener('pageshow', event => {
    if (event.persisted) {
      disposed = false; busy = false; setBusy(false); output.hidden = true; lab.dataset.playing = 'false';
      for (const id of ['audio-stop', 'audio-cancel']) if (byId(id)) byId(id).disabled = true;
      if (byId('audio-level')) byId('audio-level').value = 0;
      say('Ready for a new message.');
    }
  });
}());
