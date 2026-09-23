/**
 * Overlay voice I/O — mic listening (Web Speech API) + WS send.
 * Speech RECOGNITION uses the browser engine; TTS audio comes from the
 * backend (edge-tts) and is played by the overlay audio pipeline.
 */
const micState = {
  recognition: null,
  listening: false,
  supported: !!(window.SpeechRecognition || window.webkitSpeechRecognition),
};

function initMic(onTranscript, onBargeIn) {
  if (!micState.supported) {
    console.warn('[HINATA overlay] Web Speech API unavailable — mic disabled');
    return false;
  }
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const rec = new SR();
  rec.continuous = true;
  rec.interimResults = true;
  rec.lang = 'en-US';

  rec.onspeechstart = () => { if (onBargeIn) onBargeIn(); };

  rec.onresult = (event) => {
    let finalText = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      if (event.results[i].isFinal) finalText += event.results[i][0].transcript;
    }
    if (finalText.trim() && onTranscript) onTranscript(finalText.trim());
  };

  rec.onend = () => {
    if (micState.listening) { try { rec.start(); } catch {} }
  };
  rec.onerror = (e) => {
    if (e.error === 'not-allowed') {
      console.warn('[HINATA overlay] mic permission denied');
      micState.listening = false;
    }
  };

  micState.recognition = rec;
  return true;
}

function toggleMic() {
  if (!micState.recognition) return false;
  micState.listening = !micState.listening;
  if (micState.listening) {
    try { micState.recognition.start(); } catch {}
  } else {
    try { micState.recognition.stop(); } catch {}
  }
  return micState.listening;
}

function isListening() {
  return micState.listening;
}

// Wire into the overlay: expose to overlay.js via window scope
window.__overlayMic = { initMic, toggleMic, isListening, supported: micState.supported };
