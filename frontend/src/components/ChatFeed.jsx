import React, { useEffect, useRef, useState } from 'react';

export default function ChatFeed({ messages, onSend }) {
  const [input, setInput] = useState('');
  const feedRef = useRef(null);

  useEffect(() => {
    feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const submit = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    onSend(input);
    setInput('');
  };

  return (
    <>
      <section className="chat-feed" ref={feedRef}>
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.role === 'user' ? 'user' : 'assistant'}`}>
            <div className="msg-sender">{m.sender}</div>
            <div className="msg-content">{m.text}</div>
            {m.mood && <div className="msg-mood">mood: {m.mood}</div>}
          </div>
        ))}
      </section>
      <form className="input-dock" onSubmit={submit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Talk to HINATA..."
          autoFocus
        />
        <button type="submit">Send</button>
      </form>
    </>
  );
}
