"""
Duino API — Cross-Platform Python Stack Installer
Equivalent to Unsloth's install_python_stack.py

Usage:
    python install_python_stack.py
    python install_python_stack.py --cpu-only
    python install_python_stack.py --cuda 12.1
    python install_python_stack.py --rocm 6.0
"""
from __future__ import annotations

import argparse
import platform
import subprocess
import sys
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent


def run(cmd: list[str], check: bool = True) -> int:
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False)
    if check and result.returncode != 0:
        print(f"[ERROR] Command failed with code {result.returncode}")
        sys.exit(result.returncode)
    return result.returncode


def detect_gpu() -> dict:
    """Detect GPU type: NVIDIA, AMD ROCm, or none."""
    # NVIDIA
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0 and out.stdout.strip():
            parts = out.stdout.strip().split(", ")
            return {"vendor": "nvidia", "name": parts[0], "vram_mb": int(parts[1])}
    except Exception:
        pass

    # AMD ROCm
    try:
        out = subprocess.run(
            ["rocminfo"], capture_output=True, text=True, timeout=5
        )
        if out.returncode == 0:
            # Find GFX ISA lines (e.g. gfx1100, gfx942)
            matches = re.findall(r"\bgfx\d{3,4}[a-z]?\b", out.stdout)
            if matches:
                return {"vendor": "amd", "gfx": matches[0], "name": matches[0]}
    except Exception:
        pass

    return {"vendor": "none"}


def detect_cuda_version() -> str | None:
    """Return CUDA version string like '12.1' or None."""
    try:
        out = subprocess.run(
            ["nvcc", "--version"], capture_output=True, text=True, timeout=5
        )
        m = re.search(r"release (\d+\.\d+)", out.stdout)
        if m:
            return m.group(1)
    except Exception:
        pass
    try:
        out = subprocess.run(
            ["nvidia-smi"], capture_output=True, text=True, timeout=5
        )
        m = re.search(r"CUDA Version: (\d+\.\d+)", out.stdout)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None


def recommend_quant(vram_mb: int) -> str:
    if vram_mb >= 40_000:
        return "none"
    if vram_mb >= 24_000:
        return "awq"
    return "bnb-4bit"


def install_torch(cuda_ver: str | None, rocm_ver: str | None, cpu_only: bool) -> None:
    print("\n[PyTorch]")

    if cpu_only:
        print("  CPU-only mode requested")
        run([sys.executable, "-m", "pip", "install", "torch",
             "--index-url", "https://download.pytorch.org/whl/cpu", "--quiet"])
        return

    if cuda_ver:
        # Map cuda X.Y → whl tag cuXY
        tag = "cu" + cuda_ver.replace(".", "")
        whl = f"https://download.pytorch.org/whl/{tag}"
        print(f"  CUDA {cuda_ver} → {whl}")
        run([sys.executable, "-m", "pip", "install", "torch",
             "--index-url", whl, "--quiet"])

    elif rocm_ver:
        tag = "rocm" + rocm_ver.replace(".", "")
        whl = f"https://download.pytorch.org/whl/{tag}"
        print(f"  ROCm {rocm_ver} → {whl}")
        run([sys.executable, "-m", "pip", "install", "torch",
             "--index-url", whl, "--quiet"])

    else:
        print("  No GPU detected — installing CPU PyTorch")
        run([sys.executable, "-m", "pip", "install", "torch",
             "--index-url", "https://download.pytorch.org/whl/cpu", "--quiet"])


def install_inference_extras(gpu: dict) -> None:
    print("\n[Inference extras]")
    pkgs = ["transformers>=4.41.0", "accelerate>=0.30.0",
            "sentencepiece>=0.2.0", "einops>=0.8.0", "huggingface-hub>=0.23.0"]

    if gpu["vendor"] == "nvidia":
        vram = gpu.get("vram_mb", 0)
        quant = recommend_quant(vram)
        print(f"  VRAM: {vram} MB → recommended quantization: {quant}")

        if quant in ("bnb-4bit", "bnb-8bit") and platform.system() == "Linux":
            pkgs.append("bitsandbytes>=0.43.1")
            print("  Adding bitsandbytes (Linux + CUDA)")

    run([sys.executable, "-m", "pip", "install", *pkgs, "--quiet"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Duino API Python Stack Installer")
    parser.add_argument("--cpu-only", action="store_true", help="Force CPU-only install")
    parser.add_argument("--cuda", metavar="VERSION", help="Override CUDA version (e.g. 12.1)")
    parser.add_argument("--rocm", metavar="VERSION", help="Override ROCm version (e.g. 6.0)")
    parser.add_argument("--skip-torch", action="store_true", help="Skip PyTorch install")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════╗")
    print("║  ⚡ Duino API — Python Stack Installer   ║")
    print("╚══════════════════════════════════════════╝")
    print(f"  Python  : {sys.version.split()[0]}")
    print(f"  OS      : {platform.system()} {platform.machine()}")

    # ── GPU detection ─────────────────────────────────────────────────────────
    gpu = detect_gpu()
    if not args.cpu_only:
        if args.cuda:
            cuda_ver = args.cuda
        elif args.rocm:
            cuda_ver = None
        else:
            cuda_ver = detect_cuda_version()
        rocm_ver = args.rocm
    else:
        cuda_ver = None
        rocm_ver = None

    print(f"  GPU     : {gpu.get('name', 'None')} [{gpu['vendor']}]")
    print(f"  CUDA    : {cuda_ver or 'not detected'}")

    # ── pip upgrade ────────────────────────────────────────────────────────────
    print("\n[pip]")
    run([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "--quiet"])

    # ── Core requirements ──────────────────────────────────────────────────────
    print("\n[Core requirements]")
    run([sys.executable, "-m", "pip", "install", "-r",
         str(REPO_ROOT / "requirements.txt"), "--quiet"])

    # ── PyTorch ───────────────────────────────────────────────────────────────
    if not args.skip_torch:
        install_torch(cuda_ver, rocm_ver, args.cpu_only)

    # ── Inference extras ──────────────────────────────────────────────────────
    install_inference_extras(gpu)

    # ── Duino API package ─────────────────────────────────────────────────────
    print("\n[Duino API package]")
    run([sys.executable, "-m", "pip", "install", "-e", str(REPO_ROOT), "--quiet"])

    print("\n✅ Installation complete!")
    print("   Run: duinobot deploy")


if __name__ == "__main__":
    main()
