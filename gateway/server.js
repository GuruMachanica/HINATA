/**
 * HINATA Gateway Server
 * Hosts presentation shell static assets, avatar 3D models, and WebSocket endpoint.
 * Strictly under 65 LOC.
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const { WebSocketServer } = require('ws');
const { setupWebSocket } = require('./ws_handler');

const PORT = parseInt(process.env.GATEWAY_PORT || '8080', 10);
const STATIC_DIR = path.resolve(__dirname, '..', 'shell-bella');

const MIME_TYPES = {
  '.html': 'text/html',
  '.css': 'text/css',
  '.js': 'application/javascript',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.glb': 'model/gltf-binary',
  '.gltf': 'model/gltf+json',
  '.vrm': 'model/gltf-binary',
  '.vrma': 'model/gltf-binary'
};

const server = http.createServer((req, res) => {
  const reqPath = decodeURIComponent(req.url.split('?')[0]);
  if (reqPath === '/favicon.ico') { res.writeHead(204); return res.end(); }
  let filePath;

  if (reqPath.startsWith('/models/')) {
    filePath = path.join(STATIC_DIR, reqPath);
  } else {
    filePath = path.join(STATIC_DIR, reqPath === '/' ? 'index.html' : reqPath);
  }

  fs.readFile(filePath, (err, data) => {
    if (err) {
      console.warn('[404 Not Found]', req.url, '->', filePath);
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      return res.end('404 Not Found');
    }
    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, { 'Content-Type': MIME_TYPES[ext] || 'application/octet-stream' });
    res.end(data);
  });
});

const wss = new WebSocketServer({ server });
setupWebSocket(wss);

server.listen(PORT, () => {
  console.log(`[HINATA Gateway] Running at http://127.0.0.1:${PORT}`);
});
