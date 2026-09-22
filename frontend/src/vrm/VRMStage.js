/**
 * HINATA VRMStage (React-compatible singleton class)
 * Merges: ARPA VRM loading + liqu procedural pose engine + mood expressions
 * + amplitude lip-sync over backend TTS audio.
 */

import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';

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

const BONE_EASE = {
  hips: 4, spine: 5, chest: 6, head: 8,
  leftUpperArm: 6, rightUpperArm: 6,
  leftLowerArm: 9, rightLowerArm: 9,
  leftHand: 12, rightHand: 12,
  leftUpperLeg: 5, rightUpperLeg: 5,
  leftLowerLeg: 8, rightLowerLeg: 8,
};

const POSES = {
  idle: { fn: () => {} },
  look: { fn: (t, el, T, add) => add('head', Math.sin(t * 0.33) * 0.1, Math.sin(t * 0.5) * 0.4, 0) },
  wave: {
    fn: (t, el, T, add, setAbs, armLift) => {
      const raise = Math.min(el / 0.4, 1);
      armLift('right', 0.55 + 0.85 * raise, 0.1 * raise, 1.0 * raise);
      add('rightLowerArm', 0, 0, Math.sin(el * 9) * 0.4);
      add('head', 0, -0.15 * raise, 0);
    },
  },
  think: {
    fn: (t, el, T, add, setAbs, armLift) => {
      armLift('right', 0.9, 0.25, 1.9);
      add('head', 0.12, -0.1, -0.08);
      add('spine', 0.03, 0, 0.02);
    },
  },
  stretch: {
    fn: (t, el, T, add, setAbs, armLift) => {
      const s = Math.min(el / 0.8, 1);
      armLift('left', 1.15 * s, 0.1);
      armLift('right', 1.15 * s, 0.1);
      add('spine', -0.1 * s, 0, 0);
      add('head', -0.12 * s, 0, 0);
    },
  },
  walk: {
    fn: (t, el, T, add, setAbs, armLift) => {
      const stride = el * 7.0;
      const swing = Math.sin(stride) * 0.55;
      setAbs('leftUpperLeg', swing * 0.7, 0, 0.05);
      setAbs('rightUpperLeg', -swing * 0.7, 0, -0.05);
      setAbs('leftLowerLeg', Math.max(0, -swing) * 0.9, 0, 0);
      setAbs('rightLowerLeg', Math.max(0, swing) * 0.9, 0, 0);
      armLift('left', 0.18, -swing * 0.4, 0.25);
      armLift('right', 0.18, swing * 0.4, 0.25);
      add('spine', 0.06, 0, swing * 0.06);
      T.group.position.y = Math.abs(Math.sin(stride)) * 0.03;
    },
  },
  sit: {
    fn: (t, el, T, add, setAbs, armLift) => {
      setAbs('leftUpperLeg', -1.4, 0, 0.1);
      setAbs('rightUpperLeg', -1.4, 0, -0.1);
      setAbs('leftLowerLeg', 1.5, 0, 0);
      setAbs('rightLowerLeg', 1.5, 0, 0);
      add('hips', 0.05, 0, 0);
      armLift('left', 0.12, 0.2, 0.3);
      armLift('right', 0.12, 0.2, 0.3);
      T.group.position.y = -0.15;
    },
  },
};

const IDLE_ALTERNATES = ['look', 'stretch', 'think'];

export class VRMStage {
  constructor(container) {
    this.container = container;
    this.behavior = 'idle';
    this._poseStart = 0;

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(container.clientWidth || 440, container.clientHeight || 520);
    this.renderer.setClearColor(0x000000, 0);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    container.appendChild(this.renderer.domElement);

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(30, (container.clientWidth || 440) / (container.clientHeight || 520), 0.05, 50);
    this.camera.position.set(0, 0.82, 3.15);
    this.camera.lookAt(0, 0.72, 0);

    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x444455, 2.0));
    const key = new THREE.DirectionalLight(0xfffaed, 1.5); key.position.set(1, 2, 2.5); this.scene.add(key);
    const rim = new THREE.DirectionalLight(0x00e5ff, 0.6); rim.position.set(-1, 1.8, -1.6); this.scene.add(rim);

    // Floor standing shadow disc so avatar is grounded, not floating
    const shadowCanvas = document.createElement('canvas');
    shadowCanvas.width = 128; shadowCanvas.height = 128;
    const sCtx = shadowCanvas.getContext('2d');
    const grad = sCtx.createRadialGradient(64, 64, 0, 64, 64, 60);
    grad.addColorStop(0, 'rgba(0, 229, 255, 0.35)');
    grad.addColorStop(0.3, 'rgba(0, 0, 0, 0.55)');
    grad.addColorStop(0.7, 'rgba(0, 0, 0, 0.2)');
    grad.addColorStop(1, 'rgba(0, 0, 0, 0)');
    sCtx.fillStyle = grad;
    sCtx.beginPath(); sCtx.arc(64, 64, 64, 0, Math.PI * 2); sCtx.fill();
    const shadowTexture = new THREE.CanvasTexture(shadowCanvas);
    const shadowGeo = new THREE.PlaneGeometry(1.2, 1.2);
    const shadowMat = new THREE.MeshBasicMaterial({
      map: shadowTexture, transparent: true, opacity: 0.85, depthWrite: false,
    });
    const shadowMesh = new THREE.Mesh(shadowGeo, shadowMat);
    shadowMesh.rotation.x = -Math.PI / 2;
    shadowMesh.position.y = 0.002;
    this.scene.add(shadowMesh);

    this.group = new THREE.Group();
    this.scene.add(this.group);

    this.vrm = null;
    this.clock = new THREE.Clock();
    this._euler = new THREE.Euler();
    this._quat = new THREE.Quaternion();

    // blink / expressions / lipsync state
    this._blinkNext = 2 + Math.random() * 3;
    this._blinkUntil = 0;
    this._exprCurrent = {};
    this._exprTarget = {};
    this.speaking = false;
    this._audioLevel = 0;
    this._lipSmoothed = 0;
    this._lipPhase = 0;

    // audio
    this._audioEl = new Audio();
    this._audioEl.crossOrigin = 'anonymous';
    this._ctx = null;
    this._analyser = null;
    this._freq = null;
    this._initAudio();

    // cursor gaze
    window.addEventListener('mousemove', (e) => {
      this._gazeX = (e.clientX / window.innerWidth) * 2 - 1;
      this._gazeY = (e.clientY / window.innerHeight) * 2 - 1;
    });

    // idle variation timer
    this._idleNext = performance.now() + 18000;
    this._idleUntil = 0;
    this._idleSaved = null;
  }

  _initAudio() {
    const unlock = () => {
      if (this._ctx && this._ctx.state === 'suspended') {
        this._ctx.resume().catch(() => {});
      }
    };
    window.addEventListener('click', unlock, { once: true });
    window.addEventListener('keydown', unlock, { once: true });
    try {
      this._ctx = new (window.AudioContext || window.webkitAudioContext)();
      this._analyser = this._ctx.createAnalyser();
      this._analyser.fftSize = 256;
      this._freq = new Uint8Array(this._analyser.frequencyBinCount);
      const src = this._ctx.createMediaElementSource(this._audioEl);
      src.connect(this._analyser);
      this._analyser.connect(this._ctx.destination);
    } catch (e) {
      console.warn('[VRMStage] webaudio unavailable', e);
    }
  }

  async loadModel(url) {
    const loader = new GLTFLoader();
    loader.register((parser) => new VRMLoaderPlugin(parser));
    const gltf = await loader.loadAsync(url);
    const vrm = gltf.userData.vrm;
    VRMUtils.combineSkeletons(vrm.scene);
    VRMUtils.rotateVRM0(vrm);
    this.group.add(vrm.scene);
    this.vrm = vrm;

    // Attach gaze target
    const target = new THREE.Object3D();
    target.position.set(0, 1.35, 5);
    this.group.add(target);
    this._gazeTarget = target;
    if (vrm.lookAt) vrm.lookAt.target = target;
  }

  setBehavior(b) {
    if (!POSES[b]) return;
    this.behavior = b;
    this._poseStart = this.clock.getElapsedTime();
  }

  setMood(mood, expression) {
    const presets = {
      happy: { happy: 0.8 }, sad: { sad: 0.7 }, angry: { angry: 0.75 },
      surprised: { surprised: 0.85 }, relaxed: { relaxed: 0.6 }, neutral: {},
    };
    this._exprTarget = presets[expression] || presets[mood] || presets.neutral;
  }

  playAudio(dataUri) {
    if (!dataUri) return;
    if (this._ctx && this._ctx.state === 'suspended') {
      this._ctx.resume().catch(() => {});
    }
    this._audioEl.src = dataUri;
    this._audioEl.onplaying = () => { this.speaking = true; };
    this._audioEl.onended = () => { this.speaking = false; this._audioLevel = 0; };
    this._audioEl.play().catch((err) => {
      console.warn('[VRMStage] audio play failed', err);
      this.speaking = false;
    });
  }

  stopAudio() {
    this._audioEl.pause();
    this._audioEl.currentTime = 0;
    this.speaking = false;
    this._audioLevel = 0;
  }

  _add(targets, name, dx, dy, dz) {
    if (!targets[name]) return;
    targets[name].x += dx; targets[name].y += dy; targets[name].z += dz;
  }
  _setAbs(targets, name, x, y, z) {
    if (!targets[name]) return;
    targets[name].x = x; targets[name].y = y; targets[name].z = z;
  }
  _armLift(targets, side, lift, fwd = 0, bend = 0) {
    const upper = side === 'left' ? 'leftUpperArm' : 'rightUpperArm';
    const lower = side === 'left' ? 'leftLowerArm' : 'rightLowerArm';
    this._setAbs(targets, upper, fwd, 0, armZ(side, lift));
    this._setAbs(targets, lower, 0, 0, side === 'left' ? bend : -bend);
  }

  _computeTargets(t, el) {
    const targets = {};
    TRACKED_BONES.forEach((n) => (targets[n] = { ...BASE_POSE[n] }));

    const breathe = (Math.sin(t * 1.1) + Math.sin(t * 1.7 + 0.6) * 0.4) * 0.022;
    const sway = (Math.sin(t * 0.45) + Math.sin(t * 0.8 + 1.1) * 0.35) * 0.06;
    const weight = Math.sin(t * 0.16) * 0.1;
    const weightFast = Math.sin(t * 0.33 + 0.7) * 0.03;
    const drift = Math.sin(t * 0.7 + 1.3) * 0.03;
    const driftSlow = Math.sin(t * 0.27 + 2.4) * 0.04;
    const microL = (Math.sin(t * 1.9 + 0.5) + Math.sin(t * 3.1 + 1.7) * 0.4) * 0.018;
    const microR = (Math.sin(t * 1.7 + 2.1) + Math.sin(t * 2.9 + 0.3) * 0.4) * 0.018;

    const add = (n, dx, dy, dz) => this._add(targets, n, dx, dy, dz);
    const setAbs = (n, x, y, z) => this._setAbs(targets, n, x, y, z);
    const armLift = (side, lift, fwd, bend) => this._armLift(targets, side, lift, fwd, bend);

    add('chest', breathe * 0.7, sway * 0.15, breathe + weightFast * 0.3);
    add('spine', breathe * 0.35, sway * 0.45, weight * 0.55);
    add('hips', weightFast * 0.4, sway * 0.1, weight);
    add('leftUpperArm', microL + driftSlow * 0.3, drift * 0.5, sway * 0.12 + drift + breathe * 0.5);
    add('rightUpperArm', microR - driftSlow * 0.3, -drift * 0.5, -sway * 0.12 - drift - breathe * 0.5);
    add('leftLowerArm', microL * 1.5, microL * 2.5 + driftSlow, drift * 0.4);
    add('rightLowerArm', microR * 1.5, -microR * 2.5 - driftSlow, -drift * 0.4);

    const eyeYaw = (this._gazeX || 0) * 0.4;
    const eyePitch = -(this._gazeY || 0) * 0.25;
    add('head', breathe * 0.6 + eyePitch + driftSlow * 0.3, sway * 0.7 + eyeYaw - weight * 0.35, weight * 0.45);

    POSES[this.behavior]?.fn(t, el, this, add, setAbs, armLift);
    return targets;
  }

  _applyPose(dt, t) {
    if (!this.vrm?.humanoid) return;
    const el = t - this._poseStart;
    if (this.behavior !== 'sit' && this.behavior !== 'walk') {
      this.group.position.y = THREE.MathUtils.lerp(this.group.position.y, 0, 1 - Math.exp(-6 * dt));
    }
    const targets = this._computeTargets(t, el);
    TRACKED_BONES.forEach((name) => {
      const b = this.vrm.humanoid.getNormalizedBoneNode(name);
      if (!b) return;
      const tgt = targets[name];
      this._euler.set(tgt.x, tgt.y, tgt.z, 'XYZ');
      this._quat.setFromEuler(this._euler);
      const speed = BONE_EASE[name] || 9;
      b.quaternion.slerp(this._quat, 1 - Math.exp(-speed * dt));
    });
  }

  _updateFace(dt, t) {
    const em = this.vrm?.expressionManager;
    if (!em) return;

    if (t > this._blinkNext && this._blinkUntil < t) {
      this._blinkUntil = t + 0.12;
      this._blinkNext = t + 2.2 + Math.random() * 3;
    }
    em.setValue('blink', t < this._blinkUntil ? 1 : 0);

    const rate = Math.min(1, dt * 7);
    const keys = new Set([...Object.keys(this._exprCurrent), ...Object.keys(this._exprTarget)]);
    for (const k of keys) {
      const tgt = this._exprTarget[k] || 0;
      const cur = this._exprCurrent[k] || 0;
      const next = cur + (tgt - cur) * rate;
      this._exprCurrent[k] = Math.abs(next) < 0.001 ? 0 : next;
      if (em.getExpression?.(k)) em.setValue(k, this._exprCurrent[k]);
    }

    // Amplitude lip-sync
    if (this._analyser && this.speaking) {
      this._analyser.getByteFrequencyData(this._freq);
      let sum = 0;
      for (let i = 0; i < this._freq.length; i++) sum += this._freq[i];
      this._audioLevel = sum / this._freq.length / 255;
    } else {
      this._audioLevel = 0;
    }
    const normalized = this.speaking && this._audioLevel > 0.008 ? Math.min(1, this._audioLevel * 2.8) : 0;
    const smoothing = 1 - Math.exp(-dt / (normalized > this._lipSmoothed ? 0.055 : 0.1));
    this._lipSmoothed += (normalized - this._lipSmoothed) * smoothing;
    this._lipPhase += dt * (8 + this._lipSmoothed * 9);
    const VISEMES = ['aa', 'ee', 'ih', 'oh', 'ou'];
    const active = Math.floor(this._lipPhase) % VISEMES.length;
    for (let i = 0; i < VISEMES.length; i++) {
      const shape = Math.max(0, 1 - Math.abs(i - active) * 0.72);
      const flutter = 0.74 + Math.sin(this._lipPhase * 5.7 + i) * 0.18;
      em.setValue(VISEMES[i], this._lipSmoothed * shape * flutter);
    }
  }

  _updateIdleVariation() {
    const now = performance.now();
    if (this.behavior === 'idle' && now > this._idleNext && now > this._idleUntil) {
      this._idleSaved = 'idle';
      this.setBehavior(IDLE_ALTERNATES[Math.floor(Math.random() * IDLE_ALTERNATES.length)]);
      this._idleUntil = now + 3500 + Math.random() * 2500;
      this._idleNext = now + 22000 + Math.random() * 13000;
    } else if (this._idleSaved && now > this._idleUntil) {
      if (IDLE_ALTERNATES.includes(this.behavior)) this.setBehavior('idle');
      this._idleSaved = null;
    }
  }

  update() {
    const dt = Math.min(0.1, this.clock.getDelta());
    const t = this.clock.getElapsedTime();
    this._updateIdleVariation();
    if (this.vrm) {
      this.vrm.update(dt);
      this._applyPose(dt, t);
      this._updateFace(dt, t);
    }
    this.camera.lookAt(0, 0.72, 0);
    this.renderer.render(this.scene, this.camera);
  }
}
