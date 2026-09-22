/**
 * HINATA Neural Speech Player
 * Plays neural audio, extracts formants, and routes speech boundary events.
 * Strictly under 90 LOC.
 */

class SpeechPlayer {
  constructor(onStart, onEnd) {
    this.queue = [];
    this.isPlaying = false;
    this.audioEl = new Audio();
    this.audioEl.crossOrigin = 'anonymous';
    this.synth = window.speechSynthesis;
    this.onStart = onStart;
    this.onEnd = onEnd;
    this.onBoundary = null;
    this._initWebAudio();
  }

  _initWebAudio() {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    try {
      this.ctx = new AudioCtx();
      this.analyser = this.ctx.createAnalyser();
      this.analyser.fftSize = 256;
      this.source = this.ctx.createMediaElementSource(this.audioEl);
      this.source.connect(this.analyser);
      this.analyser.connect(this.ctx.destination);
      this.freqData = new Uint8Array(this.analyser.frequencyBinCount);
    } catch (e) {
      console.warn('[SpeechPlayer] AudioContext deferred/fallback active');
    }
  }

  getAudioAnalysis() {
    if (!this.analyser || !this.isPlaying || !this.audioEl.src) return null;
    this.analyser.getByteFrequencyData(this.freqData);
    let low = 0, mid = 0, high = 0;
    for (let i = 1; i <= 4; i++) low += this.freqData[i];
    for (let i = 5; i <= 16; i++) mid += this.freqData[i];
    for (let i = 17; i <= 45; i++) high += this.freqData[i];
    return { low: low / 1020, mid: mid / 3060, high: high / 7395, volume: (low + mid + high) / 11475 };
  }

  enqueue(chunk) {
    this.queue.push(chunk);
    if (!this.isPlaying) this.playNext();
  }

  playNext() {
    if (!this.queue.length) {
      this.isPlaying = false;
      if (this.onEnd) this.onEnd();
      return;
    }
    this.isPlaying = true;
    if (this.ctx && this.ctx.state === 'suspended') this.ctx.resume();
    if (this.onStart) this.onStart();

    const chunk = this.queue.shift();
    if (chunk.audio) {
      this.audioEl.src = chunk.audio;
      this.audioEl.onended = () => this.playNext();
      this.audioEl.onerror = () => this.playNext();
      this.audioEl.play().catch(() => this.playFallback(chunk));
      return;
    }
    this.playFallback(chunk);
  }

  playFallback(chunk) {
    if (!this.synth) return this.playNext();
    const utt = new SpeechSynthesisUtterance(chunk.text);
    utt.onboundary = (e) => {
      if (this.onBoundary) this.onBoundary((chunk.text || '').substring(e.charIndex, e.charIndex + (e.charLength || 6)).trim());
    };
    utt.onend = () => this.playNext();
    utt.onerror = () => this.playNext();
    this.synth.speak(utt);
  }

  bargeIn() {
    this.queue = [];
    this.audioEl.pause();
    this.audioEl.currentTime = 0;
    if (this.synth) this.synth.cancel();
    this.isPlaying = false;
    if (this.onEnd) this.onEnd();
  }
}

window.SpeechPlayer = SpeechPlayer;
