/**
 * HINATA WebSocket Connection Handler (merged product)
 * Hermes brain (real NousResearch agent via Python adapter) + Bella mood
 * streaming + neural speech chunks + barge-in.
 */

const { spawn } = require('child_process');
const path = require('path');
const readline = require('readline');

const ROOT_DIR = path.resolve(__dirname, '..');
const BRAIN = path.join(__dirname, 'hermes_brain.py');

function setupWebSocket(wss) {
  wss.on('connection', (ws) => {
    sendFrame(ws, 'system_ready', {
      companion: 'HINATA',
      brain: 'hermes-agent (NousResearch) -> ollama dolphin3',
      voice: 'en-US-AriaNeural',
    });

    ws.on('message', (message) => {
      let data;
      try {
        data = JSON.parse(message.toString());
      } catch {
        return sendFrame(ws, 'error', { message: 'Invalid JSON payload' });
      }

      if (data.type === 'barge_in') {
        sendFrame(ws, 'barge_in_ack', { interrupted: true });
        return;
      }

      if (data.type === 'chat' && data.text) {
        sendFrame(ws, 'agent_state', { state: 'thinking' });

        // One brain turn = one python adapter call (real Hermes agent inside).
        const proc = spawn('python', [BRAIN, data.text], { cwd: ROOT_DIR });
        let stdout = '', stderr = '';

        proc.stdout.on('data', (d) => { stdout += d.toString(); });
        proc.stderr.on('data', (d) => { stderr += d.toString(); });

        proc.on('close', () => {
          let turn;
          try {
            turn = JSON.parse(stdout.trim());
          } catch {
            sendFrame(ws, 'error', { message: stderr.trim() || 'Brain returned no data' });
            return;
          }

          sendFrame(ws, 'agent_state', { state: 'speaking' });
          sendFrame(ws, 'agent_response', { content: turn.content });
          // Bella mood frame: drives VRM expression + VRMA gesture in the shell.
          sendFrame(ws, 'avatar_mood', {
            mood: turn.mood,
            expression: turn.expression,
            animation: turn.animation,
            engine: turn.engine,
            latency_ms: turn.latency_ms,
          });

          // Speech chunks
          const sentences = splitSentences(turn.content);
          sentences.forEach((s, idx) => {
            synthesizeNeuralChunk(s, idx, sentences.length, (chunk) => {
              sendFrame(ws, 'speech_chunk', chunk);
            });
          });
          sendFrame(ws, 'agent_state', { state: 'online' });
        });

        proc.on('error', (err) => {
          sendFrame(ws, 'error', { message: `Brain spawn failed: ${err.message}` });
        });
      }
    });

    ws.on('error', () => {});
  });
}

function splitSentences(text) {
  if (!text) return [];
  const clean = text.replace(/[\r\n]+/g, ' ').trim();
  const matched = clean.match(/[^.!?]+[.!?]+|[^.!?]+$/g);
  return matched ? matched.map((s) => s.trim()).filter(Boolean) : [clean];
}function synthesizeNeuralChunk(sentence, index, total, onReady) {
  const args = [path.join(ROOT_DIR, 'voice', 'neural_tts.py'), sentence];
  const { execFile } = require('child_process');
  execFile('python', args, { cwd: ROOT_DIR, maxBuffer: 10 * 1024 * 1024 }, (err, stdout) => {
    let audioUri = null;
    if (!err && stdout) {
      try {
        const parsed = JSON.parse(stdout.trim());
        if (parsed.success && parsed.audio) audioUri = parsed.audio;
      } catch {}
    }
    onReady({ sequence: index + 1, total, text: sentence, audio: audioUri, voice: 'en-US-AriaNeural' });
  });
}

function sendFrame(ws, type, payload) {
  if (ws.readyState === ws.OPEN) {
    ws.send(JSON.stringify({ type, payload }));
  }
}

module.exports = { setupWebSocket, sendFrame };
