#!/bin/bash
# Install RVC v2 toolchain for Saymo Phase 2 (XTTS + RVC voice cloning).
#
# - Clones Applio (training UI) into ~/Applio if not present
# - Runs Applio's installer (creates its own venv, downloads pretrained models)
# - Installs rvc-python (inference library) into Saymo's uv venv
# - Creates ~/.saymo/models/rvc/ for trained model artifacts
#
# Idempotent: safe to re-run. Skips work that's already done.

set -eo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}!${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }
step() { echo -e "${BLUE}→${NC} $1"; }

SAYMO_DIR=$(cd "$(dirname "$0")/.." && pwd)
APPLIO_DIR="$HOME/Applio"
RVC_MODELS_DIR="$HOME/.saymo/models/rvc"

echo "=== Saymo RVC Installer ==="
echo ""

# ── Architecture check ──
[ "$(uname -m)" = "arm64" ] || fail "arm64 only. Open Terminal natively, not via Rosetta."
ok "Architecture: arm64"

# ── Prereqs ──
command -v git    >/dev/null || fail "git not found. Install via 'brew install git'."
command -v python3 >/dev/null || fail "python3 not found."
command -v uv     >/dev/null || fail "uv not found. Run saymo's install.sh first."
ok "Prereqs: git, python3, uv"

# ── Step 1: Applio (training UI) ──
step "Step 1/4: Applio (training)"
if [ -d "$APPLIO_DIR/.git" ]; then
    ok "Applio already cloned at $APPLIO_DIR"
else
    git clone https://github.com/IAHispano/Applio.git "$APPLIO_DIR"
    ok "Cloned Applio → $APPLIO_DIR"
fi

if [ -d "$APPLIO_DIR/env" ] || [ -d "$APPLIO_DIR/.venv" ]; then
    ok "Applio venv already created (skipping installer)"
else
    warn "Running Applio installer — downloads ~3-5 GB, takes 10-30 min."
    pushd "$APPLIO_DIR" >/dev/null
    if [ -x "./run-install.sh" ]; then
        ./run-install.sh
    else
        fail "Applio installer not found ($APPLIO_DIR/run-install.sh missing)"
    fi
    popd >/dev/null
    ok "Applio installed"
fi

# ── Step 2: rvc-python (inference, in Saymo venv) ──
step "Step 2/4: rvc-python (inference into Saymo venv)"
pushd "$SAYMO_DIR" >/dev/null
if uv run python -c "import rvc_python" 2>/dev/null; then
    ok "rvc-python already installed in Saymo venv"
else
    uv add rvc-python
    ok "Added rvc-python to Saymo dependencies"
fi
popd >/dev/null

# ── Step 3: model artifact directory ──
step "Step 3/4: model directories"
mkdir -p "$RVC_MODELS_DIR"
ok "Models dir: $RVC_MODELS_DIR"

# ── Step 4: launcher convenience ──
step "Step 4/4: launcher script"
cat > "$HOME/.saymo/run_applio.sh" <<EOF
#!/bin/bash
# Launch Applio WebUI for RVC training. Open http://127.0.0.1:6969 in browser.
cd "$APPLIO_DIR" && ./run-applio.sh
EOF
chmod +x "$HOME/.saymo/run_applio.sh"
ok "Launcher: ~/.saymo/run_applio.sh"

echo ""
echo -e "${GREEN}=== Done ===${NC}"
echo ""
echo "Next steps:"
echo "  1. Start Applio:   ~/.saymo/run_applio.sh"
echo "  2. Open browser:   http://127.0.0.1:6969"
echo "  3. Follow guide:   docs/RVC-VOICE-CLONING.md"
