import { useState, useEffect, useCallback } from 'react'

const LANGS = [
  { id: 'curl',       label: 'cURL',       icon: '🔗' },
  { id: 'python',     label: 'Python',     icon: '🐍' },
  { id: 'typescript', label: 'TypeScript', icon: '🟦' },
  { id: 'java',       label: 'Java',       icon: '☕' },
  { id: 'go',         label: 'Go',         icon: '🐹' },
  { id: 'dotnet',     label: '.NET / C#',  icon: '🟣' },
  { id: 'rest',       label: 'REST',       icon: '🌐' },
]

function getCodeSnippet(lang, apiUrl, apiKey, model = 'gemma-4-2b') {
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

export default function APIKeysPage({ apiUrl, initialApiKey }) {
  const [keys, setKeys]       = useState([])
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [error, setError]     = useState('')
  const [newKey, setNewKey]   = useState(null)    // revealed once after creation
  const [copied, setCopied]   = useState('')
  const [activeLang, setActiveLang] = useState('curl')
  const [urlExpiry, setUrlExpiry]   = useState(null)

  // Form state
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
    } catch (e) {
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
          name: form.name || 'My Key',
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
    } catch (e) {
      setError('Create failed: ' + e.message)
    } finally {
      setCreating(false)
    }
  }

  const revokeKey = async (keyId) => {
    if (!confirm('Revoke this key? It will stop working immediately.')) return
    try {
      await fetch(`${apiUrl}/v1/keys/${keyId}`, {
        method: 'DELETE',
        headers: { 'X-API-Key': authKey },
      })
      await fetchKeys()
    } catch (e) {
      setError('Revoke failed: ' + e.message)
    }
  }

  const copy = (text, label) => {
    navigator.clipboard.writeText(text)
    setCopied(label)
    setTimeout(() => setCopied(''), 2000)
  }

  const fmt = (ts) => ts ? new Date(ts * 1000).toLocaleString() : '—'
  const tierColor = (t) => ({ free: '#10b981', pro: '#6366f1', enterprise: '#f59e0b' }[t] || '#666')

  return (
    <div style={styles.page}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>🔑 API Keys</h1>
          <p style={styles.subtitle}>
            Generate unlimited keys — works with Python, TypeScript, Go, Java, .NET, curl and REST
          </p>
        </div>
        {urlExpiry && (
          <div style={styles.expiryBadge}>
            <span style={{ color: urlExpiry.is_expired ? '#f87171' : '#34d399' }}>
              {urlExpiry.is_expired ? '⚠️ URL Expired' : '⏱ URL expires in'}
            </span>
            <strong style={{ color: '#fff', marginLeft: 6 }}>
              {urlExpiry.expires_in}
            </strong>
          </div>
        )}
      </div>

      {error && <div style={styles.error}>{error}</div>}

      {/* New key revealed */}
      {newKey && (
        <div style={styles.newKeyBox}>
          <div style={styles.newKeyTitle}>✅ New API Key Created — Copy it now, it won't be shown again</div>
          <div style={styles.newKeyRow}>
            <code style={styles.keyCode}>{newKey}</code>
            <button style={styles.copyBtn} onClick={() => copy(newKey, 'new')}>
              {copied === 'new' ? '✅ Copied!' : '📋 Copy'}
            </button>
          </div>
        </div>
      )}

      {/* Create form */}
      <div style={styles.card}>
        <h2 style={styles.cardTitle}>➕ Create New Key</h2>
        <div style={styles.formGrid}>
          <label style={styles.label}>
            Name
            <input style={styles.input} placeholder="my-project-key"
              value={form.name} onChange={e => setForm({...form, name: e.target.value})} />
          </label>
          <label style={styles.label}>
            Tier
            <select style={styles.input} value={form.quota_tier}
              onChange={e => setForm({...form, quota_tier: e.target.value})}>
              <option value="free">Free</option>
              <option value="pro">Pro</option>
              <option value="enterprise">Enterprise</option>
            </select>
          </label>
          <label style={styles.label}>
            Expires in (hours)
            <input style={styles.input} type="number" min="1" max="8760"
              value={form.expires_in_hours}
              onChange={e => setForm({...form, expires_in_hours: e.target.value})} />
          </label>
          <label style={styles.label}>
            Projects (comma-separated)
            <input style={styles.input} placeholder="web-app, mobile, backend"
              value={form.projects} onChange={e => setForm({...form, projects: e.target.value})} />
          </label>
        </div>
        <label style={{...styles.label, marginTop: 8}}>
          Description
          <input style={styles.input} placeholder="What is this key for?"
            value={form.description} onChange={e => setForm({...form, description: e.target.value})} />
        </label>
        <button style={styles.createBtn} onClick={createKey} disabled={creating}>
          {creating ? '⏳ Creating…' : '🔑 Generate API Key'}
        </button>
      </div>

      {/* Code snippets */}
      <div style={styles.card}>
        <h2 style={styles.cardTitle}>📖 Code Examples</h2>
        <div style={styles.langTabs}>
          {LANGS.map(l => (
            <button key={l.id} onClick={() => setActiveLang(l.id)}
              style={{...styles.langTab, ...(activeLang === l.id ? styles.langTabActive : {})}}>
              {l.icon} {l.label}
            </button>
          ))}
        </div>
        <div style={styles.codeBlock}>
          <button style={styles.codeCopyBtn}
            onClick={() => copy(getCodeSnippet(activeLang, apiUrl, authKey), activeLang)}>
            {copied === activeLang ? '✅ Copied!' : '📋 Copy Code'}
          </button>
          <pre style={styles.pre}>
            <code>{getCodeSnippet(activeLang, apiUrl, authKey)}</code>
          </pre>
        </div>
      </div>

      {/* Keys table */}
      <div style={styles.card}>
        <div style={styles.tableHeader}>
          <h2 style={styles.cardTitle}>🗂 Your API Keys ({keys.length})</h2>
          <button style={styles.refreshBtn} onClick={fetchKeys} disabled={loading}>
            {loading ? '⏳' : '🔄 Refresh'}
          </button>
        </div>
        {keys.length === 0 ? (
          <p style={{ color: '#6b7280', padding: '20px 0' }}>No keys yet — create one above.</p>
        ) : (
          <div style={styles.tableWrap}>
            <table style={styles.table}>
              <thead>
                <tr>
                  {['Name', 'Tier', 'Projects', 'Created', 'Expires', 'Uses', 'Status', ''].map(h => (
                    <th key={h} style={styles.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {keys.map(k => (
                  <tr key={k.key_id} style={styles.tr}>
                    <td style={styles.td}>
                      <strong>{k.name}</strong>
                      {k.description && <div style={styles.desc}>{k.description}</div>}
                      <div style={styles.keyId}>
                        <code style={styles.keyIdCode}>{k.key_id.slice(0,8)}…</code>
                      </div>
                    </td>
                    <td style={styles.td}>
                      <span style={{...styles.tier, background: tierColor(k.quota_tier) + '22',
                                    color: tierColor(k.quota_tier)}}>
                        {k.quota_tier}
                      </span>
                    </td>
                    <td style={styles.td}>
                      {(k.projects || []).map(p => (
                        <span key={p} style={styles.tag}>{p}</span>
                      ))}
                    </td>
                    <td style={styles.td}>{fmt(k.created_at)}</td>
                    <td style={styles.td}>
                      <span style={{ color: k.is_expired ? '#f87171' : '#34d399' }}>
                        {k.expires_in}
                      </span>
                    </td>
                    <td style={styles.td}>{k.usage_count ?? 0}</td>
                    <td style={styles.td}>
                      <span style={{
                        color: k.is_active && !k.is_expired ? '#34d399' : '#f87171',
                        fontWeight: 700,
                      }}>
                        {k.is_active && !k.is_expired ? '● Active' : '● Inactive'}
                      </span>
                    </td>
                    <td style={styles.td}>
                      <button style={styles.revokeBtn} onClick={() => revokeKey(k.key_id)}>
                        🗑 Revoke
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Styles ───────────────────────────────────────────────────────────────────
const styles = {
  page: { maxWidth: 1100, margin: '0 auto', padding: '24px 16px', fontFamily: 'Inter, sans-serif', color: '#f3f4f6' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24, flexWrap: 'wrap', gap: 12 },
  title: { margin: 0, fontSize: 28, fontWeight: 800, background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' },
  subtitle: { margin: '6px 0 0', color: '#9ca3af', fontSize: 14 },
  expiryBadge: { background: '#1f2937', border: '1px solid #374151', borderRadius: 10, padding: '10px 16px', fontSize: 14 },
  error: { background: '#7f1d1d', border: '1px solid #dc2626', borderRadius: 8, padding: '10px 16px', marginBottom: 16, color: '#fca5a5' },
  newKeyBox: { background: '#064e3b', border: '1px solid #10b981', borderRadius: 12, padding: 16, marginBottom: 20 },
  newKeyTitle: { color: '#34d399', fontWeight: 700, marginBottom: 10 },
  newKeyRow: { display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' },
  keyCode: { flex: 1, background: '#022c22', padding: '8px 12px', borderRadius: 8, fontSize: 13, color: '#6ee7b7', wordBreak: 'break-all', fontFamily: 'monospace' },
  copyBtn: { background: '#10b981', border: 'none', borderRadius: 8, padding: '8px 16px', color: '#fff', cursor: 'pointer', fontWeight: 600, whiteSpace: 'nowrap' },
  card: { background: '#111827', border: '1px solid #1f2937', borderRadius: 14, padding: '20px 24px', marginBottom: 20 },
  cardTitle: { margin: '0 0 16px', fontSize: 18, fontWeight: 700, color: '#e5e7eb' },
  formGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 },
  label: { display: 'flex', flexDirection: 'column', gap: 6, fontSize: 13, color: '#9ca3af', fontWeight: 600 },
  input: { background: '#1f2937', border: '1px solid #374151', borderRadius: 8, padding: '8px 12px', color: '#f3f4f6', fontSize: 14, outline: 'none' },
  createBtn: { marginTop: 16, background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', border: 'none', borderRadius: 10, padding: '11px 24px', color: '#fff', fontWeight: 700, fontSize: 15, cursor: 'pointer', width: '100%' },
  langTabs: { display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 },
  langTab: { background: '#1f2937', border: '1px solid #374151', borderRadius: 8, padding: '6px 14px', color: '#9ca3af', cursor: 'pointer', fontSize: 13, fontWeight: 600, transition: 'all .2s' },
  langTabActive: { background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', borderColor: '#6366f1', color: '#fff' },
  codeBlock: { position: 'relative', background: '#0d1117', borderRadius: 10, border: '1px solid #21262d' },
  codeCopyBtn: { position: 'absolute', top: 10, right: 10, background: '#30363d', border: '1px solid #484f58', borderRadius: 6, padding: '4px 12px', color: '#e6edf3', cursor: 'pointer', fontSize: 12, fontWeight: 600 },
  pre: { margin: 0, padding: '16px', overflowX: 'auto', fontSize: 12.5, lineHeight: 1.6, color: '#c9d1d9', fontFamily: '"Fira Code", "JetBrains Mono", monospace', whiteSpace: 'pre-wrap', wordBreak: 'break-word' },
  tableHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  refreshBtn: { background: '#1f2937', border: '1px solid #374151', borderRadius: 8, padding: '6px 14px', color: '#9ca3af', cursor: 'pointer', fontSize: 13 },
  tableWrap: { overflowX: 'auto' },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontSize: 12, fontWeight: 700, borderBottom: '1px solid #1f2937', whiteSpace: 'nowrap' },
  tr: { borderBottom: '1px solid #1a2234' },
  td: { padding: '12px 12px', fontSize: 13, verticalAlign: 'top' },
  desc: { color: '#6b7280', fontSize: 12, marginTop: 2 },
  keyId: { marginTop: 4 },
  keyIdCode: { background: '#1f2937', padding: '2px 6px', borderRadius: 4, fontSize: 11, color: '#6b7280', fontFamily: 'monospace' },
  tier: { borderRadius: 6, padding: '3px 8px', fontSize: 12, fontWeight: 700 },
  tag: { background: '#1e3a5f', color: '#60a5fa', borderRadius: 6, padding: '2px 8px', fontSize: 11, marginRight: 4, display: 'inline-block' },
  revokeBtn: { background: '#7f1d1d', border: '1px solid #dc2626', borderRadius: 6, padding: '4px 10px', color: '#fca5a5', cursor: 'pointer', fontSize: 12, fontWeight: 600 },
}
