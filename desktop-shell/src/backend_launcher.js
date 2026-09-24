/** HINATA backend launcher — spawn/supervise the bundled backend exe.
 *  Packaged: backend exe lives in resources/backend/. Dev: assume already running.
 *  Under 125 LOC. */
const { app } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');

const BACKEND_PORT = process.env.HINATA_PORT || 8080;
const HEALTH_URL = `http://127.0.0.1:${BACKEND_PORT}/api/health`;
const START_TIMEOUT_MS = 150000; // cold GPU model load
let backendProc = null;

function backendExePath() {
  // electron-builder extraResources land under process.resourcesPath when packaged
  return path.join(process.resourcesPath || '', 'backend', 'hinata-backend.exe');
}

function isPackaged() {
  return app.isPackaged;
}

function checkHealth() {
  return new Promise((resolve) => {
    const req = http.get(HEALTH_URL, { timeout: 3000 }, (res) => {
      resolve(res.statusCode === 200);
      res.resume();
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => { req.destroy(); resolve(false); });
  });
}

async function waitForHealth(deadline) {
  while (Date.now() < deadline) {
    if (await checkHealth()) return true;
    await new Promise((r) => setTimeout(r, 3000));
  }
  return false;
}

/** Ensure the backend is running. Returns true when /api/health is 200. */
async function ensureBackendRunning() {
  if (await checkHealth()) {
    console.log('[backend] already running on port', BACKEND_PORT);
    return true;
  }
  if (!isPackaged()) {
    console.warn('[backend] dev mode — start it manually; continuing without');
    return false;
  }
  const exe = backendExePath();
  console.log('[backend] launching', exe);
  backendProc = spawn(exe, [], {
    detached: false,
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
  });
  backendProc.stdout.on('data', (d) => process.stdout.write(`[backend] ${d}`));
  backendProc.stderr.on('data', (d) => process.stderr.write(`[backend] ${d}`));
  backendProc.on('exit', (code) => {
    console.warn('[backend] exited with code', code);
    backendProc = null;
  });
  const ok = await waitForHealth(Date.now() + START_TIMEOUT_MS);
  if (!ok) console.error('[backend] failed to become healthy in time');
  return ok;
}

function stopBackend() {
  if (backendProc) {
    try { backendProc.kill(); } catch (e) { /* already gone */ }
    backendProc = null;
  }
}

module.exports = { ensureBackendRunning, stopBackend, checkHealth, BACKEND_PORT };
