/* Blink labs on the blink encode and decode pages. The square blinks and the camera starts only after an explicit click. */
(function () {
  'use strict';
  const API = 'https://aisenseapi.com/services/v1/';
  const MAX_BYTES = 128;
  const COUNTDOWN = 3;          // seconds to get the camera in place before the blinking starts
  const LEAD_MS = 1500;         // the square stays dark this long before and after the message
  const MAX_RECORD_MS = 180000; // the receiver reads after three minutes at the latest
  const QUIET_MS = 2500;        // and when nothing has switched for this long, or ten units if that is longer
  const SIDE = 32;              // the marked frame is scaled to this many pixels a side to measure it
  const SMALL_BELOW = 170;      // faster units flash more than three times a second: only in the small square, never full screen

  const wait = ms => new Promise(resolve => setTimeout(resolve, ms));

  async function post(endpoint, body) {
    const response = await fetch(API + endpoint, {
      method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify(body)
    });
    let json = null;
    try { json = await response.json(); } catch (e) { json = null; }
    if (!response.ok) {
      const error = new Error(json && json.error ? json.error + (json.fix ? ' ' + json.fix : '') : 'The API answered ' + response.status + '.');
      error.answer = json;
      throw error;
    }
    return json;
  }

  function say(node, message, error) {
    node.textContent = message;
    node.dataset.error = error ? 'true' : 'false';
    node.hidden = message === '';
  }

  // The sender: the API turns the text into run lengths, and the square plays them on this screen.
  function sender(lab) {
    const text = lab.querySelector('#blink-text');
    const unit = lab.querySelector('#blink-unit');
    const count = lab.querySelector('#blink-count');
    const start = lab.querySelector('#blink-start');
    const stop = lab.querySelector('#blink-stop');
    const full = lab.querySelector('#blink-full');
    const stage = lab.querySelector('.blink-stage');
    const lamp = lab.querySelector('.blink-lamp');
    const note = lab.querySelector('.blink-note');
    const status = lab.querySelector('.blink-status');
    const output = lab.querySelector('.blink-output');
    const code = lab.querySelector('.blink-code');
    const json = lab.querySelector('.blink-json');
    let run = 0;
    let lock = null;

    const bytes = () => new TextEncoder().encode(text.value).length;
    const counter = () => {
      const n = bytes();
      count.textContent = n + ' / ' + MAX_BYTES + ' bytes';
      count.dataset.invalid = n > MAX_BYTES ? 'true' : 'false';
    };
    const light = on => { lamp.dataset.on = on ? 'true' : 'false'; };
    const idle = () => {
      lab.dataset.playing = 'false';
      unit.disabled = false;
      start.disabled = false;
      stop.disabled = true;
      note.textContent = 'Ready.';
      light(false);
      if (lock) { lock.release().catch(() => {}); lock = null; }
    };

    async function play(timing, id) {
      for (let s = COUNTDOWN; s > 0; s--) {
        if (run !== id) return false;
        note.textContent = 'Starts in ' + s + ' s. Point the camera at the square.';
        await wait(1000);
      }
      if (run !== id) return false;
      note.textContent = 'Blinking.';
      await wait(LEAD_MS);
      const ends = [];
      let total = 0;
      for (const ms of timing) { total += ms; ends.push(total); }
      const begin = performance.now();
      let i = 0;
      await new Promise(resolve => {
        const frame = now => {
          const t = now - begin;
          if (run !== id || t >= total) { light(false); resolve(); return; }
          while (i < ends.length && ends[i] <= t) i++;
          light(i % 2 === 0);
          requestAnimationFrame(frame);
        };
        requestAnimationFrame(frame);
      });
      if (run !== id) return false;
      note.textContent = 'Done.';
      await wait(LEAD_MS);
      return run === id;
    }

    // A unit under 170 ms flashes more than three times a second, so the square shrinks to 140 px, under a quarter of the
    // 341 by 256 px field in which WCAG counts a general flash, and full screen is off.
    const size = () => {
      const small = Number(unit.value) < SMALL_BELOW;
      stage.dataset.small = small ? 'true' : 'false';
      full.disabled = small;
      if (small && document.fullscreenElement === stage) document.exitFullscreen().catch(() => {});
    };
    text.addEventListener('input', counter);
    unit.addEventListener('change', size);
    counter();
    size();
    start.addEventListener('click', async () => {
      const value = text.value.trim();
      if (value === '') { say(status, 'Type a message first.', true); return; }
      if (bytes() > MAX_BYTES) { say(status, 'Use at most 128 bytes.', true); return; }
      const id = ++run;
      size();
      unit.disabled = true;
      start.disabled = true;
      stop.disabled = false;
      say(status, 'Asking the API for the timing.');
      try {
        const answer = await post('blink_encode', { data: value, unit_ms: Number(unit.value) });
        if (run !== id) return;
        code.textContent = answer.morse;
        json.textContent = JSON.stringify(answer, null, 2);
        output.hidden = false;
        say(status, answer.skipped && answer.skipped.length ? 'Skipped, with no Morse code: ' + answer.skipped.join(' ') : '');
        lab.dataset.playing = 'true';
        if ('wakeLock' in navigator) { navigator.wakeLock.request('screen').then(l => { lock = l; }).catch(() => {}); }
        const done = await play(answer.timing, id);
        if (run === id) {
          say(status, done ? 'Sent ' + (Math.round(answer.duration_ms / 100) / 10) + ' s of blinking. The receiver reads it when the square stays dark.' : '');
        }
      } catch (error) {
        if (run === id) say(status, error.message, true);
      } finally {
        if (run === id) idle();
      }
    });
    stop.addEventListener('click', () => { run++; idle(); say(status, 'Stopped.'); });
    full.addEventListener('click', () => {
      if (document.fullscreenElement) { document.exitFullscreen().catch(() => {}); return; }
      if (stage.requestFullscreen) stage.requestFullscreen().catch(() => say(status, 'This browser would not go full screen.', true));
      else say(status, 'This browser has no full screen for a part of a page.', true);
    });
  }

  // The receiver: the brightness of the marked frame, one number a frame with its time, goes to the API.
  function receiver(lab) {
    const view = lab.querySelector('.blink-view');
    const video = lab.querySelector('video');
    const startButton = lab.querySelector('#blink-camera');
    const readButton = lab.querySelector('#blink-read');
    const cancelButton = lab.querySelector('#blink-cancel');
    const auto = lab.querySelector('#blink-auto');
    const meter = lab.querySelector('#blink-level');
    const dot = lab.querySelector('.blink-dot');
    const timer = lab.querySelector('.blink-timer');
    const status = lab.querySelector('.blink-status');
    const output = lab.querySelector('.blink-output');
    const result = lab.querySelector('.blink-result-text');
    const meta = lab.querySelector('.blink-result-meta');
    const json = lab.querySelector('.blink-json');
    const canvas = document.createElement('canvas');
    canvas.width = SIDE;
    canvas.height = SIDE;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    let stream = null;
    let active = false;
    let samples = [];
    let first = null;
    let last = -1;
    let lo = Infinity;
    let hi = -Infinity;
    let on = null;
    let switches = 0;
    let lastSwitch = 0;
    let shortest = Infinity;
    let frameClock = null; // chosen at the first frame: the frame's own media time when the browser gives one, else the page clock

    const shutdown = () => {
      active = false;
      if (stream) { stream.getTracks().forEach(track => track.stop()); stream = null; }
      video.srcObject = null;
      view.dataset.live = 'false';
      startButton.disabled = false;
      readButton.disabled = true;
      cancelButton.disabled = true;
      dot.dataset.on = 'false';
    };

    const brightness = () => {
      const w = video.videoWidth;
      const h = video.videoHeight;
      if (!w || !h) return null;
      const side = Math.min(w, h) * 0.25;
      ctx.drawImage(video, (w - side) / 2, (h - side) / 2, side, side, 0, 0, SIDE, SIDE);
      const data = ctx.getImageData(0, 0, SIDE, SIDE).data;
      let sum = 0;
      for (let i = 0; i < data.length; i += 4) sum += 0.2126 * data[i] + 0.7152 * data[i + 1] + 0.0722 * data[i + 2];
      return sum / (data.length / 4);
    };

    async function read() {
      const levels = samples;
      shutdown();
      if (levels.length < 6 || switches < 2) {
        say(status, 'No blinking was seen. Fit the blinking square in the marked frame and try again.', true);
        return;
      }
      say(status, 'Reading ' + levels.length + ' frames.');
      try {
        const answer = await post('blink_decode', { levels });
        result.textContent = answer.text;
        meta.textContent = 'Morse ' + answer.morse + ', a unit of ' + answer.unit_ms + ' ms, quality ' + answer.quality + (answer.inverted ? ', dark as on' : '') + '.';
        json.textContent = JSON.stringify(answer, null, 2);
        output.hidden = false;
        say(status, '');
      } catch (error) {
        const answer = error.answer || {};
        say(status, error.message + (answer.morse ? ' Read as ' + answer.morse + ', quality ' + answer.quality + '.' : ''), true);
      }
    }

    const sample = (now, frameMeta) => {
      if (!active) return;
      const hasMedia = !!frameMeta && typeof frameMeta.mediaTime === 'number' && frameMeta.mediaTime > 0;
      if (frameClock === null) frameClock = hasMedia ? 'media' : 'page';
      const stamp = frameClock === 'media' ? (hasMedia ? frameMeta.mediaTime * 1000 : null) : now;
      const value = stamp === null ? null : brightness();
      if (value !== null && (first === null || stamp - first > last)) {
        if (first === null) first = stamp;
        const t = Math.round((stamp - first) * 10) / 10;
        if (t > last) {
          last = t;
          samples.push([t, Math.round(value * 10) / 10]);
          lo = Math.min(lo, value);
          hi = Math.max(hi, value);
          meter.value = value;
          const mid = (lo + hi) / 2;
          const band = (hi - lo) / 10;
          const now_on = on === null ? value > mid : (on ? value > mid - band : value > mid + band);
          if (hi - lo >= 25 && on !== null && now_on !== on) {
            if (switches > 0) shortest = Math.min(shortest, t - lastSwitch);
            switches++;
            lastSwitch = t;
          }
          on = now_on;
          dot.dataset.on = hi - lo >= 25 && on ? 'true' : 'false';
          timer.textContent = (t / 1000).toFixed(1) + ' s' + ( t >= 1000 ? ', ' + Math.round( samples.length / ( t / 1000 ) ) + ' frames a second' : '' );
          const quiet = Math.max(QUIET_MS, 10 * (Number.isFinite(shortest) ? shortest : 0));
          if (t >= MAX_RECORD_MS || (auto.checked && switches >= 4 && t - lastSwitch >= quiet)) { read(); return; }
        }
      }
      if (video.requestVideoFrameCallback) video.requestVideoFrameCallback(sample);
      else requestAnimationFrame(sample);
    };

    startButton.addEventListener('click', async () => {
      if (!window.isSecureContext || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        say(status, 'This browser gives no camera to this page. Use a current browser over https.', true);
        return;
      }
      startButton.disabled = true;
      output.hidden = true;
      say(status, 'Starting the camera.');
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: false, video: { facingMode: { ideal: 'environment' }, width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 60 } }
        });
        video.srcObject = stream;
        await video.play();
        const w = video.videoWidth || 4;
        const h = video.videoHeight || 3;
        view.style.aspectRatio = w + ' / ' + h;
        view.dataset.portrait = h > w ? 'true' : 'false';
        view.dataset.live = 'true';
        samples = []; first = null; last = -1; lo = Infinity; hi = -Infinity; on = null; switches = 0; lastSwitch = 0; shortest = Infinity; frameClock = null;
        active = true;
        readButton.disabled = false;
        cancelButton.disabled = false;
        say(status, 'Fit the square in the marked frame and choose Blink on the sender.');
        if (video.requestVideoFrameCallback) video.requestVideoFrameCallback(sample);
        else requestAnimationFrame(sample);
      } catch (error) {
        shutdown();
        say(status, error && error.name === 'NotAllowedError' ? 'The camera was not allowed. Allow it for aisense.no and try again.' : 'The camera could not start: ' + (error && error.message ? error.message : 'unknown error') + '.', true);
      }
    });
    readButton.addEventListener('click', () => { if (active) read(); });
    cancelButton.addEventListener('click', () => { shutdown(); say(status, 'Cancelled. Nothing was sent.'); });
    document.addEventListener('visibilitychange', () => {
      if (document.hidden && active) { shutdown(); say(status, 'The camera stopped when the page was hidden. Nothing was sent.', true); }
    });
  }

  document.querySelectorAll('[data-blink-tool]').forEach(lab => {
    if (lab.dataset.blinkTool === 'send') sender(lab);
    if (lab.dataset.blinkTool === 'receive') receiver(lab);
  });
})();
