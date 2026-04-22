# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  Duino API — Kaggle / Jupyter / Lightning AI Quickstart                ║
# ╚══════════════════════════════════════════════════════════════════════════╝

# ── Cell 1: Install ──────────────────────────────────────────────────────────
"""
!pip install duino-api[inference] pyngrok -q
"""

# ── Cell 2: Auto-detect environment and deploy ───────────────────────────────
"""
from duino_api.adapters.detector import EnvironmentDetector
import subprocess, sys, threading, time

adapter = EnvironmentDetector.get()
caps    = adapter.capabilities()

print(f"Environment : {caps.runtime.value}")
print(f"GPU         : {caps.gpu_name} ({caps.gpu_vram_mb} MB VRAM)")
print(f"Quantise    : {caps.recommended_quant or 'none (full precision)'}")

# Start server
def _serve():
    subprocess.run([sys.executable, "-m", "uvicorn",
                    "duino_api.gateway.app:app",
                    "--host", "0.0.0.0", "--port", "8000"], check=False)

threading.Thread(target=_serve, daemon=True).start()
time.sleep(6)
print("Server started.")
"""

# ── Cell 3: Expose publicly ──────────────────────────────────────────────────
"""
from duino_api.adapters.detector import EnvironmentDetector
adapter = EnvironmentDetector.get()

api_url = adapter.expose_port(8000)
print(f"Public API: {api_url}")
"""

# ── Cell 4: Create API key + test ────────────────────────────────────────────
"""
import requests

r = requests.post(f"http://localhost:8000/v1/keys",
    json={"name": "notebook-key", "quota_tier": "free"})
api_key = r.json()["api_key"]
print(f"API Key: {api_key}")

# Quick test
resp = requests.post("http://localhost:8000/v1/chat/completions",
    headers={"X-API-Key": api_key},
    json={
        "model": "gemma-4-2b",
        "messages": [{"role": "user", "content": "Hello, Gemma!"}],
    })
print(resp.json()["choices"][0]["message"]["content"])
"""

# ── Cell 5: Embed React UI as iframe ─────────────────────────────────────────
"""
import subprocess, threading, time
from IPython.display import HTML

def _ui():
    subprocess.run(
        ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"],
        cwd="ui", check=False,
    )

threading.Thread(target=_ui, daemon=True).start()
time.sleep(5)

ui_url = adapter.expose_port(3000)

HTML(f\"\"\"
<script>
  document.querySelector("#df").addEventListener("load", () => {{
    document.querySelector("#df").contentWindow.postMessage({{
      type: "duino-config", apiUrl: "{api_url}", apiKey: "{api_key}"
    }}, "*");
  }});
</script>
<iframe id="df" src="{ui_url}"
  width="100%" height="620"
  style="border:none;border-radius:14px;">
</iframe>
\"\"\")
"""

# ── Cell 6: Run any React project inside the notebook ───────────────────────
"""
# Create and run a fresh Vite+React project:
# !npm create vite@latest my-app -- --template react-ts
# %cd my-app
# !npm install
# !npm run dev -- --host 0.0.0.0 --port 4000 &

# import time; time.sleep(5)
# react_public = adapter.expose_port(4000)
# from IPython.display import IFrame
# IFrame(react_public, width="100%", height=600)

# ── For Next.js: ──────────────────────────────────────────────────────────
# !npx create-next-app@latest my-next --ts --no-git
# %cd my-next
# !npm install
# !npm run dev -- -p 4000 &
"""
