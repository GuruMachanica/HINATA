/**
 * HINATA WebSocket Client Module
 * Manages resilient duplex connection to Gateway. Strictly under 100 LOC.
 */

class HinataWSClient {
  constructor(endpoint, onEvent) {
    this.endpoint = endpoint;
    this.onEvent = onEvent;
    this.ws = null;
    this.reconnectTimer = null;
  }

  connect() {
    this.ws = new WebSocket(this.endpoint);

    this.ws.onopen = () => {
      this.onEvent('connection_status', { connected: true });
    };

    this.ws.onmessage = (event) => {
      try {
        const frame = JSON.parse(event.data);
        if (frame.type) {
          this.onEvent(frame.type, frame.payload);
        }
      } catch (err) {
        console.error('WS parse error:', err);
      }
    };

    this.ws.onclose = () => {
      this.onEvent('connection_status', { connected: false });
      this.scheduleReconnect();
    };

    this.ws.onerror = (err) => {
      console.warn('WS error:', err);
      this.ws.close();
    };
  }

  scheduleReconnect() {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, 2500);
  }

  send(type, payload) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, ...payload }));
      return true;
    }
    return false;
  }

  sendChat(text, context = {}) {
    return this.send('chat', { text, context });
  }
}

window.HinataWSClient = HinataWSClient;
