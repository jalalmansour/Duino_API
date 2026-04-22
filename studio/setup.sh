#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  Duino API — Universal Setup Script (Linux / macOS / WSL / Colab)     ║
# ║  Usage: chmod +x studio/setup.sh && ./studio/setup.sh                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝
set -euo pipefail

BOLD='\033[1m'; CYAN='\033[0;36m'; GREEN='\033[0;32m'
YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

info()    { echo -e "${CYAN}[Duino]${NC} $*"; }
success() { echo -e "${GREEN}[Duino]${NC} ✅ $*"; }
warn()    { echo -e "${YELLOW}[Duino]${NC} ⚠️  $*"; }
error()   { echo -e "${RED}[Duino]${NC} ❌ $*"; exit 1; }

echo -e "${BOLD}╔══════════════════════════════════════╗${NC}"
echo -e "${BOLD}║   ⚡ Duino API — Setup               ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════╝${NC}"

# ── 1. Detect OS & environment ────────────────────────────────────────────────
OS="$(uname -s 2>/dev/null || echo Windows)"
IS_COLAB=false; IS_KAGGLE=false; IS_LINUX=false; IS_MAC=false

[[ -d /content ]] && IS_COLAB=true
[[ "${KAGGLE_KERNEL_RUN_TYPE:-}" != "" ]] && IS_KAGGLE=true
[[ "$OS" == "Linux" ]]  && IS_LINUX=true
[[ "$OS" == "Darwin" ]] && IS_MAC=true

info "OS: $OS | Colab: $IS_COLAB | Kaggle: $IS_KAGGLE"

# ── 2. Python check ───────────────────────────────────────────────────────────
PYTHON=""
for cmd in python3.11 python3.10 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        VER=$("$cmd" -c "import sys; print(sys.version_info >= (3,10))" 2>/dev/null || echo "False")
        if [[ "$VER" == "True" ]]; then
            PYTHON="$cmd"; break
        fi
    fi
done
[[ -z "$PYTHON" ]] && error "Python 3.10+ required. Install from https://python.org"
success "Python: $($PYTHON --version)"

# ── 3. Find pip (CRITICAL fix for Colab where python3.10 -m pip fails) ────────
PIP=""
# Try standalone pip commands first (works on Colab)
for cmd in pip3 pip pip3.11 pip3.10; do
    if command -v "$cmd" &>/dev/null; then
        PIP="$cmd"; break
    fi
done
# Fallback: python -m pip with the found python binary
if [[ -z "$PIP" ]]; then
    if "$PYTHON" -m pip --version &>/dev/null 2>&1; then
        PIP="$PYTHON -m pip"
    fi
fi
# Last resort: bootstrap pip via ensurepip
if [[ -z "$PIP" ]]; then
    warn "pip not found — bootstrapping via ensurepip..."
    "$PYTHON" -m ensurepip --upgrade 2>/dev/null || true
    # Try again after bootstrap
    for cmd in pip3 pip; do
        command -v "$cmd" &>/dev/null && { PIP="$cmd"; break; }
    done
fi
[[ -z "$PIP" ]] && error "Cannot find pip. Please install pip manually."
success "pip: $($PIP --version)"

# Helper: run pip with the found pip command
pip_install() { $PIP install "$@"; }

# ── 4. pip upgrade ────────────────────────────────────────────────────────────
info "Upgrading pip..."
pip_install --upgrade pip --quiet

# ── 5. Core requirements ──────────────────────────────────────────────────────
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
info "Repo root: $REPO_ROOT"
info "Installing core requirements..."
pip_install -r "$REPO_ROOT/requirements.txt" --quiet
success "Core requirements installed"

# ── 6. GPU detection + inference requirements ─────────────────────────────────
GPU_AVAILABLE=false
if command -v nvidia-smi &>/dev/null; then
    VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1 || echo 0)
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 || echo unknown)
    info "GPU: $GPU_NAME (${VRAM} MB)"
    GPU_AVAILABLE=true

    # PyTorch with CUDA — skip if already installed correctly
    if ! "$PYTHON" -c "import torch; assert torch.cuda.is_available()" &>/dev/null 2>&1; then
        info "Installing PyTorch CUDA 12.1..."
        pip_install torch --index-url https://download.pytorch.org/whl/cu121 --quiet
    else
        success "PyTorch CUDA already installed"
    fi

    # bitsandbytes (Linux only)
    if $IS_LINUX || $IS_COLAB; then
        pip_install bitsandbytes --quiet 2>/dev/null || warn "bitsandbytes optional — skipping"
    fi

    pip_install -r "$REPO_ROOT/requirements-inference.txt" --quiet
    success "GPU inference requirements installed"
else
    warn "No NVIDIA GPU — CPU inference only"
    if ! "$PYTHON" -c "import torch" &>/dev/null 2>&1; then
        info "Installing CPU PyTorch..."
        pip_install torch --index-url https://download.pytorch.org/whl/cpu --quiet
    fi
    pip_install transformers accelerate sentencepiece einops huggingface-hub --quiet
    success "CPU inference requirements installed"
fi

# ── 7. Node.js (for React UI) ─────────────────────────────────────────────────
if command -v node &>/dev/null; then
    success "Node.js: $(node --version)"
    if [[ -f "$REPO_ROOT/ui/package.json" ]]; then
        info "Installing React UI dependencies..."
        npm install --prefix "$REPO_ROOT/ui" --silent 2>/dev/null || true
        success "React UI ready"
    fi
else
    warn "Node.js not found — React UI unavailable (optional)"
    # Auto-install on Colab/Linux via nvm
    if $IS_COLAB || $IS_LINUX; then
        info "Installing Node.js 20 via nvm..."
        curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash &>/dev/null || true
        export NVM_DIR="$HOME/.nvm"
        # shellcheck disable=SC1091
        [[ -s "$NVM_DIR/nvm.sh" ]] && source "$NVM_DIR/nvm.sh" || true
        nvm install 20 --silent &>/dev/null && nvm use 20 --silent &>/dev/null || warn "nvm install failed"
        if command -v node &>/dev/null && [[ -f "$REPO_ROOT/ui/package.json" ]]; then
            npm install --prefix "$REPO_ROOT/ui" --silent 2>/dev/null || true
            success "React UI ready"
        fi
    fi
fi

# ── 8. .env setup ─────────────────────────────────────────────────────────────
ENV_FILE="$REPO_ROOT/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    cp "$REPO_ROOT/.env.example" "$ENV_FILE"
    warn ".env created — add HF_TOKEN and NGROK_AUTHTOKEN if needed"
fi

# ── 9. Install Duino API as editable package ──────────────────────────────────
info "Installing duino-api package (editable)..."
pip_install -e "$REPO_ROOT" --quiet
success "duino-api installed"

echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║   ✅  Setup Complete!                     ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Start platform : ${CYAN}duinobot deploy${NC}"
echo -e "  API only       : ${CYAN}duinobot serve${NC}"
echo -e "  Status         : ${CYAN}duinobot status${NC}"
echo -e "  API docs       : ${CYAN}http://localhost:8000/docs${NC}"
echo ""
