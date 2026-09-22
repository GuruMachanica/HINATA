import React, { useEffect, useRef, useState } from 'react';

function FormattedText({ content }) {
  if (!content) return null;

  // Split into paragraphs by double newlines or line breaks
  const paragraphs = content.split(/\n\n+/);

  return (
    <div className="formatted-body">
      {paragraphs.map((para, pIdx) => {
        const lines = para.split(/\n/);
        return (
          <p key={pIdx} className="msg-para">
            {lines.map((line, lIdx) => (
              <React.Fragment key={lIdx}>
                {lIdx > 0 && <br />}
                {renderFormattedLine(line)}
              </React.Fragment>
            ))}
          </p>
        );
      })}
    </div>
  );
}

function renderFormattedLine(text) {
  // Simple inline code formatting `code`
  const parts = text.split(/(`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      return <code key={i} className="inline-code">{part.slice(1, -1)}</code>;
    }
    return part;
  });
}

export default function ChatFeed({ messages, onSend, state }) {
  const [input, setInput] = useState('');
  const feedRef = useRef(null);
  const isThinking = state === 'thinking';

  useEffect(() => {
    feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, isThinking]);

  const submit = (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || isThinking) return;
    onSend(text);
    setInput('');
  };

  return (
    <>
      <section className="chat-feed" ref={feedRef}>
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.role === 'user' ? 'user' : 'assistant'}`}>
            <div className="msg-header">
              <span className="msg-sender">{m.sender}</span>
              {m.role === 'assistant' && m.mood && m.mood !== 'calm' && m.mood !== 'neutral' && (
                <span className={`msg-mood-tag mood-${m.mood}`}>{m.mood}</span>
              )}
            </div>
            <div className="msg-content">
              <FormattedText content={m.text} />
            </div>
          </div>
        ))}

        {isThinking && (
          <div className="message assistant thinking">
            <div className="msg-header">
              <span className="msg-sender">HINATA</span>
            </div>
            <div className="msg-content thinking-bubble">
              <span className="dot"></span>
              <span className="dot"></span>
              <span className="dot"></span>
            </div>
          </div>
        )}
      </section>

      <form className="input-dock" onSubmit={submit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={isThinking ? "HINATA is thinking..." : "Talk to HINATA..."}
          disabled={isThinking}
          autoFocus
        />
        <button type="submit" disabled={isThinking || !input.trim()} className={isThinking ? 'busy' : ''}>
          {isThinking ? '...' : 'Send'}
        </button>
      </form>
    </>
  );
}
