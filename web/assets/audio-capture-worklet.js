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
    this.coefficients = [1400, 1800, 2200, 2600, 18500, 18900, 19300, 19700].map(frequency => 2 * Math.cos(2 * Math.PI * frequency / sampleRate));
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
    // This only recognizes tone activity to end capture after a quiet gap.
    // It does not decode a message or replace the server's integrity check.
    if (energy / channel.length > 0.000009) {
      for (const coefficient of this.coefficients) {
        let previous = 0, before = 0;
        for (const value of channel) {
          const next = value + coefficient * previous - before;
          before = previous; previous = next;
        }
        const power = previous * previous + before * before - coefficient * previous * before;
        if (power / (energy * channel.length) > 0.22) {
          this.toneSamples += frames;
          this.lastToneSample = this.samples + frames;
          break;
        }
      }
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
