#!/bin/bash
set -e

echo "=== Saymo Installer ==="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}!${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; }

# 1. Check architecture
ARCH=$(uname -m)
if [ "$ARCH" != "arm64" ]; then
    fail "Running under $ARCH (Rosetta). Saymo needs native arm64."
    echo "  Fix: Open Terminal.app → Get Info → uncheck 'Open using Rosetta'"
    echo "  Or run: arch -arm64 /bin/zsh"
    exit 1
fi
ok "Architecture: arm64"

# 2. Check Python
PYTHON=$(which python3 2>/dev/null)
if [ -z "$PYTHON" ]; then
    fail "Python 3 not found"
    exit 1
fi
PY_VER=$(python3 --version 2>&1 | awk '{print $2}')
ok "Python: $PY_VER ($PYTHON)"

# 3. Check brew
if ! command -v brew &>/dev/null; then
    fail "Homebrew not found. Install: https://brew.sh"
    exit 1
fi
ok "Homebrew: found"

# 4. Install system dependencies
echo ""
echo "--- System dependencies ---"

if ! brew list ffmpeg &>/dev/null; then
    echo "Installing FFmpeg..."
    brew install ffmpeg
else
    ok "FFmpeg: installed"
fi

if ! brew list blackhole-2ch &>/dev/null; then
    echo "Installing BlackHole 2ch..."
    brew install blackhole-2ch
else
    ok "BlackHole 2ch: installed"
fi

if ! brew list blackhole-16ch &>/dev/null; then
    warn "BlackHole 16ch not installed (needed for auto mode)"
    echo "  Install with: brew install blackhole-16ch"
else
    ok "BlackHole 16ch: installed"
fi

if ! brew list portaudio &>/dev/null; then
    echo "Installing PortAudio..."
    brew install portaudio
else
    ok "PortAudio: installed"
fi

# 5. Install Python package
echo ""
echo "--- Python dependencies ---"

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
pip3 install -e "$SCRIPT_DIR" 2>&1 | tail -3

# 6. Install ML dependencies
echo ""
echo "--- ML dependencies ---"

pip3 install torch torchaudio 2>&1 | tail -1
pip3 install "coqui-tts[codec]" 2>&1 | tail -1
pip3 install faster-whisper 2>&1 | tail -1
pip3 install "transformers>=4.46,<5" 2>&1 | tail -1

ok "ML dependencies installed"

# 7. Check Ollama
echo ""
echo "--- Ollama ---"

if command -v ollama &>/dev/null; then
    ok "Ollama: $(ollama --version 2>/dev/null || echo 'installed')"
    if curl -s http://localhost:11434 &>/dev/null; then
        ok "Ollama service: running"
    else
        warn "Ollama not running. Start with: ollama serve"
    fi
    # Check for model
    if ollama list 2>/dev/null | grep -q "qwen2.5-coder:7b"; then
        ok "Model qwen2.5-coder:7b: available"
    else
        warn "Model qwen2.5-coder:7b not found. Install: ollama pull qwen2.5-coder:7b"
    fi
else
    warn "Ollama not found. Install: https://ollama.ai"
fi

# 8. Download Piper Russian voice (fallback TTS)
echo ""
echo "--- Piper TTS (fallback) ---"

PIPER_DIR="$HOME/.saymo/piper_models"
PIPER_MODEL="$PIPER_DIR/ru_RU-dmitri-medium.onnx"
if [ -f "$PIPER_MODEL" ]; then
    ok "Piper Russian voice: installed"
else
    echo "Downloading Russian voice model..."
    mkdir -p "$PIPER_DIR"
    curl -sL "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/ru/ru_RU/dmitri/medium/ru_RU-dmitri-medium.onnx" \
        -o "$PIPER_MODEL"
    curl -sL "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/ru/ru_RU/dmitri/medium/ru_RU-dmitri-medium.onnx.json" \
        -o "$PIPER_DIR/ru_RU-dmitri-medium.onnx.json"
    ok "Piper Russian voice: downloaded"
fi

# 9. Chrome JS permission
echo ""
echo "--- Chrome ---"

if pgrep -x "Google Chrome" &>/dev/null; then
    ok "Chrome: running"
    # Try to enable JS from Apple Events
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
    warn "Chrome not running. Start Chrome and re-run installer to enable JS permissions."
fi

# 10. Verify
echo ""
echo "--- Verification ---"

python3 -m saymo test-devices 2>/dev/null && ok "Saymo CLI: working" || fail "Saymo CLI: failed"

echo ""
echo "=== Installation complete ==="
echo ""
echo "Quick start:"
echo "  1. Record voice:     python3 -m saymo record-voice -d 300"
echo "  2. Before standup:   python3 -m saymo prepare"
echo "  3. Review audio:     python3 -m saymo review"
echo "  4. During standup:   python3 -m saymo speak --glip"
echo "  5. Auto mode:        python3 -m saymo auto"
echo ""
echo "Audio setup (one-time):"
echo "  1. Open Audio MIDI Setup → Create Multi-Output Device"
echo "     - Check: Plantronics (master) + BlackHole 16ch (drift correction)"
echo "  2. In Glip call → Audio → Microphone → BlackHole 2ch"
echo "  3. In Glip call → Audio → Speakers → Multi-Output Device"
echo ""
