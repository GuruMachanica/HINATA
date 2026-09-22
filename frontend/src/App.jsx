import React, { useEffect, useRef, useState } from 'react';
import { VRMStage } from './vrm/VRMStage.js';
import { useHinataWS } from './hooks/useHinataWS.js';
import ChatFeed from './components/ChatFeed.jsx';
import KGPanel from './components/KGPanel.jsx';
import StatusBar from './components/StatusBar.jsx';

const MODEL_URL = '/models/vrm/hinata.vrm';

export default function App() {
  const stageHostRef = useRef(null);
  const stageRef = useRef(null);
  const [ready, setReady] = useState(false);

  // WS -> stage callbacks (kept in a ref so handlers see latest stage)
  const onEventRef = useRef(() => {});

  const { messages, state, mood, kgEvents, sendChat } = useHinataWS((type, payload) => {
    onEventRef.current(type, payload);
  });

  useEffect(() => {
    if (!stageHostRef.current || stageRef.current) return;
    const stage = new VRMStage(stageHostRef.current);
    stageRef.current = stage;
    stage.loadModel(MODEL_URL)
      .then(() => setReady(true))
      .catch((e) => console.error('[HINATA] VRM load failed', e));

    onEventRef.current = (type, payload) => {
      switch (type) {
        case 'agent_state':
          if (payload.state === 'thinking') stage.setBehavior('think');
          if (payload.state === 'online' || payload.state === 'speaking') {
            if (stage.behavior === 'think') stage.setBehavior('idle');
          }
          break;
        case 'avatar_mood':
          if (payload.expression) stage.setMood(payload.mood, payload.expression);
          if (payload.mood === 'happy' || payload.mood === 'excited') {
            stage.setBehavior('wave');
            setTimeout(() => stage.setBehavior('idle'), 2800);
          }
          break;
        case 'speech_chunk':
          stage.playAudio(payload.audio);
          break;
        case 'barge_in_ack':
          stage.stopAudio();
          break;
      }
    };

    let raf;
    const loop = () => { stage.update(); raf = requestAnimationFrame(loop); };
    loop();
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <div className="shell">
      <aside className="panel avatar-panel">
        <StatusBar state={state} mood={mood} ready={ready} />
        <div className="avatar-host" ref={stageHostRef} />
        <div className="telemetry">
          <span>Brain: Hermes Agent</span>
          <span>Model: hinata-brain (local)</span>
          <span>Memory: SQLite + KG</span>
        </div>
      </aside>

      <main className="panel chat-panel">
        <header className="chat-header">
          <h1>HINATA <span>CORTEX</span></h1>
        </header>
        <ChatFeed messages={messages} onSend={sendChat} state={state} />
        <KGPanel events={kgEvents} />
      </main>
    </div>
  );
}
