# STT Model Comparison for Saymo

> Target hardware: Apple M1 Pro, 16GB RAM, 16 GPU cores
> Current engine: faster-whisper (small, CPU int8)
> Primary language: Russian (ru)
> Use case: real-time name detection + question transcription in calls

---

## Summary

| Model | RTF (M1 Pro) | Russian | Size | Backend | Streaming | Latency (4s chunk) |
|-------|-------------|---------|------|---------|-----------|-------------------|
| **faster-whisper small** (current) | ~17x RT | Good | 461MB | CPU int8 | No | ~1-2s |
| **faster-whisper large-v3-turbo** | ~8x RT | Excellent | 800MB | CPU int8 | No | ~2-3s |
| **mlx-whisper large-v3-turbo** | ~30x RT | Excellent | 809MB | MLX GPU | Yes | ~0.5s |
| **WhisperKit large-v3-turbo** | ~20x RT | Excellent | ~800MB | CoreML NE | Yes | ~0.7s |
| **whisper.cpp large-v3-turbo** | ~15-20x RT | Excellent | 800MB | Metal GPU | Yes | ~0.8s |
| **Parakeet (mlx)** | 3-6x faster than Whisper | Weak | ~600MB | MLX GPU | Yes | ~0.2s |

> RTF = Real-Time Factor. 17x RT means 4s of audio processed in ~0.24s.

---

## Detailed Analysis

### 1. faster-whisper (Current)

**What we have now** (`saymo/stt/whisper_local.py`):

```python
# Current config
model_size = "small"      # 461MB
device = "cpu"
compute_type = "int8"
language = "ru"
beam_size = 5
best_of = 3
vad_filter = False        # Disabled to catch short names like "Миш"
```

**Pros:**
- Proven, stable in production
- Good Russian recognition
- int8 quantization keeps CPU usage low
- No GPU memory needed

**Cons:**
- CPU-only on macOS (no CUDA)
- `small` model misses some words
- No streaming — must wait for full chunk
- 1-2s latency per 4s chunk

**Verdict:** Works but leaves GPU idle. Upgrading to large-v3-turbo on MLX would use GPU and improve accuracy.

---

### 2. mlx-whisper large-v3-turbo (Recommended)

Apple's MLX framework, native GPU acceleration on M-series chips. Benchmarked ~2x faster than faster-whisper on M1 Pro.

**Benchmarks (M1 Pro):**
- `large-v3-turbo`: ~1.0s for 30s audio (30x realtime)
- `small`: ~0.6s for 30s audio (50x realtime)
- vs faster-whisper small: 18.7s vs 32.1s on same audio (1.7x faster)

**Pros:**
- Native Apple Silicon GPU acceleration via MLX
- Same Whisper models, same accuracy
- Streaming support (word-level timestamps)
- Drop-in API replacement for faster-whisper
- large-v3-turbo: 2x faster than large-v3, same WER

**Cons:**
- ~800MB GPU memory for large-v3-turbo
- MLX ecosystem less mature than CUDA
- Slightly newer, less battle-tested

**Migration from faster-whisper:**

```python
# Before (faster-whisper)
from faster_whisper import WhisperModel
model = WhisperModel("small", device="cpu", compute_type="int8")
segments, _ = model.transcribe(audio, language="ru")

# After (mlx-whisper)
import mlx_whisper
result = mlx_whisper.transcribe(
    audio,
    path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
    language="ru",
)
text = result["text"]
```

**Install:**
```bash
pip install mlx-whisper
# Model auto-downloads from HuggingFace on first use
```

---

### 3. WhisperKit (CoreML + Neural Engine)

Swift-native Whisper optimized for Apple Neural Engine. Halves Whisper latency (200-500ms → 150-300ms).

**Pros:**
- Uses Neural Engine (frees GPU for TTS)
- Very low power consumption
- Streaming with word timestamps

**Cons:**
- Swift library — harder to integrate with Python
- Requires CoreML model conversion
- Less flexible than Python-based solutions

**Verdict:** Best if building a Swift app. For Python-based Saymo, mlx-whisper is simpler.

---

### 4. whisper.cpp (Metal)

C++ implementation with Metal GPU backend.

**Pros:**
- Very fast on Apple Silicon via Metal
- Low memory footprint
- CLI + C API + Python bindings

**Cons:**
- Python bindings less ergonomic
- Build complexity (cmake + Metal shaders)
- Less Pythonic API

**Verdict:** Good alternative if mlx-whisper has issues. Similar performance.

---

### 5. Parakeet (NVIDIA, mlx port)

NVIDIA's CTC-based STT. 3-6x faster than Whisper. ~80ms latency on Apple Silicon.

**Pros:**
- Fastest option by far
- Excellent English accuracy
- Streaming native

**Cons:**
- **Weak Russian support** — trained primarily on English
- No multilingual model comparable to Whisper
- Smaller community

**Verdict:** Not suitable for Saymo (Russian is primary language).

---

## Recommendation

### Primary: mlx-whisper + large-v3-turbo

```
Speed:     ~30x realtime on M1 Pro (0.5s for 4s chunk)
Accuracy:  Whisper large-v3 level (best multilingual)
Russian:   Excellent (same as OpenAI Whisper)
Memory:    ~800MB GPU
Streaming: Yes (word timestamps)
Install:   pip install mlx-whisper
```

### Why not stay with faster-whisper?

| Metric | faster-whisper small | mlx-whisper large-v3-turbo |
|--------|---------------------|---------------------------|
| Speed | ~17x RT (CPU) | ~30x RT (GPU) |
| Accuracy (WER) | ~12% (RU) | ~5% (RU) |
| Model quality | Small (244M params) | Large-turbo (809M params) |
| GPU usage | 0% | ~800MB |
| Streaming | No | Yes |

**Upgrade gives**: 2x speed + 2x accuracy + streaming, using idle GPU.

### Memory budget impact

```
Current:   faster-whisper small   =  461MB RAM (CPU)
Proposed:  mlx-whisper l-v3-turbo =  800MB GPU + ~200MB RAM
Delta:     +539MB total
```

Fits within 16GB budget even with Qwen3-TTS (3.5GB) + Ollama (3GB).

---

## Config Changes

```yaml
# config.yaml — proposed
stt:
  engine: "mlx_whisper"          # was: "faster_whisper"
  mlx_whisper:
    model: "mlx-community/whisper-large-v3-turbo"
    language: "ru"
  whisper:                       # keep as fallback
    model_size: "small"
    device: "cpu"
    compute_type: "int8"
```

---

## Sources

- [mac-whisper-speedtest benchmarks](https://github.com/anvanvan/mac-whisper-speedtest)
- [Whisper Performance on Apple Silicon](https://www.voicci.com/blog/apple-silicon-whisper-performance.html)
- [MLX vs Faster-Whisper streaming comparison](https://medium.com/@GenerationAI/streaming-with-whisper-in-mlx-vs-faster-whisper-vs-insanely-fast-whisper-37cebcfc4d27)
- [Whisper vs Parakeet on Apple Silicon](https://macparakeet.com/blog/whisper-to-parakeet-neural-engine/)
- [Whisper large-v3-turbo announcement](https://whispernotes.app/blog/introducing-whisper-large-v3-turbo)
- [MLX-Audio project](https://github.com/Blaizzy/mlx-audio)
