#!/bin/bash
set -e

echo "=== Saymo Installer ==="
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}!${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; }

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

# ── Architecture ──
ARCH=$(uname -m)
if [ "$ARCH" != "arm64" ]; then
    fail "Running under $ARCH (Rosetta). Saymo needs native arm64."
    echo "  Fix: Open Terminal.app → Get Info → uncheck 'Open using Rosetta'"
    exit 1
fi
ok "Architecture: arm64"

# ── Python ──
PYTHON=$(which python3 2>/dev/null)
if [ -z "$PYTHON" ]; then
    fail "Python 3 not found"
    exit 1
fi
ok "Python: $(python3 --version 2>&1 | awk '{print $2}')"

# ── Package manager: prefer uv, fallback to pip ──
USE_UV=false
if command -v uv &>/dev/null; then
    UV_VER=$(uv --version 2>/dev/null | awk '{print $2}')
    ok "uv: $UV_VER (will use for fast installs)"
    USE_UV=true
else
    warn "uv not found, using pip (install uv for 10-50x faster installs: curl -LsSf https://astral.sh/uv/install.sh | sh)"
fi

install_pkg() {
    if $USE_UV; then
        uv pip install --system "$@" 2>&1 | tail -1
    else
        pip3 install "$@" 2>&1 | tail -1
    fi
}

# ── Brew dependencies ──
echo ""
echo "--- System dependencies ---"

for pkg in ffmpeg portaudio; do
    if ! brew list $pkg &>/dev/null; then
        echo "Installing $pkg..."
        brew install $pkg
    else
        ok "$pkg: installed"
    fi
done

if ! brew list blackhole-2ch &>/dev/null; then
    echo "Installing BlackHole 2ch..."
    brew install blackhole-2ch
else
    ok "BlackHole 2ch: installed"
fi

if ! brew list blackhole-16ch &>/dev/null; then
    warn "BlackHole 16ch not installed (needed for auto mode)"
    echo "  Install: brew install blackhole-16ch"
else
    ok "BlackHole 16ch: installed"
fi

# ── Python package ──
echo ""
echo "--- Saymo core ---"

if $USE_UV; then
    uv pip install --system -e "$SCRIPT_DIR" 2>&1 | tail -3
else
    pip3 install -e "$SCRIPT_DIR" 2>&1 | tail -3
fi
ok "Saymo core: installed"

# ── TTS dependencies (voice cloning) ──
echo ""
echo "--- TTS (voice cloning) ---"

if $USE_UV; then
    uv pip install --system -e "$SCRIPT_DIR[tts]" 2>&1 | tail -3
else
    pip3 install -e "$SCRIPT_DIR[tts]" 2>&1 | tail -3
fi
ok "TTS dependencies: installed"

# ── STT dependencies (speech recognition) ──
echo ""
echo "--- STT (speech recognition) ---"

if $USE_UV; then
    uv pip install --system -e "$SCRIPT_DIR[stt]" 2>&1 | tail -3
else
    pip3 install -e "$SCRIPT_DIR[stt]" 2>&1 | tail -3
fi
ok "STT dependencies: installed"

# ── Verify PyTorch ──
echo ""
echo "--- PyTorch ---"

PY_TORCH=$(python3 -c "import torch; print(torch.__version__)" 2>/dev/null || echo "MISSING")
if [ "$PY_TORCH" = "MISSING" ]; then
    fail "PyTorch not working. Try: pip3 install --force-reinstall torch torchaudio"
else
    MPS=$(python3 -c "import torch; print(torch.backends.mps.is_available())" 2>/dev/null)
    ok "PyTorch: $PY_TORCH (MPS: $MPS)"
fi

# ── Ollama ──
echo ""
echo "--- Ollama ---"

if command -v ollama &>/dev/null; then
    ok "Ollama: installed"
    if curl -s http://localhost:11434 &>/dev/null; then
        ok "Ollama service: running"
    else
        warn "Ollama not running. Start: ollama serve"
    fi
    if ollama list 2>/dev/null | grep -q "qwen2.5-coder:7b"; then
        ok "Model qwen2.5-coder:7b: available"
    else
        warn "Model not found. Install: ollama pull qwen2.5-coder:7b"
    fi
else
    warn "Ollama not found. Install: https://ollama.ai"
fi

# ── Piper voice (fallback TTS) ──
echo ""
echo "--- Piper voice ---"

PIPER_DIR="$HOME/.saymo/piper_models"
PIPER_MODEL="$PIPER_DIR/ru_RU-dmitri-medium.onnx"
if [ -f "$PIPER_MODEL" ]; then
    ok "Piper Russian voice: installed"
else
    echo "Downloading Russian voice model (~60MB)..."
    mkdir -p "$PIPER_DIR"
    curl -sL "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/ru/ru_RU/dmitri/medium/ru_RU-dmitri-medium.onnx" \
        -o "$PIPER_MODEL"
    curl -sL "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/ru/ru_RU/dmitri/medium/ru_RU-dmitri-medium.onnx.json" \
        -o "$PIPER_DIR/ru_RU-dmitri-medium.onnx.json"
    ok "Piper Russian voice: downloaded"
fi

# ── Chrome JS permission ──
echo ""
echo "--- Chrome ---"

if pgrep -x "Google Chrome" &>/dev/null; then
    ok "Chrome: running"
    osascript -e '
    tell application "Google Chrome" to activate
    delay 0.3
    tell application "System Events"
        tell process "Google Chrome"
            try
                click menu item "Developer" of menu "View" of menu bar 1
                delay 0.3
                click menu item "Allow JavaScript from Apple Events" of menu 1 of menu item "Developer" of menu "View" of menu bar 1
            end try
        end tell
    end tell
    ' 2>/dev/null
    ok "Chrome JS from Apple Events: enabled"
else
    warn "Chrome not running — start Chrome and re-run to enable JS permissions"
fi

# ── Verify ──
echo ""
echo "--- Verification ---"

python3 -m saymo test-devices 2>/dev/null && ok "Saymo CLI: working" || fail "Saymo CLI error"

echo ""
echo -e "${GREEN}=== Installation complete ===${NC}"
echo ""
echo "First time setup:"
echo "  python3 -m saymo setup              # Interactive wizard"
echo "  python3 -m saymo record-voice -d 300 # Record 5-min voice sample"
echo ""
echo "Daily usage:"
echo "  python3 -m saymo prepare -p standup  # Before meeting"
echo "  python3 -m saymo speak --glip        # During meeting"
echo "  python3 -m saymo auto -p standup     # Full auto mode"
echo ""
echo "Audio setup (one-time):"
echo "  1. Audio MIDI Setup → Create Multi-Output Device"
echo "     Plantronics (master) + BlackHole 16ch (drift correction)"
echo "  2. Glip → Audio → Mic → BlackHole 2ch"
echo "  3. Glip → Audio → Speakers → Multi-Output Device"
echo ""
