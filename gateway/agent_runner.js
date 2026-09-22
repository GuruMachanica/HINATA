/**
 * HINATA Agent Runner
 * Spawns Python bridge subprocess, parses JSON event streams, and handles errors.
 * Strictly under 100 LOC.
 */

const { spawn } = require('child_process');
const path = require('path');
const readline = require('readline');

const ROOT_DIR = path.resolve(__dirname, '..');
const BRIDGE_PATH = path.join(ROOT_DIR, 'hermes-core', 'bridge.py');

function executeQuery(prompt, context, onEvent, onComplete) {
  if (typeof context === 'function') {
    onComplete = onEvent;
    onEvent = context;
    context = null;
  }
  const args = [BRIDGE_PATH, '-q', prompt];
  if (context) {
    args.push('-c', typeof context === 'object' ? JSON.stringify(context) : String(context));
  }
  const proc = spawn('python', args, { cwd: ROOT_DIR });

  const rl = readline.createInterface({ input: proc.stdout });

  rl.on('line', (line) => {
    const trimmed = line.trim();
    if (!trimmed) return;
    try {
      const parsed = JSON.parse(trimmed);
      if (parsed.type && parsed.payload) {
        onEvent(parsed);
      }
    } catch {
      // Non-JSON stdout fallback
      onEvent({ type: 'agent_log', payload: { text: trimmed } });
    }
  });

  proc.stderr.on('data', (data) => {
    onEvent({ type: 'agent_error', payload: { error: data.toString() } });
  });

  proc.on('close', (code) => {
    onComplete(code);
  });

  proc.on('error', (err) => {
    onEvent({ type: 'agent_error', payload: { error: err.message } });
    onComplete(1);
  });
}

module.exports = { executeQuery };
