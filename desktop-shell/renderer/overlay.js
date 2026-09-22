/**
 * HINATA Overlay — transparent always-on-top desktop companion renderer.
 * Procedural pose engine ported from vendor/liqu companion.js (MIT reference),
 * merged with the HINATA VRM stage, gateway WS brain, mood expressions,
 * and amplitude lip-sync.
 */

import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';

const BACKEND_PORT = process.env.HINATA_PORT || 8080;
const GATEWAY_WS = `ws://127.0.0.1:${BACKEND_PORT}`;
const MODEL_URL = GATEWAY_WS.replace('ws', 'http') + '/models/vrm/hinata.vrm';

/* ------------------------------------------------------------------ *
 * Three.js scene — alpha canvas over the transparent window
 * ------------------------------------------------------------------ */
const stageEl = document.getElementById('stage');
const bubbleEl = document.getElementById('speech-bubble');

const STAGE_W = 440;
const STAGE_H = 580;

const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(STAGE_W, STAGE_H);
renderer.setClearColor(0x000000, 0);
renderer.outputColorSpace = THREE.SRGBColorSpace;
stageEl.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(26, STAGE_W / STAGE_H, 0.05, 50);
camera.position.set(0, 0.75, 4.1);
camera.lookAt(0, 0.72, 0);

scene.add(new THREE.HemisphereLight(0xffffff, 0x444455, 2.2));
const key = new THREE.DirectionalLight(0xfffaed, 1.6); key.position.set(1.0, 2.0, 2.5); scene.add(key);
const fill = new THREE.DirectionalLight(0xdbe8ff, 0.6); fill.position.set(-1.8, 0.8, 1.2); scene.add(fill);
const rim = new THREE.DirectionalLight(0x00e5ff, 0.5); rim.position.set(0, 1.5, -2.0); scene.add(rim);

// Grounded 3D Stage Pedestal so avatar firmly stands on a physical base inside the box
const pedestalGeo = new THREE.CylinderGeometry(0.82, 0.88, 0.035, 48);
const pedestalMat = new THREE.MeshStandardMaterial({
  color: 0x0f1422,
  roughness: 0.45,
  metalness: 0.8,
});
const pedestal = new THREE.Mesh(pedestalGeo, pedestalMat);
pedestal.position.y = -0.018;
scene.add(pedestal);

// Glowing cybernetic ring and contact floor shadow on pedestal top
const floorCanvas = document.createElement('canvas');
floorCanvas.width = 256; floorCanvas.height = 256;
const fCtx = floorCanvas.getContext('2d');
const cx = 128, cy = 128;
const bootShadow = fCtx.createRadialGradient(cx, cy, 0, cx, cy, 64);
bootShadow.addColorStop(0, 'rgba(0, 0, 0, 0.85)');
bootShadow.addColorStop(0.55, 'rgba(0, 0, 0, 0.45)');
bootShadow.addColorStop(1, 'rgba(0, 0, 0, 0)');
fCtx.fillStyle = bootShadow;
fCtx.beginPath(); fCtx.arc(cx, cy, 64, 0, Math.PI * 2); fCtx.fill();

fCtx.strokeStyle = 'rgba(0, 229, 255, 0.65)';
fCtx.lineWidth = 3;
fCtx.beginPath(); fCtx.arc(cx, cy, 106, 0, Math.PI * 2); fCtx.stroke();

fCtx.strokeStyle = 'rgba(0, 229, 255, 0.35)';
fCtx.lineWidth = 1.5;
fCtx.beginPath(); fCtx.arc(cx, cy, 78, 0, Math.PI * 2); fCtx.stroke();

for (let a = 0; a < Math.PI * 2; a += Math.PI / 12) {
  const x1 = cx + Math.cos(a) * 100;
  const y1 = cy + Math.sin(a) * 100;
  const x2 = cx + Math.cos(a) * 106;
  const y2 = cy + Math.sin(a) * 106;
  fCtx.beginPath(); fCtx.moveTo(x1, y1); fCtx.lineTo(x2, y2); fCtx.stroke();
}

const floorTexture = new THREE.CanvasTexture(floorCanvas);
const floorPlaneGeo = new THREE.PlaneGeometry(1.64, 1.64);
const floorPlaneMat = new THREE.MeshBasicMaterial({
  map: floorTexture, transparent: true, opacity: 0.95, depthWrite: false,
});
const floorPlane = new THREE.Mesh(floorPlaneGeo, floorPlaneMat);
floorPlane.rotation.x = -Math.PI / 2;
floorPlane.position.y = 0.001;
scene.add(floorPlane);

const modelGroup = new THREE.Group();
scene.add(modelGroup);

let currentVrm = null;
const gltfLoader = new GLTFLoader();
gltfLoader.register((parser) => new VRMLoaderPlugin(parser));

window.addEventListener('resize', () => {
  camera.aspect = STAGE_W / STAGE_H;
  camera.updateProjectionMatrix();
  renderer.setSize(STAGE_W, STAGE_H);
});

async function loadModel(url) {
  const gltf = await gltfLoader.loadAsync(url);
  const vrm = gltf.userData.vrm;
  VRMUtils.combineSkeletons(vrm.scene);
  VRMUtils.rotateVRM0(vrm);
  modelGroup.add(vrm.scene);
  currentVrm = vrm;
  const lookTarget = new THREE.Object3D();
  lookTarget.position.set(0, 1.35, 5);
  vrm.scene.add(lookTarget);
  if (vrm.lookAt) vrm.lookAt.target = lookTarget;
  console.log('[HINATA overlay] VRM loaded');
}

/* ------------------------------------------------------------------ *
 * Procedural pose engine — ported from vendor/liqu companion.js
 * ------------------------------------------------------------------ */
const ARM_DOWN = 1.25;
function armZ(side, lift) {
  const z = ARM_DOWN * (1 - lift);
  return side === 'left' ? z : -z;
}

const BASE_POSE = {
  chest: { x: 0.02, y: 0.01, z: 0.01 },
  spine: { x: 0.015, y: 0.02, z: 0.02 },
  hips: { x: 0, y: 0, z: -0.03 },
  head: { x: 0.01, y: -0.02, z: 0.015 },
  leftUpperArm: { x: 0.14, y: 0.04, z: armZ('left', 0.16) },
  rightUpperArm: { x: 0.12, y: -0.03, z: armZ('right', 0.13) },
  leftLowerArm: { x: 0.05, y: 0.28, z: 0.4 },
  rightLowerArm: { x: 0.04, y: -0.24, z: -0.34 },
  leftHand: { x: 0.05, y: 0.06, z: 0.16 },
  rightHand: { x: 0.04, y: -0.05, z: -0.13 },
  leftUpperLeg: { x: 0.02, y: 0.01, z: 0.05 },
  rightUpperLeg: { x: -0.04, y: -0.01, z: -0.02 },
  leftLowerLeg: { x: 0.06, y: 0, z: 0 },
  rightLowerLeg: { x: 0.12, y: 0, z: 0 },
};
const TRACKED_BONES = Object.keys(BASE_POSE);

function bone(name) {
  return currentVrm?.humanoid?.getNormalizedBoneNode(name) || null;
}

function add(targets, name, dx = 0, dy = 0, dz = 0) {
  if (!targets[name]) return;
  targets[name].x += dx; targets[name].y += dy; targets[name].z += dz;
}
function setAbs(targets, name, x, y, z) {
  if (!targets[name]) return;
  targets[name].x = x; targets[name].y = y; targets[name].z = z;
}
function armLift(targets, side, lift, fwd = 0, bend = 0) {
  const upper = side === 'left' ? 'leftUpperArm' : 'rightUpperArm';
  const lower = side === 'left' ? 'leftLowerArm' : 'rightLowerArm';
  setAbs(targets, upper, fwd, 0, armZ(side, lift));
  setAbs(targets, lower, 0, 0, side === 'left' ? bend : -bend);
}

/* Behavior poses (subset tuned for HINATA) */
let behavior = 'idle';
let poseStartTime = 0;

const POSES = {
  idle: { label: 'Idle / breathing', fn: () => {} },

  look: {
    label: 'Look around',
    fn: (t, el, targets) => {
      add(targets, 'head', Math.sin(t * 0.33) * 0.1, Math.sin(t * 0.5) * 0.4, 0);
    },
  },

  wave: {
    label: 'Greeting wave',
    fn: (t, el, targets) => {
      const raise = Math.min(el / 0.4, 1);
      armLift(targets, 'right', 0.85 * raise, 0.25 * raise, 1.35 * raise);
      add(targets, 'rightLowerArm', 0, 0, Math.sin(el * 8) * 0.35);
      add(targets, 'rightHand', 0, Math.sin(el * 8) * 0.4, 0);
      add(targets, 'head', 0, -0.1 * raise, 0);
    },
  },

  think: {
    label: 'Thinking',
    fn: (t, el, targets) => {
      armLift(targets, 'right', 0.85, 0.25, 1.8);
      add(targets, 'head', 0.1, -0.08, -0.06);
      add(targets, 'spine', 0.03, 0, 0.02);
    },
  },

  stretch: {
    label: 'Stretch',
    fn: (t, el, targets) => {
      const s = Math.min(el / 0.8, 1);
      armLift(targets, 'left', 0.55 * s, 0.25 * s, 0.7 * s);
      armLift(targets, 'right', 0.55 * s, 0.25 * s, 0.7 * s);
      add(targets, 'spine', -0.08 * s, 0, 0);
      add(targets, 'head', -0.08 * s, 0, 0);
    },
  },

  sit: {
    label: 'Sit / perch',
    fn: (t, el, targets) => {
      setAbs(targets, 'leftUpperLeg', -1.4, 0, 0.1);
      setAbs(targets, 'rightUpperLeg', -1.4, 0, -0.1);
      setAbs(targets, 'leftLowerLeg', 1.5, 0, 0);
      setAbs(targets, 'rightLowerLeg', 1.5, 0, 0);
      add(targets, 'hips', 0.05, 0, 0);
      armLift(targets, 'left', 0.12, 0.2, 0.3);
      armLift(targets, 'right', 0.12, 0.2, 0.3);
      modelGroup.position.y = -0.15;
    },
  },

  walk: {
    label: 'Walk cycle',
    fn: (t, el, targets) => {
      const stride = el * 7.0;
      const swing = Math.sin(stride) * 0.55;
      setAbs(targets, 'leftUpperLeg', swing * 0.7, 0, 0.05);
      setAbs(targets, 'rightUpperLeg', -swing * 0.7, 0, -0.05);
      setAbs(targets, 'leftLowerLeg', Math.max(0, -swing) * 0.9, 0, 0);
      setAbs(targets, 'rightLowerLeg', Math.max(0, swing) * 0.9, 0, 0);
      armLift(targets, 'left', 0.18, -swing * 0.4, 0.25);
      armLift(targets, 'right', 0.18, swing * 0.4, 0.25);
      add(targets, 'spine', 0.06, 0, swing * 0.06);
      add(targets, 'head', -0.03, 0, -swing * 0.05);
      modelGroup.position.y = Math.abs(Math.sin(stride)) * 0.03;
    },
  },
};

function setBehavior(b) {
  behavior = b;
  poseStartTime = clock.getElapsedTime();
}

/* Ambient procedural life: breathing, sway, weight-shift, micro-motion */
function computePoseTargets(t, el) {
  const targets = {};
  TRACKED_BONES.forEach((n) => (targets[n] = { ...BASE_POSE[n] }));

  const def = POSES[behavior] || POSES.idle;

  const breathe = (Math.sin(t * 1.1) + Math.sin(t * 1.7 + 0.6) * 0.4) * 0.022;
  const sway = (Math.sin(t * 0.45) + Math.sin(t * 0.8 + 1.1) * 0.35) * 0.06;
  const weight = Math.sin(t * 0.16) * 0.1;
  const weightFast = Math.sin(t * 0.33 + 0.7) * 0.03;
  const drift = Math.sin(t * 0.7 + 1.3) * 0.03;
  const driftSlow = Math.sin(t * 0.27 + 2.4) * 0.04;
  const microL = (Math.sin(t * 1.9 + 0.5) + Math.sin(t * 3.1 + 1.7) * 0.4) * 0.018;
  const microR = (Math.sin(t * 1.7 + 2.1) + Math.sin(t * 2.9 + 0.3) * 0.4) * 0.018;

  add(targets, 'chest', breathe * 0.7, sway * 0.15, breathe + weightFast * 0.3);
  add(targets, 'spine', breathe * 0.35, sway * 0.45, weight * 0.55);
  add(targets, 'hips', weightFast * 0.4, sway * 0.1, weight);

  add(targets, 'leftUpperLeg', 0, 0, weight * 0.5 - weightFast * 0.2);
  add(targets, 'rightUpperLeg', 0, 0, weight * 0.5 + weightFast * 0.2);
  add(targets, 'leftLowerLeg', Math.max(0, -weight) * 0.5, 0, 0);
  add(targets, 'rightLowerLeg', Math.max(0, weight) * 0.5, 0, 0);

  add(targets, 'leftUpperArm', microL + driftSlow * 0.3, drift * 0.5, sway * 0.12 + drift + breathe * 0.5);
  add(targets, 'rightUpperArm', microR - driftSlow * 0.3, -drift * 0.5, -sway * 0.12 - drift - breathe * 0.5);
  add(targets, 'leftLowerArm', microL * 1.5, microL * 2.5 + driftSlow, drift * 0.4);
  add(targets, 'rightLowerArm', microR * 1.5, -microR * 2.5 - driftSlow, -drift * 0.4);
  add(targets, 'leftHand', 0, microL * 3, microL * 2);
  add(targets, 'rightHand', 0, -microR * 3, -microR * 2);

  // Head follows the global cursor (normalized from main process)
  const eyeYaw = cursorX * 0.4;
  const eyePitch = -cursorY * 0.25;
  add(targets, 'head', breathe * 0.6 + eyePitch + driftSlow * 0.3, sway * 0.7 + eyeYaw - weight * 0.35, weight * 0.45 + sway * 0.1);

  def.fn(t, el, targets);
  return targets;
}

/* Per-bone quaternion slerp easing (no rigid snapping — liqu approach) */
const clock = new THREE.Clock();
const SMOOTH = 9;
const BONE_EASE = {
  hips: 4, spine: 5, chest: 6,
  head: 8,
  leftUpperArm: 6, rightUpperArm: 6,
  leftLowerArm: 9, rightLowerArm: 9,
  leftHand: 12, rightHand: 12,
  leftUpperLeg: 5, rightUpperLeg: 5,
  leftLowerLeg: 8, rightLowerLeg: 8,
};
const _targetEuler = new THREE.Euler();
const _targetQuat = new THREE.Quaternion();

function applyPoseSmoothed(dt, t) {
  if (!currentVrm?.humanoid) return;
  const el = t - poseStartTime;

  if (behavior !== 'sit' && behavior !== 'walk') {
    modelGroup.position.y = THREE.MathUtils.lerp(modelGroup.position.y, 0, 1 - Math.exp(-6 * dt));
  }

  const targets = computePoseTargets(t, el);
  TRACKED_BONES.forEach((name) => {
    const b = bone(name);
    if (!b) return;
    const target = targets[name];
    _targetEuler.set(target.x, target.y, target.z, 'XYZ');
    _targetQuat.setFromEuler(_targetEuler);
    const speed = BONE_EASE[name] || SMOOTH;
    b.quaternion.slerp(_targetQuat, 1 - Math.exp(-speed * dt));
  });
}

/* Spring-bone wind for hair/cloth (liqu ambient wind) */
function applyAmbientWind(t) {
  const manager = currentVrm?.springBoneManager;
  if (!manager?.joints) return;
  try {
    const gust = Math.sin(t * 0.8) * 0.5 + Math.sin(t * 1.9 + 1.0) * 0.3 + Math.sin(t * 3.7 + 2.0) * 0.2;
    const dirX = Math.sin(t * 1.6) * 0.6 + gust * 0.3;
    const dirZ = Math.cos(t * 1.1) * 0.4 + gust * 0.2;
    const power = 0.25 + 0.35 * (0.5 + 0.5 * gust);
    manager.joints.forEach((joint) => {
      const s = joint.settings;
      if (!s) return;
      if (s._origGravityPower === undefined) {
        s._origGravityPower = (s.gravityPower !== undefined) ? s.gravityPower : 0;
      }
      if (s.gravityDir) s.gravityDir.set(dirX, -0.5, dirZ).normalize();
      if (s.gravityPower !== undefined) s.gravityPower = s._origGravityPower + power;
    });
  } catch (e) { /* spring bone manager API mismatch — degrade silently */ }
}

/* Idle variation: occasionally strike a pose, then return to idle */
const IDLE_ALTERNATES = ['look', 'stretch', 'think'];
let idleVariationUntil = 0;
let idleVariationNext = performance.now() + 20000;
let savedBehaviorForVariation = null;

function updateIdleVariation() {
  const now = performance.now();
  if (behavior === 'idle' && now > idleVariationNext && now > idleVariationUntil) {
    savedBehaviorForVariation = 'idle';
    setBehavior(IDLE_ALTERNATES[Math.floor(Math.random() * IDLE_ALTERNATES.length)]);
    idleVariationUntil = now + 3500 + Math.random() * 2500;
    idleVariationNext = now + 22000 + Math.random() * 13000;
  } else if (savedBehaviorForVariation && now > idleVariationUntil) {
    if (IDLE_ALTERNATES.includes(behavior)) setBehavior('idle');
    savedBehaviorForVariation = null;
  }
}

/* ------------------------------------------------------------------ *
 * Expressions, blink, lip-sync
 * ------------------------------------------------------------------ */
const EXPRESSION_NAMES = ['happy', 'relaxed', 'sad', 'angry', 'surprised'];
let currentExpression = 'neutral';
let _exprCurrent = {};
let _exprTarget = {};
let nextBlinkAt = 2 + Math.random() * 4;
let blinkUntil = 0;

function applyExpression(name) {
  const presets = {
    happy: { happy: 0.8 }, sad: { sad: 0.7 }, angry: { angry: 0.75 },
    surprised: { surprised: 0.85 }, relaxed: { relaxed: 0.6 }, neutral: {},
  };
  _exprTarget = presets[name] || presets.neutral;
  currentExpression = name;
}

function updateBlinkAndExpressions(dt, t) {
  const em = currentVrm?.expressionManager;
  if (!em) return;

  // Blink
  if (t > nextBlinkAt && blinkUntil < t) {
    blinkUntil = t + 0.12;
    nextBlinkAt = t + 2.2 + Math.random() * 3.0;
  }
  em.setValue('blink', t < blinkUntil ? 1 : 0);

  // Smooth expression blend
  const rate = Math.min(1, dt * 7);
  const keys = new Set([...Object.keys(_exprCurrent), ...Object.keys(_exprTarget)]);
  for (const k of keys) {
    const target = _exprTarget[k] || 0;
    const cur = _exprCurrent[k] || 0;
    const next = cur + (target - cur) * rate;
    _exprCurrent[k] = Math.abs(next) < 0.001 ? 0 : next;
    if (em.getExpression && em.getExpression(k)) em.setValue(k, _exprCurrent[k]);
  }

  // Amplitude lip-sync (audio analyser from gateway TTS stream)
  const audible = speaking && audioLevel > 0.008;
  const normalized = audible ? Math.min(1, audioLevel * 2.8) : 0;
  const smoothing = 1 - Math.exp(-dt / (normalized > lipSmoothed ? 0.055 : 0.1));
  lipSmoothed += (normalized - lipSmoothed) * smoothing;
  lipPhase += dt * (8 + lipSmoothed * 9);
  const VISEMES = ['aa', 'ee', 'ih', 'oh', 'ou'];
  const active = Math.floor(lipPhase) % VISEMES.length;
  for (let i = 0; i < VISEMES.length; i++) {
    const shape = Math.max(0, 1 - Math.abs(i - active) * 0.72);
    const flutter = 0.74 + Math.sin(lipPhase * 5.7 + i) * 0.18;
    em.setValue(VISEMES[i], lipSmoothed * shape * flutter);
  }
}

let speaking = false;
let audioLevel = 0;
let lipSmoothed = 0;
let lipPhase = 0;

/* ------------------------------------------------------------------ *
 * Eye tracking (global cursor from main process)
 * ------------------------------------------------------------------ */
let cursorX = 0, cursorY = 0;
const _eyeTmp = new THREE.Vector3();
const lookTargetNode = () => currentVrm?.lookAt?.target;

window.hinataAPI?.onCursorPosition((p) => { cursorX = p.x; cursorY = p.y; });

function updateEyeLookAt(dt) {
  if (!currentVrm?.lookAt) return;
  const headPos = currentVrm.humanoid?.getNormalizedBoneNode('head')?.getWorldPosition(new THREE.Vector3())
    || new THREE.Vector3(0, 1.3, 0);
  _eyeTmp.set(headPos.x + cursorX * 1.4, headPos.y - cursorY * 1.0, headPos.z + 4);
  const target = lookTargetNode();
  if (target) target.position.lerp(_eyeTmp, 1 - Math.exp(-10 * dt));
}

/* ------------------------------------------------------------------ *
 * Movement integration (main process drives screen position)
 * ------------------------------------------------------------------ */
let movingNow = false;
let faceDir = 1;
let savedBehaviorBeforeWalk = null;

window.hinataAPI?.onMoveState((s) => {
  if (s.moving) {
    if (!movingNow) {
      savedBehaviorBeforeWalk = behavior === 'walk' ? 'idle' : behavior;
      setBehavior('walk');
    }
    if (s.dirX !== 0) faceDir = s.dirX;
    movingNow = true;
  } else {
    if (movingNow && behavior === 'walk') setBehavior(savedBehaviorBeforeWalk || 'idle');
    movingNow = false;
  }
});

window.hinataAPI?.onMovePos((p) => {
  stageEl.style.left = p.x + 'px';
  stageEl.style.top = p.y + 'px';
});

/* ------------------------------------------------------------------ *
 * Click-through: pass events to windows below except when hovering her
 * ------------------------------------------------------------------ */
let charHovered = false;
stageEl.addEventListener('pointerenter', () => { charHovered = true; window.hinataAPI?.setIgnoreMouse(false); });
stageEl.addEventListener('pointerleave', () => { charHovered = false; window.hinataAPI?.setIgnoreMouse(true); });

function pokeReaction() {
  applyExpression('surprised');
  setTimeout(() => applyExpression(currentExpression), 700);
  showBubble('*kyaa!* You poked me~');
}
stageEl.addEventListener('mousedown', pokeReaction);

/* ------------------------------------------------------------------ *
 * Speech bubble
 * ------------------------------------------------------------------ */
function showBubble(text) {
  const clean = (text || '').replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE00}-\u{FE0F}\u{1F900}-\u{1F9FF}]/gu, '').trim();
  bubbleEl.textContent = clean;
  bubbleEl.classList.add('show');
  clearTimeout(showBubble._t);
  showBubble._t = setTimeout(() => bubbleEl.classList.remove('show'), 4200);
}

/* ------------------------------------------------------------------ *
 * Gateway WS: brain + TTS audio stream + mood events
 * ------------------------------------------------------------------ */
let ws = null;
let audioCtx = null;
let analyser = null;
let analyserData = null;
let currentSource = null;

function connectGateway() {
  ws = new WebSocket(GATEWAY_WS);
  ws.addEventListener('open', () => console.log('[HINATA overlay] gateway connected'));
  ws.addEventListener('close', () => setTimeout(connectGateway, 3000));
  ws.addEventListener('message', (event) => {
    let msg;
    try { msg = JSON.parse(event.data); } catch { return; }
    const { type, payload } = msg;
    switch (type) {
      case 'agent_state':
        if (payload.state === 'thinking') setBehavior('think');
        if (payload.state === 'online' && behavior === 'think') setBehavior('idle');
        break;
      case 'agent_response':
        showBubble(payload.content.slice(0, 140));
        break;
      case 'avatar_mood':
        if (payload.expression) applyExpression(payload.expression);
        if (payload.mood === 'happy' || payload.mood === 'excited') {
          setBehavior('wave');
          setTimeout(() => setBehavior('idle'), 2800);
        }
        break;
      case 'speech_chunk':
        playAudioChunk(payload);
        break;
    }
  });
}

async function playAudioChunk(payload) {
  // payload: { audio: 'data:audio/mp3;base64,...', text } from gateway edge-tts
  const uri = payload?.audio;
  if (!uri) return;
  try {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === 'suspended') await audioCtx.resume();

    const fetchResponse = await fetch(uri);
    const arrayBuffer = await fetchResponse.arrayBuffer();
    const buffer = await audioCtx.decodeAudioData(arrayBuffer);

    const source = audioCtx.createBufferSource();
    source.buffer = buffer;
    const gain = audioCtx.createGain();
    gain.gain.value = 0.9;
    analyser = audioCtx.createAnalyser();
    analyser.fftSize = 256;
    analyserData = new Uint8Array(analyser.frequencyBinCount);

    source.connect(analyser);
    analyser.connect(gain);
    gain.connect(audioCtx.destination);

    source.onended = () => { speaking = false; audioLevel = 0; };
    speaking = true;
    currentSource = source;
    source.start();
  } catch (e) {
    console.warn('[HINATA overlay] audio playback failed', e);
  }
}

function sampleAudio() {
  if (!analyser || !speaking) { audioLevel = 0; return; }
  analyser.getByteFrequencyData(analyserData);
  let sum = 0;
  for (let i = 0; i < analyserData.length; i++) sum += analyserData[i];
  audioLevel = sum / analyserData.length / 255;
}

/* ------------------------------------------------------------------ *
 * Render loop
 * ------------------------------------------------------------------ */
function animate() {
  requestAnimationFrame(animate);
  const dt = Math.min(0.1, clock.getDelta());
  const t = clock.getElapsedTime();

  updateIdleVariation();
  sampleAudio();

  if (currentVrm) {
    currentVrm.update(dt);
    applyPoseSmoothed(dt, t);
    updateEyeLookAt(dt);
    updateBlinkAndExpressions(dt, t);
    applyAmbientWind(t);

    // Face travel direction while walking
    const targetYaw = behavior === 'walk' ? (faceDir < 0 ? Math.PI : 0) : 0;
    modelGroup.rotation.y += (targetYaw - modelGroup.rotation.y) * (1 - Math.exp(-8 * dt));
  }

  renderer.render(scene, camera);
}

/* ------------------------------------------------------------------ *
 * Boot
 * ------------------------------------------------------------------ */
(async () => {
  try {
    await loadModel(MODEL_URL);
  } catch (e) {
    console.error('[HINATA overlay] VRM load failed — is the gateway running?', e);
    showBubble('Gateway offline — start it with: cd gateway && npm start');
  }
  connectGateway();
  animate();
})();
