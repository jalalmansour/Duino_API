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
        VER=$("$cmd" -c "import sys; print(sys.version_info >= (3,10))" 2>/dev/null)
        if [[ "$VER" == "True" ]]; then
            PYTHON="$cmd"; break
        fi
    fi
done
[[ -z "$PYTHON" ]] && error "Python 3.10+ required. Install from https://python.org"
success "Python: $($PYTHON --version)"

# ── 3. pip upgrade ────────────────────────────────────────────────────────────
info "Upgrading pip..."
"$PYTHON" -m pip install --upgrade pip --quiet

# ── 4. Core requirements ──────────────────────────────────────────────────────
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
info "Installing core requirements from $REPO_ROOT/requirements.txt..."
"$PYTHON" -m pip install -r "$REPO_ROOT/requirements.txt" --quiet
success "Core requirements installed"

# ── 5. GPU detection + inference requirements ─────────────────────────────────
GPU_AVAILABLE=false
if command -v nvidia-smi &>/dev/null; then
    VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1 || echo 0)
    info "GPU detected: $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1) (${VRAM} MB)"
    GPU_AVAILABLE=true

    # PyTorch with CUDA
    if ! "$PYTHON" -c "import torch; assert torch.cuda.is_available()" &>/dev/null; then
        info "Installing PyTorch with CUDA 12.1..."
        "$PYTHON" -m pip install torch --index-url https://download.pytorch.org/whl/cu121 --quiet
    fi

    # bitsandbytes (Linux only — quantization)
    if $IS_LINUX; then
        "$PYTHON" -m pip install bitsandbytes>=0.43.1 --quiet 2>/dev/null || warn "bitsandbytes not installed (optional)"
    fi

    "$PYTHON" -m pip install -r "$REPO_ROOT/requirements-inference.txt" --quiet
    success "GPU inference requirements installed"
else
    warn "No NVIDIA GPU found — CPU inference only"
    # CPU PyTorch
    if ! "$PYTHON" -c "import torch" &>/dev/null; then
        info "Installing CPU PyTorch..."
        "$PYTHON" -m pip install torch --index-url https://download.pytorch.org/whl/cpu --quiet
    fi
    "$PYTHON" -m pip install transformers accelerate sentencepiece einops huggingface-hub --quiet
    success "CPU inference requirements installed"
fi

# ── 6. Node.js check (for React UI) ──────────────────────────────────────────
if command -v node &>/dev/null; then
    success "Node.js: $(node --version)"
else
    warn "Node.js not found — React UI will not be available"
    info  "Install Node.js: https://nodejs.org"

    # Auto-install on Colab/Linux
    if $IS_COLAB || $IS_LINUX; then
        info "Attempting Node.js install via nvm..."
        curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash &>/dev/null || true
        export NVM_DIR="$HOME/.nvm"
        # shellcheck disable=SC1091
        [[ -s "$NVM_DIR/nvm.sh" ]] && source "$NVM_DIR/nvm.sh"
        nvm install 20 --silent 2>/dev/null && nvm use 20 --silent 2>/dev/null || warn "nvm install failed — install Node.js manually"
    fi
fi

# ── 7. React UI dependencies ──────────────────────────────────────────────────
UI_DIR="$REPO_ROOT/ui"
if command -v npm &>/dev/null && [[ -f "$UI_DIR/package.json" ]]; then
    info "Installing React UI dependencies..."
    npm install --prefix "$UI_DIR" --silent
    success "React UI dependencies installed"
fi

# ── 8. .env setup ─────────────────────────────────────────────────────────────
ENV_FILE="$REPO_ROOT/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    cp "$REPO_ROOT/.env.example" "$ENV_FILE"
    warn ".env created from .env.example — add your HF_TOKEN and NGROK_AUTHTOKEN"
fi

# ── 9. Install Duino API as editable package ──────────────────────────────────
info "Installing duino-api package..."
"$PYTHON" -m pip install -e "$REPO_ROOT" --quiet
success "duino-api installed"

echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║   ✅  Setup Complete!                     ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Start platform : ${CYAN}duinobot deploy${NC}"
echo -e "  API only       : ${CYAN}duinobot serve${NC}"
echo -e "  Health check   : ${CYAN}duinobot status${NC}"
echo -e "  API docs       : ${CYAN}http://localhost:8000/docs${NC}"
echo ""
