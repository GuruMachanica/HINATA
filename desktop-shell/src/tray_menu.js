/** Tray menu — extracted from main.js (LOC law). Reads shared UI state via callbacks. */
const { Menu, Tray, nativeImage, app, shell } = require('electron');
const path = require('path');
const fs = require('fs');

const GATEWAY_URL_BASE = 'http://127.0.0.1';

/** Build and return the Tray with the standard HINATA menu. */
function createTray({ toggleVisibility, setMoveMode, moveMode, backendPort }) {
  const iconPath = path.join(__dirname, '..', 'tray_icon.png');
  const icon = fs.existsSync(iconPath)
    ? nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 })
    : nativeImage.createEmpty();
  const tray = new Tray(icon);
  tray.setToolTip('HINATA — Desktop Companion');
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: 'Show / Hide  (Alt+Shift+H)', click: toggleVisibility },
    { label: 'Movement: Wander', type: 'radio', checked: moveMode === 'wander',
      click: () => setMoveMode('wander') },
    { label: 'Movement: Follow cursor', type: 'radio', checked: moveMode === 'follow',
      click: () => setMoveMode('follow') },
    { label: 'Movement: Off', type: 'radio', checked: moveMode === 'off',
      click: () => setMoveMode('off') },
    { type: 'separator' },
    { label: 'Open full cortex (React UI)',
      click: () => shell.openExternal(`${GATEWAY_URL_BASE}:${backendPort}`) },
    { type: 'separator' },
    { label: 'Quit HINATA', click: () => require('electron').app.quit() },
  ]));
  return tray;
}

module.exports = { createTray };
