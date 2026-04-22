import { useState, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

const LANGS = [
  { id: 'curl',       label: 'cURL' },
  { id: 'python',     label: 'Python' },
  { id: 'typescript', label: 'TypeScript' },
  { id: 'java',       label: 'Java' },
  { id: 'go',         label: 'Go' },
  { id: 'dotnet',     label: '.NET / C#' },
  { id: 'rest',       label: 'REST' },
]

function getCodeSnippet(lang: string, apiUrl: string, apiKey: string, model = 'gemma-4-2b') {
  const url = `${apiUrl}/v1/chat/completions`
  switch (lang) {
    case 'curl': return `#!/bin/bash
# Duino API — Shell Example
# Provisioned via Nocturnal UI Craft

curl -X POST "${url}" \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: ${apiKey}" \\
  -d '{
    "model": "${model}",
    "messages": [{"role": "user", "content": "Hello, Duino!"}],
    "max_tokens": 256,
    "stream": false
  }'`

    case 'python': return `# Duino API — Python SDK Example
import requests
import json

def chat(prompt):
    url = "${url}"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "${apiKey}"
    }
    payload = {
        "model": "${model}",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
        "stream": True
    }
    
    response = requests.post(url, headers=headers, json=payload, stream=True)
    for line in response.iter_lines():
        if line:
            data = line.decode()
            if data.startswith("data: ") and data[6:] != "[DONE]":
                token = json.loads(data[6:])["choices"][0]["delta"].get("content", "")
                print(token, end="", flush=True)`

    case 'typescript': return `// Duino API — TypeScript / Node.js Example
const DUINO_API_KEY = "${apiKey}";
const DUINO_API_URL = "${apiUrl}";

// ── Single request ─────────────────────────────────────
async function chat(prompt: string): Promise<string> {
  const res = await fetch(\`\${DUINO_API_URL}/v1/chat/completions\`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": DUINO_API_KEY,
    },
    body: JSON.stringify({
      model: "${model}",
      messages: [{ role: "user", content: prompt }],
      max_tokens: 256,
    }),
  });
  const data = await res.json();
  return data.choices[0].message.content;
}

// ── Streaming ──────────────────────────────────────────
async function streamChat(prompt: string): Promise<void> {
  const res = await fetch(\`\${DUINO_API_URL}/v1/chat/completions\`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": DUINO_API_KEY },
    body: JSON.stringify({
      model: "${model}",
      messages: [{ role: "user", content: prompt }],
      max_tokens: 512,
      stream: true,
    }),
  });
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const lines = decoder.decode(value).split("\\n");
    for (const line of lines) {
      if (line.startsWith("data: ") && line.slice(6) !== "[DONE]") {
        const token = JSON.parse(line.slice(6)).choices[0]?.delta?.content ?? "";
        process.stdout.write(token);
      }
    }
  }
}

chat("Hello, Duino!").then(console.log);`

    case 'java': return `// Duino API — Java Example (Java 11+ HttpClient)
import java.net.URI;
import java.net.http.*;
import java.net.http.HttpResponse.BodyHandlers;

public class DuinoClient {
    static final String API_KEY = "${apiKey}";
    static final String API_URL = "${apiUrl}";

    public static void main(String[] args) throws Exception {
        var client = HttpClient.newHttpClient();
        var body = """
            {
                "model": "${model}",
                "messages": [{"role": "user", "content": "Hello, Duino!"}],
                "max_tokens": 256
            }
            """;

        var request = HttpRequest.newBuilder()
            .uri(URI.create(API_URL + "/v1/chat/completions"))
            .header("Content-Type", "application/json")
            .header("X-API-Key", API_KEY)
            .POST(HttpRequest.BodyPublishers.ofString(body))
            .build();

        var response = client.send(request, BodyHandlers.ofString());
        System.out.println(response.body());
    }
}`

    case 'go': return `// Duino API — Go Example
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
)

const (
	APIKey = "${apiKey}"
	APIURL = "${apiUrl}"
	Model  = "${model}"
)

type Message struct {
	Role    string \`json:"role"\`
	Content string \`json:"content"\`
}

type ChatRequest struct {
	Model     string    \`json:"model"\`
	Messages  []Message \`json:"messages"\`
	MaxTokens int       \`json:"max_tokens"\`
}

func main() {
	payload, _ := json.Marshal(ChatRequest{
		Model:     Model,
		Messages:  []Message{{Role: "user", Content: "Hello, Duino!"}},
		MaxTokens: 256,
	})

	req, _ := http.NewRequest("POST", APIURL+"/v1/chat/completions", bytes.NewBuffer(payload))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-API-Key", APIKey)

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		panic(err)
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	fmt.Println(string(body))
}`

    case 'dotnet': return `// Duino API — .NET / C# Example
using System;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using System.Threading.Tasks;

class DuinoClient
{
    const string ApiKey = "${apiKey}";
    const string ApiUrl = "${apiUrl}";
    const string Model  = "${model}";

    static async Task Main()
    {
        using var client = new HttpClient();
        client.DefaultRequestHeaders.Add("X-API-Key", ApiKey);

        var payload = new
        {
            model    = Model,
            messages = new[] { new { role = "user", content = "Hello, Duino!" } },
            max_tokens = 256,
        };

        var response = await client.PostAsJsonAsync(
            ApiUrl + "/v1/chat/completions", payload);

        var json = await response.Content.ReadAsStringAsync();
        using var doc = JsonDocument.Parse(json);
        var text = doc.RootElement
            .GetProperty("choices")[0]
            .GetProperty("message")
            .GetProperty("content")
            .GetString();

        Console.WriteLine(text);
    }
}`

    case 'rest': return `# ── Chat Completion ────────────────────────────────────────
POST ${url}
Content-Type: application/json
X-API-Key: ${apiKey}

{
  "model": "${model}",
  "messages": [
    {"role": "user", "content": "Hello, Duino!"}
  ],
  "max_tokens": 256,
  "temperature": 0.7,
  "top_p": 0.95,
  "stream": false,
  "session_id": null
}

# ── List Models ────────────────────────────────────────────
GET ${apiUrl}/v1/models
X-API-Key: ${apiKey}

# ── Create Session ─────────────────────────────────────────
POST ${apiUrl}/v1/sessions
X-API-Key: ${apiKey}
{"model_id": "${model}"}

# ── Create API Key ─────────────────────────────────────────
POST ${apiUrl}/v1/keys
{"name": "my-project", "quota_tier": "free", "expires_in_hours": 90}

# ── List API Keys ──────────────────────────────────────────
GET ${apiUrl}/v1/keys
X-API-Key: ${apiKey}

# ── URL Expiry ─────────────────────────────────────────────
GET ${apiUrl}/v1/url/expiry

# ── Health ─────────────────────────────────────────────────
GET ${apiUrl}/v1/health`

    default: return '// Select a language'
  }
}

// ─── APIKeysPage component ────────────────────────────────────────────────────

export default function APIKeysPage({ apiUrl, initialApiKey }: { apiUrl: string, initialApiKey: string }) {
  const [keys, setKeys]       = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [error, setError]     = useState('')
  const [newKey, setNewKey]   = useState<string | null>(null)
  const [copied, setCopied]   = useState('')
  const [activeLang, setActiveLang] = useState('curl')
  const [urlExpiry, setUrlExpiry]   = useState<any>(null)

  const [form, setForm] = useState({
    name: '',
    quota_tier: 'free',
    expires_in_hours: 90,
    projects: '',
    description: '',
  })

  const authKey = initialApiKey

  const fetchKeys = useCallback(async () => {
    if (!apiUrl || !authKey) return
    setLoading(true)
    try {
      const r = await fetch(\`\${apiUrl}/v1/keys\`, {
        headers: { 'X-API-Key': authKey },
      })
      const d = await r.json()
      setKeys(d.keys || [])
    } catch (e: any) {
      setError('Failed to load keys: ' + e.message)
    } finally {
      setLoading(false)
    }
  }, [apiUrl, authKey])

  const fetchExpiry = useCallback(async () => {
    if (!apiUrl) return
    try {
      const r = await fetch(\`\${apiUrl}/v1/url/expiry\`)
      setUrlExpiry(await r.json())
    } catch {}
  }, [apiUrl])

  useEffect(() => {
    fetchKeys()
    fetchExpiry()
  }, [fetchKeys, fetchExpiry])

  const createKey = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreating(true)
    setError('')
    try {
      const r = await fetch(\`\${apiUrl}/v1/keys\`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.detail || 'Creation failed')
      setNewKey(d.key)
      setForm({ ...form, name: '' })
      fetchKeys()
    } catch (e: any) {
      setError(e.message)
    } finally {
      setCreating(false)
    }
  }

  const revokeKey = async (keyId: string) => {
    try {
      const r = await fetch(\`\${apiUrl}/v1/keys/\${keyId}\`, {
        method: 'DELETE',
        headers: { 'X-API-Key': authKey },
      })
      if (!r.ok) throw new Error('Revoke failed')
      fetchKeys()
    } catch (e: any) {
      setError(e.message)
    }
  }

  const copy = (txt: string, label: string) => {
    navigator.clipboard.writeText(txt)
    setCopied(label)
    setTimeout(() => setCopied(''), 2000)
  }

  return (
    <div className="flex flex-col gap-10">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-bone mb-3">Provisioning</h1>
          <p className="text-mist font-normal">Manage authentication tokens and integration parameters.</p>
        </div>
        {urlExpiry && (
          <div className="flex items-center gap-3 border border-slate px-4 py-2 rounded-[4px] bg-ink">
            <span className={\`text-[10px] font-semibold uppercase tracking-[0.08em] \${urlExpiry.is_expired ? 'text-crimson' : 'text-mist'}\`}>
              {urlExpiry.is_expired ? 'URL_EXPIRED' : 'TTL_GATEWAY'}
            </span>
            <span className="text-sm font-mono text-bone tracking-tighter">{urlExpiry.expires_in}</span>
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 bg-ink border-l-2 border-crimson text-[14px] text-bone">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 items-start">
        {/* Create Key */}
        <Card className="bg-ink border-slate rounded-[6px] shadow-none h-full">
          <CardHeader className="border-b border-slate/50 pb-6">
            <CardTitle className="text-xs font-semibold text-mist uppercase tracking-[0.08em]">Generate Token</CardTitle>
          </CardHeader>
          <CardContent className="pt-8">
            <form onSubmit={createKey} className="space-y-8">
              <div className="space-y-3">
                <label className="text-[10px] font-semibold text-mist uppercase tracking-[0.08em]">Identification</label>
                <Input 
                  value={form.name} 
                  onChange={e => setForm({ ...form, name: e.target.value })} 
                  placeholder="e.g. production-gateway-01" 
                  required
                  className="bg-void border-slate rounded-[4px] h-11 text-bone placeholder:text-mist/30"
                />
              </div>
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-3">
                  <label className="text-[10px] font-semibold text-mist uppercase tracking-[0.08em]">Quota tier</label>
                  <select 
                    value={form.quota_tier}
                    onChange={e => setForm({ ...form, quota_tier: e.target.value })}
                    className="w-full bg-void border border-slate rounded-[4px] h-11 px-3 text-sm text-bone focus:ring-2 focus:ring-violet outline-none"
                  >
                    <option value="free">Standard (Free)</option>
                    <option value="pro">Pro (Pay-per-token)</option>
                    <option value="enterprise">Unlimited</option>
                  </select>
                </div>
                <div className="space-y-3">
                  <label className="text-[10px] font-semibold text-mist uppercase tracking-[0.08em]">TTL (Hours)</label>
                  <Input 
                    type="number"
                    value={form.expires_in_hours} 
                    onChange={e => setForm({ ...form, expires_in_hours: parseInt(e.target.value) })} 
                    className="bg-void border-slate rounded-[4px] h-11 text-bone"
                  />
                </div>
              </div>
              <Button type="submit" disabled={creating} className="w-full h-11 bg-bone text-void hover:bg-bone/90 font-semibold text-xs uppercase tracking-widest rounded-[4px]">
                {creating ? 'Generating...' : 'Create token'}
              </Button>
            </form>

            {newKey && (
              <div className="mt-10 p-6 bg-void border border-violet/30 rounded-none animate-in fade-in slide-in-from-top-2 duration-300">
                <p className="text-[10px] font-semibold text-mist uppercase tracking-[0.08em] mb-4">Secret key provisioned</p>
                <div className="flex gap-3">
                  <Input readOnly value={newKey} className="font-mono text-xs bg-void border-slate text-violet h-10" />
                  <Button variant="secondary" className="h-10 bg-slate/20 border-slate text-bone" onClick={() => copy(newKey, 'new')}>
                    {copied === 'new' ? 'Copied' : 'Copy'}
                  </Button>
                </div>
                <p className="text-[10px] text-mist mt-4 italic leading-relaxed">
                  Store this token securely. It will not be displayed again.
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Integration */}
        <Card className="bg-ink border-slate rounded-[6px] shadow-none h-full flex flex-col">
          <CardHeader className="border-b border-slate/50 pb-4">
            <div className="flex flex-wrap gap-1">
              {LANGS.map(l => (
                <button 
                  key={l.id}
                  onClick={() => setActiveLang(l.id)}
                  className={\`px-3 py-1.5 text-[10px] font-semibold uppercase tracking-widest transition-colors rounded-[2px] \${
                    activeLang === l.id ? 'bg-bone text-void' : 'text-mist hover:text-bone hover:bg-slate/30'
                  }\`}
                >
                  {l.label}
                </button>
              ))}
            </div>
          </CardHeader>
          <CardContent className="p-0 flex-1 relative">
            <div className="absolute top-4 right-4 z-10">
              <Button variant="secondary" size="sm" className="h-8 bg-slate/50 border border-slate/50 text-bone text-[10px] uppercase tracking-widest" onClick={() => copy(getCodeSnippet(activeLang, apiUrl, initialApiKey), 'code')}>
                {copied === 'code' ? 'Copied' : 'Copy block'}
              </Button>
            </div>
            <pre className="p-8 bg-void h-full text-[13px] font-mono leading-relaxed overflow-auto text-mist prose-code:text-violet selection:bg-violet/30">
              <code>{getCodeSnippet(activeLang, apiUrl, initialApiKey)}</code>
            </pre>
          </CardContent>
        </Card>
      </div>

      {/* Keys Table */}
      <Card className="bg-ink border-slate rounded-[6px] shadow-none overflow-hidden">
        <CardHeader className="border-b border-slate/50 pb-6">
          <CardTitle className="text-xs font-semibold text-mist uppercase tracking-[0.08em]">Active tokens</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-12 flex items-center justify-center gap-3">
              <div className="size-4 bg-mist animate-pulse rounded-full" />
              <span className="text-xs font-semibold text-mist uppercase tracking-widest">Querying database...</span>
            </div>
          ) : keys.length === 0 ? (
            <p className="text-mist text-sm p-12 text-center">No active authentication tokens discovered.</p>
          ) : (
            <div className="overflow-x-auto">
              <Table className="rounded-none border-none">
                <TableHeader className="bg-void">
                  <TableRow className="border-slate hover:bg-transparent">
                    <TableHead className="text-[10px] font-semibold uppercase tracking-[0.08em] text-mist py-4">Descriptor</TableHead>
                    <TableHead className="text-[10px] font-semibold uppercase tracking-[0.08em] text-mist py-4">Provisioned</TableHead>
                    <TableHead className="text-[10px] font-semibold uppercase tracking-[0.08em] text-mist py-4">Expiration</TableHead>
                    <TableHead className="text-[10px] font-semibold uppercase tracking-[0.08em] text-mist py-4">State</TableHead>
                    <TableHead className="text-[10px] font-semibold uppercase tracking-[0.08em] text-mist py-4 text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {keys.map(k => {
                    const fmt = (d: string) => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
                    return (
                      <TableRow key={k.key_id} className="border-slate hover:bg-slate/10 transition-colors">
                        <TableCell className="py-4">
                          <div className="flex flex-col gap-1">
                            <span className="font-semibold text-sm text-bone">{k.name}</span>
                            <span className="font-mono text-[11px] text-mist tracking-tighter uppercase">{k.key_id}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-mist text-[13px] py-4">{fmt(k.created_at)}</TableCell>
                        <TableCell className="py-4">
                          <span className={\`text-[13px] font-mono \${k.is_expired ? 'text-crimson' : 'text-bone'}\`}>
                            {k.expires_in}
                          </span>
                        </TableCell>
                        <TableCell className="py-4">
                          <span className={\`text-[11px] font-semibold uppercase tracking-tight \${k.is_active && !k.is_expired ? 'text-bone' : 'text-mist'}\`}>
                            {k.is_active && !k.is_expired ? 'Active' : 'Inactive'}
                          </span>
                        </TableCell>
                        <TableCell className="text-right py-4">
                          <Button variant="ghost" className="h-8 px-4 text-[11px] uppercase tracking-widest rounded-[4px] text-crimson hover:bg-crimson/10 hover:text-crimson transition-colors" onClick={() => revokeKey(k.key_id)}>
                            Revoke token
                          </Button>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
