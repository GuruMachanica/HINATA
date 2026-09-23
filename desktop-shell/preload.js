const { contextBridge, ipcRenderer } = require('electron');

// Backend port from the main process env (safe to expose — non-secret config)
const BACKEND_PORT = process.env.HINATA_PORT || '8080';

contextBridge.exposeInMainWorld('HINATA_BACKEND_PORT', BACKEND_PORT);

contextBridge.exposeInMainWorld('hinataAPI', {
  setIgnoreMouse: (ignore) => ipcRenderer.invoke('window:set-ignore-mouse', ignore),
  setMoveMode: (mode) => ipcRenderer.invoke('move:set-mode', mode),
  quit: () => ipcRenderer.invoke('app:quit'),

  onCursorPosition: (cb) => ipcRenderer.on('cursor:position', (_e, pos) => cb(pos)),
  onMoveState: (cb) => ipcRenderer.on('move:state', (_e, s) => cb(s)),
  onMovePos: (cb) => ipcRenderer.on('move:pos', (_e, p) => cb(p)),
  onMicToggle: (cb) => ipcRenderer.on('mic:toggle', () => cb()),
});
