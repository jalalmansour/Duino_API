# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  Duino API — Google Colab Quickstart                                   ║
# ║  Run each cell in order. React UI will open as an iframe below.        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

# ── Cell 1: Install ──────────────────────────────────────────────────────────
# %% [code]
"""
!pip install duino-api[inference] pyngrok -q
"""

# ── Cell 2: Deploy (API + React UI) ─────────────────────────────────────────
# %% [code]
"""
import os, threading, time, subprocess, sys

# Optional: set HuggingFace token for gated models
# os.environ["HF_TOKEN"] = "hf_xxx"

# Start the platform
proc = subprocess.Popen(
    [sys.executable, "-m", "duino_api.cli.main", "serve",
     "--model", "gemma-4-2b", "--port", "8000"],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
)
time.sleep(5)  # wait for model load

# Expose via Colab proxy
from google.colab.output import eval_js
api_url = eval_js("google.colab.kernel.proxyPort(8000)")
print(f"API URL: {api_url}")
"""

# ── Cell 3: Create API key ───────────────────────────────────────────────────
# %% [code]
"""
import requests

r = requests.post(f"{api_url}/v1/keys",
    json={"name": "colab-session", "quota_tier": "free"})
api_key = r.json()["api_key"]
print(f"API Key: {api_key}")
"""

# ── Cell 4: Test inference ───────────────────────────────────────────────────
# %% [code]
"""
r = requests.post(f"{api_url}/v1/chat/completions",
    headers={"X-API-Key": api_key},
    json={
        "model": "gemma-4-2b",
        "messages": [{"role": "user", "content": "What is the capital of France?"}],
        "max_tokens": 128,
    }
)
print(r.json()["choices"][0]["message"]["content"])
"""

# ── Cell 5: Launch React UI as iframe ────────────────────────────────────────
# %% [code]
"""
# Method A: Run the bundled UI via npm + Vite
import subprocess, threading, time

def start_ui():
    subprocess.run(
        ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"],
        cwd="/content/duino-api/ui", check=False
    )

threading.Thread(target=start_ui, daemon=True).start()
time.sleep(6)

from google.colab.output import eval_js
ui_url = eval_js("google.colab.kernel.proxyPort(3000)")

from IPython.display import HTML
HTML(f'''
<script>
  const frame = document.querySelector("#duino-frame");
  frame.addEventListener("load", () => {{
    frame.contentWindow.postMessage({{
      type: "duino-config",
      apiUrl: "{api_url}",
      apiKey: "{api_key}"
    }}, "*");
  }});
</script>
<iframe id="duino-frame"
  src="{ui_url}"
  width="100%"
  height="600"
  style="border:none;border-radius:14px;background:#0a0a0f;">
</iframe>
''')
"""

# ── Cell 6: Full React project inside Colab ──────────────────────────────────
# %% [code]
"""
# You can also scaffold a brand new React project and run it here:

# !npm create vite@latest my-react-app -- --template react
# %cd my-react-app
# !npm install
# !npm run dev -- --host 0.0.0.0 --port 4000 &

# import time; time.sleep(5)
# from google.colab.output import eval_js
# react_url = eval_js("google.colab.kernel.proxyPort(4000)")
# from IPython.display import IFrame
# IFrame(react_url, width="100%", height=600)
"""
