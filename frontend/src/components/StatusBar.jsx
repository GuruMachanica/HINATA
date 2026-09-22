import React from 'react';

const STATE_LABELS = {
  connecting: 'CONNECTING', online: 'ONLINE', thinking: 'THINKING',
  speaking: 'SPEAKING', reconnecting: 'RECONNECTING',
};

export default function StatusBar({ state, mood, ready }) {
  return (
    <header className="status-bar">
      <span className={`status-dot ${state}`} />
      <span className="status-text">{STATE_LABELS[state] || state}</span>
      {mood && mood !== 'neutral' && <span className="mood-chip">{mood}</span>}
      <span className="badge">{ready ? 'VRM ready' : 'loading VRM...'}</span>
    </header>
  );
}
