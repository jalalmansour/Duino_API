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


# ─── Repository root (two levels up from this file) ──────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

API_PORT = 8000
UI_PORT  = 3000


def start(
    model: str        = "gemma-4-2b",
    api_port: int     = API_PORT,
    ui_port: int      = UI_PORT,
    expose: bool      = True,
    hf_token: str     | None = None,
    ngrok_token: str  | None = None,
) -> dict[str, str]:
    """
    One-call platform launcher for notebooks.

    Returns a dict with:
        api_url   — public HTTPS API URL
        ui_url    — public HTTPS React UI URL
        api_key   — auto-generated API key
        embed_html — ready-to-use <iframe> HTML string

    Usage (any notebook):
        from studio.backend.colab import start
        urls = start()
    """
    from rich.console import Console
    console = Console()

    console.print("\n[bold cyan]⚡ Duino API — Starting...[/]")

    # ── Token injection ───────────────────────────────────────────────────────
    if hf_token:
        os.environ["HF_TOKEN"] = hf_token
    if ngrok_token:
        os.environ["NGROK_AUTHTOKEN"] = ngrok_token

    # Try reading from Colab secrets
    _try_colab_secrets()

    os.environ["DEFAULT_MODEL"]  = model
    os.environ["DUINO_PORT"]     = str(api_port)
    os.environ["UI_PORT"]        = str(ui_port)

    # ── Detect environment ───────────────────────────────────────────────────
    from duino_api.adapters.detector import EnvironmentDetector
    adapter = EnvironmentDetector.get()
    caps    = adapter.capabilities()
    console.print(f"  Environment : [cyan]{caps.runtime.value}[/]")
    console.print(f"  GPU         : [cyan]{caps.gpu_name}[/] ({caps.gpu_vram_mb} MB)")
    console.print(f"  Quantize    : [cyan]{caps.recommended_quant or 'none'}[/]")

    # ── Start API server (background thread) ─────────────────────────────────
    console.print("  [yellow]Starting API server...[/]")
    _start_api(api_port)
    _wait_for_api(api_port, timeout=60)
    console.print("  [green]API server ready.[/]")

    # ── Create default API key ───────────────────────────────────────────────
    api_key = _create_key(api_port)
    console.print(f"  API Key  : [bold green]{api_key}[/]")

    # ── Expose API via HTTPS ─────────────────────────────────────────────────
    api_url = f"http://localhost:{api_port}"
    if expose:
        try:
            api_url = adapter.expose_port(api_port)
        except Exception as exc:
            console.print(f"  [yellow]Tunnel failed ({exc}) — using localhost[/]")
    console.print(f"  API URL  : [bold cyan]{api_url}[/]")

    # ── React UI ─────────────────────────────────────────────────────────────
    ui_url = _start_ui(ui_port, api_url=api_url, adapter=adapter, expose=expose)
    console.print(f"  UI URL   : [bold cyan]{ui_url}[/]")

    embed_html = (
        f'<script>'
        f'document.querySelector("#duino-iframe")?.addEventListener("load",()=>{{'
        f'document.querySelector("#duino-iframe").contentWindow.postMessage('
        f'{{type:"duino-config",apiUrl:"{api_url}",apiKey:"{api_key}"}},"*");'
        f'}});</script>'
        f'<iframe id="duino-iframe" src="{ui_url}" width="100%" height="700" '
        f'style="border:none;border-radius:14px;background:#0a0a0f;"></iframe>'
    )

    console.print("\n[bold green]✅ Duino API is live![/]")
    console.print(f"  Embed: [dim]<iframe src=\"{ui_url}\" ..>[/]")

    return {
        "api_url":    api_url,
        "ui_url":     ui_url,
        "api_key":    api_key,
        "embed_html": embed_html,
    }


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _start_api(port: int) -> None:
    def _run():
        env = os.environ.copy()
        subprocess.run(
            [sys.executable, "-m", "uvicorn",
             "duino_api.gateway.app:app",
             "--host", "0.0.0.0", "--port", str(port),
             "--no-access-log"],
            cwd=str(REPO_ROOT),
            env=env,
        )
    threading.Thread(target=_run, daemon=True).start()


def _wait_for_api(port: int, timeout: int = 60) -> None:
    import urllib.request, urllib.error
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://localhost:{port}/v1/health", timeout=2)
            return
        except Exception:
            time.sleep(2)
    raise TimeoutError(f"API did not start on port {port} within {timeout}s")


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
    except Exception:
        return "key-unavailable"


def _start_ui(port: int, api_url: str, adapter, expose: bool) -> str:
    ui_dir  = REPO_ROOT / "ui"
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
    elif (ui_dir / "package.json").exists() and _node_available():
        # Install deps if needed
        if not (ui_dir / "node_modules").exists():
            subprocess.run(["npm", "install"], cwd=str(ui_dir),
                           capture_output=True)
        threading.Thread(target=_npm_dev, daemon=True).start()
        time.sleep(5)
    else:
        return f"http://localhost:{port}"

    if expose:
        try:
            return adapter.expose_port(port)
        except Exception:
            pass
    return f"http://localhost:{port}"


def _node_available() -> bool:
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
        return True
    except Exception:
        return False


def _try_colab_secrets() -> None:
    """Read HF_TOKEN from google.colab.userdata if available."""
    try:
        from google.colab import userdata  # type: ignore
        for secret in ("HF_TOKEN", "NGROK_AUTHTOKEN"):
            try:
                val = userdata.get(secret)
                if val:
                    os.environ.setdefault(secret, val)
            except Exception:
                pass
    except ImportError:
        pass
