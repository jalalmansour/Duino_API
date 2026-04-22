"""
Duino API — CLI
`duinobot deploy | serve | generate-ui | keys | status`
"""
from __future__ import annotations

import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="duinobot",
    help="☁️  Duino API — Cloud-Agnostic Hyperscale Inference CLI",
    rich_markup_mode="rich",
)
console = Console()


# ─── deploy ───────────────────────────────────────────────────────────────────

@app.command()
def deploy(
    model: str = typer.Option("gemma-4-2b", help="Model to load (gemma-4-2b/9b/27b)"),
    port: int = typer.Option(8000, help="API port"),
    ui: bool = typer.Option(True, help="Launch React UI"),
    ui_port: int = typer.Option(3000, help="React UI port"),
    expose: bool = typer.Option(True, help="Expose via HTTPS tunnel"),
):
    """🚀 Full platform deploy: model + API + UI + HTTPS tunnel."""
    console.print(Panel("☁️  [bold cyan]Duino API — Deploy[/]", expand=False))

    # Detect environment
    from duino_api.adapters.detector import EnvironmentDetector
    adapter = EnvironmentDetector.get()
    caps = adapter.capabilities()

    console.print(f"  Environment : [cyan]{caps.runtime.value}[/]")
    console.print(f"  GPU         : [cyan]{caps.gpu_name}[/] ({caps.gpu_vram_mb} MB)")
    console.print(f"  Quantize    : [cyan]{caps.recommended_quant or 'none'}[/]")

    # Start API server in background thread
    console.print("\n  [yellow]Starting API server...[/]")
    _start_server_thread(port)
    time.sleep(3)

    api_url = f"http://localhost:{port}"
    public_api = api_url

    if expose:
        console.print("  [yellow]Creating HTTPS tunnel for API...[/]")
        public_api = adapter.expose_port(port)
        console.print(f"  [green]API URL  : {public_api}[/]")

    # React UI
    if ui:
        ui_url = _deploy_react_ui(ui_port, api_url=public_api, expose=expose, adapter=adapter)
        console.print(f"  [green]UI URL   : {ui_url}[/]")
        console.print(
            f"\n  [bold]Embed:[/] [dim]<iframe src=\"{ui_url}\" width=\"100%\" height=\"600\"></iframe>[/]"
        )

    # Bootstrap a default API key
    console.print("\n  [yellow]Creating default API key...[/]")
    _create_default_key(port)

    console.print(Panel(
        f"[bold green]✅ Platform running![/]\n"
        f"API : {public_api}\n"
        f"Docs: {public_api}/docs",
        title="Duino API Ready",
        expand=False,
    ))
    console.print("  Press [bold]Ctrl+C[/] to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/]")


# ─── serve ────────────────────────────────────────────────────────────────────

@app.command()
def serve(
    model: str = typer.Option("gemma-4-2b", help="Model ID"),
    port: int = typer.Option(8000, help="Port"),
    reload: bool = typer.Option(False, help="Hot reload (dev only)"),
):
    """🔧 Start API server only (no UI, no tunnel)."""
    console.print(f"[cyan]Starting Duino API on port {port}...[/]")
    import os
    os.environ["DEFAULT_MODEL"] = model
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "duino_api.gateway.app:app",
         "--host", "0.0.0.0", "--port", str(port),
         "--reload" if reload else "--no-access-log"],
        check=True,
    )


# ─── generate-ui ──────────────────────────────────────────────────────────────

@app.command(name="generate-ui")
def generate_ui(
    api_url: str = typer.Option("http://localhost:8000", help="API base URL"),
    port: int = typer.Option(3000, help="UI dev server port"),
    expose: bool = typer.Option(True, help="Tunnel UI via HTTPS"),
):
    """🎨 Build and serve the React UI."""
    from duino_api.adapters.detector import EnvironmentDetector
    adapter = EnvironmentDetector.get()
    ui_url = _deploy_react_ui(port, api_url=api_url, expose=expose, adapter=adapter)
    console.print(f"[green]UI live at: {ui_url}[/]")
    console.print(f'[dim]<iframe src="{ui_url}" width="100%" height="600"></iframe>[/]')
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


# ─── keys ─────────────────────────────────────────────────────────────────────

@app.command()
def keys(
    action: str = typer.Argument(help="create | list"),
    name: str = typer.Option("default", help="Key name"),
    tier: str = typer.Option("free", help="Quota tier: free|pro|enterprise"),
    api_url: str = typer.Option("http://localhost:8000", help="API URL"),
):
    """🔑 Manage API keys."""
    import httpx

    if action == "create":
        resp = httpx.post(
            f"{api_url}/v1/keys",
            json={"name": name, "quota_tier": tier},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            console.print(Panel(
                f"[bold green]{data['api_key']}[/]\n"
                f"ID: {data['key_id']}  Tier: {data['quota_tier']}",
                title="🔑 API Key Created",
            ))
        else:
            console.print(f"[red]Error: {resp.text}[/]")

    elif action == "list":
        console.print("[yellow]Key listing requires admin auth. See /docs.[/]")


# ─── status ───────────────────────────────────────────────────────────────────

@app.command()
def status(
    api_url: str = typer.Option("http://localhost:8000", help="API URL"),
):
    """📊 Show platform health and status."""
    import httpx
    try:
        resp = httpx.get(f"{api_url}/v1/health", timeout=5)
        data = resp.json()
    except Exception as exc:
        console.print(f"[red]Cannot reach API: {exc}[/]")
        raise typer.Exit(1)

    table = Table(title="Duino API Status", show_header=True)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    for k, v in data.items():
        table.add_row(str(k), str(v))
    console.print(table)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _start_server_thread(port: int) -> None:
    import os
    def _run():
        subprocess.run(
            [sys.executable, "-m", "uvicorn", "duino_api.gateway.app:app",
             "--host", "0.0.0.0", "--port", str(port), "--no-access-log"],
            check=False,
        )
    t = threading.Thread(target=_run, daemon=True)
    t.start()


def _deploy_react_ui(
    port: int, api_url: str, expose: bool, adapter
) -> str:
    ui_dir = Path(__file__).parent.parent.parent / "ui"
    dist_dir = ui_dir / "dist"

    if dist_dir.exists():
        # Serve pre-built dist
        console.print("  [yellow]Serving pre-built React UI...[/]")

        def _serve():
            subprocess.run(
                [sys.executable, "-m", "http.server", str(port), "--directory", str(dist_dir)],
                check=False,
            )

        threading.Thread(target=_serve, daemon=True).start()
    elif ui_dir.exists() and (ui_dir / "package.json").exists():
        # npm dev server
        console.print("  [yellow]Starting Vite dev server...[/]")

        def _vite():
            subprocess.run(
                ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", str(port)],
                cwd=str(ui_dir), check=False,
            )

        threading.Thread(target=_vite, daemon=True).start()
        time.sleep(4)
    else:
        console.print("  [dim]No UI directory found — skipping UI[/]")
        return f"http://localhost:{port}"

    if expose:
        return adapter.expose_port(port)
    return f"http://localhost:{port}"


def _create_default_key(api_port: int) -> None:
    import httpx, time
    time.sleep(1)
    try:
        resp = httpx.post(
            f"http://localhost:{api_port}/v1/keys",
            json={"name": "default", "quota_tier": "free"},
            timeout=10,
        )
        if resp.status_code == 200:
            key = resp.json()["api_key"]
            console.print(f"  [green]Default Key:[/] [bold]{key}[/]")
    except Exception:
        pass


if __name__ == "__main__":
    app()
