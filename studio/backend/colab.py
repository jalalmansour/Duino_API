"""
Duino API — studio/backend/colab.py
The start() function: one call to launch the full platform inside any notebook.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path


# ─── Repository root (two levels up: studio/backend/colab.py → repo root) ─────
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

API_PORT = 8000
UI_PORT  = 3000

# Log file for debugging server startup
SERVER_LOG = "/tmp/duino_api_server.log"


def start(
    model: str        = "gemma-4-2b",
    api_port: int     = API_PORT,
    ui_port: int      = UI_PORT,
    expose: bool      = True,
    hf_token: str     | None = None,
    ngrok_token: str  | None = None,
) -> dict[str, str]:
    """
    One-call platform launcher for any notebook environment.

    Returns:
        api_url    — public HTTPS API URL
        ui_url     — public HTTPS React UI URL
        api_key    — auto-generated API key
        embed_html — ready-to-use <iframe> HTML string
    """
    try:
        from rich.console import Console
        console = Console()
    except ImportError:
        # Rich may not be installed yet — use plain print
        class _Console:
            def print(self, msg, *a, **kw):
                import re
                builtins_print = __builtins__["print"] if isinstance(__builtins__, dict) else __import__("builtins").print
                builtins_print(re.sub(r"\[.*?\]", "", msg))
        console = _Console()

    console.print("\n[bold cyan]⚡ Duino API — Starting...[/]")

    # ── 1. Inject tokens ──────────────────────────────────────────────────────
    if hf_token:
        os.environ["HF_TOKEN"] = hf_token
    if ngrok_token:
        os.environ["NGROK_AUTHTOKEN"] = ngrok_token
    _try_colab_secrets()

    os.environ["DEFAULT_MODEL"]  = model
    os.environ["DUINO_PORT"]     = str(api_port)
    os.environ["UI_PORT"]        = str(ui_port)

    # ── 2. Install all dependencies inline (CRITICAL — must happen first) ─────
    console.print("  [yellow]Installing/verifying dependencies...[/]")
    _ensure_dependencies()
    console.print("  [green]Dependencies OK[/]")

    # ── 3. Detect environment ─────────────────────────────────────────────────
    from duino_api.adapters.detector import EnvironmentDetector
    adapter = EnvironmentDetector.get()
    caps    = adapter.capabilities()
    console.print(f"  Environment : [cyan]{caps.runtime.value}[/]")
    console.print(f"  GPU         : [cyan]{caps.gpu_name}[/] ({caps.gpu_vram_mb} MB)")
    console.print(f"  Quantize    : [cyan]{caps.recommended_quant or 'none (full precision)'}[/]")

    # ── 4. Start API server ───────────────────────────────────────────────────
    console.print("  [yellow]Starting API server...[/]")
    _start_api(api_port)

    # Wait with visible progress
    started = _wait_for_api(api_port, timeout=90)
    if not started:
        # Show logs to help diagnose
        _show_server_log()
        raise RuntimeError(
            f"API server failed to start on port {api_port}. "
            f"Check /tmp/duino_api_server.log for details."
        )
    console.print("  [green]API server ready[/]")

    # ── 5. Create API key ─────────────────────────────────────────────────────
    api_key = _create_key(api_port)
    console.print(f"  API Key  : [bold green]{api_key}[/]")

    # ── 6. Expose via HTTPS tunnel ────────────────────────────────────────────
    api_url = f"http://localhost:{api_port}"
    if expose:
        try:
            api_url = adapter.expose_port(api_port)
            console.print(f"  API URL  : [bold cyan]{api_url}[/]")
        except Exception as exc:
            console.print(f"  [yellow]Tunnel failed ({exc}). Using Colab proxy...[/]")
            api_url = _colab_proxy_url(api_port) or f"http://localhost:{api_port}"
            console.print(f"  API URL  : [bold cyan]{api_url}[/]")

    # ── 7. React UI ───────────────────────────────────────────────────────────
    ui_url = _start_ui(ui_port, api_url=api_url, adapter=adapter, expose=expose)
    console.print(f"  UI URL   : [bold cyan]{ui_url}[/]")

    embed_html = (
        f'<script>'
        f'(function(){{var f=document.getElementById("duino-iframe");'
        f'if(f)f.addEventListener("load",function(){{'
        f'f.contentWindow.postMessage({{'
        f'type:"duino-config",apiUrl:"{api_url}",apiKey:"{api_key}"'
        f'}},"*");}});}})();</script>'
        f'<iframe id="duino-iframe" src="{ui_url}" width="100%" height="700" '
        f'style="border:none;border-radius:14px;background:#0a0a0f;">'
        f'</iframe>'
    )

    console.print("\n[bold green]✅ Duino API is live![/]")
    console.print(f"  Docs: {api_url}/docs")
    console.print(f"  Embed: <iframe src=\"{ui_url}\" width=\"100%\" height=\"700\">")

    return {
        "api_url":    api_url,
        "ui_url":     ui_url,
        "api_key":    api_key,
        "embed_html": embed_html,
    }


# ─── Dependency installer (runs before everything else) ──────────────────────

def _find_pip() -> list[str]:
    """Return a pip command as a list, usable with subprocess.run()."""
    # Prefer standalone pip executables (always works on Colab)
    for exe in ["pip3", "pip"]:
        try:
            r = subprocess.run([exe, "--version"], capture_output=True, timeout=5)
            if r.returncode == 0:
                return [exe]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    # Fallback: python -m pip
    for py in [sys.executable, "python3", "python"]:
        try:
            r = subprocess.run([py, "-m", "pip", "--version"],
                               capture_output=True, timeout=5)
            if r.returncode == 0:
                return [py, "-m", "pip"]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    raise RuntimeError("Cannot find pip. Run: curl https://bootstrap.pypa.io/get-pip.py | python3")


def _ensure_dependencies() -> None:
    """Install requirements if not already satisfied."""
    pip = _find_pip()

    def _pip(*args):
        subprocess.run([*pip, *args], check=True, capture_output=True)

    # Core requirements
    req = REPO_ROOT / "requirements.txt"
    if req.exists():
        _pip("install", "-r", str(req), "-q", "--no-warn-script-location")

    # Install the package itself in editable mode
    _pip("install", "-e", str(REPO_ROOT), "-q", "--no-warn-script-location")

    # GPU inference deps
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=name",
                                  "--format=csv,noheader"],
                                 capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            req_inf = REPO_ROOT / "requirements-inference.txt"
            if req_inf.exists():
                _pip("install", "-r", str(req_inf), "-q", "--no-warn-script-location")
    except Exception:
        pass


# ─── API server ───────────────────────────────────────────────────────────────

def _start_api(port: int) -> None:
    def _run():
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        with open(SERVER_LOG, "w") as log:
            subprocess.run(
                [sys.executable, "-m", "uvicorn",
                 "duino_api.gateway.app:app",
                 "--host", "0.0.0.0",
                 "--port", str(port),
                 "--no-access-log"],
                cwd=str(REPO_ROOT),
                env=env,
                stdout=log,
                stderr=log,
            )
    threading.Thread(target=_run, daemon=True).start()


def _wait_for_api(port: int, timeout: int = 90) -> bool:
    """Return True if API came up, False on timeout."""
    import urllib.request, urllib.error
    deadline = time.time() + timeout
    dot_every = 5
    last_dot  = time.time()
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://localhost:{port}/v1/health", timeout=3)
            print()  # newline after dots
            return True
        except Exception:
            if time.time() - last_dot > dot_every:
                print("  ⏳ waiting for API...", flush=True)
                last_dot = time.time()
            time.sleep(2)
    print()
    return False


def _show_server_log() -> None:
    """Print the last 30 lines of the server log to help diagnose failures."""
    try:
        with open(SERVER_LOG) as f:
            lines = f.readlines()
        print("\n── Server log (last 30 lines) ──")
        for line in lines[-30:]:
            print(line, end="")
        print("────────────────────────────────")
    except Exception:
        pass


# ─── Key creation ─────────────────────────────────────────────────────────────

def _create_key(port: int) -> str:
    import json, urllib.request
    body = json.dumps({"name": "notebook-auto", "quota_tier": "free"}).encode()
    req  = urllib.request.Request(
        f"http://localhost:{port}/v1/keys",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())["api_key"]
    except Exception as exc:
        print(f"  ⚠️  Key creation failed: {exc}")
        return "key-unavailable"


# ─── React UI ─────────────────────────────────────────────────────────────────

def _start_ui(port: int, api_url: str, adapter, expose: bool) -> str:
    ui_dir   = REPO_ROOT / "ui"
    dist_dir = ui_dir / "dist"

    if not ui_dir.exists():
        return f"http://localhost:{port}"

    def _npm_dev():
        env = os.environ.copy()
        env["VITE_API_URL"] = api_url
        subprocess.run(
            ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", str(port)],
            cwd=str(ui_dir), env=env, check=False,
        )

    def _http_serve():
        subprocess.run(
            [sys.executable, "-m", "http.server", str(port),
             "--directory", str(dist_dir)],
            check=False,
        )

    if dist_dir.exists():
        threading.Thread(target=_http_serve, daemon=True).start()
        time.sleep(2)
    elif (ui_dir / "package.json").exists() and _node_available():
        if not (ui_dir / "node_modules").exists():
            subprocess.run(["npm", "install"], cwd=str(ui_dir),
                           capture_output=True)
        threading.Thread(target=_npm_dev, daemon=True).start()
        time.sleep(6)
    else:
        # No Node.js: serve API docs instead
        return f"http://localhost:{port}"

    if expose:
        try:
            return adapter.expose_port(port)
        except Exception:
            return _colab_proxy_url(port) or f"http://localhost:{port}"
    return f"http://localhost:{port}"


def _node_available() -> bool:
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True, timeout=5)
        return True
    except Exception:
        return False


def _colab_proxy_url(port: int) -> str | None:
    """Use google.colab.output to get the proxy URL for a port."""
    try:
        from google.colab.output import eval_js  # type: ignore
        url = str(eval_js(f"google.colab.kernel.proxyPort({port})"))
        return url.replace("http://", "https://")
    except Exception:
        return None


def _try_colab_secrets() -> None:
    """Read HF_TOKEN / NGROK_AUTHTOKEN from Colab Secrets if available."""
    try:
        from google.colab import userdata  # type: ignore
        for secret in ("HF_TOKEN", "NGROK_AUTHTOKEN", "CF_TUNNEL_TOKEN"):
            try:
                val = userdata.get(secret)
                if val:
                    os.environ.setdefault(secret, val)
            except Exception:
                pass
    except ImportError:
        pass
