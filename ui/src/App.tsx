import { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import APIKeysPage from './pages/APIKeysPage';
import ModelsPage from './pages/ModelsPage';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

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
  const [messages, setMessages]   = useState<{role: string, content: string}[]>([]);
  const [input, setInput]         = useState('');
  const [streaming, setStreaming] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [apiKey, setApiKey]       = useState(cfg.apiKey);
  const [apiUrl, setApiUrl]       = useState(cfg.apiUrl);
  const [showSetup, setShowSetup] = useState(!cfg.apiKey);
  const [health, setHealth]       = useState<any>(null);
  const [page, setPage]           = useState('chat');  // 'chat' | 'keys' | 'models'
  const [currentModel, setCurrentModel] = useState(cfg.model);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textRef   = useRef<HTMLTextAreaElement>(null);

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
        model: currentModel,
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

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No body");
      const dec    = new TextDecoder();
      let buf = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const lines = buf.split('\n');
        buf = lines.pop() || '';

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
    } catch (err: any) {
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          ...updated[updated.length - 1],
          content: `Error: ${err.message}`,
        };
        return updated;
      });
    } finally {
      setStreaming(false);
      textRef.current?.focus();
    }
  }, [input, streaming, messages, sessionId, apiKey, apiUrl, currentModel]);

  const onKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  };

  const newSession = async () => {
    try {
      const r = await fetch(`${apiUrl}/v1/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
        body: JSON.stringify({ model_id: currentModel }),
      });
      const d = await r.json();
      setSessionId(d.session_id);
      setMessages([]);
    } catch (e) { console.error(e); }
  };

  // ── Setup overlay ──────────────────────────────────────────────────────────
  if (showSetup) return (
    <div className="fixed inset-0 bg-background/80 flex items-center justify-center z-50">
      <div className="bg-card border border-border p-6 rounded-md w-full max-w-md">
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-foreground mb-1">Configure API</h2>
          <p className="text-sm text-muted-foreground">Provide connection details to continue.</p>
        </div>
        <div className="flex flex-col gap-4">
          <div className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">API URL</label>
            <Input value={apiUrl} onChange={e => setApiUrl(e.target.value)} placeholder="http://localhost:8000" />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">API Key</label>
            <Input value={apiKey} onChange={e => setApiKey(e.target.value)} placeholder="nxs_prod_..." type="password" />
          </div>
          <Button className="w-full mt-2" onClick={() => {
            cfg.apiUrl = apiUrl; cfg.apiKey = apiKey;
            setShowSetup(false);
          }}>Connect</Button>
          <p className="text-xs text-muted-foreground mt-2 text-center">
            Reference: <code className="font-mono bg-muted p-1 rounded">POST {apiUrl}/v1/keys</code>
          </p>
        </div>
      </div>
    </div>
  );

  // ── Main UI ───────────────────────────────────────────────────────────────
  return (
    <div className={`flex flex-col h-screen bg-background text-foreground ${isEmbedded ? ' embedded' : ''}`}>
      {/* Header */}
      <header className="flex items-center justify-between h-14 px-6 bg-card border-b border-border shrink-0">
        <div className="flex items-center gap-4">
          <span className="font-semibold text-foreground text-base">Duino API</span>
          <span className="text-xs text-muted-foreground font-medium">
            {health
              ? `${health.environment} / ${health.model_loaded ? 'Loaded' : 'No model'}${
                  health.url_expires_in ? ` / Expires: ${health.url_expires_in}` : ''
                }`
              : 'Connecting...'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Button variant={page === 'chat' ? 'secondary' : 'ghost'} size="sm" onClick={() => setPage('chat')}>Chat</Button>
          <Button variant={page === 'keys' ? 'secondary' : 'ghost'} size="sm" onClick={() => setPage('keys')}>Keys</Button>
          <Button variant={page === 'models' ? 'secondary' : 'ghost'} size="sm" onClick={() => setPage('models')}>Models</Button>
          <div className="w-px h-4 bg-border mx-2" />
          <Button variant="outline" size="sm" onClick={newSession}>New session</Button>
          <Button variant="ghost" size="sm" onClick={() => setShowSetup(true)}>Settings</Button>
        </div>
      </header>

      {/* Main Layout */}
      <div className="flex flex-1 overflow-hidden">
        {page === 'keys' ? (
          <div className="flex-1 w-full max-w-7xl mx-auto p-8 overflow-y-auto">
            <APIKeysPage apiUrl={apiUrl} initialApiKey={apiKey} />
          </div>
        ) : page === 'models' ? (
          <div className="flex-1 w-full max-w-7xl mx-auto p-8 overflow-y-auto">
            <ModelsPage 
              apiUrl={apiUrl} 
              apiKey={apiKey} 
              currentModel={currentModel} 
              onSelectModel={setCurrentModel} 
            />
          </div>
        ) : (
          <div className="flex flex-col flex-1 w-full max-w-4xl mx-auto p-8 overflow-y-auto relative">
            {/* Messages */}
            <main className="flex-1 overflow-y-auto flex flex-col gap-6 pb-32">
              {messages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                  <p>No messages</p>
                </div>
              )}
              {messages.map((m, i) => (
                <div key={i} className="flex flex-col gap-2 w-full">
                  <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    {m.role === 'user' ? 'User' : 'Assistant'}
                  </span>
                  <div className="text-sm leading-relaxed text-foreground prose prose-invert max-w-none">
                    <ReactMarkdown>{m.content || (streaming && i === messages.length - 1 ? '▋' : '')}</ReactMarkdown>
                  </div>
                </div>
              ))}
              <div ref={bottomRef} />
            </main>

            {/* Input */}
            <footer className="absolute bottom-0 left-0 right-0 bg-background pt-4 pb-8 px-8 flex gap-3">
              <Textarea
                ref={textRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={onKey}
                placeholder="Message Duino..."
                className="min-h-[52px] resize-none border-border focus-visible:ring-ring"
                disabled={streaming}
                rows={1}
              />
              <Button onClick={send} disabled={streaming || !input.trim()} className="h-[52px] px-6">
                {streaming ? 'Sending' : 'Send'}
              </Button>
            </footer>
          </div>
        )}
      </div>
    </div>
  );
}
