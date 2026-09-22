/**
 * HINATA Microphone Controller & VAD Barge-In
 * Captures user speech and triggers immediate barge-in interruption.
 * Strictly under 80 LOC.
 */

class MicController {
  constructor(onTranscript, onBargeIn) {
    this.onTranscript = onTranscript;
    this.onBargeIn = onBargeIn;
    this.recognition = null;
    this.isListening = false;
    this._init();
  }

  _init() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) return;

    this.recognition = new SpeechRec();
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.lang = 'en-US';

    this.recognition.onstart = () => {
      this.isListening = true;
    };

    this.recognition.onspeechstart = () => {
      // VAD Trigger: User spoke -> Instant Barge-in!
      if (this.onBargeIn) this.onBargeIn();
    };

    this.recognition.onresult = (event) => {
      let finalTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const item = event.results[i];
        if (item.isFinal) {
          finalTranscript += item[0].transcript;
        }
      }
      if (finalTranscript.trim() && this.onTranscript) {
        this.onTranscript(finalTranscript.trim());
      }
    };

    this.recognition.onend = () => {
      if (this.isListening) {
        try { this.recognition.start(); } catch {}
      }
    };
  }

  toggle(active) {
    if (!this.recognition) return false;
    if (active) {
      this.isListening = true;
      try { this.recognition.start(); } catch {}
    } else {
      this.isListening = false;
      try { this.recognition.stop(); } catch {}
    }
    return this.isListening;
  }
}

window.MicController = MicController;
