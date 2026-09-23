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
const CHAR_W = 300, CHAR_H = 395; // compact desktop presence

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
    // Taskbar-lane: she walks only along the bottom edge of the work area
    // (the taskbar strip is her ground), never roams the full screen.
    const laneY = wa.height - CHAR_H; // feet planted on the taskbar top edge

    if (charScreenX < 0) {
      // First run: bottom-right on the taskbar lane
      charScreenX = wa.width - CHAR_W - 40;
      charScreenY = laneY;
      mainWindow.webContents.send('move:pos', { x: Math.round(charScreenX), y: Math.round(charScreenY) });
    }

    let targetX, stopDist;
    if (moveMode === 'follow') {
      const { x: cx } = screen.getCursorScreenPoint();
      targetX = cx - wa.x - CHAR_W / 2;
      stopDist = 100;
    } else {
      // Wander: pick a random X along the taskbar, repath every 5-10s
      const now = Date.now();
      if (!wanderTarget || now > wanderRepathAt) {
        const margin = 20;
        wanderTarget = { x: margin + Math.random() * Math.max(1, wa.width - CHAR_W - margin * 2) };
        wanderRepathAt = now + 5000 + Math.random() * 5000;
      }
      targetX = wanderTarget.x;
      stopDist = 12;
    }

    // Clamp inside the current display horizontally
    targetX = Math.max(0, Math.min(targetX, wa.width - CHAR_W));

    const dx = targetX - charScreenX;
    const dist = Math.abs(dx);

    if (dist <= stopDist) {
      mainWindow.webContents.send('move:state', { moving: false, dirX: 0 });
      if (moveMode === 'wander') wanderTarget = null;
      return;
    }

    const speed = Math.min(5, dist * 0.08);
    charScreenX += (dx / dist) * speed;
    charScreenY = laneY; // never leaves the taskbar lane
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

/* ------------------------------------------------------------------
 * Window
 * ------------------------------------------------------------------ */
// Native HWND_TOPMOST: Electron's 'screen-saver' z-order sits BELOW the
// Windows taskbar. A one-shot PowerShell SetWindowPos(HWND_TOPMOST) puts
// her band above it so she can walk along the taskbar face.
function setNativeTopMost(win) {
  try {
    const hwndBuf = win.getNativeWindowHandle();
    let hwnd = 0;
    for (let i = hwndBuf.length - 1; i >= 0; i--) hwnd = hwnd * 256 + hwndBuf[i];
    const script =
      "Add-Type -Name U -Namespace W -MemberDefinition '[DllImport(\"user32.dll\")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f);'; " +
      `[W.U]::SetWindowPos([IntPtr]::new(${hwnd}), [IntPtr]::new(-1), 0, 0, 0, 0, 0x0043)`;
    require('child_process')
      .spawn('powershell', ['-NoProfile', '-Command', script], { detached: true, stdio: 'ignore' })
      .unref();
  } catch (e) {
    console.warn('[overlay] native topmost failed (non-fatal):', e.message);
  }
}

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
      webSecurity: false, // file:// renderer fetches VRM + CDN modules from localhost
    },
  });

  // Windows: 'screen-saver' level sits BELOW the taskbar. Use 'floating' +
  // a native SetWindowPos(HWND_TOPMOST) so she walks ON TOP of the taskbar.
  mainWindow.setAlwaysOnTop(true, 'floating');
  if (process.platform === 'win32') {
    setNativeTopMost(mainWindow);
  }
  mainWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  // Click-through by default; renderer re-enables input when hovering her body
  mainWindow.setIgnoreMouseEvents(true, { forward: true });

  // Surface renderer errors in the terminal — no more silent black screens
  const wc = mainWindow.webContents;
  wc.on('console-message', (_e, level, message, line, sourceId) => {
    if (level >= 2) console.error(`[overlay:${path.basename(sourceId)}:${line}] ${message}`);
  });
  wc.on('did-fail-load', (_e, code, desc, url) => {
    console.error(`[overlay] failed to load ${url}: ${code} ${desc}`);
  });
  wc.on('render-process-gone', (_e, details) => {
    console.error(`[overlay] renderer crashed: ${details.reason}`);
  });

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'overlay.html'));

  mainWindow.on('closed', () => { mainWindow = null; });
}

function toggleVisibility() {
  if (!mainWindow) return;
  mainWindow.isVisible() ? mainWindow.hide() : mainWindow.show();
}

function createTray() {
  // Sun-disc icon (HINATA = ひなた, a warm sunlit place)
  const iconPath = path.join(__dirname, 'tray_icon.png');
  const icon = fs.existsSync(iconPath)
    ? nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 })
    : nativeImage.createEmpty();
  tray = new Tray(icon);
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

// Toggle mic listening from the global hotkey
function toggleMic() {
  if (mainWindow) mainWindow.webContents.send('mic:toggle');
}
// Push-to-talk: Alt+Shift+M toggles always-on listening (VAD barge-in in renderer)
globalShortcut.register('Alt+Shift+M', toggleMic);

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
