import { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';

// ── Config (override via postMessage from parent frame) ──────────────────────
const cfg = {
  apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  apiKey: import.meta.env.VITE_API_KEY || '',
  model:  import.meta.env.VITE_MODEL   || 'gemma-4-2b',
};

window.addEventListener('message', (e) => {
  if (e.data?.type === 'duino-config') {
    if (e.data.apiUrl) cfg.apiUrl = e.data.apiUrl;
    if (e.data.apiKey) cfg.apiKey = e.data.apiKey;
    if (e.data.model)  cfg.model  = e.data.model;
  }
});

const isEmbedded = window.self !== window.top;

// ── App ───────────────────────────────────────────────────────────────────────
export default function App() {
  const [messages, setMessages]   = useState([]);
  const [input, setInput]         = useState('');
  const [streaming, setStreaming] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [apiKey, setApiKey]       = useState(cfg.apiKey);
  const [apiUrl, setApiUrl]       = useState(cfg.apiUrl);
  const [showSetup, setShowSetup] = useState(!cfg.apiKey);
  const [health, setHealth]       = useState(null);
  const bottomRef = useRef(null);
  const textRef   = useRef(null);

  // Auto-scroll
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  // Health poll
  useEffect(() => {
    const check = async () => {
      try {
        const r = await fetch(`${apiUrl}/v1/health`);
        setHealth(await r.json());
      } catch { setHealth(null); }
    };
    check();
    const id = setInterval(check, 30_000);
    return () => clearInterval(id);
  }, [apiUrl]);

  const send = useCallback(async () => {
    if (!input.trim() || streaming) return;
    const userMsg = { role: 'user', content: input.trim() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setStreaming(true);

    const assistantMsg = { role: 'assistant', content: '' };
    setMessages(prev => [...prev, assistantMsg]);

    try {
      const body = {
        model: cfg.model,
        messages: [...messages, userMsg],
        stream: true,
        session_id: sessionId,
      };

      const res = await fetch(`${apiUrl}/v1/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
        body: JSON.stringify(body),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.getReader();
      const dec    = new TextDecoder();
      let buf = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const lines = buf.split('\n');
        buf = lines.pop();

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const payload = line.slice(6);
          if (payload === '[DONE]') break;
          try {
            const delta = JSON.parse(payload).choices?.[0]?.delta?.content || '';
            setMessages(prev => {
              const updated = [...prev];
              updated[updated.length - 1] = {
                ...updated[updated.length - 1],
                content: updated[updated.length - 1].content + delta,
              };
              return updated;
            });
          } catch {}
        }
      }
    } catch (err) {
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          ...updated[updated.length - 1],
          content: `❌ Error: ${err.message}`,
        };
        return updated;
      });
    } finally {
      setStreaming(false);
      textRef.current?.focus();
    }
  }, [input, streaming, messages, sessionId, apiKey, apiUrl]);

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  };

  const newSession = async () => {
    try {
      const r = await fetch(`${apiUrl}/v1/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
        body: JSON.stringify({ model_id: cfg.model }),
      });
      const d = await r.json();
      setSessionId(d.session_id);
      setMessages([]);
    } catch (e) { console.error(e); }
  };

  // ── Setup overlay ──────────────────────────────────────────────────────────
  if (showSetup) return (
    <div className="setup-overlay">
      <div className="setup-card">
        <h2>⚙️ Configure Duino API</h2>
        <label>API URL</label>
        <input value={apiUrl} onChange={e => setApiUrl(e.target.value)}
               placeholder="http://localhost:8000" />
        <label>API Key</label>
        <input value={apiKey} onChange={e => setApiKey(e.target.value)}
               placeholder="nxs_prod_..." type="password" />
        <button onClick={() => {
          cfg.apiUrl = apiUrl; cfg.apiKey = apiKey;
          setShowSetup(false);
        }}>Connect</button>
        <p className="hint">
          Get a key: <code>POST {apiUrl}/v1/keys</code>
        </p>
      </div>
    </div>
  );

  // ── Main UI ───────────────────────────────────────────────────────────────
  return (
    <div className={`duino-app${isEmbedded ? ' embedded' : ''}`}>
      {/* Header */}
      <header className="duino-header">
        <div className="header-left">
          <span className="logo">⚡ Duino API</span>
          <span className={`status-dot ${health?.status === 'ok' ? 'online' : 'offline'}`} />
          <span className="status-label">
            {health ? `${health.environment} · ${health.model_loaded ? '🟢 loaded' : '🔴 no model'}` : 'connecting…'}
          </span>
        </div>
        <div className="header-right">
          <button className="btn-ghost" onClick={newSession} title="New session">＋ Session</button>
          <button className="btn-ghost" onClick={() => setShowSetup(true)} title="Settings">⚙️</button>
        </div>
      </header>

      {/* Messages */}
      <main className="messages">
        {messages.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">🤖</div>
            <h3>Gemma 4 · Ready</h3>
            <p>Ask anything. Responses stream in real-time.</p>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg msg-${m.role}`}>
            <span className="msg-avatar">{m.role === 'user' ? '👤' : '🤖'}</span>
            <div className="msg-bubble">
              <ReactMarkdown>{m.content || (streaming && i === messages.length - 1 ? '▋' : '')}</ReactMarkdown>
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </main>

      {/* Input */}
      <footer className="input-bar">
        <textarea
          ref={textRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKey}
          placeholder="Message Gemma 4… (Enter to send, Shift+Enter for newline)"
          rows={1}
          disabled={streaming}
        />
        <button className="btn-send" onClick={send} disabled={streaming || !input.trim()}>
          {streaming ? '⏳' : '➤'}
        </button>
      </footer>
    </div>
  );
}
