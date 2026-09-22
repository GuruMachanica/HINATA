/**
 * HINATA merged shell (vanilla ES modules)
 * VRM avatar stage + chat + mic + neural speech + avatar mood driving.
 */

import { VRMStage } from './vrm_stage.js';

const MODEL_URL = '/models/vrm/hinata.vrm';
const ANIMS = {
  'vrma-01': '/models/vrm/animations/VRMA_01.vrma',
  'vrma-02': '/models/vrm/animations/VRMA_02.vrma',
  'vrma-03': '/models/vrm/animations/VRMA_03.vrma',
  'vrma-04': '/models/vrm/animations/VRMA_04.vrma',
  'vrma-05': '/models/vrm/animations/VRMA_05.vrma',
  'vrma-06': '/models/vrm/animations/VRMA_06.vrma',
  'vrma-07': '/models/vrm/animations/VRMA_07.vrma',
};

const ui = new UIController();
const stageEl = document.getElementById('avatar-canvas-wrap');
const form = document.getElementById('input-form');
const input = document.getElementById('user-input');
const micBtn = document.getElementById('mic-btn');
const clockEl = document.getElementById('hud-clock');
const animSel = document.getElementById('anim-select');

setInterval(() => { clockEl.textContent = new Date().toTimeString().split(' ')[0]; }, 1000);

const stage = new VRMStage(stageEl);
stage.loadModel(MODEL_URL).then(() => {
  console.log('[HINATA] VRM loaded');
  stage.playAnimation(ANIMS['vrma-01'], 'loop'); // idle loop
}).catch((e) => console.error('[HINATA] VRM load failed', e));

const player = new SpeechPlayer(
  () => { ui.setAgentState('speaking'); stage.setSpeaking(true); },
  () => { ui.setAgentState('online'); stage.setSpeaking(false); stage.setMood('calm', 'relaxed'); }
);

// Animation select UI
if (animSel) {
  for (const [id, url] of Object.entries(ANIMS)) {
    const opt = document.createElement('option');
    opt.value = url; opt.textContent = id.replace('vrma-', 'Motion ');
    animSel.appendChild(opt);
  }
  animSel.addEventListener('change', (e) => {
    if (e.target.value) stage.playAnimation(e.target.value, 'loop');
  });
}

// Populate the anim count label once
if (animSel) animSel.options[0].textContent = `🎬 Animations (${Object.keys(ANIMS).length})...`;

// Audio analysis drives lip-sync amplitude
stage._analyserHook = () => {
  const a = player.getAudioAnalysis();
  if (a) stage.setAudioLevel(a.volume);
};

// ---- WebSocket ----
const client = new HinataWSClient(`ws://${window.location.host}`, (type, payload) => {
  switch (type) {
    case 'connection_status': ui.setAgentState(payload.connected ? 'online' : 'reconnecting'); break;
    case 'agent_state': ui.setAgentState(payload.state); break;
    case 'speech_chunk': player.enqueue(payload); break;
    case 'agent_response': ui.appendMessage('HINATA', payload.content, false); break;
    case 'avatar_mood':
      if (payload.expression) stage.setMood(payload.mood, payload.expression);
      if (payload.animation && ANIMS[payload.animation]) {
        stage.playAnimation(ANIMS[payload.animation], 'once', () =>
          stage.playAnimation(ANIMS['vrma-01'], 'loop'));
      }
      break;
    case 'barge_in_ack':
      player.bargeIn(); stage.setSpeaking(false); ui.setAgentState('listening');
      break;
  }
});
client.connect();

// ---- Mic ----
const mic = new MicController(
  (text) => { input.value = text; form.dispatchEvent(new Event('submit')); },
  () => { player.bargeIn(); stage.setSpeaking(false); client.send('barge_in', {}); ui.setAgentState('listening'); }
);
let micActive = false;
micBtn.addEventListener('click', () => { micActive = !micActive; mic.toggle(micActive); micBtn.classList.toggle('active', micActive); });

// ---- Chat form ----
form.addEventListener('submit', (e) => {
  e.preventDefault();
  const query = input.value.trim();
  if (!query) return;
  player.bargeIn(); stage.setSpeaking(false);
  ui.appendMessage('YOU', query, true);
  input.value = '';
  client.sendChat(query, {});
});

// ---- Render loop ----
(function animate() {
  stage._analyserHook();
  stage.update();
  requestAnimationFrame(animate);
})();
