"""
Duino API — Live CLI Monitor
Real-time GPU + API dashboard that runs in any notebook terminal.

Usage:
    from studio.monitor import Monitor
    m = Monitor(api_url, api_key)
    m.run()   # blocks forever — stops only on Ctrl+C / STOP button
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import threading
import requests
from datetime import datetime, timedelta


# ─── ANSI escape helpers ──────────────────────────────────────────────────────
ESC     = "\033["
RESET   = f"{ESC}0m"
BOLD    = f"{ESC}1m"
DIM     = f"{ESC}2m"
RED     = f"{ESC}91m"
GREEN   = f"{ESC}92m"
YELLOW  = f"{ESC}93m"
CYAN    = f"{ESC}96m"
WHITE   = f"{ESC}97m"
MAGENTA = f"{ESC}95m"
BLUE    = f"{ESC}94m"

def _clear_line():  return f"{ESC}2K\r"
def _move_up(n):    return f"{ESC}{n}A"
def _home():        return f"{ESC}H"
def _clrscr():      return f"{ESC}2J{ESC}H"


# ─── GPU probe ────────────────────────────────────────────────────────────────

def _gpu_stats() -> list[dict]:
    try:
        out = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=index,name,memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        gpus = []
        for line in out.stdout.strip().splitlines():
            p = [x.strip() for x in line.split(",")]
            if len(p) >= 7:
                gpus.append({
                    "idx":      int(p[0]),
                    "name":     p[1],
                    "used_mb":  float(p[2]),
                    "total_mb": float(p[3]),
                    "util":     float(p[4]),
                    "temp_c":   float(p[5]),
                    "power_w":  float(p[6].replace("N/A","0") or 0),
                })
        return gpus
    except Exception:
        return []


def _bar(value: float, total: float, width: int = 20) -> str:
    """Render a colored ASCII progress bar."""
    pct   = min(value / total, 1.0) if total > 0 else 0
    fill  = int(pct * width)
    empty = width - fill

    if pct > 0.85:   color = RED
    elif pct > 0.60: color = YELLOW
    else:            color = GREEN

    bar = color + "█" * fill + DIM + "░" * empty + RESET
    return f"[{bar}] {BOLD}{pct*100:5.1f}%{RESET}"


def _api_health(api_url: str, api_key: str, timeout: int = 5) -> dict:
    try:
        r = requests.get(f"{api_url}/v1/health",
                         headers={"X-API-Key": api_key},
                         timeout=timeout)
        if r.status_code == 200:
            return {**r.json(), "_ok": True}
        return {"_ok": False, "status": r.status_code}
    except Exception as exc:
        return {"_ok": False, "error": str(exc)[:60]}


# ─── Monitor class ────────────────────────────────────────────────────────────

class Monitor:
    """
    Infinite live dashboard.
    Shows per-GPU utilization, VRAM, temperature, power draw,
    plus API health and live uptime counter.
    Stops ONLY on KeyboardInterrupt (user presses STOP).
    """

    def __init__(
        self,
        api_url:  str  = "http://localhost:8000",
        api_key:  str  = "",
        interval: int  = 3,        # refresh every N seconds
        ping_api: bool = True,
    ):
        self.api_url  = api_url
        self.api_key  = api_key
        self.interval = interval
        self.ping_api = ping_api

        self._start    = time.time()
        self._ticks    = 0
        self._errors   = 0
        self._api_ok   = True
        self._health   = {}
        self._gpus     = []
        self._lock     = threading.Lock()
        self._running  = True

        # Background GPU poller (faster than API poll)
        self._gpu_thread = threading.Thread(target=self._poll_gpus, daemon=True)

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Start monitor — blocks until STOP / Ctrl+C."""
        self._gpu_thread.start()
        try:
            while self._running:
                self._tick()
                time.sleep(self.interval)
        except KeyboardInterrupt:
            pass
        finally:
            self._running = False
            elapsed = timedelta(seconds=int(time.time() - self._start))
            print(f"\n{GREEN}[Monitor] Stopped after {elapsed} | {self._ticks} ticks{RESET}")

    # ── Background GPU polling (every 1s) ─────────────────────────────────────

    def _poll_gpus(self) -> None:
        while self._running:
            stats = _gpu_stats()
            with self._lock:
                self._gpus = stats
            time.sleep(1)

    # ── Main tick ─────────────────────────────────────────────────────────────

    def _tick(self) -> None:
        self._ticks += 1

        # Ping API every tick
        if self.ping_api:
            h = _api_health(self.api_url, self.api_key)
            with self._lock:
                self._api_ok = h.get("_ok", False)
                self._health = h
                if not self._api_ok:
                    self._errors += 1

        self._render()

    # ── Render dashboard ──────────────────────────────────────────────────────

    def _render(self) -> None:
        with self._lock:
            gpus   = list(self._gpus)
            api_ok = self._api_ok
            health = dict(self._health)

        elapsed = timedelta(seconds=int(time.time() - self._start))
        now     = datetime.now().strftime("%H:%M:%S")
        lines   = []

        # ── Header ────────────────────────────────────────────────────────────
        lines.append(
            f"{BOLD}{CYAN}╔══════════════════════════════════════════════════════╗{RESET}"
        )
        lines.append(
            f"{BOLD}{CYAN}║  ⚡ Duino API Monitor    {WHITE}{now}{CYAN}  uptime: {WHITE}{elapsed}{CYAN}  ║{RESET}"
        )
        lines.append(
            f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════╝{RESET}"
        )

        # ── API status ────────────────────────────────────────────────────────
        api_icon = f"{GREEN}● ONLINE{RESET}" if api_ok else f"{RED}● OFFLINE{RESET}"
        lines.append(
            f"  API Status   : {api_icon}   "
            f"{DIM}ticks={self._ticks}  errors={self._errors}{RESET}"
        )
        if api_ok and health:
            model   = health.get("model", "–")
            backend = health.get("backend", "–")
            req_cnt = health.get("requests_total", "–")
            lines.append(
                f"  Model        : {BOLD}{model}{RESET}   "
                f"backend={backend}   requests={req_cnt}"
            )
        lines.append(f"  API URL      : {CYAN}{self.api_url}{RESET}")
        lines.append("")

        # ── GPU section ───────────────────────────────────────────────────────
        if gpus:
            lines.append(f"  {BOLD}GPUs ({len(gpus)} device{'s' if len(gpus)>1 else ''}){RESET}")
            lines.append(f"  {'─'*54}")
            for g in gpus:
                vram_bar = _bar(g["used_mb"], g["total_mb"], width=18)
                util_bar = _bar(g["util"],    100,           width=10)

                # Temp color
                t = g["temp_c"]
                tc = RED if t > 85 else YELLOW if t > 70 else GREEN

                lines.append(
                    f"  GPU {g['idx']}  {BOLD}{g['name'][:30]:<30}{RESET}"
                )
                lines.append(
                    f"    VRAM  {vram_bar}  "
                    f"{BOLD}{g['used_mb']/1024:.1f}/{g['total_mb']/1024:.1f} GB{RESET}"
                )
                lines.append(
                    f"    Load  {util_bar}   "
                    f"Temp: {tc}{t:.0f}°C{RESET}   "
                    f"Power: {MAGENTA}{g['power_w']:.0f}W{RESET}"
                )
                lines.append("")
        else:
            lines.append(f"  {YELLOW}No NVIDIA GPU detected (CPU mode){RESET}")
            lines.append("")

        # ── Footer ────────────────────────────────────────────────────────────
        lines.append(
            f"  {DIM}Refreshing every {self.interval}s — Press STOP (■) to terminate{RESET}"
        )

        # ── Print in-place (overwrite previous output) ────────────────────────
        total = len(lines)
        # Move cursor up to overwrite previous dashboard
        if self._ticks > 1:
            sys.stdout.write(_move_up(self._last_lines))

        for line in lines:
            sys.stdout.write(_clear_line() + line + "\n")
        sys.stdout.flush()
        self._last_lines = total


def run_monitor(api_url: str, api_key: str, interval: int = 3) -> None:
    """Convenience function — runs Monitor directly."""
    m = Monitor(api_url=api_url, api_key=api_key, interval=interval)
    m.run()
