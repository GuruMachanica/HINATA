/**
 * HINATA Desktop Shell — Electron main process
 * Transparent always-on-top VRM overlay, adapted from vendor/liqu (MIT-style reference).
 *
 * The brain stays in the gateway (real Hermes AIAgent + Ollama). This process owns
 * the desktop layer: overlay window, tray, global hotkey, movement engine,
 * cursor tracking, and screen-position state.
 */

const { app, BrowserWindow, Tray, Menu, ipcMain, screen, nativeImage, globalShortcut } = require('electron');
const path = require('path');
const fs = require('fs');

const BACKEND_PORT = process.env.HINATA_PORT || 8080;
const GATEWAY_URL = `http://127.0.0.1:${BACKEND_PORT}`;

let mainWindow = null;
let tray = null;
let cursorInterval = null;
let moveInterval = null;

/* ------------------------------------------------------------------ *
 * Movement engine (ported from liqu main.js)
 * Runs in the main process because the overlay is click-through —
 * the renderer cannot be trusted with global screen coordinates.
 * ------------------------------------------------------------------ */
let moveMode = process.env.HINATA_MOVE_MODE || 'wander'; // 'wander' | 'follow' | 'off'
let wanderTarget = null;
let wanderRepathAt = 0;
let charScreenX = -1, charScreenY = -1;
const CHAR_W = 440, CHAR_H = 580;

function getActiveDisplay() {
  if (mainWindow && !mainWindow.isDestroyed()) {
    try {
      const bounds = mainWindow.getBounds();
      const matched = screen.getDisplayMatching(bounds);
      if (matched) return matched;
    } catch {}
  }
  const cursorPoint = screen.getCursorScreenPoint();
  return screen.getDisplayNearestPoint(cursorPoint) || screen.getPrimaryDisplay();
}

function startMovementEngine() {
  moveInterval = setInterval(() => {
    if (!mainWindow || !mainWindow.isVisible() || moveMode === 'off') return;

    const wa = getActiveDisplay().workArea;
    if (charScreenX < 0) {
      // First run: bottom-right, above the taskbar
      charScreenX = wa.width - CHAR_W - 40;
      charScreenY = wa.height - CHAR_H - 20;
    }

    let targetX, targetY, stopDist;
    if (moveMode === 'follow') {
      const { x: cx, y: cy } = screen.getCursorScreenPoint();
      targetX = cx - wa.x - CHAR_W / 2;
      targetY = cy - wa.y - CHAR_H * 0.75;
      stopDist = 120;
    } else {
      // Wander: pick a random screen edge, repath every 6-12s
      const now = Date.now();
      if (!wanderTarget || now > wanderRepathAt) {
        const margin = 40;
        const edge = Math.floor(Math.random() * 4);
        wanderTarget =
          edge === 0 ? { x: Math.random() * Math.max(1, wa.width - CHAR_W), y: margin } :
          edge === 1 ? { x: wa.width - CHAR_W - margin, y: Math.random() * Math.max(1, wa.height - CHAR_H) } :
          edge === 2 ? { x: Math.random() * Math.max(1, wa.width - CHAR_W), y: wa.height - CHAR_H - margin } :
                       { x: margin, y: Math.random() * Math.max(1, wa.height - CHAR_H) };
        wanderRepathAt = now + 6000 + Math.random() * 6000;
      }
      targetX = wanderTarget.x;
      targetY = wanderTarget.y;
      stopDist = 24;
    }

    const dx = targetX - charScreenX;
    const dy = targetY - charScreenY;
    const dist = Math.hypot(dx, dy);

    if (dist <= stopDist) {
      mainWindow.webContents.send('move:state', { moving: false, dirX: 0 });
      if (moveMode === 'wander') wanderTarget = null;
      return;
    }

    const speed = Math.min(6, dist * 0.08);
    charScreenX += (dx / dist) * speed;
    charScreenY += (dy / dist) * speed;
    mainWindow.webContents.send('move:pos', { x: Math.round(charScreenX), y: Math.round(charScreenY) });
    mainWindow.webContents.send('move:state', { moving: true, dirX: Math.sign(dx) });
  }, 30);
}

/* ------------------------------------------------------------------ *
 * Cursor tracking (normalized to screen center, for eye gaze)
 * ------------------------------------------------------------------ */
function startCursorTracking() {
  cursorInterval = setInterval(() => {
    if (!mainWindow || !mainWindow.isVisible()) return;
    const { x: cx, y: cy } = screen.getCursorScreenPoint();
    const [wx, wy] = mainWindow.getPosition();
    const [ww, wh] = mainWindow.getSize();
    const centerX = wx + ww / 2;
    const centerY = wy + wh / 2;
    const activeDisp = getActiveDisplay();
    const { width: sw, height: sh } = activeDisp.workAreaSize;
    const nx = Math.max(-1, Math.min(1, (cx - centerX) / (sw / 2)));
    const ny = Math.max(-1, Math.min(1, (cy - centerY) / (sh / 2)));
    mainWindow.webContents.send('cursor:position', { x: nx, y: ny });
  }, 50);
}

/* ------------------------------------------------------------------ *
 * Window
 * ------------------------------------------------------------------ */
function createWindow() {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width: screenWidth, height: screenHeight, x: waX, y: waY } = primaryDisplay.workArea;

  mainWindow = new BrowserWindow({
    width: screenWidth,
    height: screenHeight,
    x: waX,
    y: waY,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    hasShadow: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.setAlwaysOnTop(true, 'screen-saver');
  mainWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  // Click-through by default; renderer re-enables input when hovering her body
  mainWindow.setIgnoreMouseEvents(true, { forward: true });

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'overlay.html'));

  mainWindow.on('closed', () => { mainWindow = null; });
}

function toggleVisibility() {
  if (!mainWindow) return;
  mainWindow.isVisible() ? mainWindow.hide() : mainWindow.show();
}

function createTray() {
  // Generate a simple tray icon (16x16 sun emoji rendered as image is overkill;
  // use an empty image with a tooltip + menu on all platforms)
  tray = new Tray(nativeImage.createEmpty());
  tray.setToolTip('HINATA — Desktop Companion');
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: 'Show / Hide  (Alt+Shift+H)', click: toggleVisibility },
    {
      label: 'Movement: Wander',
      type: 'radio',
      checked: moveMode === 'wander',
      click: () => setMoveMode('wander'),
    },
    {
      label: 'Movement: Follow cursor',
      type: 'radio',
      checked: moveMode === 'follow',
      click: () => setMoveMode('follow'),
    },
    {
      label: 'Movement: Off',
      type: 'radio',
      checked: moveMode === 'off',
      click: () => setMoveMode('off'),
    },
    { type: 'separator' },
    {
      label: 'Open full cortex (React UI)',
      click: () => require('electron').shell.openExternal(GATEWAY_URL),
    },
    { type: 'separator' },
    { label: 'Quit HINATA', click: () => app.quit() },
  ]));
}

function setMoveMode(mode) {
  moveMode = ['wander', 'follow'].includes(mode) ? mode : 'off';
  wanderTarget = null;
  if (mainWindow && moveMode === 'off') {
    mainWindow.webContents.send('move:state', { moving: false, dirX: 0 });
  }
}

/* ------------------------------------------------------------------ *
 * IPC surface
 * ------------------------------------------------------------------ */
ipcMain.handle('window:set-ignore-mouse', (_evt, ignore) => {
  if (mainWindow) mainWindow.setIgnoreMouseEvents(ignore, { forward: true });
});

ipcMain.handle('move:set-mode', (_evt, mode) => {
  setMoveMode(mode);
  return moveMode;
});

ipcMain.handle('app:quit', () => app.quit());

/* ------------------------------------------------------------------ *
 * Boot
 * ------------------------------------------------------------------ */
app.whenReady().then(() => {
  createWindow();
  createTray();
  startCursorTracking();
  startMovementEngine();

  globalShortcut.register('Alt+Shift+H', toggleVisibility);
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
  clearInterval(cursorInterval);
  clearInterval(moveInterval);
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
