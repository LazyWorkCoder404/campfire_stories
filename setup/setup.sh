#!/usr/bin/env bash
# Campfire Stories: one-time setup.
# Installs everything the game needs. Safe to run again: finished steps are skipped,
# and interrupted model downloads resume where they stopped.
set -euo pipefail

cd "$(dirname "$0")"
ROOT="$(pwd)"

LLM_MODEL="${CAMPFIRE_LLM:-gemma3:12b}"
COMFY_DIR="$ROOT/services/ComfyUI"
HF="https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files"

step() { printf '\n\033[1;33m==> %s\033[0m\n' "$1"; }
ok()   { printf '\033[1;32m    %s\033[0m\n' "$1"; }
warn() { printf '\033[1;31m    %s\033[0m\n' "$1"; }
die()  { warn "$1"; exit 1; }

# ---------------------------------------------------------------------------
step "Checking this computer"
[[ "$(uname -s)" == "Linux" ]] || die "Campfire Stories needs Linux."
command -v nvidia-smi >/dev/null || die "No NVIDIA driver found (nvidia-smi is missing). Install the driver first."
nvidia-smi --query-gpu=name --format=csv,noheader | head -1 | sed 's/^/    GPU: /'
command -v python3 >/dev/null || die "python3 is missing."
PYV="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
ok "Python $PYV"

FREE_GB="$(df -BG --output=avail "$ROOT" | tail -1 | tr -dc '0-9')"
if [[ ! -f "$COMFY_DIR/models/diffusion_models/z_image_turbo_bf16.safetensors" && "$FREE_GB" -lt 45 ]]; then
    die "Only ${FREE_GB} GB free here; setup needs about 45 GB for the models and libraries."
fi

# ---------------------------------------------------------------------------
step "Installing system packages (asks for your password)"
if command -v apt-get >/dev/null; then
    sudo apt-get update
    sudo apt-get install -y git curl wget build-essential espeak-ng \
        "python${PYV}-venv" "python${PYV}-dev" python3-full
else
    warn "apt-get not found. Install these with your package manager, then rerun:"
    warn "  git curl wget build-essential espeak-ng python${PYV} venv + dev headers"
    exit 1
fi

# ---------------------------------------------------------------------------
step "Ollama (the storyteller)"
if ! command -v ollama >/dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
fi
for _ in {1..30}; do
    curl -fs http://localhost:11434/api/tags >/dev/null && break
    sleep 1
done
curl -fs http://localhost:11434/api/tags >/dev/null || die "Ollama isn't responding. Try: sudo systemctl start ollama"
ollama pull "$LLM_MODEL"
ok "Story model ready: $LLM_MODEL"

# ---------------------------------------------------------------------------
step "Game environment (Python packages)"
[[ -x .venv/bin/python ]] || python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
mkdir -p output logs
ok "Game environment ready"

# ---------------------------------------------------------------------------
step "ComfyUI (the illustrator)"
mkdir -p services
[[ -f "$COMFY_DIR/main.py" ]] || git clone https://github.com/comfyanonymous/ComfyUI.git "$COMFY_DIR"
[[ -x "$COMFY_DIR/venv/bin/python" ]] || python3 -m venv "$COMFY_DIR/venv"
"$COMFY_DIR/venv/bin/pip" install --upgrade pip
"$COMFY_DIR/venv/bin/pip" install torch torchvision torchaudio
"$COMFY_DIR/venv/bin/pip" install -r "$COMFY_DIR/requirements.txt"
if "$COMFY_DIR/venv/bin/python" -c "import torch, sys; sys.exit(0 if torch.cuda.is_available() else 1)"; then
    ok "PyTorch can see the GPU"
else
    warn "PyTorch can't see the GPU. Install the CUDA build from pytorch.org inside services/ComfyUI/venv."
fi

# ---------------------------------------------------------------------------
step "Image model: Z-Image Turbo (about 20 GB, this is the long part)"
download() {  # download <url> <destination>
    local url="$1" dest="$2"
    if [[ -f "$dest" ]]; then
        ok "Already have $(basename "$dest")"
        return
    fi
    mkdir -p "$(dirname "$dest")"
    echo "    Downloading $(basename "$dest")..."
    wget -c -q --show-progress -O "$dest.part" "$url"
    mv "$dest.part" "$dest"
}
download "$HF/diffusion_models/z_image_turbo_bf16.safetensors" "$COMFY_DIR/models/diffusion_models/z_image_turbo_bf16.safetensors"
download "$HF/text_encoders/qwen_3_4b.safetensors"             "$COMFY_DIR/models/text_encoders/qwen_3_4b.safetensors"
download "$HF/vae/ae.safetensors"                              "$COMFY_DIR/models/vae/ae.safetensors"

# ---------------------------------------------------------------------------
step "Final checks"
chmod +x start.sh scripts/start_comfyui.sh 2>/dev/null || true
if [[ -f workflows/pumpkin.json ]]; then
    ok "Workflow file found"
else
    warn "workflows/pumpkin.json is missing. Export it from ComfyUI (see the README) before playing."
fi

printf '\n\033[1;32mSetup complete. Start the game with:  ./start.sh\033[0m\n\n'
