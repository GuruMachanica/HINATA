/**
 * HINATA Gateway WebSocket Integration Test with Neural Audio Check
 * Under 50 LOC.
 */

const WebSocket = require('ws');
const ws = new WebSocket('ws://127.0.0.1:8080');
const events = [];

ws.on('open', () => {
  console.log('[TestClient] Connected. Querying HINATA...');
  ws.send(JSON.stringify({ type: 'chat', text: 'State your readiness.' }));
});

ws.on('message', (data) => {
  const frame = JSON.parse(data.toString());
  console.log(`[TestClient] Frame [${frame.type}]:`, (frame.payload && frame.payload.text) ? frame.payload.text.slice(0, 50) : '');
  events.push(frame.type);

  if (frame.type === 'speech_chunk' && frame.payload && frame.payload.audio) {
    console.log('[TestClient] SUCCESS: Received studio neural audio URI in speech_chunk!');
    ws.close();
    process.exit(0);
  }
});

setTimeout(() => {
  console.error('[TestClient] Timeout waiting for speech_chunk');
  process.exit(1);
}, 20000);
