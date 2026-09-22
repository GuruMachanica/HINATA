/**
 * HINATA Presentation Shell UI Controller
 * Manipulates DOM, renders chat bubbles, states, and telemetry.
 * Strictly under 100 LOC.
 */

class UIController {
  constructor() {
    this.chatFeed = document.getElementById('chat-feed');
    this.statusDot = document.getElementById('status-dot');
    this.statusText = document.getElementById('status-text');
    this.avatarRing = document.getElementById('avatar-ring');
    this.gpuMetric = document.getElementById('gpu-metric');
    this.vramMetric = document.getElementById('vram-metric');
  }

  appendMessage(sender, text, isUser = false) {
    const msg = document.createElement('div');
    msg.className = `message ${isUser ? 'user' : 'assistant'}`;
    msg.innerHTML = `
      <div class="msg-sender">${sender}</div>
      <div class="msg-content">${text.replace(/\n/g, '<br>')}</div>
    `;
    this.chatFeed.appendChild(msg);
    this.chatFeed.scrollTop = this.chatFeed.scrollHeight;
  }

  setAgentState(state) {
    const s = state.toLowerCase();
    this.statusText.textContent = s.toUpperCase();
    
    if (s === 'thinking') {
      this.statusDot.style.background = 'var(--status-thinking)';
      this.statusDot.style.boxShadow = '0 0 12px var(--status-thinking)';
      this.avatarRing.style.borderColor = 'var(--status-thinking)';
    } else if (s === 'speaking') {
      this.statusDot.style.background = 'var(--status-speaking)';
      this.statusDot.style.boxShadow = '0 0 12px var(--status-speaking)';
      this.avatarRing.style.borderColor = 'var(--accent-cyan)';
    } else {
      this.statusDot.style.background = 'var(--status-online)';
      this.statusDot.style.boxShadow = '0 0 10px var(--status-online)';
      this.avatarRing.style.borderColor = 'rgba(0, 229, 255, 0.3)';
    }
  }

  updateTelemetry(gpuStats) {
    if (!gpuStats || !gpuStats.gpus || !gpuStats.gpus.length) return;
    const gpu = gpuStats.gpus[0];
    this.gpuMetric.textContent = `${gpu.temperature_c}°C (${gpu.utilization_pct}%)`;
    const usedGb = (gpu.memory_used_mb / 1024).toFixed(1);
    const totalGb = (gpu.memory_total_mb / 1024).toFixed(1);
    this.vramMetric.textContent = `${usedGb} / ${totalGb} GB`;
  }
}

window.UIController = UIController;
