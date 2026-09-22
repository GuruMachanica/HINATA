import assert from 'node:assert/strict';
import test from 'node:test';
import {
  defaultLipSyncMouthStrength,
  defaultLipSyncSensitivity,
  normalizeLipSyncMouthStrength,
  normalizeLipSyncSensitivity,
} from './lipSyncSensitivity.js';

test('normalizeLipSyncSensitivity keeps supported values', () => {
  assert.equal(normalizeLipSyncSensitivity(0.25), 0.25);
  assert.equal(normalizeLipSyncSensitivity(1), 1);
  assert.equal(normalizeLipSyncSensitivity('2.5'), 2.5);
  assert.equal(normalizeLipSyncSensitivity(4), 4);
});

test('normalizeLipSyncMouthStrength clamps to the VRM expression range', () => {
  assert.equal(normalizeLipSyncMouthStrength(0), 0.1);
  assert.equal(normalizeLipSyncMouthStrength(0.65), 0.65);
  assert.equal(normalizeLipSyncMouthStrength(2), 1);
  assert.equal(normalizeLipSyncMouthStrength(null), defaultLipSyncMouthStrength);
  assert.equal(normalizeLipSyncMouthStrength(undefined), defaultLipSyncMouthStrength);
});

test('normalizeLipSyncSensitivity clamps or defaults invalid values', () => {
  assert.equal(normalizeLipSyncSensitivity(0), 0.25);
  assert.equal(normalizeLipSyncSensitivity(10), 4);
  assert.equal(normalizeLipSyncSensitivity('nope'), defaultLipSyncSensitivity);
  assert.equal(normalizeLipSyncSensitivity(null), defaultLipSyncSensitivity);
  assert.equal(normalizeLipSyncSensitivity(undefined), defaultLipSyncSensitivity);
});
