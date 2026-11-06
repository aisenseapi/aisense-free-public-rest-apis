/* Capture mono PCM without playing the microphone back through the speakers. */
class AudioDataCapture extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = new Int16Array(4096);
    this.used = 0;
    this.level = 0;
    this.running = true;
    this.samples = 0;
    this.maxSamples = Math.floor(sampleRate * 40);
    this.toneSamples = 0;
    this.lastToneSample = 0;
    this.coefficients = [1400, 1800, 2200, 2600, 14800, 15200, 15600, 16000, 18500, 18900, 19300, 19700].map(frequency => 2 * Math.cos(2 * Math.PI * frequency / sampleRate));
    this.history = new Float64Array(4); // The last four input samples, for the high-pass filter.
    this.highpassed = new Float32Array(128);
    this.port.onmessage = event => {
      if (event.data === 'stop') {
        this.running = false;
        this.flush();
        this.port.postMessage({ stopped: true });
      }
    };
  }

  flush() {
    if (!this.used) return;
    const pcm = this.buffer.slice(0, this.used);
    this.port.postMessage({ pcm, level: this.level, toneSamples: this.toneSamples, lastToneSample: this.lastToneSample }, [pcm.buffer]);
    this.used = 0;
    this.level = 0;
  }

  // True when one of four tones carries most of this block's energy.
  hasTone(samples, length, energy, first) {
    if (energy / length <= 0.000009) return false;
    for (let k = first; k < first + 4; k++) {
      const coefficient = this.coefficients[k];
      let previous = 0, before = 0;
      for (let i = 0; i < length; i++) {
        const next = samples[i] + coefficient * previous - before;
        before = previous; previous = next;
      }
      const power = previous * previous + before * before - coefficient * previous * before;
      if (power / (energy * length) > 0.22) return true;
    }
    return false;
  }

  process(inputs) {
    if (!this.running) return false;
    const channels = inputs[0];
    if (!channels || !channels.length) return true;
    // Keep the strongest channel. Averaging opposite-phase stereo would erase
    // the data tones when a device ignores the requested mono constraint.
    let channel = channels[0];
    let energy = -1;
    for (const candidate of channels) {
      let candidateEnergy = 0;
      for (const value of candidate) candidateEnergy += value * value;
      if (candidateEnergy > energy) { channel = candidate; energy = candidateEnergy; }
    }
    const frames = Math.min(channel.length, this.maxSamples - this.samples);
    // High tones are judged after a fourth-order difference, (1 - z^-1)^4, as
    // on the server, so room noise and hum cannot hide a weak 15 or 19 kHz tone.
    if (this.highpassed.length < channel.length) this.highpassed = new Float32Array(channel.length);
    const history = this.history;
    let x1 = history[0], x2 = history[1], x3 = history[2], x4 = history[3];
    let highEnergy = 0;
    for (let i = 0; i < channel.length; i++) {
      const value = channel[i];
      const filtered = value - 4 * x1 + 6 * x2 - 4 * x3 + x4;
      x4 = x3; x3 = x2; x2 = x1; x1 = value;
      this.highpassed[i] = filtered;
      highEnergy += filtered * filtered;
    }
    history[0] = x1; history[1] = x2; history[2] = x3; history[3] = x4;
    // This only recognizes tone activity to end capture after a quiet gap.
    // It does not decode a message or replace the server's integrity check.
    if (this.hasTone(channel, channel.length, energy, 0) || this.hasTone(this.highpassed, channel.length, highEnergy, 4) || this.hasTone(this.highpassed, channel.length, highEnergy, 8)) {
      this.toneSamples += frames;
      this.lastToneSample = this.samples + frames;
    }
    for (let i = 0; i < frames; i++) {
      const sample = Math.max(-1, Math.min(1, channel[i]));
      this.level = Math.max(this.level, Math.abs(sample));
      this.buffer[this.used++] = Math.round(sample * (sample < 0 ? 32768 : 32767));
      this.samples++;
      if (this.used === this.buffer.length) this.flush();
    }
    if (this.samples >= this.maxSamples) {
      this.running = false;
      this.flush();
      this.port.postMessage({ limit: true });
      return false;
    }
    return true;
  }
}

registerProcessor('audio-data-capture', AudioDataCapture);
