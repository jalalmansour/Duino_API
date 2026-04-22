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
    keep_alive: bool  = True,   # DEFAULT True — blocks forever, only STOP (■) exits
) -> dict[str, str]:
    """
    One-call platform launcher for any notebook environment.

    keep_alive=True  → blocks the cell forever (like Cell 9 built-in).
                       Only the STOP button (■) terminates it.
    keep_alive=False → returns dict immediately so you can use result['api_url'] etc.

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

    # Wait with visible progress — 300s timeout to allow model download on first run
    started = _wait_for_api(api_port, timeout=300)
    if not started:
        # Show logs to help diagnose
        _show_server_log()
        raise RuntimeError(
            f"API server failed to start on port {api_port}. "
            f"Check /tmp/duino_api_server.log for details."
        )
    console.print("  [green]API server ready[/]")
    # Always show server log for debugging model load issues
    _show_server_log()

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

    result = {
        "api_url":    api_url,
        "ui_url":     ui_url,
        "api_key":    api_key,
        "embed_html": embed_html,
    }

    if keep_alive:
        _run_keepalive(api_url=api_url, ui_url=ui_url, api_key=api_key, api_port=api_port)

    return result


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
    """
    Install all requirements needed to run Duino API.

    Strategy (most → least invasive):
    1. Upgrade setuptools (fixes BackendUnavailable on Colab Python 3.12)
    2. Add REPO_ROOT to sys.path directly — no build system needed
    3. Install core requirements.txt packages
    4. Try pip install -e (editable) with --no-build-isolation
    5. Fall back to regular (non-editable) pip install .
    6. Install GPU inference extras if NVIDIA GPU present
    """
    pip = _find_pip()

    def _pip(*args, check: bool = True) -> int:
        r = subprocess.run([*pip, *args], capture_output=True, text=True)
        if check and r.returncode != 0:
            raise subprocess.CalledProcessError(r.returncode, [*pip, *args],
                                                r.stdout, r.stderr)
        return r.returncode

    # Step 1 — Upgrade setuptools first (CRITICAL for Colab Python 3.12)
    # Fixes: BackendUnavailable: Cannot import 'setuptools.backends.legacy'
    _pip("install", "--upgrade", "setuptools", "wheel", "-q",
         "--no-warn-script-location", check=False)

    # Step 2 — Register repo on sys.path (works without any build system)
    repo_str = str(REPO_ROOT)
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)

    # Step 3 — Core requirements
    req = REPO_ROOT / "requirements.txt"
    if req.exists():
        _pip("install", "-r", str(req), "-q", "--no-warn-script-location",
             check=False)

    # Step 4 — Install the package (try editable → fallback to regular)
    installed = False

    # 4a: editable with no-build-isolation (avoids legacy backend issue)
    if _pip("install", "-e", str(REPO_ROOT), "-q",
            "--no-build-isolation", "--no-warn-script-location",
            check=False) == 0:
        installed = True

    # 4b: editable without flag
    if not installed:
        if _pip("install", "-e", str(REPO_ROOT), "-q",
                "--no-warn-script-location", check=False) == 0:
            installed = True

    # 4c: regular install (non-editable) as final fallback
    if not installed:
        _pip("install", str(REPO_ROOT), "-q",
             "--no-warn-script-location", check=False)

    # Step 5 — GPU inference extras (non-fatal)
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=name",
                             "--format=csv,noheader"],
                            capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            req_inf = REPO_ROOT / "requirements-inference.txt"
            if req_inf.exists():
                _pip("install", "-r", str(req_inf), "-q",
                     "--no-warn-script-location", check=False)
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
        # Patch vite.config.js at runtime — replace string 'all' with boolean true
        # and add --allowed-hosts all CLI flag as belt-and-suspenders
        _patch_vite_config(ui_dir)
        subprocess.run(
            ["npm", "run", "dev", "--",
             "--host", "0.0.0.0",
             "--port", str(port)],
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


# ─── Vite config patcher ──────────────────────────────────────────────────────

def _patch_vite_config(ui_dir: Path) -> None:
    """
    Rewrite vite.config.js at runtime to ensure allowedHosts: true.
    This fixes the 'Blocked request' error on Colab/Kaggle proxy hostnames.
    The string 'all' does NOT work in Vite 5.x — only the boolean `true` does.
    """
    cfg = ui_dir / "vite.config.js"
    if not cfg.exists():
        return
    try:
        text = cfg.read_text()
        # Replace any string variant with the boolean true
        import re
        text = re.sub(r"allowedHosts\s*:\s*['\"]all['\"]", "allowedHosts: true", text)
        text = re.sub(r"hmr\s*:\s*\{[^}]*\}", "hmr: false", text, flags=re.DOTALL)
        cfg.write_text(text)
    except Exception:
        pass


# ─── Built-in keep-alive (single-cell mode) ───────────────────────────────────

def _run_keepalive(
    api_url:  str,
    ui_url:   str,
    api_key:  str,
    api_port: int = 8000,
) -> None:
    """
    Infinite keep-alive loop.
    ── Layer 1: JavaScript anti-disconnect (browser level) ──────────────────────
      Injects JS that simulates mouse activity every 60s to prevent Colab's
      90-min idle session timeout.
    ── Layer 2: Python watchdog (kernel level) ───────────────────────────────────
      while True: pings /v1/health every 120s. Catches ALL exceptions.
      Only the STOP button (■) / KeyboardInterrupt exits.
    ── Layer 3: Live CLI output ──────────────────────────────────────────────────
      Prints status heartbeat every 5 pings to the notebook terminal.
    """
    import urllib.request

    # ── Inject JS anti-disconnect ─────────────────────────────────────────────
    try:
        from IPython.display import display, Javascript  # type: ignore
        display(Javascript("""
(function duinoKeepAlive() {
  try {
    document.dispatchEvent(new MouseEvent('mousemove', {bubbles: true}));
    var btn = document.querySelector('#top-toolbar > colab-connect-button');
    if (btn) btn.click();
  } catch(e) {}
  setTimeout(duinoKeepAlive, 60000);
})();
console.log('[Duino] Anti-disconnect watchdog active');
"""))
    except Exception:
        pass

    # ── Print banner ──────────────────────────────────────────────────────────
    print("\n" + "═" * 62)
    print("  ⚡ DUINO API — RUNNING (press STOP ■ to terminate)")
    print("═" * 62)
    print(f"  📡 API  : {api_url}")
    print(f"  📖 Docs : {api_url}/docs")
    print(f"  🎨 UI   : {ui_url}")
    print(f"  🔑 Key  : {api_key}")
    print("═" * 62)
    print("  ⏱  Heartbeat every 120s  |  Anti-disconnect JS every 60s")
    print("═" * 62 + "\n")

    # ── Try to use live monitor if available ──────────────────────────────────
    try:
        import sys
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        from studio.monitor import Monitor  # type: ignore
        m = Monitor(
            api_url=api_url,
            api_key=api_key,
            interval=5,
            ping_api=True,
            local_port=api_port,    # CRITICAL: ping localhost, not external proxy
        )
        m.run()   # blocks forever — only KeyboardInterrupt exits
        return
    except Exception:
        pass  # fall back to simple loop below

    # ── Simple fallback loop (no rich monitor) ────────────────────────────────
    t_start = time.time()
    pings   = 0
    errors  = 0
    PING_INTERVAL = 120   # seconds between API pings
    last_ping = 0.0

    while True:
        try:
            now = time.time()

            # Ping API every PING_INTERVAL seconds
            if now - last_ping >= PING_INTERVAL:
                pings    += 1
                last_ping = now
                ok = False
                try:
                    urllib.request.urlopen(
                        f"http://localhost:{api_port}/v1/health", timeout=8
                    )
                    ok = True
                except Exception:
                    errors += 1
                    ok = False

                elapsed = time.time() - t_start
                h, r    = divmod(int(elapsed), 3600)
                m2, s   = divmod(r, 60)
                icon    = "✅" if ok else "⚠️ "
                print(
                    f"[{h:02d}h {m2:02d}m {s:02d}s] {icon} ping #{pings}"
                    f" | errors: {errors}"
                    f" | {'API OK' if ok else 'API DOWN'}",
                    flush=True,
                )

            time.sleep(5)

        except KeyboardInterrupt:
            elapsed = time.time() - t_start
            h, r    = divmod(int(elapsed), 3600)
            m2, s   = divmod(r, 60)
            print(f"\n[Duino] Stopped after {h:02d}h {m2:02d}m {s:02d}s | {pings} pings | {errors} errors")
            return

        except Exception as exc:
            errors += 1
            print(f"[Duino] ⚠️ Exception in keepalive (continuing): {exc}", flush=True)
            time.sleep(5)

