/** Movement engine — extracted from main.js (LOC law).
 *  Runs in the main process because the overlay is click-through:
 *  the renderer cannot be trusted with global screen coordinates. */
const { screen } = require('electron');

let moveMode = process.env.HINATA_MOVE_MODE || 'wander'; // 'wander' | 'follow' | 'off'
let wanderTarget = null;
let wanderRepathAt = 0;
let charScreenX = -1, charScreenY = -1;
const CHAR_W = 300, CHAR_H = 395; // compact desktop presence
let moveInterval = null;

function activeDisplay(mainWindow) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    try {
      const matched = screen.getDisplayMatching(mainWindow.getBounds());
      if (matched) return matched;
    } catch { /* fall through */ }
  }
  return screen.getDisplayNearestPoint(screen.getCursorScreenPoint())
    || screen.getPrimaryDisplay();
}

function start(getMainWindow, send) {
  moveInterval = setInterval(() => {
    const win = getMainWindow();
    if (!win || !win.isVisible() || moveMode === 'off') return;

    const wa = activeDisplay(win).workArea;
    const laneY = wa.height - CHAR_H; // feet planted on the taskbar top edge

    if (charScreenX < 0) {
      charScreenX = wa.width - CHAR_W - 40; // first run: bottom-right
      charScreenY = laneY;
      send('move:pos', { x: Math.round(charScreenX), y: Math.round(charScreenY) });
    }

    let targetX, stopDist;
    if (moveMode === 'follow') {
      targetX = screen.getCursorScreenPoint().x - wa.x - CHAR_W / 2;
      stopDist = 100;
    } else {
      const now = Date.now();
      if (!wanderTarget || now > wanderRepathAt) {
        const margin = 20;
        wanderTarget = { x: margin + Math.random() * Math.max(1, wa.width - CHAR_W - margin * 2) };
        wanderRepathAt = now + 5000 + Math.random() * 5000;
      }
      targetX = wanderTarget.x;
      stopDist = 12;
    }
    targetX = Math.max(0, Math.min(targetX, wa.width - CHAR_W));

    const dx = targetX - charScreenX;
    const dist = Math.abs(dx);
    if (dist <= stopDist) {
      send('move:state', { moving: false, dirX: 0 });
      if (moveMode === 'wander') wanderTarget = null;
      return;
    }
    const speed = Math.min(5, dist * 0.08);
    charScreenX += (dx / dist) * speed;
    charScreenY = laneY; // never leaves the taskbar lane
    send('move:pos', { x: Math.round(charScreenX), y: Math.round(charScreenY) });
    send('move:state', { moving: true, dirX: Math.sign(dx) });
  }, 30);
}

function setMode(mode) {
  moveMode = ['wander', 'follow'].includes(mode) ? mode : 'off';
  wanderTarget = null;
  return moveMode;
}

function mode() { return moveMode; }
function stop() { clearInterval(moveInterval); }

module.exports = { start, stop, setMode, mode, CHAR_W, CHAR_H };
