# Conversational AI Spec — Interactive Q&A Mode

> Saymo should answer questions during calls using local models.
> Target: Apple M1 Pro, 16GB RAM. Fully offline, no cloud APIs.

---

## Overview

New mode: `saymo auto --interactive`

After delivering the standup report, Saymo continues listening. When someone asks a question directed at "Миша", Saymo:
1. Transcribes the question (STT)
2. Generates an answer (LLM)
3. Speaks the answer in cloned voice (TTS)
4. Plays it into the call

```
┌─────────────────────────────────────────────────────────────────────┐
│                    saymo auto --interactive                         │
│                                                                     │
│  Phase 1: Standup Delivery (existing)                               │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Listen → Detect name → Play cached standup audio            │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                          │                                          │
│                          ▼                                          │
│  Phase 2: Q&A Mode (new)                                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                             │    │
│  │  Call Audio (BlackHole 16ch)                                │    │
│  │       │                                                     │    │
│  │       ▼                                                     │    │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐              │    │
│  │  │ Silero   │    │ mlx-     │    │ Question │              │    │
│  │  │ VAD      │───▶│ whisper  │───▶│ Detector │              │    │
│  │  │          │    │ STT      │    │          │              │    │
│  │  └──────────┘    └──────────┘    └────┬─────┘              │    │
│  │                                       │                     │    │
│  │                          ┌────────────┘                     │    │
│  │                          ▼                                  │    │
│  │                   ┌──────────────┐                          │    │
│  │                   │ Ollama LLM   │                          │    │
│  │                   │ (qwen3-4b)   │                          │    │
│  │                   │              │                          │    │
│  │                   │ System:      │                          │    │
│  │                   │ - standup    │                          │    │
│  │                   │   context    │                          │    │
│  │                   │ - JIRA tasks │                          │    │
│  │                   └──────┬───────┘                          │    │
│  │                          │                                  │    │
│  │                          ▼                                  │    │
│  │                   ┌──────────────┐                          │    │
│  │                   │ Qwen3-TTS    │                          │    │
│  │                   │ (streaming)  │───▶ BlackHole 2ch        │    │
│  │                   │ voice clone  │───▶ Headphones           │    │
│  │                   └──────────────┘                          │    │
│  │                                                             │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Pipeline Components

### 1. Voice Activity Detection (VAD)

**Purpose:** Detect when someone finishes speaking (end-of-utterance) to trigger transcription.

**Model:** Silero VAD v5

```python
# Silero VAD — lightweight, runs on CPU
import torch
model, utils = torch.hub.load('snakers4/silero-vad', 'silero_vad')
(get_speech_timestamps, _, read_audio, _, _) = utils
```

**Why VAD is needed:**
- Current system uses fixed 4s chunks → can cut mid-sentence
- For Q&A, we need full question before answering
- VAD detects speech end → triggers transcription of complete utterance

**Parameters:**
```python
vad_config:
  threshold: 0.5           # Speech probability threshold
  min_speech_duration: 0.5  # Minimum speech length (seconds)
  min_silence_duration: 0.8 # Silence after speech = end of utterance
  window_size: 512          # 32ms at 16kHz
```

**Memory:** ~2MB (negligible)

---

### 2. STT — Speech-to-Text

**Model:** mlx-whisper large-v3-turbo (see [STT-COMPARISON.md](STT-COMPARISON.md))

**Changes from current pipeline:**
- Replace faster-whisper → mlx-whisper
- Process full utterances (VAD-segmented) instead of fixed 4s chunks
- Keep 4s chunk mode for name detection, switch to utterance mode after trigger

```python
# Two modes
class STTEngine:
    async def transcribe_chunk(self, audio: np.ndarray) -> str:
        """Fixed 4s chunks for name detection (Phase 1)."""
        ...

    async def transcribe_utterance(self, audio: np.ndarray) -> str:
        """Full utterance for Q&A (Phase 2)."""
        # VAD-segmented, variable length
        ...
```

**Memory:** ~800MB GPU

---

### 3. Question Detection

**Purpose:** Determine if the transcribed speech is a question directed at Saymo.

**Two-level detection:**

**Level 1 — Keyword trigger (fast, regex):**
```python
# Patterns are built at runtime from config.user.name_variants.
# Example (name_variants=["Alex", "Саша"]):
QUESTION_PATTERNS = [
    r"(Alex|Саша)\s*,?\s*(а |вопрос|скажи|расскажи|объясни|почему|когда|как )",
    r"(Alex|Саша)\s*,?\s*\?",
    r"(Alex|Саша)\s*,?\s*что\s+(такое|значит|делать|будет)",
]
```

**Level 2 — LLM classification (if keyword matched):**
```python
CLASSIFICATION_PROMPT = """
Ты — классификатор. Определи, является ли фраза вопросом к {user_name}.
Ответь ТОЛЬКО "yes" или "no".

Фраза: "{text}"
"""
```

This avoids answering when someone just mentions the name in passing.

**Cooldown:** 5 seconds between answers (prevents rapid-fire responses).

---

### 4. LLM — Answer Generation

**Model:** Ollama with qwen3-4b (or llama3.2-3b as fallback)

**Why qwen3-4b:**
- 4B parameters fits in ~3GB RAM
- Good Russian language understanding
- Fast inference on M1 Pro (~2-5 tokens/s)
- Supports tool/function calling (future: JIRA lookup)

**System prompt with context:**

```python
# Template is user-configurable via config.prompts.qa_system_ru.
# Default template (generic, placeholders resolved at runtime):
QA_SYSTEM_PROMPT = """
Ты — {user_name}, {user_role}. Тебе задают вопросы на встрече.

Контекст твоей работы:
{standup_summary}

Задачи из трекера:
{jira_tasks}

Правила ответа:
- Отвечай кратко, 1-3 предложения
- Говори от первого лица
- Разговорный стиль
- Если не знаешь ответа — «не уверен, уточню позже»
- Не выдумывай факты
- Максимум 15 секунд устной речи
"""
```

**Conversation history:** Keep last 5 Q&A pairs in context for follow-up questions.

```python
@dataclass
class QAContext:
    standup_summary: str           # Today's standup text
    jira_tasks: dict               # Raw JIRA data
    conversation: list[dict]       # Last 5 exchanges
    max_history: int = 5
```

**Ollama API call:**
```python
response = await ollama.chat(
    model="qwen3-4b",
    messages=[
        {"role": "system", "content": system_prompt},
        *conversation_history,
        {"role": "user", "content": question},
    ],
    options={
        "temperature": 0.7,
        "num_predict": 150,    # ~15s of speech
    },
)
```

**Memory:** ~3GB

---

### 5. TTS — Text-to-Speech (Streaming)

**Model:** Qwen3-TTS 1.7B with voice clone (see [TTS-COMPARISON.md](TTS-COMPARISON.md))

**Streaming is critical for Q&A:**
- Without streaming: LLM generates full text → TTS generates full audio → play
- With streaming: LLM streams → TTS generates sentence by sentence → play immediately

**Expected latency:**

```
Without streaming:
  STT (0.5s) + LLM (3-5s) + TTS (2-3s) = 6-8.5s total delay

With streaming:
  STT (0.5s) + LLM first sentence (1-2s) + TTS first sentence (0.3s) = 1.8-2.8s
```

**Implementation:**

```python
async def answer_question(question: str, context: QAContext):
    """Stream LLM → TTS → playback."""

    # 1. Start LLM streaming
    sentence_buffer = ""
    async for token in ollama.stream(question, context):
        sentence_buffer += token

        # 2. When sentence complete, send to TTS
        if sentence_buffer.rstrip().endswith((".", "!", "?", "...")):
            normalized = normalize_for_tts(sentence_buffer)
            audio_chunk = await tts.synthesize(normalized)
            await play_audio(audio_chunk)
            sentence_buffer = ""

    # 3. Flush remaining text
    if sentence_buffer.strip():
        audio_chunk = await tts.synthesize(normalize_for_tts(sentence_buffer))
        await play_audio(audio_chunk)
```

**Memory:** ~3.5GB GPU

---

## Memory Budget

```
Component                        Memory      Device
──────────────────────────────────────────────────────
mlx-whisper large-v3-turbo       ~800MB      GPU (MLX)
Qwen3-TTS 1.7B                  ~3.5GB      GPU (MLX)
Ollama qwen3-4b                  ~3.0GB      RAM (CPU)
Silero VAD                       ~2MB        CPU
Python + libraries               ~500MB      RAM
macOS + system                   ~4.0GB      RAM
──────────────────────────────────────────────────────
Total                            ~11.8GB     / 16GB
Headroom                          ~4.2GB
```

> GPU memory on M1 is unified (shared with system RAM), so "GPU" and "RAM" draw from the same 16GB pool.
> 4.2GB headroom is sufficient for OS operations and spikes.

### Fallback if memory tight

If 16GB proves insufficient under load:
- Swap mlx-whisper to `small` model: saves ~350MB
- Swap Ollama to `llama3.2-1b`: saves ~1.5GB
- Use Piper TTS for Q&A (no clone): saves ~3GB

---

## CLI Interface

```bash
# Full interactive mode
saymo auto -p standup --interactive

# Interactive mode with custom LLM
saymo auto -p standup --interactive --qa-model qwen3-4b

# Disable Q&A, standup only (current behavior)
saymo auto -p standup
```

### Config

```yaml
# config.yaml — new section
interactive:
  enabled: false                          # opt-in
  qa_model: "qwen3-4b"                   # Ollama model for Q&A
  max_answer_tokens: 150                  # ~15s speech
  cooldown_seconds: 5                     # between answers
  max_conversation_history: 5             # Q&A pairs to keep
  vad:
    threshold: 0.5
    min_speech_duration: 0.5
    min_silence_duration: 0.8
  question_detection:
    keyword_trigger: true                 # regex patterns
    llm_classify: true                    # LLM verification
```

---

## New Files

```
saymo/
├── qa/
│   ├── __init__.py
│   ├── vad.py              # Silero VAD wrapper
│   ├── question_detector.py # Keyword + LLM question classification
│   ├── qa_engine.py         # Orchestrator: STT → LLM → TTS → play
│   └── context.py           # QAContext management (history, JIRA data)
├── tts/
│   └── qwen3_tts.py         # New TTS engine (Qwen3-TTS)
└── stt/
    └── mlx_whisper.py        # New STT engine (mlx-whisper)
```

---

## State Machine

```
                    ┌─────────────┐
                    │   IDLE      │
                    │ (listening) │
                    └──────┬──────┘
                           │ name detected
                           ▼
                    ┌─────────────┐
                    │  STANDUP    │
                    │ (playing)   │
                    └──────┬──────┘
                           │ playback done
                           ▼
              ┌────────────────────────┐
              │   Q&A LISTENING        │
              │ (VAD + STT + detect)   │◄──────────┐
              └────────────┬───────────┘           │
                           │ question detected     │
                           ▼                       │
              ┌────────────────────────┐           │
              │   ANSWERING            │           │
              │ (LLM → TTS → play)    │───────────┘
              └────────────────────────┘   answer done
                           │
                           │ 60s no questions
                           ▼
                    ┌─────────────┐
                    │   IDLE      │
                    │ (listening) │
                    └─────────────┘
```

**Timeout:** Return to IDLE after 60s of no questions in Q&A mode.

---

## Anti-Echo Protection

Critical: Saymo must not hear its own answers and respond to them.

```python
class EchoGuard:
    """Prevents self-listening during playback."""

    def __init__(self):
        self.speaking = asyncio.Event()

    async def play_with_guard(self, audio: bytes):
        self.speaking.set()         # Block transcription
        await play_audio(audio)
        await asyncio.sleep(0.5)    # Buffer for echo
        self.speaking.clear()       # Resume transcription

    def should_transcribe(self) -> bool:
        return not self.speaking.is_set()
```

This extends the existing `speaking` flag in `cli.py` auto mode.

---

## End-to-End Latency Target

| Step | Target | Notes |
|------|--------|-------|
| VAD (end-of-speech detection) | 0.8s | min_silence_duration |
| STT (full utterance) | 0.5s | mlx-whisper, ~5s utterance |
| Question classification | 0.1s | Regex first, LLM only if matched |
| LLM (first sentence) | 1-2s | Ollama streaming, qwen3-4b |
| TTS (first sentence) | 0.3s | Qwen3-TTS streaming |
| **Total (first audio)** | **2.7-3.7s** | Acceptable for conversation |

> 3-4 seconds is comparable to a human thinking pause before answering.

---

## Similar Projects (Reference)

- [MacBot](https://github.com/lukifer23/MacBot) — offline voice assistant for macOS (VAD + Whisper + LLM + Piper TTS)
- [ollama-STT-TTS](https://github.com/sancliffe/ollama-STT-TTS) — hands-free voice assistant with Ollama
- [june](https://github.com/mezbaul-h/june) — local voice chatbot (Ollama + Coqui TTS)
- [LocalVocal](https://localvocal.ai/) — MLX-based voice interface for LLMs on Apple Silicon

---

## Implementation Priority

1. **Phase A:** Add mlx-whisper STT engine (`stt/mlx_whisper.py`)
2. **Phase B:** Add Qwen3-TTS engine (`tts/qwen3_tts.py`)
3. **Phase C:** Add VAD + question detection (`qa/vad.py`, `qa/question_detector.py`)
4. **Phase D:** Build Q&A orchestrator (`qa/qa_engine.py`)
5. **Phase E:** Integrate into CLI `auto --interactive` command
6. **Phase F:** Test end-to-end with real calls

Each phase is independently testable and deployable.
