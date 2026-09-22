import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * useHinataWS — HINATA WS protocol as a React hook.
 * Event protocol (same as backend/main.py):
 *   connection_status, agent_state, agent_response, avatar_mood,
 *   speech_chunk, kg_update
 */
export function useHinataWS(onEvent) {
  const [messages, setMessages] = useState([
    { role: 'assistant', sender: 'HINATA', text: 'HINATA online. Hermes cortex, local model, memory and knowledge graph active.' },
  ]);
  const [state, setState] = useState('connecting');
  const [mood, setMood] = useState('neutral');
  const [kgEvents, setKgEvents] = useState([]);
  const wsRef = useRef(null);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${location.host}`);
    wsRef.current = ws;

    ws.onopen = () => setState('online');
    ws.onclose = () => { setState('reconnecting'); setTimeout(() => ws.close(), 2000); };

    ws.onmessage = (event) => {
      let msg;
      try { msg = JSON.parse(event.data); } catch { return; }
      const { type, payload } = msg;
      onEventRef.current?.(type, payload);

      switch (type) {
        case 'connection_status':
          setState(payload.connected ? 'online' : 'reconnecting');
          break;
        case 'agent_state':
          setState(payload.state);
          break;
        case 'agent_response':
          setMessages((m) => [...m, {
            role: 'assistant', sender: 'HINATA', text: payload.content, mood: payload.mood,
          }]);
          break;
        case 'avatar_mood':
          setMood(payload.mood);
          break;
        case 'kg_update':
          setKgEvents((k) => [...k.slice(-9), payload]);
          break;
        default:
          break;
      }
    };

    return () => ws.close();
  }, []);

  const sendChat = useCallback((query) => {
    const text = query.trim();
    if (!text) return;
    setMessages((m) => [...m, { role: 'user', sender: 'YOU', text }]);
    wsRef.current?.send(JSON.stringify({ type: 'chat', payload: { query: text } }));
  }, []);

  const requestTTS = useCallback((text) => {
    wsRef.current?.send(JSON.stringify({ type: 'tts_request', payload: { text } }));
  }, []);

  return { messages, state, mood, kgEvents, sendChat, requestTTS };
}
