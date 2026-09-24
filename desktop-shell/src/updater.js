/** Auto-update — electron-updater against GitHub Releases.
 *  Checks on boot and every 6h; installs silently on quit. Under 125 LOC. */
const { autoUpdater } = require('electron-updater');
const { dialog } = require('electron');

const CHECK_INTERVAL_MS = 6 * 60 * 60 * 1000;
let timer = null;
let win = null; // renderer webContents for status events (optional)

function notifyRenderer(channel, payload) {
  try { if (win) win.send('update:' + channel, payload); } catch { /* window gone */ }
}

function bindEvents() {
  autoUpdater.on('checking-for-update', () => notifyRenderer('checking', {}));
  autoUpdater.on('update-available', (info) => notifyRenderer('available', { version: info.version }));
  autoUpdater.on('update-not-available', () => notifyRenderer('none', {}));
  autoUpdater.on('download-progress', (p) =>
    notifyRenderer('progress', { percent: Math.round(p.percent) }));
  autoUpdater.on('update-downloaded', (info) => {
    notifyRenderer('ready', { version: info.version });
    // Quiet UX: install on next quit. Ask only once per download.
    dialog.showMessageBox({
      type: 'info',
      title: 'HINATA update ready',
      message: `Version ${info.version} is ready and will install the next time HINATA quits.`,
      buttons: ['Restart now', 'Later'],
      defaultId: 1,
    }).then(({ response }) => {
      if (response === 0) autoUpdater.quitAndInstall();
    });
  });
  autoUpdater.on('error', (err) => {
    // Non-fatal: offline machines, private repos, unsigned blocks, etc.
    console.warn('[updater] check failed (non-fatal):', err.message);
  });
}

function attachWindow(webContents) {
  win = webContents;
}

/** Start checking. Safe to call on every boot; no-ops when already active. */
function start() {
  if (timer) return;
  bindEvents();
  try {
    autoUpdater.checkForUpdatesAndNotify().catch((e) =>
      console.warn('[updater] initial check skipped:', e.message));
  } catch (e) {
    console.warn('[updater] unavailable in this build:', e.message);
    return;
  }
  timer = setInterval(() => {
    autoUpdater.checkForUpdatesAndNotify().catch(() => { /* offline */ });
  }, CHECK_INTERVAL_MS);
}

function stop() {
  if (timer) clearInterval(timer);
  timer = null;
}

module.exports = { start, stop, attachWindow };
