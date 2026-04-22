@echo off
:: ╔══════════════════════════════════════════════════════════════════════════╗
:: ║  Duino API — Windows Setup Script (CMD)                                ║
:: ║  Usage: studio\setup.bat                                               ║
:: ╚══════════════════════════════════════════════════════════════════════════╝
setlocal EnableDelayedExpansion
title Duino API - Setup

echo.
echo  ======================================
echo    Duino API -- Windows Setup
echo  ======================================
echo.

:: ── Root directory (parent of studio\) ───────────────────────────────────────
set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
pushd "%REPO_ROOT%"

:: ── 1. Python check ───────────────────────────────────────────────────────────
set "PYTHON="
for %%P in (python3.11 python3.10 python3 python py) do (
    if "!PYTHON!"=="" (
        %%P --version >nul 2>&1 && set "PYTHON=%%P"
    )
)
if "!PYTHON!"=="" (
    echo [ERROR] Python 3.10+ not found. Get it from https://python.org
    pause & exit /b 1
)
echo [OK] Found Python: & !PYTHON! --version

:: ── 2. pip upgrade ────────────────────────────────────────────────────────────
echo [INFO] Upgrading pip...
!PYTHON! -m pip install --upgrade pip --quiet

:: ── 3. Core requirements ──────────────────────────────────────────────────────
echo [INFO] Installing core requirements...
!PYTHON! -m pip install -r requirements.txt --quiet
if !errorlevel! neq 0 ( echo [ERROR] pip install failed & pause & exit /b 1 )
echo [OK] Core requirements installed.

:: ── 4. GPU detection ──────────────────────────────────────────────────────────
set "HAS_GPU=0"
nvidia-smi >nul 2>&1 && set "HAS_GPU=1"

if "!HAS_GPU!"=="1" (
    echo [INFO] NVIDIA GPU detected
    !PYTHON! -c "import torch; torch.cuda.is_available()" >nul 2>&1
    if !errorlevel! neq 0 (
        echo [INFO] Installing PyTorch CUDA 12.1...
        !PYTHON! -m pip install torch --index-url https://download.pytorch.org/whl/cu121 --quiet
    )
    !PYTHON! -m pip install -r requirements-inference.txt --quiet
    echo [OK] GPU inference requirements installed.
) else (
    echo [WARN] No GPU found -- CPU inference only
    !PYTHON! -c "import torch" >nul 2>&1
    if !errorlevel! neq 0 (
        echo [INFO] Installing CPU PyTorch...
        !PYTHON! -m pip install torch --index-url https://download.pytorch.org/whl/cpu --quiet
    )
    !PYTHON! -m pip install transformers accelerate sentencepiece einops huggingface-hub --quiet
    echo [OK] CPU inference requirements installed.
)

:: ── 5. Node.js check ──────────────────────────────────────────────────────────
node --version >nul 2>&1
if !errorlevel! equ 0 (
    echo [OK] Node.js found: & node --version
    if exist "ui\package.json" (
        echo [INFO] Installing React UI dependencies...
        npm install --prefix ui --silent
        echo [OK] React UI ready.
    )
) else (
    echo [WARN] Node.js not found -- React UI will not be available.
    echo        Install from: https://nodejs.org
)

:: ── 6. .env setup ─────────────────────────────────────────────────────────────
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo [WARN] .env created -- edit it to add HF_TOKEN and NGROK_AUTHTOKEN
)

:: ── 7. Install package ────────────────────────────────────────────────────────
echo [INFO] Installing duino-api package...
!PYTHON! -m pip install -e . --quiet
echo [OK] duino-api installed.

echo.
echo  ======================================
echo    Setup Complete!
echo  ======================================
echo.
echo  Start platform : duinobot deploy
echo  API only       : duinobot serve
echo  Health check   : duinobot status
echo  API docs       : http://localhost:8000/docs
echo.
popd
pause
