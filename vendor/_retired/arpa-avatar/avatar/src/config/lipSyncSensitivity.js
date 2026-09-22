export const defaultLipSyncSensitivity = 1;
export const minLipSyncSensitivity = 0.25;
export const maxLipSyncSensitivity = 4;
export const defaultLipSyncMouthStrength = 1;
export const minLipSyncMouthStrength = 0.1;
export const maxLipSyncMouthStrength = 1;

/** @param {unknown} value */
export function normalizeLipSyncSensitivity(value) {
  if (value == null) return defaultLipSyncSensitivity;
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return defaultLipSyncSensitivity;
  return Math.min(maxLipSyncSensitivity, Math.max(minLipSyncSensitivity, numeric));
}

/** @param {unknown} value */
export function normalizeLipSyncMouthStrength(value) {
  if (value == null) return defaultLipSyncMouthStrength;
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return defaultLipSyncMouthStrength;
  return Math.min(maxLipSyncMouthStrength, Math.max(minLipSyncMouthStrength, numeric));
}
