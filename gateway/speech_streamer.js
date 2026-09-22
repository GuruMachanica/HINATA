/**
 * HINATA Speech Streamer with Neural TTS Synthesis
 * Splits text into sentences and generates studio-quality neural audio via edge-tts.
 * Strictly under 80 LOC.
 */

const { execFile } = require('child_process');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..');
const NEURAL_TTS_PY = path.join(ROOT_DIR, 'voice', 'neural_tts.py');

function splitSentences(text) {
  if (!text) return [];
  const clean = text.replace(/[\r\n]+/g, ' ').trim();
  const matched = clean.match(/[^.!?]+[.!?]+|[^.!?]+$/g);
  return matched ? matched.map((s) => s.trim()).filter(Boolean) : [clean];
}

function synthesizeNeuralChunk(sentence, index, total, onReady) {
  const args = [NEURAL_TTS_PY, sentence];
  
  execFile('python', args, { cwd: ROOT_DIR, maxBuffer: 10 * 1024 * 1024 }, (err, stdout) => {
    let audioUri = null;
    if (!err && stdout) {
      try {
        const parsed = JSON.parse(stdout.trim());
        if (parsed.success && parsed.audio) {
          audioUri = parsed.audio;
        }
      } catch {}
    }

    onReady({
      sequence: index + 1,
      total: total,
      text: sentence,
      audio: audioUri,
      voice: 'en-US-AriaNeural'
    });
  });
}

module.exports = { splitSentences, synthesizeNeuralChunk };
