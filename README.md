# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  Duino API — README                                                    ║
# ╚══════════════════════════════════════════════════════════════════════════╝

# Duino API — Hyperscale Inference Platform

> **Cloud-agnostic · Gemma 4 · Secure HTTPS APIs · React-in-Notebooks**

---

## ⚡ One-Command Deploy (any environment)

```bash
pip install -e ".[inference]"
duinobot deploy --model gemma-4-2b
```

The CLI auto-detects your environment (Colab, Kaggle, Lightning AI, AWS, Jupyter, bare-metal),
loads the optimal quantized model, starts the API, launches the React UI, and
returns a public HTTPS URL you can share or embed immediately.

---

## 🗂️ Project Structure

```
Duin_Inference/
├── duino_api/
│   ├── config.py              ← Settings from env vars
│   ├── adapters/
│   │   └── detector.py        ← Runtime auto-detection (Colab/Kaggle/Lightning/AWS/Jupyter)
│   ├── auth/
│   │   ├── keys.py            ← API key generation, hashing, validation
│   │   └── quota.py           ← Sliding-window rate limiter
│   ├── sessions/
│   │   └── manager.py         ← Distributed session store (Redis / in-memory)
│   ├── inference/
│   │   └── engine.py          ← Gemma 4 model serving (vLLM / transformers)
│   ├── gateway/
│   │   └── app.py             ← FastAPI gateway (all routes)
│   └── cli/
│       └── main.py            ← Typer CLI (deploy/serve/generate-ui/keys/status)
├── ui/
│   ├── src/
│   │   ├── App.jsx            ← React chat UI with streaming
│   │   └── index.css          ← Dark-mode design system
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── docker/
│   ├── Dockerfile             ← GPU-enabled image
│   └── docker-compose.yml     ← Full stack (gateway + Redis + UI)
├── notebooks/
│   ├── colab_quickstart.py    ← Google Colab step-by-step
│   └── universal_quickstart.py ← Kaggle / Jupyter / Lightning AI
├── .env.example
└── pyproject.toml
```

---

## 🔑 API Reference

All endpoints require `X-API-Key` header.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/chat/completions` | OpenAI-compatible inference (streaming ✅) |
| GET  | `/v1/models` | List available models |
| POST | `/v1/sessions` | Create session |
| GET  | `/v1/sessions/{id}` | Retrieve session + history |
| DELETE | `/v1/sessions/{id}` | Delete session |
| POST | `/v1/keys` | Create API key |
| GET  | `/v1/health` | Platform health + GPU info |

---

## 🌐 Supported Environments

| Environment | Tunnel | GPU | Storage |
|-------------|--------|-----|---------|
| Google Colab | Native proxy | T4/A100 | ❌ (ephemeral) |
| Kaggle | ngrok | P100/T4 | ✅ |
| Lightning AI | Native proxy | A10G | ✅ |
| AWS SageMaker | Native | Any | ✅ |
| Jupyter (local) | ngrok | Any | ✅ |
| Docker / Bare metal | Cloudflare Tunnel | Any | ✅ |

---

## ⚛️ Running React inside Notebooks

**Method 1 — Vite (recommended):**
```python
import subprocess, threading
threading.Thread(
    target=lambda: subprocess.run(
        ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"],
        cwd="ui"
    ), daemon=True
).start()
```

**Method 2 — New project from scratch:**
```bash
!npm create vite@latest my-app -- --template react
%cd my-app && npm install && npm run dev -- --host &
```

**Method 3 — Inline CDN React (no build):**
```python
from IPython.display import HTML
HTML('<script src="https://unpkg.com/react@19/umd/react.production.min.js"></script>...')
```

---

## 🐳 Docker Deploy

```bash
cd docker
cp ../.env.example ../.env  # fill in HF_TOKEN, NGROK_AUTHTOKEN
docker compose up --build
```

---

## 📊 Quota Tiers

| Tier | RPM | Daily | Max Tokens |
|------|-----|-------|------------|
| free | 10 | 500 | 512 |
| pro | 60 | 10,000 | 4,096 |
| enterprise | 300 | 100,000 | 8,192 |

---

## 🔒 Security

- API keys are **SHA-256 hashed** — raw keys never stored
- All sessions are **owner-isolated** — cross-tenant access blocked
- Rate limiting enforced at gateway level (sliding window)
- HTTPS enforced via tunnel (ngrok / Cloudflare / native proxies)
- Notebook cell output automatically redacts tokens

---

## License
MIT © Duino API
