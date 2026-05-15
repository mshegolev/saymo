#!/bin/bash
# Saymo master setup — one command does everything from a fresh Mac.
#
# Walks the user through:
#   1. Install Saymo core deps (uv venv, models, Chrome JS)
#   2. Install F5-TTS Russian (recommended voice cloning engine)
#   3. (Optional) Install Applio + RVC alternative pipeline
#   4. Run the interactive wizard to configure config.yaml
#   5. Quick smoke test
#
# Each step is idempotent — safe to re-run. Prompts at every fork.

set -eo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

ok()    { echo -e "${GREEN}✓${NC} $1"; }
warn()  { echo -e "${YELLOW}!${NC} $1"; }
fail()  { echo -e "${RED}✗${NC} $1"; exit 1; }
step()  { echo ""; echo -e "${BLUE}${BOLD}═══ $1 ═══${NC}"; }
prompt() { echo ""; echo -en "${BOLD}? ${NC}$1 [Y/n] "; read -r ans; case "${ans:-y}" in [Yy]*) return 0 ;; *) return 1 ;; esac; }

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

clear
cat <<'BANNER'

   ███████╗ █████╗ ██╗   ██╗███╗   ███╗ ██████╗
   ██╔════╝██╔══██╗╚██╗ ██╔╝████╗ ████║██╔═══██╗
   ███████╗███████║ ╚████╔╝ ██╔████╔██║██║   ██║
   ╚════██║██╔══██║  ╚██╔╝  ██║╚██╔╝██║██║   ██║
   ███████║██║  ██║   ██║   ██║ ╚═╝ ██║╚██████╔╝
   ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚═╝     ╚═╝ ╚═════╝

        Local AI voice assistant — speaks in YOUR voice on calls
        ─────────────────────────────────────────────────────────
BANNER
echo ""
echo -e "${BOLD}Master setup${NC} — guides you through installing everything Saymo needs."
echo "Each step asks before doing anything heavy. Re-runnable; skips what's done."

# ── 0. Sanity ──
step "Pre-flight checks"

[ "$(uname -m)" = "arm64" ] || fail "Saymo needs Apple Silicon (arm64). You're on $(uname -m)."
ok "Apple Silicon"

[ "$(uname -s)" = "Darwin" ] || fail "Saymo is macOS-only."
ok "macOS"

if ! command -v brew >/dev/null; then
    warn "Homebrew not found — required for installing system audio (BlackHole)."
    if prompt "Install Homebrew now?"; then
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else
        fail "Homebrew is required. Install manually from https://brew.sh and re-run."
    fi
fi
ok "Homebrew"

# ── 1. Saymo core ──
step "Step 1/4: Saymo core (Python venv + models + Chrome JS)"

if [ -d "$SCRIPT_DIR/.venv" ] && "$SCRIPT_DIR/.venv/bin/saymo" --version >/dev/null 2>&1; then
    ok "Saymo already installed (run 'rm -rf .venv && bash setup.sh' to reinstall)"
else
    if prompt "Run install.sh? Downloads Ollama, Whisper, BlackHole if missing (~5-15 min)"; then
        bash "$SCRIPT_DIR/install.sh"
    else
        fail "Saymo core is required. Re-run when ready."
    fi
fi

# Make `saymo` available in this shell session
export PATH="$SCRIPT_DIR/.venv/bin:$PATH"

# ── 2. F5-TTS (recommended) ──
step "Step 2/4: F5-TTS Russian voice cloning  (RECOMMENDED)"
echo ""
echo "  F5-TTS is the default Saymo voice engine. One-stage cloning, Russian-tuned."
echo "  Setup: ~10 min, ~1.5 GB download."
echo ""

if [ -f "$HOME/F5TTS/.venv/bin/python" ] && [ -f "$HOME/.saymo/f5tts_model.txt" ]; then
    ok "F5-TTS already installed at ~/F5TTS/"
else
    if prompt "Install F5-TTS now?"; then
        bash "$SCRIPT_DIR/scripts/install_f5tts.sh"
    else
        warn "Skipped. You'll need a TTS engine to use Saymo on calls. See docs/QUICK-START.md."
    fi
fi

# ── 3. RVC (optional) ──
step "Step 3/4: XTTS+RVC alternative pipeline  (OPTIONAL)"
echo ""
echo "  Two-stage cloning via Applio. Heavier setup but gives different timbre."
echo "  Useful as fallback or for A/B comparison. Setup: ~30 min, ~3-5 GB."
echo ""

if [ -d "$HOME/Applio/.venv" ]; then
    ok "Applio already installed at ~/Applio/"
else
    if prompt "Install Applio + RVC? (skip unless you want the alternative path)"; then
        bash "$SCRIPT_DIR/scripts/install_rvc.sh"
    else
        ok "Skipped (F5-TTS alone is enough for most users)"
    fi
fi

# ── 4. Wizard ──
step "Step 4/4: Interactive config wizard"
echo ""
echo "  Sets up your name/voice/Ollama/audio devices in ~/.saymo/config.yaml."
echo "  Records a fresh voice sample if needed."
echo ""

if [ -f "$HOME/.saymo/config.yaml" ]; then
    ok "config.yaml exists at ~/.saymo/"
    if prompt "Re-run wizard to update settings?"; then
        saymo setup
    fi
else
    if prompt "Run wizard now?"; then
        saymo setup
    fi
fi

# ── Done ──
step "All done!"
cat <<EOF

  ${GREEN}${BOLD}Saymo is ready.${NC}

  Quick test:
    ${BOLD}saymo test-tts "Доброе утро коллеги."${NC}

  Before a call:
    ${BOLD}saymo prepare -p personal${NC}              # or your meeting profile
    ${BOLD}saymo speak -p personal --provider glip${NC} # or --provider zoom, --provider google_meet, etc.

  Listen mode (auto-respond when your name is mentioned):
    ${BOLD}saymo auto -p personal${NC}

  Docs:
    ${BOLD}docs/QUICK-START.md${NC}            ← start here
    ${BOLD}docs/F5TTS-VOICE-CLONING.md${NC}    ← F5-TTS setup, tuning
    ${BOLD}docs/RVC-VOICE-CLONING.md${NC}      ← XTTS+RVC alternative
    ${BOLD}docs/VOICE-TRAINING.md${NC}         ← XTTS fine-tune

EOF
