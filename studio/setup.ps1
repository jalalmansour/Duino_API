#Requires -Version 5.1
<#
.SYNOPSIS
    Duino API — Windows PowerShell Setup Script
.DESCRIPTION
    Installs all dependencies for Duino API on Windows.
    Works in PowerShell 5.1+ and PowerShell 7+
.EXAMPLE
    .\studio\setup.ps1
    # If execution policy blocks it:
    PowerShell -ExecutionPolicy Bypass -File .\studio\setup.ps1
#>

$ErrorActionPreference = "Stop"

function Write-Info    { Write-Host "[Duino] " -ForegroundColor Cyan  -NoNewline; Write-Host $args }
function Write-Success { Write-Host "[Duino] " -ForegroundColor Green -NoNewline; Write-Host "✅ $args" }
function Write-Warn    { Write-Host "[Duino] " -ForegroundColor Yellow -NoNewline; Write-Host "⚠️  $args" }
function Write-Fail    { Write-Host "[Duino] " -ForegroundColor Red   -NoNewline; Write-Host "❌ $args"; exit 1 }

Write-Host ""
Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   ⚡ Duino API — Windows Setup        ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$RepoRoot = Split-Path $PSScriptRoot -Parent
Push-Location $RepoRoot

# ── 1. Python detection ───────────────────────────────────────────────────────
$Python = $null
foreach ($cmd in @("python3.11","python3.10","python3","python","py")) {
    try {
        $ver = & $cmd -c "import sys; print(sys.version_info >= (3,10))" 2>$null
        if ($ver -eq "True") { $Python = $cmd; break }
    } catch {}
}
if (-not $Python) { Write-Fail "Python 3.10+ required. Get it from https://python.org" }
Write-Success "Python: $(& $Python --version 2>&1)"

# ── 2. Upgrade pip ────────────────────────────────────────────────────────────
Write-Info "Upgrading pip..."
& $Python -m pip install --upgrade pip --quiet

# ── 3. Core requirements ──────────────────────────────────────────────────────
Write-Info "Installing core requirements..."
& $Python -m pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) { Write-Fail "pip install failed" }
Write-Success "Core requirements installed"

# ── 4. GPU detection ──────────────────────────────────────────────────────────
$HasGPU = $false
try {
    $gpuName = (nvidia-smi --query-gpu=name --format=csv,noheader 2>$null | Select-Object -First 1).Trim()
    if ($gpuName) {
        Write-Info "GPU detected: $gpuName"
        $HasGPU = $true
    }
} catch {}

if ($HasGPU) {
    $torchOk = & $Python -c "import torch; print(torch.cuda.is_available())" 2>$null
    if ($torchOk -ne "True") {
        Write-Info "Installing PyTorch CUDA 12.1..."
        & $Python -m pip install torch --index-url https://download.pytorch.org/whl/cu121 --quiet
    }
    & $Python -m pip install -r requirements-inference.txt --quiet
    Write-Success "GPU inference requirements installed"
} else {
    Write-Warn "No NVIDIA GPU found — CPU inference only"
    $torchInstalled = & $Python -c "import torch; print('ok')" 2>$null
    if ($torchInstalled -ne "ok") {
        Write-Info "Installing CPU PyTorch..."
        & $Python -m pip install torch --index-url https://download.pytorch.org/whl/cpu --quiet
    }
    & $Python -m pip install transformers accelerate sentencepiece einops huggingface-hub --quiet
    Write-Success "CPU inference requirements installed"
}

# ── 5. Node.js ────────────────────────────────────────────────────────────────
try {
    $nodeVer = node --version 2>$null
    Write-Success "Node.js: $nodeVer"
    if (Test-Path "ui\package.json") {
        Write-Info "Installing React UI dependencies..."
        npm install --prefix ui --silent 2>$null
        Write-Success "React UI dependencies installed"
    }
} catch {
    Write-Warn "Node.js not found — React UI unavailable"
    Write-Info  "Install from: https://nodejs.org"
}

# ── 6. .env ───────────────────────────────────────────────────────────────────
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Warn ".env created — add your HF_TOKEN and NGROK_AUTHTOKEN"
}

# ── 7. Install package ────────────────────────────────────────────────────────
Write-Info "Installing duino-api package..."
& $Python -m pip install -e . --quiet
Write-Success "duino-api installed"

Pop-Location

Write-Host ""
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║   ✅  Setup Complete!                     ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "  Start platform : " -NoNewline; Write-Host "duinobot deploy" -ForegroundColor Cyan
Write-Host "  API only       : " -NoNewline; Write-Host "duinobot serve"  -ForegroundColor Cyan
Write-Host "  Health check   : " -NoNewline; Write-Host "duinobot status" -ForegroundColor Cyan
Write-Host "  API docs       : " -NoNewline; Write-Host "http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
