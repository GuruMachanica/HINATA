/**
 * HINATA Desktop Shell — Electron main process
 * Transparent always-on-top VRM overlay. This process owns the desktop layer:
 * overlay window, tray, hotkeys, cursor tracking; modules do the rest.
 */

const { app, BrowserWindow, ipcMain, screen, globalShortcut } = require('electron');
const path = require('path');
const { ensureBackendRunning, stopBackend } = require('./backend_launcher');
const { createTray } = require('./tray_menu');
const movement = require('./movement_engine');

let mainWindow = null;
let tray = null;
let cursorInterval = null;

// Native HWND_TOPMOST: Electron's 'screen-saver' z-order sits BELOW the
// Windows taskbar. One-shot SetWindowPos puts her band above it.
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
  const { width, height, x: waX, y: waY } = screen.getPrimaryDisplay().workArea;

  mainWindow = new BrowserWindow({
    width, height, x: waX, y: waY,
    frame: false, transparent: true, alwaysOnTop: true, skipTaskbar: true,
    resizable: false, hasShadow: false,
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload.js'),
      contextIsolation: true, nodeIntegration: false,
      webSecurity: false, // file:// renderer fetches VRM + CDN modules from localhost
    },
  });

  mainWindow.setAlwaysOnTop(true, 'floating');
  if (process.platform === 'win32') setNativeTopMost(mainWindow);
  mainWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  mainWindow.setIgnoreMouseEvents(true, { forward: true }); // click-through by default

  const wc = mainWindow.webContents;
  wc.on('console-message', (_e, level, message, line, sourceId) => {
    if (level >= 2) console.error(`[overlay:${path.basename(sourceId)}:${line}] ${message}`);
  });
  wc.on('did-fail-load', (_e, code, desc, url) =>
    console.error(`[overlay] failed to load ${url}: ${code} ${desc}`));
  wc.on('render-process-gone', (_e, details) =>
    console.error(`[overlay] renderer crashed: ${details.reason}`));

  mainWindow.loadFile(path.join(__dirname, '..', 'renderer', 'overlay.html'));
  mainWindow.on('closed', () => { mainWindow = null; });
}

function toggleVisibility() {
  if (!mainWindow) return;
  mainWindow.isVisible() ? mainWindow.hide() : mainWindow.show();
}

function setMoveMode(mode) {
  movement.setMode(mode);
  if (mainWindow && mode === 'off') {
    mainWindow.webContents.send('move:state', { moving: false, dirX: 0 });
  }
  if (tray) tray._rebuildMenu?.();
}

/* IPC surface */
ipcMain.handle('window:set-ignore-mouse', (_evt, ignore) => {
  if (mainWindow) mainWindow.setIgnoreMouseEvents(ignore, { forward: true });
});
ipcMain.handle('move:set-mode', (_evt, mode) => setMoveMode(mode) || movement.mode());
ipcMain.handle('app:quit', () => app.quit());

function startCursorTracking() {
  cursorInterval = setInterval(() => {
    if (!mainWindow || !mainWindow.isVisible()) return;
    const { x: cx, y: cy } = screen.getCursorScreenPoint();
    const [wx, wy] = mainWindow.getPosition();
    const [ww, wh] = mainWindow.getSize();
    const { width: sw, height: sh } = screen.getPrimaryDisplay().workAreaSize;
    const nx = Math.max(-1, Math.min(1, (cx - (wx + ww / 2)) / (sw / 2)));
    const ny = Math.max(-1, Math.min(1, (cy - (wy + wh / 2)) / (sh / 2)));
    mainWindow.webContents.send('cursor:position', { x: nx, y: ny });
  }, 50);
}

app.whenReady().then(async () => {
  createWindow();
  tray = createTray({ toggleVisibility, setMoveMode, moveMode: movement.mode() });
  startCursorTracking();
  movement.start(() => mainWindow, (ch, payload) => mainWindow?.webContents.send(ch, payload));
  globalShortcut.register('Alt+Shift+H', toggleVisibility);
  globalShortcut.register('Alt+Shift+M', () => mainWindow?.webContents.send('mic:toggle'));

  // Packaged builds launch their own bundled backend; dev assumes it's running.
  await ensureBackendRunning();
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
  clearInterval(cursorInterval);
  movement.stop();
  stopBackend();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
