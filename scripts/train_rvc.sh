#!/bin/bash
# Headless RVC training pipeline — preprocess → extract → train → index → install.
#
# Drives Applio's CLI (~/Applio/core.py) to train an RVC v2 model on Saymo's
# training dataset, then copies the resulting .pth + .index into
# ~/.saymo/models/rvc/ ready for tts.engine: xtts_rvc_clone.
#
# Idempotent within stages — but the Applio commands themselves rebuild from
# scratch each run. Re-running this script after a successful run wastes time
# unless you change inputs (more data, more epochs, etc).

set -eo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}!${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }
step() { echo -e "\n${BLUE}→${NC} $1"; }

# ── Defaults (override via flags or env) ──
MODEL_NAME="${MODEL_NAME:-saymo_voice}"
DATASET_DIR="${DATASET_DIR:-$HOME/.saymo/training_dataset/wavs}"
SAMPLE_RATE="${SAMPLE_RATE:-40000}"
EPOCHS="${EPOCHS:-99}"  # <100 so periodic eval (crashes on MPS >65536) never fires; best_epoch.pth saves on loss improvement throughout
BATCH_SIZE="${BATCH_SIZE:-4}"
SAVE_EVERY="${SAVE_EVERY:-100}"  # max allowed; combine with EPOCHS<100 to skip periodic eval (which crashes on MPS >65536). best_epoch.pth still saves on loss improvement.
F0_METHOD="${F0_METHOD:-rmvpe}"
EMBEDDER="${EMBEDDER:-contentvec}"
GPU_ID="${GPU_ID:--}"          # "-" = CPU on Mac (Applio extract has no MPS support; train auto-detects MPS regardless)
VOCODER="${VOCODER:-MRF HiFi-GAN}"  # smaller than HiFi-GAN; HiFi-GAN crashes on MPS (>65536 channels)
APPLIO_DIR="${APPLIO_DIR:-$HOME/Applio}"
RVC_TARGET_DIR="$HOME/.saymo/models/rvc"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Train an RVC v2 voice model from Saymo's recorded dataset, headlessly.

Options:
  --model-name NAME       Output model name (default: $MODEL_NAME)
  --dataset PATH          Path to wavs/ dir (default: $DATASET_DIR)
  --epochs N              Total training epochs (default: $EPOCHS)
  --batch-size N          Batch size (default: $BATCH_SIZE, ↓ if OOM)
  --gpu ID                GPU id; "" for CPU; "0" default (default: $GPU_ID)
  --vocoder NAME          HiFi-GAN | MRF HiFi-GAN | RefineGAN (default: $VOCODER)
  --sample-rate {32000|40000|48000}  Target SR (default: $SAMPLE_RATE)
  -h, --help              Show this help

Env-var overrides also work (MODEL_NAME, EPOCHS, BATCH_SIZE, GPU_ID, ...).
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --model-name)  MODEL_NAME="$2"; shift 2 ;;
        --dataset)     DATASET_DIR="$2"; shift 2 ;;
        --epochs)      EPOCHS="$2"; shift 2 ;;
        --batch-size)  BATCH_SIZE="$2"; shift 2 ;;
        --gpu)         GPU_ID="$2"; shift 2 ;;
        --vocoder)     VOCODER="$2"; shift 2 ;;
        --sample-rate) SAMPLE_RATE="$2"; shift 2 ;;
        -h|--help)     usage; exit 0 ;;
        *) fail "Unknown option: $1 (try --help)" ;;
    esac
done

# ── Sanity checks ──
[ -d "$APPLIO_DIR/.venv" ] || fail "Applio venv not found at $APPLIO_DIR/.venv. Run scripts/install_rvc.sh first."
[ -d "$DATASET_DIR" ]      || fail "Dataset dir not found: $DATASET_DIR"
WAV_COUNT=$(find "$DATASET_DIR" -maxdepth 1 -name "*.wav" -type f | wc -l | tr -d ' ')
[ "$WAV_COUNT" -ge 30 ]    || fail "Need ≥30 WAVs in $DATASET_DIR (found $WAV_COUNT). Run 'saymo train-prepare' first."
ok "Dataset: $WAV_COUNT WAVs in $DATASET_DIR"

APPLIO_PY="$APPLIO_DIR/.venv/bin/python"
APPLIO_CORE="$APPLIO_DIR/core.py"
[ -x "$APPLIO_PY" ] || fail "Applio python missing: $APPLIO_PY"
[ -f "$APPLIO_CORE" ] || fail "Applio core.py missing: $APPLIO_CORE"

mkdir -p "$RVC_TARGET_DIR"

# Apple Silicon MPS env. Harmless on CPU-only runs.
export PYTORCH_ENABLE_MPS_FALLBACK=1
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0

cd "$APPLIO_DIR"

START_TS=$(date +%s)

# ── 1. Preprocess ──
step "1/4 Preprocess (~1-2 min)"
"$APPLIO_PY" "$APPLIO_CORE" preprocess \
    --model_name "$MODEL_NAME" \
    --dataset_path "$DATASET_DIR" \
    --sample_rate "$SAMPLE_RATE" \
    --cpu_cores 4 \
    --cut_preprocess Automatic \
    --process_effects True \
    --noise_reduction False \
    --noise_reduction_strength 0.5 \
    --chunk_len 3.0 \
    --overlap_len 0.3 \
    --normalization_mode post
ok "Preprocess done"

# ── 2. Extract features ──
step "2/4 Extract features (~3-5 min)"
"$APPLIO_PY" "$APPLIO_CORE" extract \
    --model_name "$MODEL_NAME" \
    --f0_method "$F0_METHOD" \
    --cpu_cores 4 \
    --gpu "$GPU_ID" \
    --sample_rate "$SAMPLE_RATE" \
    --embedder_model "$EMBEDDER" \
    --include_mutes 2
ok "Feature extraction done"

# ── 3. Train ──
step "3/4 Train ($EPOCHS epochs, ~30-60 min)"
"$APPLIO_PY" "$APPLIO_CORE" train \
    --model_name "$MODEL_NAME" \
    --vocoder "$VOCODER" \
    --checkpointing False \
    --save_every_epoch "$SAVE_EVERY" \
    --save_only_latest True \
    --save_every_weights True \
    --total_epoch "$EPOCHS" \
    --sample_rate "$SAMPLE_RATE" \
    --batch_size "$BATCH_SIZE" \
    --gpu "$GPU_ID" \
    --overtraining_detector True \
    --overtraining_threshold 50 \
    --pretrained True \
    --cleanup False \
    --cache_data_in_gpu False
ok "Training done"

# ── 4. Build index ──
step "4/4 Build feature index"
"$APPLIO_PY" "$APPLIO_CORE" index \
    --model_name "$MODEL_NAME" \
    --index_algorithm Auto
ok "Index built"

# ── 5. Copy artifacts ──
step "Install artifacts → $RVC_TARGET_DIR"
LOG_DIR="$APPLIO_DIR/logs/$MODEL_NAME"
[ -d "$LOG_DIR" ] || fail "Expected output dir missing: $LOG_DIR"

# Best/final .pth: prefer best, fall back to highest-numbered checkpoint
PTH=$(ls -t "$LOG_DIR"/*.pth 2>/dev/null | head -1)
INDEX=$(ls -t "$LOG_DIR"/*.index 2>/dev/null | head -1)
[ -n "$PTH" ]   || fail "No .pth file in $LOG_DIR"
[ -n "$INDEX" ] || fail "No .index file in $LOG_DIR (training may have stopped before index step)"

cp "$PTH"   "$RVC_TARGET_DIR/$MODEL_NAME.pth"
cp "$INDEX" "$RVC_TARGET_DIR/$MODEL_NAME.index"
ok "Copied $MODEL_NAME.pth + $MODEL_NAME.index → $RVC_TARGET_DIR"

ELAPSED=$(( $(date +%s) - START_TS ))
echo ""
echo -e "${GREEN}=== Done in $((ELAPSED/60))m $((ELAPSED%60))s ===${NC}"
echo ""
echo "To activate in Saymo, add to ~/.saymo/config.yaml:"
echo ""
echo "  tts:"
echo "    engine: xtts_rvc_clone"
echo "    rvc:"
echo "      model_path: $RVC_TARGET_DIR/$MODEL_NAME.pth"
echo "      index_path: $RVC_TARGET_DIR/$MODEL_NAME.index"
echo "      pitch_shift: 0"
echo "      index_rate: 0.75"
echo ""
echo "Then verify with:  saymo test-tts \"Доброе утро коллеги.\""
