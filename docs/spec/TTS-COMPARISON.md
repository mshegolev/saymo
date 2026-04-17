# TTS Voice Cloning Model Comparison for Saymo

> Target hardware: Apple M1 Pro, 16GB RAM, 16 GPU cores
> Current engine: XTTS v2 (Coqui TTS, ~2GB)
> Primary language: Russian (ru)
> Use case: voice cloning for standup delivery + real-time Q&A responses

---

## Summary

| Model | RTF | Clone (min audio) | Russian | Size | MOS | Streaming | Status |
|-------|-----|-------------------|---------|------|-----|-----------|--------|
| **XTTS v2** (current) | 0.3-0.5x | 6s | Yes | ~2GB | 3.5-3.8 | No | Archived (Coqui closed) |
| **Qwen3-TTS 1.7B** | sub-100ms latency | 3s | **Yes** | ~3.5GB | 4.0+ | **Yes** | Active (Alibaba) |
| **F5-TTS** | 0.15 RTF | 10s | No (EN/ZH) | ~1.2GB | 3.8-4.1 | No | Active |
| **Fish Speech 1.5** | <150ms latency | 10-30s | Partial | ~2GB | 3.5-3.8 | Yes | Active |
| **CosyVoice 2** | 0.1-0.3x | 3-5s | No (ZH/EN) | ~4GB | 4.0+ | Yes | Active (Alibaba) |
| **Voxtral 4B (Mistral)** | 1.33x RT | Yes | Unknown | ~3.5GB (6bit) | 3.5+ | Yes | Active |
| **NeuTTS Air 0.5B** | Fast | 3s | Unknown | ~1GB (GGUF) | 3.5+ | Yes | Active |
| **IndexTTS** | Good | Short | Partial | ~2GB | 3.8+ | No | Active |

> RTF = Real-Time Factor. 0.15 means 1s of audio generated in 0.15s. Sub-1.0 = faster than realtime.

---

## Detailed Analysis

### 1. XTTS v2 (Current)

**What we have** (`saymo/tts/coqui_clone.py`):

```python
# Current implementation
self._tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
tts.tts_to_file(
    text=text,
    speaker_wav=self.voice_sample,  # ~/.saymo/voice_samples/voice_sample.wav
    language="ru",
    file_path=tmp_path,
)
```

**Pros:**
- Proven in Saymo, working pipeline
- Good Russian voice cloning
- 17 languages supported
- 6 seconds of reference audio enough

**Cons:**
- **Coqui AI shut down (Jan 2024)** — no more updates
- Pronunciation drifts in long texts
- Voice timbre inconsistent across chunks
- Slow loading (~10-30s cold start)
- No streaming output
- ~2GB model size

**Verdict:** Works but dead project. Should migrate to actively maintained alternative.

---

### 2. Qwen3-TTS 1.7B (Recommended)

Alibaba's latest TTS model. Best quality for Russian voice cloning as of 2026.

**Key specs:**
- 10 languages: ZH, EN, JA, KO, DE, FR, **RU**, PT, ES, IT
- 3-second voice clone (vs 6s for XTTS)
- Cross-lingual cloning (clone voice in RU, speak in EN)
- Streaming output support
- Apple Silicon optimized via MLX
- Sub-100ms first-token latency

**Quality comparison with XTTS v2:**

| Aspect | XTTS v2 | Qwen3-TTS |
|--------|---------|-----------|
| Short text quality | Good | Excellent |
| Long narration consistency | Drifts | Stable |
| Voice timbre preservation | Good | Excellent |
| Prosody/intonation | Decent | Natural |
| Russian pronunciation | Good | Very good |
| Min clone audio | 6s | 3s |

> "Qwen3 TTS 1.7B produces the most natural-sounding speech, with prosody, pronunciation consistency, and expressiveness clearly a step above" — [BentoML comparison](https://www.bentoml.com/blog/exploring-the-world-of-open-source-text-to-speech-models)

**Apple Silicon (MLX) setup:**

```bash
# Via mlx-audio
pip install mlx-audio

# Or dedicated repo
git clone https://github.com/kapi2800/qwen3-tts-apple-silicon
cd qwen3-tts-apple-silicon
pip install -r requirements.txt
```

**API example:**

```python
# Qwen3-TTS voice cloning
from qwen3_tts import Qwen3TTS

tts = Qwen3TTS(model="Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice")
audio = tts.clone_and_speak(
    text="Вчера я работал над автотестами для NS2 пайплайна.",
    reference_audio="voice_sample.wav",
    language="ru",
)
```

**Streaming for Q&A mode:**

```python
# Streaming generation (sentence by sentence)
for chunk in tts.stream(text=answer, reference_audio="voice_sample.wav"):
    play_audio(chunk)  # Play as generated
```

**Memory:** ~3.5GB (model weights)

---

### 3. F5-TTS

Flow-matching TTS. Fastest RTF (0.15), excellent English quality.

**Pros:**
- Fastest generation (RTF 0.15)
- Excellent English MOS (~4.1)
- Small model (~1.2GB)
- Active development

**Cons:**
- **No native Russian** — only English and Chinese
- Requires community fine-tune for RU
- 10s minimum reference audio (vs 3s for Qwen3)
- No streaming

**Verdict:** Best for English-only projects. Not suitable for Saymo without Russian fine-tune.

---

### 4. Fish Speech 1.5

LLM-based TTS with fast inference.

**Pros:**
- <150ms latency
- Good voice cloning from 10-30s sample
- 80+ languages claimed
- Streaming support
- Active development

**Cons:**
- Russian quality unverified/partial
- Needs more reference audio (10-30s vs 3s for Qwen3)
- Less battle-tested for Russian

**Verdict:** Promising but Russian quality uncertain. Second choice after Qwen3-TTS.

---

### 5. CosyVoice 2

Alibaba's two-stage TTS (AR + flow matching).

**Pros:**
- Excellent quality for Chinese
- Very fast (0.1-0.3x RTF)
- 3-5s reference audio
- Streaming support

**Cons:**
- **No Russian support** — Chinese and English only
- Large model (~4GB)
- Complex two-stage pipeline

**Verdict:** Not suitable (no Russian).

---

### 6. Voxtral 4B (Mistral)

Mistral's entry into TTS. Available as quantized MLX model.

**Pros:**
- Streaming support
- 6-bit quantized version ~3.5GB
- 1.33x realtime on M4 Pro
- Voice cloning capable

**Cons:**
- Russian support unconfirmed
- Larger model (4B parameters)
- Newer, less tested
- M4 benchmarks only (M1 may be slower)

**Verdict:** Worth watching, but Russian support unclear.

---

### 7. NeuTTS Air 0.5B

Neuphonic's compact on-device TTS.

**Pros:**
- Very small (~1GB GGUF)
- 3s voice clone
- GGUF format (llama.cpp compatible)
- Designed for consumer hardware

**Cons:**
- Russian support unconfirmed
- Very new (limited community testing)
- Smaller model may sacrifice quality

**Verdict:** Interesting for memory-constrained setups if Russian works.

---

## Recommendation

### Primary: Qwen3-TTS 1.7B

```
Quality:    MOS 4.0+ (best in class for open-source)
Russian:    Native support (1 of 10 languages)
Clone:      3 seconds of audio
Speed:      Sub-100ms first token, streaming
Memory:     ~3.5GB
Ecosystem:  MLX optimized, active development (Alibaba)
```

### Migration path from XTTS v2

**Phase 1: Add Qwen3TTS engine** (new file `saymo/tts/qwen3_tts.py`)

```python
from saymo.tts.base import TTSEngine

class Qwen3CloneTTS:
    """Qwen3-TTS voice cloning engine."""

    async def synthesize(self, text: str) -> bytes:
        # Load model, clone voice, generate audio
        ...

    async def synthesize_stream(self, text: str):
        # Streaming generation for Q&A mode
        for chunk in self._model.stream(...):
            yield chunk

    async def stop(self) -> None:
        ...
```

**Phase 2: Update config**

```yaml
tts:
  engine: "qwen3_clone"       # was: "coqui_clone"
  qwen3:
    model: "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
    min_clone_audio: 3         # seconds
  coqui_clone: ...             # keep as fallback
```

**Phase 3: Update CLI**

```python
# cli.py — add to _synthesize()
elif config.tts.engine == "qwen3_clone":
    return await Qwen3CloneTTS(
        voice_sample=voice_sample_path,
        language=config.speech.language,
    ).synthesize(text)
```

**Phase 4: Remove XTTS v2** (after validation)

### Memory comparison

```
Current:   XTTS v2          = ~2GB (CPU/GPU)
Proposed:  Qwen3-TTS 1.7B   = ~3.5GB (GPU preferred)
Delta:     +1.5GB
Total with STT + LLM:       ~11.3GB / 16GB ✓
```

---

## Benchmark Repository

For hands-on comparison with identical audio samples:
[reilxlx/TTS-Model-Comparison](https://github.com/reilxlx/TTS-Model-Comparison) — compares IndexTTS, Fish-Speech-1.5, SparkTTS, CosyVoice2, F5-TTS on voice similarity, naturalness, expressiveness.

---

## Sources

- [12 Best Open-Source TTS Models Compared (2025)](https://www.inferless.com/learn/comparing-different-text-to-speech---tts--models-part-2)
- [Best Open-Source TTS Models 2026 — BentoML](https://www.bentoml.com/blog/exploring-the-world-of-open-source-text-to-speech-models)
- [Qwen3-TTS GitHub](https://github.com/QwenLM/Qwen3-TTS)
- [Qwen3-TTS Apple Silicon](https://github.com/kapi2800/qwen3-tts-apple-silicon)
- [Qwen3-TTS Technical Report](https://arxiv.org/html/2601.15621v1)
- [Qwen3-TTS Complete Guide 2026](https://dev.to/czmilo/qwen3-tts-the-complete-2026-guide-to-open-source-voice-cloning-and-ai-speech-generation-1in6)
- [Best Open Source Voice Cloning 2026](https://www.siliconflow.com/articles/en/best-open-source-models-for-voice-cloning)
- [TTS-Model-Comparison Benchmark](https://github.com/reilxlx/TTS-Model-Comparison)
- [MLX-Audio project](https://github.com/Blaizzy/mlx-audio)
- [CodeSOTA TTS Benchmarks](https://www.codesota.com/guides/tts-models)
- [Voxtral TTS Local Benchmark on Apple Silicon](https://ainewshome.com/article/mistral-voxtral-4b-tts-local-benchmark-apple-silicon/)
