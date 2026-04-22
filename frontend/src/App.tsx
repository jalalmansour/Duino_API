import { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import APIKeysPage from './pages/APIKeysPage';
import ModelsPage from './pages/ModelsPage';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { RootLayout } from '@/components/layout/RootLayout';
import { View } from '@/components/layout/AppSidebar';
import { Send, Plus, Loader2 } from 'lucide-react';

// ── Config ───────────────────────────────────────────────────────────────────
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
  const [page, setPage]           = useState<View>('chat');
  const [currentModel, setCurrentModel] = useState(cfg.model);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textRef   = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { 
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); 
  }, [messages]);

  useEffect(() => {
    const check = async () => {
      try {
        const r = await fetch(`${apiUrl}/v1/health`, {
          headers: { 'ngrok-skip-browser-warning': 'true' }
        });
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
          'ngrok-skip-browser-warning': 'true',
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
        headers: { 
          'Content-Type': 'application/json', 
          'X-API-Key': apiKey,
          'ngrok-skip-browser-warning': 'true'
        },
        body: JSON.stringify({ model_id: currentModel }),
      });
      const d = await r.json();
      setSessionId(d.session_id);
      setMessages([]);
      setPage('chat');
    } catch (e) { console.error(e); }
  };

  if (showSetup) return (
    <div className="fixed inset-0 bg-void flex items-center justify-center z-50 p-4">
      <div className="bg-ink border border-slate p-10 rounded-[6px] w-full max-w-md">
        <div className="mb-10">
          <div className="size-10 rounded-[4px] bg-bone flex items-center justify-center mb-8">
            <span className="text-void font-bold text-xl">D</span>
          </div>
          <h2 className="text-2xl font-semibold text-bone mb-3 tracking-tight">Initialize session</h2>
          <p className="text-sm text-mist leading-relaxed font-normal">Establish gateway connection parameters to begin inference.</p>
        </div>
        <div className="flex flex-col gap-8">
          <div className="space-y-3">
            <label className="text-[10px] font-semibold text-mist uppercase tracking-[0.08em]">Gateway URL</label>
            <Input 
              value={apiUrl} 
              onChange={e => setApiUrl(e.target.value)} 
              placeholder="http://localhost:8000"
              className="bg-void border-slate rounded-[4px] h-11 text-bone placeholder:text-mist/30"
            />
          </div>
          <div className="space-y-3">
            <label className="text-[10px] font-semibold text-mist uppercase tracking-[0.08em]">Master Token</label>
            <Input 
              value={apiKey} 
              onChange={e => setApiKey(e.target.value)} 
              placeholder="nxs_prod_..." 
              type="password"
              className="bg-void border-slate rounded-[4px] h-11 text-bone placeholder:text-mist/30"
            />
          </div>
          <Button className="w-full mt-4 h-12 text-xs font-semibold uppercase tracking-widest bg-bone text-void hover:bg-bone/90 rounded-[4px]" onClick={() => {
            cfg.apiUrl = apiUrl; cfg.apiKey = apiKey;
            setShowSetup(false);
          }}>Connect</Button>
          <div className="pt-6 border-t border-slate mt-2 text-center">
            <span className="text-[10px] text-mist uppercase tracking-widest">
              Active node: <span className="font-mono text-bone ml-1">{new URL(apiUrl).hostname}</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <RootLayout 
      currentView={page} 
      onViewChange={setPage} 
      onNewSession={newSession}
      health={health}
    >
      <div className="h-full w-full overflow-hidden bg-void">
        {page === 'keys' ? (
          <div className="h-full overflow-y-auto">
            <div className="max-w-6xl mx-auto p-10">
              <APIKeysPage apiUrl={apiUrl} initialApiKey={apiKey} />
            </div>
          </div>
        ) : page === 'models' ? (
          <div className="h-full overflow-y-auto">
            <div className="max-w-6xl mx-auto p-10">
              <ModelsPage 
                apiUrl={apiUrl} 
                apiKey={apiKey} 
                currentModel={currentModel} 
                onSelectModel={setCurrentModel} 
              />
            </div>
          </div>
        ) : page === 'settings' ? (
          <div className="h-full overflow-y-auto">
            <div className="max-w-3xl mx-auto p-10">
              <div className="space-y-10">
                <div>
                  <h1 className="text-3xl font-semibold tracking-tight text-bone mb-3">Settings</h1>
                  <p className="text-mist font-normal">Manage platform configuration and connection parameters.</p>
                </div>
                
                <div className="grid gap-10">
                  <div className="p-8 rounded-[6px] border border-slate bg-ink">
                    <h3 className="text-xs font-semibold text-mist uppercase tracking-[0.08em] mb-6">Gateway configuration</h3>
                    <div className="space-y-6">
                      <div className="space-y-3">
                        <label className="text-[10px] font-semibold text-mist uppercase tracking-[0.08em]">API Gateway</label>
                        <Input value={apiUrl} readOnly className="bg-void border-slate text-mist cursor-default h-11" />
                      </div>
                      <div className="space-y-3">
                        <label className="text-[10px] font-semibold text-mist uppercase tracking-[0.08em]">Active Token</label>
                        <Input value={apiKey} type="password" readOnly className="bg-void border-slate text-mist cursor-default h-11" />
                      </div>
                    </div>
                  </div>
                  <Button variant="secondary" className="h-11 rounded-[4px] border border-slate bg-slate/20 text-bone hover:bg-slate/30" onClick={() => setShowSetup(true)}>Change Gateway</Button>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex flex-col h-full relative">
            {/* Chat Container */}
            <div className="flex-1 overflow-y-auto">
              <div className="max-w-4xl mx-auto p-10 pb-40">
                {messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-32 text-center">
                    <div className="size-16 rounded-[4px] border border-slate bg-ink flex items-center justify-center mb-8">
                      <Plus className="size-6 text-mist" />
                    </div>
                    <div>
                      <h2 className="text-xl font-semibold text-bone mb-3 tracking-tight">No messages</h2>
                      <p className="text-mist font-normal text-sm max-w-xs mx-auto leading-relaxed">
                        Select a model and transmit a prompt to initiate the session.
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-12">
                    {messages.map((m, i) => (
                      <div key={i} className={`flex flex-col gap-4 ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
                        <div className={`flex items-center gap-3 ${m.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                          <div className={`size-5 rounded-[2px] flex items-center justify-center text-[9px] font-bold ${
                            m.role === 'user' ? 'bg-slate text-bone' : 'bg-bone text-void'
                          }`}>
                            {m.role === 'user' ? 'U' : 'A'}
                          </div>
                          <span className="text-[10px] font-semibold text-mist uppercase tracking-[0.08em]">
                            {m.role === 'user' ? 'User' : 'Assistant'}
                          </span>
                        </div>
                        
                        <div className={`max-w-[90%] rounded-[4px] p-6 text-[14px] leading-relaxed ${
                          m.role === 'user' 
                            ? 'bg-slate/10 border border-slate/40 text-bone' 
                            : 'bg-ink border border-slate text-bone'
                        }`}>
                          <div className="prose prose-invert prose-sm max-w-none prose-headings:text-bone prose-p:text-bone prose-strong:text-bone prose-code:text-violet">
                            <ReactMarkdown>{m.content || (streaming && i === messages.length - 1 ? '▋' : '')}</ReactMarkdown>
                          </div>
                        </div>
                      </div>
                    ))}
                    <div ref={bottomRef} className="h-4" />
                  </div>
                )}
              </div>
            </div>

            {/* Input Footer */}
            <div className="absolute bottom-0 left-0 right-0 p-10 bg-void/80 backdrop-blur-sm border-t border-slate/20">
              <div className="max-w-3xl mx-auto relative group">
                <div className="relative flex gap-4 p-2 bg-ink border border-slate rounded-[6px] shadow-sm">
                  <Textarea
                    ref={textRef}
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={onKey}
                    placeholder={`Transmit to ${currentModel}...`}
                    className="min-h-[44px] max-h-40 bg-transparent border-none focus-visible:ring-0 resize-none py-3 px-4 text-[14px] text-bone placeholder:text-mist/30"
                    disabled={streaming}
                    rows={1}
                  />
                  <Button 
                    onClick={send} 
                    disabled={streaming || !input.trim()} 
                    size="icon"
                    className="size-11 mt-auto shrink-0 rounded-[4px] bg-bone text-void hover:bg-bone/90"
                  >
                    {streaming ? <div className="size-4 rounded-full border-2 border-void/30 border-t-void animate-spin" /> : <Send className="size-4" />}
                  </Button>
                </div>
                <div className="mt-3 px-1 flex justify-between items-center">
                  <span className="text-[10px] text-mist uppercase tracking-[0.08em]">
                    {streaming ? "Transmitting..." : "Command + Enter to send"}
                  </span>
                  {sessionId && (
                    <span className="text-[10px] text-mist/40 font-mono tracking-tighter uppercase">
                      Session_ID: {sessionId.slice(0, 8)}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </RootLayout>
  );
}
