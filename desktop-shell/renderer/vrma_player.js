/**
 * VRMA animation player — plays the bundled .vrma motion files.
 *
 * The vendor three-vrm bundle (v3.4.2 core) does not include the VRM animation
 * module, so clips are built directly from the .vrma JSON (humanoid rotation
 * tracks) and slerped onto the normalized-bone rig the pose engine uses.
 */
import * as THREE from 'three';

// Dev: renderer is served over the gateway which exposes /models; packaged:
// the VRM assets are an extraResource copied next to the app root.
const VRMA_BASE = (window.HINATA_MODE === 'packaged')
  ? '../models/vrm/animations/'
  : 'http://127.0.0.1:8080/models/vrm/animations/';
const HUMANOID_MAP = {
  hips: 'hips', spine: 'spine', chest: 'chest', head: 'head',
  leftUpperArm: 'leftUpperArm', rightUpperArm: 'rightUpperArm',
  leftLowerArm: 'leftLowerArm', rightLowerArm: 'rightLowerArm',
  leftHand: 'leftHand', rightHand: 'rightHand',
  leftUpperLeg: 'leftUpperLeg', rightUpperLeg: 'rightUpperLeg',
  leftLowerLeg: 'leftLowerLeg', rightLowerLeg: 'rightLowerLeg',
};

const state = { clips: new Map(), active: null, t0: 0, duration: 0, snapshot: null };

async function loadVrma(name) {
  const res = await fetch(`${VRMA_BASE}${name}.vrma`);
  if (!res.ok) throw new Error(`vrma ${name}: HTTP ${res.status}`);
  return res.json();
}

/** Parse a .vrma JSON into per-bone quaternion keyframe tracks. */
function buildTracks(json) {
  const tracks = [];
  const anim = json.humanoid ?? json.animations?.[0]?.humanoid;
  if (!anim) return tracks;
  const times = anim.humanoidRotationTime ?? [];
  for (const [ourName, spec] of Object.entries(HUMANOID_MAP)) {
    const node = anim[spec] ?? anim.nodes?.[spec];
    if (!node?.rotation) continue;
    const q = node.rotation; // flat array [x,y,z,w] * frames
    const frames = q.length / 4;
    const values = new Float32Array(q);
    const track = new THREE.QuaternionKeyframeTrack(
      `.bones.${ourName}`, times.slice(0, frames), values);
    tracks.push(track);
  }
  return tracks;
}

/** Preload every available VRMA clip. Non-fatal on individual failures. */
export async function preloadAll(names) {
  for (const name of names) {
    try {
      const json = await loadVrma(name);
      const tracks = buildTracks(json);
      if (tracks.length) {
        state.clips.set(name, { tracks, duration: Math.max(...tracks.map(
          (t) => t.times[t.times.length - 1] || 0)) });
      }
    } catch (e) {
      console.warn(`[vrma] skipped ${name}:`, e.message);
    }
  }
  return state.clips.size;
}

export function available() { return [...state.clips.keys()]; }

/** Start a clip; blends from the current procedural pose naturally. */
export function play(name, currentVrm) {
  const clip = state.clips.get(name);
  if (!clip || !currentVrm) return false;
  state.snapshot = capturePose(currentVrm);
  state.active = clip;
  state.t0 = performance.now() / 1000;
  state.duration = clip.duration || 1;
  return true;
}

export function stop() { state.active = null; }
export function playing() { return state.active !== null; }

function capturePose(vrm) {
  const snap = {};
  for (const name of Object.keys(HUMANOID_MAP)) {
    const node = vrm.humanoid?.getNormalizedBoneNode(name);
    if (node) snap[name] = node.quaternion.clone();
  }
  return snap;
}

/** Called once per frame; returns true while a clip is driving the rig. */
export function tick(currentVrm) {
  if (!state.active || !currentVrm) return false;
  const t = performance.now() / 1000 - state.t0;
  if (t >= state.duration) { state.active = null; return false; }
  // Sample each track at time t and slerp onto the bones (blend 60% clip)
  for (const track of state.active.tracks) {
    const boneName = track.name.replace('.bones.', '');
    const node = currentVrm.humanoid?.getNormalizedBoneNode(boneName);
    if (!node) continue;
    const q = sampleTrack(track, t);
    if (q) node.quaternion.slerp(q, 0.6);
  }
  return true;
}

function sampleTrack(track, t) {
  const times = track.times;
  let i = 0;
  while (i < times.length - 1 && times[i + 1] < t) i++;
  const q = new THREE.Quaternion();
  if (i >= times.length - 1) {
    q.fromArray(track.values, i * 4);
  } else {
    const a = new THREE.Quaternion().fromArray(track.values, i * 4);
    const b = new THREE.Quaternion().fromArray(track.values, (i + 1) * 4);
    const alpha = (t - times[i]) / Math.max(1e-6, times[i + 1] - times[i]);
    q.slerpQuaternions(a, b, alpha);
  }
  return q;
}
