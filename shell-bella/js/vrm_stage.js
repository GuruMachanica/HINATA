/**
 * HINATA VRM Stage (merged product)
 * Vanilla-JS port of ARPA's VRM pipeline: three-vrm loading, VRMA animation
 * with cross-fade + sequences, blink, amplitude lip-sync, mood expressions.
 * Adapted from vendor/arpa-avatar (MIT).
 */

import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';
import { VRMAnimationLoaderPlugin, createVRMAnimationClip } from '@pixiv/three-vrm-animation';

const VISEMES = ['aa', 'ee', 'ih', 'oh', 'ou'];
const FADE = 0.65;

export class VRMStage {
  constructor(container) {
    this.container = container;
    this.scene = new THREE.Scene();

    this.width = container.clientWidth || 440;
    this.height = container.clientHeight || 480;
    this.camera = new THREE.PerspectiveCamera(35, this.width / this.height, 0.1, 100);
    this.camTarget = new THREE.Vector3(0, 1.35, 1.9);
    this.lookTarget = new THREE.Vector3(0, 1.30, 0);
    this.currentLook = this.lookTarget.clone();
    this.camera.position.copy(this.camTarget);

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    this.renderer.setSize(this.width, this.height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(this.renderer.domElement);

    this._setupLighting();
    this._bindControls();

    this.vrm = null;
    this.mixer = null;
    this.currentAction = null;
    this.animCache = new Map();
    this.clock = new THREE.Clock();

    // Blink state
    this._blinkNext = 2 + Math.random() * 4;
    this._blinkProgress = 0;

    // Lip-sync state
    this._lipSmoothed = 0;
    this._lipPhase = 0;
    this.speaking = false;
    this.audioLevel = 0;

    // Mood expression targets
    this._exprCurrent = {};
    this._exprTarget = {};

    this.vrmLoader = new GLTFLoader();
    this.vrmLoader.register((parser) => new VRMLoaderPlugin(parser));
    this.vrmaLoader = new GLTFLoader();
    this.vrmaLoader.register((parser) => new VRMAnimationLoaderPlugin(parser));

    window.addEventListener('resize', () => this.onResize());
  }

  _setupLighting() {
    this.scene.add(new THREE.AmbientLight(0xf5ebe4, 0.9));
    const key = new THREE.DirectionalLight(0xfffaed, 1.4); key.position.set(0.6, 2.2, 1.8); this.scene.add(key);
    const fill = new THREE.DirectionalLight(0xdbe8ff, 0.7); fill.position.set(-0.9, 1.8, 1.2); this.scene.add(fill);
    const rim = new THREE.DirectionalLight(0x00e5ff, 0.9); rim.position.set(-0.8, 2.1, -1.4); this.scene.add(rim);
  }

  _bindControls() {
    let dragging = false, lastX = 0, angle = 0;
    this.renderer.domElement.addEventListener('pointerdown', (e) => { dragging = true; lastX = e.clientX; });
    window.addEventListener('pointerup', () => { dragging = false; });
    window.addEventListener('pointermove', (e) => {
      if (!dragging) return;
      angle += (e.clientX - lastX) * 0.008; lastX = e.clientX;
      const radius = Math.hypot(this.camTarget.x, this.camTarget.z);
      this.camTarget.x = Math.sin(angle) * radius; this.camTarget.z = Math.cos(angle) * radius;
    });
    // Eye tracking follows the cursor
    window.addEventListener('mousemove', (e) => {
      if (!this.vrm) return;
      const nx = (e.clientX / window.innerWidth) * 2 - 1;
      const ny = (e.clientY / window.innerHeight) * 2 - 1;
      if (this.vrm.lookAt) {
        const yaw = nx * 0.35, pitch = ny * 0.25;
        const s = Math.sin(yaw), c = Math.cos(yaw);
        const sp = Math.sin(pitch), cp = Math.cos(pitch);
        this.vrm.lookAt.target && this.vrm.lookAt.target.position.set(-s * 5, 1.35 - sp * 2, -c * 5);
      }
    });
  }

  async loadModel(url) {
    const gltf = await this.vrmLoader.loadAsync(url);
    const vrm = gltf.userData.vrm;
    VRMUtils.combineSkeletons(vrm.scene);
    VRMUtils.rotateVRM0(vrm);
    this.scene.add(vrm.scene);
    this.vrm = vrm;
    this.mixer = new THREE.AnimationMixer(vrm.scene);
    // Look-at target node in front of the avatar
    this._lookTarget = new THREE.Object3D();
    this._lookTarget.position.set(0, 1.35, 5);
    vrm.scene.add(this._lookTarget);
    if (vrm.lookAt) vrm.lookAt.target = this._lookTarget;
    return vrm;
  }

  async playAnimation(url, playback = 'once', onComplete = null) {
    if (!this.vrm || !this.mixer) return;
    try {
      let animation = this.animCache.get(url);
      if (!animation) {
        const gltf = await this.vrmaLoader.loadAsync(url);
        animation = gltf.userData.vrmAnimations?.[0];
        if (!animation) throw new Error(`No VRMA data in ${url}`);
        this.animCache.set(url, animation);
      }
      const clip = createVRMAnimationClip(animation, this.vrm);
      const action = this.mixer.clipAction(clip);
      action.reset();
      if (playback === 'once') {
        action.setLoop(THREE.LoopOnce, 1);
        action.clampWhenFinished = true;
        if (onComplete) {
          const onFinished = ({ action: a }) => {
            if (a !== action) return;
            this.mixer.removeEventListener('finished', onFinished);
            onComplete();
          };
          this.mixer.addEventListener('finished', onFinished);
        }
      } else {
        action.setLoop(THREE.LoopRepeat, Infinity);
      }
      this.currentAction?.fadeOut(FADE);
      action.setEffectiveWeight(1).fadeIn(FADE).play();
      this.currentAction = action;
    } catch (err) {
      console.warn('[VRMStage] animation load failed', err);
      onComplete?.();
    }
  }

  returnToRest() {
    this.currentAction?.fadeOut(FADE);
    this.currentAction = null;
  }

  /** Bella mood -> VRM expression weights. expression: happy|sad|angry|relaxed|neutral|surprised */
  setMood(mood, expression) {
    const presets = {
      happy:     { happy: 0.8, neutral: 0.1 },
      sad:       { sad: 0.7, neutral: 0.2 },
      angry:     { angry: 0.75, neutral: 0.1 },
      surprised: { surprised: 0.85, neutral: 0.1 },
      relaxed:   { relaxed: 0.6, neutral: 0.3 },
      neutral:   { neutral: 0.4 },
    };
    this._exprTarget = presets[expression] || presets[mood] || presets.neutral;
  }

  setSpeaking(speaking) { this.speaking = speaking; if (!speaking) this.audioLevel = 0; }
  setAudioLevel(level) { this.audioLevel = level; }

  _updateBlink(dt) {
    const em = this.vrm?.expressionManager;
    if (!em) return;
    if (this._blinkProgress > 0) {
      this._blinkProgress += dt / 0.24;
      if (this._blinkProgress >= 1) {
        this._blinkProgress = 0;
        this._blinkNext = this._blinkProgress + 2 + Math.random() * 4;
        em.setValue('blink', 0);
      } else {
        em.setValue('blink', Math.sin(this._blinkProgress * Math.PI));
      }
    } else {
      this._blinkNext -= dt;
      if (this._blinkNext <= 0) this._blinkProgress = 0.0001;
    }
  }

  _updateLipSync(dt) {
    const em = this.vrm?.expressionManager;
    if (!em) return;
    const audible = this.speaking && this.audioLevel > 0.008;
    const normalized = audible ? Math.min(1, this.audioLevel * 2.8) : 0;
    const smoothing = 1 - Math.exp(-dt / (normalized > this._lipSmoothed ? 0.055 : 0.1));
    this._lipSmoothed += (normalized - this._lipSmoothed) * smoothing;
    this._lipPhase += dt * (8 + this._lipSmoothed * 9);
    const active = Math.floor(this._lipPhase) % VISEMES.length;
    for (let i = 0; i < VISEMES.length; i++) {
      const shape = Math.max(0, 1 - Math.abs(i - active) * 0.72);
      const flutter = 0.74 + Math.sin(this._lipPhase * 5.7 + i) * 0.18;
      em.setValue(VISEMES[i], this._lipSmoothed * shape * flutter);
    }
  }

  _updateExpressions(dt) {
    const em = this.vrm?.expressionManager;
    if (!em) return;
    const rate = Math.min(1, dt * 7);
    const keys = new Set([...Object.keys(this._exprCurrent), ...Object.keys(this._exprTarget)]);
    for (const k of keys) {
      const target = this._exprTarget[k] || 0;
      const cur = this._exprCurrent[k] || 0;
      const next = cur + (target - cur) * rate;
      this._exprCurrent[k] = Math.abs(next) < 0.001 ? 0 : next;
      if (em.getExpression && em.getExpression(k)) em.setValue(k, this._exprCurrent[k]);
    }
  }

  update() {
    const dt = Math.min(0.1, this.clock.getDelta());
    this.mixer?.update(dt);
    this._updateBlink(dt);
    this._updateLipSync(dt);
    this._updateExpressions(dt);
    this.vrm?.update(dt);
    // Subtle idle breathing on the whole model
    if (this.vrm) this.vrm.scene.position.y = Math.sin(this.clock.elapsedTime * 1.4) * 0.004;
    this.camera.position.lerp(this.camTarget, 0.08);
    this.currentLook.lerp(this.lookTarget, 0.08);
    this.camera.lookAt(this.currentLook);
    this.renderer.render(this.scene, this.camera);
  }

  onResize() {
    this.width = this.container.clientWidth;
    this.height = this.container.clientHeight;
    this.camera.aspect = this.width / this.height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(this.width, this.height);
  }
}
