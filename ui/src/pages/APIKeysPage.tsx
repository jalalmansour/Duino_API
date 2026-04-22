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
# Duino API — cURL Example
export DUINO_API_KEY="${apiKey}"
export DUINO_API_URL="${apiUrl}"

curl -X POST "${url}" \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: $DUINO_API_KEY" \\
  -d '{
    "model": "${model}",
    "messages": [{"role": "user", "content": "Hello, Duino!"}],
    "max_tokens": 256,
    "stream": false
  }'

# Streaming
curl -X POST "${url}" \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: $DUINO_API_KEY" \\
  --no-buffer \\
  -d '{
    "model": "${model}",
    "messages": [{"role": "user", "content": "Write a poem."}],
    "max_tokens": 512,
    "stream": true
  }'`

    case 'python': return `import os
import requests

DUINO_API_KEY = "${apiKey}"
DUINO_API_URL = "${apiUrl}"

headers = {
    "Content-Type": "application/json",
    "X-API-Key": DUINO_API_KEY,
}

# ── Single request ──────────────────────────────────────
response = requests.post(
    f"{DUINO_API_URL}/v1/chat/completions",
    headers=headers,
    json={
        "model": "${model}",
        "messages": [{"role": "user", "content": "Hello, Duino!"}],
        "max_tokens": 256,
    },
)
print(response.json()["choices"][0]["message"]["content"])

# ── Streaming ──────────────────────────────────────────
import json

with requests.post(
    f"{DUINO_API_URL}/v1/chat/completions",
    headers=headers,
    json={
        "model": "${model}",
        "messages": [{"role": "user", "content": "Write a poem."}],
        "max_tokens": 512,
        "stream": True,
    },
    stream=True,
) as r:
    for line in r.iter_lines():
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

        String body = """
            {
              "model": "${model}",
              "messages": [{"role":"user","content":"Hello, Duino!"}],
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

    case 'rest': return `### Duino API — REST Reference

# Base URL
${apiUrl}

# Authentication
# All endpoints require the X-API-Key header:
X-API-Key: ${apiKey}

# ── Chat Completions ───────────────────────────────────────
POST ${apiUrl}/v1/chat/completions
Content-Type: application/json
X-API-Key: ${apiKey}

{
  "model": "${model}",
  "messages": [{"role": "user", "content": "Hello!"}],
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
      const r = await fetch(`${apiUrl}/v1/keys`, {
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

  const fetchUrlExpiry = useCallback(async () => {
    if (!apiUrl) return
    try {
      const r = await fetch(`${apiUrl}/v1/url/expiry`)
      const d = await r.json()
      setUrlExpiry(d)
    } catch (_) {}
  }, [apiUrl])

  useEffect(() => {
    fetchKeys()
    fetchUrlExpiry()
    const t = setInterval(fetchUrlExpiry, 60000)
    return () => clearInterval(t)
  }, [fetchKeys, fetchUrlExpiry])

  const createKey = async () => {
    setCreating(true)
    setError('')
    setNewKey(null)
    try {
      const r = await fetch(`${apiUrl}/v1/keys`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: form.name || 'my-project-key',
          quota_tier: form.quota_tier,
          expires_in_hours: Number(form.expires_in_hours),
          projects: form.projects.split(',').map(s => s.trim()).filter(Boolean),
          description: form.description,
        }),
      })
      const d = await r.json()
      setNewKey(d.api_key)
      setForm({ name: '', quota_tier: 'free', expires_in_hours: 90, projects: '', description: '' })
      await fetchKeys()
    } catch (e: any) {
      setError('Create failed: ' + e.message)
    } finally {
      setCreating(false)
    }
  }

  const revokeKey = async (keyId: string) => {
    if (!confirm('Revoke this key? It will cease functioning immediately.')) return
    try {
      await fetch(`${apiUrl}/v1/keys/${keyId}`, {
        method: 'DELETE',
        headers: { 'X-API-Key': authKey },
      })
      await fetchKeys()
    } catch (e: any) {
      setError('Revoke failed: ' + e.message)
    }
  }

  const copy = (text: string, label: string) => {
    navigator.clipboard.writeText(text)
    setCopied(label)
    setTimeout(() => setCopied(''), 2000)
  }

  const fmt = (ts: number) => ts ? new Date(ts * 1000).toLocaleString() : '—'

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">API Keys</h1>
          <p className="text-sm text-muted-foreground mt-2">
            Generate keys for programmatic access.
          </p>
        </div>
        {urlExpiry && (
          <div className="flex items-center gap-2 border border-border px-3 py-2 rounded">
            <span className={\`text-xs uppercase \${urlExpiry.is_expired ? 'text-destructive' : 'text-muted-foreground'}\`}>
              {urlExpiry.is_expired ? 'URL Expired' : 'URL Expires in'}
            </span>
            <span className="text-sm font-medium">{urlExpiry.expires_in}</span>
          </div>
        )}
      </div>

      {error && <div className="p-4 bg-card border-l-2 border-destructive text-sm text-foreground">{error}</div>}

      {newKey && (
        <div className="p-4 bg-card border-l-2 border-primary text-sm text-foreground flex justify-between items-center">
          <div>
            <div className="font-medium mb-2">Key generated. Copy hash now; it will not be displayed again.</div>
            <code className="font-mono bg-muted px-2 py-1 rounded text-xs">{newKey}</code>
          </div>
          <Button variant="outline" size="sm" onClick={() => copy(newKey, 'new')}>
            {copied === 'new' ? 'Copied' : 'Copy hash'}
          </Button>
        </div>
      )}

      {/* Create form */}
      <Card className="bg-card shadow-none">
        <CardHeader>
          <CardTitle className="text-base font-semibold">Create key</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Name</label>
              <Input placeholder="my-project-key" value={form.name} onChange={e => setForm({...form, name: e.target.value})} />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Tier</label>
              <select className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-base shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 md:text-sm" value={form.quota_tier} onChange={e => setForm({...form, quota_tier: e.target.value})}>
                <option value="free">Free</option>
                <option value="pro">Pro</option>
                <option value="enterprise">Enterprise</option>
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Expires in (hours)</label>
              <Input type="number" min="1" max="8760" value={form.expires_in_hours} onChange={e => setForm({...form, expires_in_hours: Number(e.target.value)})} />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Projects (comma-separated)</label>
              <Input placeholder="web-app, mobile" value={form.projects} onChange={e => setForm({...form, projects: e.target.value})} />
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Description</label>
            <Input placeholder="Internal tool integration" value={form.description} onChange={e => setForm({...form, description: e.target.value})} />
          </div>
          <div className="pt-2">
            <Button onClick={createKey} disabled={creating}>
              {creating ? 'Creating...' : 'Generate key'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Code snippets */}
      <Card className="bg-card shadow-none">
        <CardHeader>
          <CardTitle className="text-base font-semibold">Code examples</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2 flex-wrap mb-4">
            {LANGS.map(l => (
              <Button 
                key={l.id} 
                size="sm"
                variant={activeLang === l.id ? "secondary" : "ghost"}
                onClick={() => setActiveLang(l.id)}
              >
                {l.label}
              </Button>
            ))}
          </div>
          <div className="relative border border-border bg-background rounded-md">
            <Button 
              variant="outline" 
              size="sm" 
              className="absolute top-2 right-2 bg-card"
              onClick={() => copy(getCodeSnippet(activeLang, apiUrl, authKey), activeLang)}
            >
              {copied === activeLang ? 'Copied' : 'Copy code'}
            </Button>
            <pre className="p-4 overflow-x-auto text-xs font-mono text-foreground">
              <code>{getCodeSnippet(activeLang, apiUrl, authKey)}</code>
            </pre>
          </div>
        </CardContent>
      </Card>

      {/* Keys table */}
      <Card className="bg-card shadow-none">
        <CardHeader className="flex flex-row justify-between items-center">
          <CardTitle className="text-base font-semibold">Active keys ({keys.length})</CardTitle>
          <Button variant="ghost" size="sm" onClick={fetchKeys} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh data'}
          </Button>
        </CardHeader>
        <CardContent>
          {keys.length === 0 ? (
            <p className="text-muted-foreground text-sm py-4">No active keys.</p>
          ) : (
            <div className="rounded-md border border-border">
              <Table>
                <TableHeader className="bg-muted/50">
                  <TableRow>
                    {['Name', 'Tier', 'Projects', 'Created', 'Expires', 'Uses', 'Status', 'Actions'].map(h => (
                      <TableHead key={h} className="text-xs uppercase text-muted-foreground">{h}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {keys.map(k => (
                    <TableRow key={k.key_id} className="hover:bg-muted/50">
                      <TableCell>
                        <div className="font-medium text-foreground">{k.name}</div>
                        {k.description && <div className="text-xs text-muted-foreground my-1">{k.description}</div>}
                        <code className="text-xs font-mono bg-muted px-1 py-0.5 rounded text-muted-foreground">{k.key_id.slice(0,8)}...</code>
                      </TableCell>
                      <TableCell className="text-sm">{k.quota_tier}</TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {(k.projects || []).map((p: string) => (
                            <span key={p} className="text-[10px] px-1.5 py-0.5 border border-border font-mono text-muted-foreground rounded-sm">{p}</span>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">{fmt(k.created_at)}</TableCell>
                      <TableCell>
                        <span className={\`text-sm \${k.is_expired ? 'text-destructive' : 'text-foreground'}\`}>
                          {k.expires_in}
                        </span>
                      </TableCell>
                      <TableCell className="text-sm">{k.usage_count ?? 0}</TableCell>
                      <TableCell>
                        <span className={\`text-sm \${k.is_active && !k.is_expired ? 'text-foreground' : 'text-muted-foreground'}\`}>
                          {k.is_active && !k.is_expired ? 'Active' : 'Inactive'}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Button variant="destructive" size="sm" onClick={() => revokeKey(k.key_id)}>
                          Revoke
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
