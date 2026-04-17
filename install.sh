#!/bin/bash
set -eo pipefail

echo "=== Saymo Installer (uv + Python 3.12) ==="
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}!${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; }

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
VENV_DIR="$SCRIPT_DIR/.venv"
PY_VERSION="3.12"

# ── Architecture ──
ARCH=$(uname -m)
if [ "$ARCH" != "arm64" ]; then
    fail "Running under $ARCH (Rosetta). Saymo needs native arm64."
    echo "  Fix: Open Terminal.app → Get Info → uncheck 'Open using Rosetta'"
    exit 1
fi
ok "Architecture: arm64"

# ── uv (required) ──
if ! command -v uv &>/dev/null; then
    fail "uv not found. Install first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi
ok "uv: $(uv --version | awk '{print $2}')"

# ── Create venv with Python 3.12 ──
echo ""
echo "--- Virtualenv (Python $PY_VERSION) ---"

if [ -d "$VENV_DIR" ]; then
    EXISTING_VER=$(grep '^version' "$VENV_DIR/pyvenv.cfg" 2>/dev/null | awk '{print $3}' | cut -d. -f1,2)
    if [ "$EXISTING_VER" != "$PY_VERSION" ]; then
        warn "Existing venv uses Python $EXISTING_VER — recreating with $PY_VERSION"
        rm -rf "$VENV_DIR"
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    uv venv --python "$PY_VERSION" "$VENV_DIR"
fi
ok "venv: $VENV_DIR ($(grep '^version' "$VENV_DIR/pyvenv.cfg" | awk '{print $3}'))"

# All uv pip calls target this venv
export VIRTUAL_ENV="$VENV_DIR"
PY="$VENV_DIR/bin/python"

# ── Brew system deps ──
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

# ── Saymo core + extras ──
echo ""
echo "--- Saymo core ---"
uv pip install -e "$SCRIPT_DIR" 2>&1 | tail -3
ok "Saymo core: installed"

echo ""
echo "--- TTS (voice cloning + piper) ---"
uv pip install -e "$SCRIPT_DIR[tts]" 2>&1 | tail -3
ok "TTS dependencies: installed (coqui-tts, torch, piper)"

echo ""
echo "--- STT (speech recognition) ---"
uv pip install -e "$SCRIPT_DIR[stt]" 2>&1 | tail -3
ok "STT dependencies: installed"

# verify coqui TTS import
if "$PY" -c "from TTS.api import TTS" 2>/dev/null; then
    ok "Coqui TTS import: OK"
else
    fail "Coqui TTS import failed in $VENV_DIR"
fi

# ── Verify PyTorch ──
echo ""
echo "--- PyTorch ---"

PY_TORCH=$("$PY" -c "import torch; print(torch.__version__)" 2>/dev/null || echo "MISSING")
if [ "$PY_TORCH" = "MISSING" ]; then
    fail "PyTorch not working. Try: VIRTUAL_ENV=$VENV_DIR uv pip install --force-reinstall torch torchaudio"
else
    MPS=$("$PY" -c "import torch; print(torch.backends.mps.is_available())" 2>/dev/null)
    ok "PyTorch: $PY_TORCH (MPS: $MPS)"
fi

# ── Ollama ──
echo ""
echo "--- Ollama ---"

OLLAMA_MODEL="qwen2.5-coder:7b"

if ! command -v ollama &>/dev/null; then
    if brew list ollama &>/dev/null; then
        ok "Ollama: installed via brew"
    else
        echo "Installing Ollama via brew..."
        brew install ollama
        ok "Ollama: installed"
    fi
else
    ok "Ollama: $(ollama --version 2>/dev/null | head -1)"
fi

# Ensure service is up before pull
if ! curl -fsS http://localhost:11434 >/dev/null 2>&1; then
    echo "Starting ollama service..."
    if command -v brew &>/dev/null && brew services list 2>/dev/null | grep -q '^ollama'; then
        brew services start ollama >/dev/null 2>&1 || true
    else
        nohup ollama serve >/dev/null 2>&1 &
    fi
    # wait up to 15s for API to come up
    for i in {1..15}; do
        if curl -fsS http://localhost:11434 >/dev/null 2>&1; then break; fi
        sleep 1
    done
fi

if curl -fsS http://localhost:11434 >/dev/null 2>&1; then
    ok "Ollama service: running"
    if ollama list 2>/dev/null | awk '{print $1}' | grep -qx "$OLLAMA_MODEL"; then
        ok "Model $OLLAMA_MODEL: available"
    else
        echo "Pulling model $OLLAMA_MODEL (~4.4GB, several minutes)..."
        if ollama pull "$OLLAMA_MODEL"; then
            ok "Model $OLLAMA_MODEL: installed"
        else
            fail "Model pull failed. Retry manually: ollama pull $OLLAMA_MODEL"
        fi
    fi
else
    warn "Ollama API not responding on :11434. Start it with: ollama serve"
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
    JS_RESULT=$(osascript \
        -e 'tell application "Google Chrome" to activate' \
        -e 'delay 0.3' \
        -e 'tell application "System Events" to tell process "Google Chrome"' \
        -e '  set viewMenuName to ""' \
        -e '  repeat with m in (menu bar items of menu bar 1)' \
        -e '    if name of m is in {"View", "Вид"} then set viewMenuName to name of m' \
        -e '  end repeat' \
        -e '  if viewMenuName is "" then return "no_view_menu"' \
        -e '  try' \
        -e '    click menu item 1 of menu 1 of menu item "Developer" of menu viewMenuName of menu bar 1' \
        -e '    return "ok_en"' \
        -e '  end try' \
        -e '  try' \
        -e '    click menu item 1 of menu 1 of menu item "Разработка" of menu viewMenuName of menu bar 1' \
        -e '    return "ok_ru"' \
        -e '  end try' \
        -e '  return "menu_not_found"' \
        -e 'end tell' \
        2>&1 || true)
    case "$JS_RESULT" in
        ok_en|ok_ru) ok "Chrome JS from Apple Events: toggled (Developer menu)" ;;
        *) warn "Could not toggle JS permission automatically ($JS_RESULT). Enable manually: View → Developer → Allow JavaScript from Apple Events" ;;
    esac
else
    warn "Chrome not running — start Chrome and re-run to enable JS permissions"
fi

# ── Verify ──
echo ""
echo "--- Verification ---"

"$PY" -m saymo test-devices 2>/dev/null && ok "Saymo CLI: working" || fail "Saymo CLI error"

echo ""
echo -e "${GREEN}=== Installation complete ===${NC}"
echo ""
echo "Activate venv:"
echo "  source .venv/bin/activate"
echo ""
echo "Or run directly without activating:"
echo "  .venv/bin/saymo <command>"
echo ""
echo "First time setup:"
echo "  .venv/bin/saymo setup              # Interactive wizard"
echo "  .venv/bin/saymo record-voice -d 300 # Record 5-min voice sample"
echo ""
echo "Daily usage:"
echo "  .venv/bin/saymo prepare -p standup  # Before meeting"
echo "  .venv/bin/saymo speak --glip        # During meeting"
echo "  .venv/bin/saymo auto -p standup     # Full auto mode"
echo ""
echo "Audio setup (one-time):"
echo "  1. Audio MIDI Setup → Create Multi-Output Device"
echo "     Plantronics (master) + BlackHole 16ch (drift correction)"
echo "  2. Glip → Audio → Mic → BlackHole 2ch"
echo "  3. Glip → Audio → Speakers → Multi-Output Device"
echo ""
