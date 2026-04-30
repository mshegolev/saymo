# Voice Naturalness Guide

Rules and presets for making saymo's cloned voice output sound like a
real human on a call. Distilled from ElevenLabs, Inworld AI, Coqui
XTTS-v2 official docs, F5-TTS fine-tuning guides, and what we learned
generating real presentations through `scripts/synthesize_presentation.py`.

**Read this before** writing any new TTS-generation script or tweaking
the synthesis pipeline. The single biggest quality lever isn't a model
parameter — it's the reference recording and the source text. Fix
those first; touch params only if you've already done the rest.

## TL;DR — the 80/20

If you only have time for four things, do these:

1. **Re-record `~/.saymo/voice_samples/voice_sample.wav`** as 30–60 sec
   in a quiet room with a pop filter, in *the exact register you want
   the AI to use* (calm presenter / energetic standup / etc).
2. **Write the script the way you'd actually talk** — short sentences
   (8–15 words), commas as breath beats, em-dash for emphasis, digit
   form for English numbers.
3. **Use `NATURAL_PRESET`** from `saymo.tts.naturalness` (see below)
   instead of XTTS defaults.
4. **Listen back via `saymo review`** and re-roll the 2–3 sentences
   that sound off — usually fixed by a small text rewrite or
   `temperature: 0.78`.

## A. Reference recording

| Spec | XTTS one-shot (saymo default) | Fine-tune dataset | Pro / studio |
|---|---|---|---|
| Length | 30–60 sec single take | 5–20 min total | 20+ min, 120+ clips |
| Format | mono WAV | mono WAV | mono WAV |
| Sample rate | 22050 Hz | 22050 / 24000 Hz | 48 kHz |
| Bit depth | 16-bit | 16-bit | 24-bit |
| Peak | ≤ –3 dBFS | ≤ –3 dBFS | –5 dBFS true peak |
| Noise floor | ≤ –50 dB | ≤ –55 dB | ≤ –60 dB |
| Lead-in | 1–2 sec silence | 1–2 sec silence | — |

**Performance rules** (verbatim from ElevenLabs + Inworld):

* **Be consistent.** One register only. Don't mix animated and subdued
  in the same recording.
* **Match style to use case.** Recording for calls? Speak like you're
  on a call.
* **No filler** — `uh`, `um`, sighs, throat clears, coughs all get
  cloned. Edit them out.
* **No long mid-recording pauses** — they break prosody flow.
* **No mid-word cuts** when trimming. Cut at silence boundaries only.
* **Cover the prosody range** — include a question, statement,
  exclamation, list. Inworld script that works:

  > Are you ready to save big? Get set for the sale of the century!
  > Deals and discounts like never before! You won't want to miss this.

**Mic + room** (ElevenLabs):

* XLR condenser ($150–300: AT2020, Rode NT1) + Focusrite-class
  interface. USB condenser is fine for one-shot cloning.
* Pop filter between mouth and mic.
* ~20 cm distance, speak at a slight angle to dodge plosives.
* Quiet, deadened room. Blanket fort / closet against soft surfaces if
  no booth.

**Per-language samples**:

XTTS v2 supports 17 languages but cross-lingual transfer leaks accent.
For best quality, keep **one reference per output language**:

```
~/.saymo/voice_samples/
├── voice_sample.wav        # default (whatever language.config.speech.language is)
├── voice_sample_en.wav     # English-specific (optional)
└── voice_sample_ru.wav     # Russian-specific (optional)
```

`saymo.tts.naturalness.resolve_voice_sample(language)` picks the
right one with a fallback chain.

## B. Source text rules

XTTS prosody is driven by punctuation, sentence length, and first-word
energy. These rules apply to *any* text you feed the engine.

* **Short sentences, 8–15 words.** Long sentences flatten into
  monotone because XTTS's intonation contour resets only at `.` `?`
  `!`.
* **Commas as breath beats.** Add commas where you'd take a tiny
  inhale. *"In Q1, we focused on AI tools, and the framework."* reads
  with two micro-pauses.
* **Em-dash (—) = emphasis pause** (~200 ms). Use for *"First — AI
  Regression Guard."* style.
* **Ellipsis (...) = thoughtful pause.** Sparingly, max once per
  paragraph.
* **Discourse markers prime prosody**: start sentences with `So,`
  `Now,` `Also,` `Right,` `Look,`. XTTS first-word energy is sometimes
  flat; a soft filler smooths it.
* **Numbers** —
  * English: digit form (`76%`, `38 out of 50`). XTTS reads them
    naturally.
  * Russian: spell out (the `text_normalizer.py` ABBREV_MAP +
    `_num_to_words_ru` handle this).
* **Avoid all-caps and unknown abbreviations.** `ETL` is read
  letter-by-letter unless `vocabulary.abbreviations` says otherwise.
* **One language per sentence.** Mid-sentence code-switches
  mispronounce. For mixed text, write phonetic spelling: `"NS2"` →
  `"N-S-two"` for English output.
* **`[pause:N]` markers** are honoured by
  `synthesize_presentation.py`'s splitter — drop `[pause:1.5]`
  anywhere in the text to inject N seconds of silence.

## C. Synthesis-time rules

* **Sentence-by-sentence chunking.** XTTS quality drops past ~250
  characters per call. Always split.
* **Inter-sentence silence**: 200–300 ms.
* **Inter-paragraph break**: splice a real inhale from the reference
  sample, not `np.zeros(...)`. Use
  `saymo.tts.naturalness.load_breath_sample()` — it scans the first
  1.5 s of the reference for the quietest 250 ms window, normalises
  and attenuates it, and applies a 30 ms fade in/out.
* **Crossfade 20–30 ms** between sentence boundaries to kill
  micro-clicks (optional polish).
* **Loudness normalisation**: peak –3 dB, average ≈ –18 dB.
  Glip/Zoom/Teams compressors eat full-scale audio and sound boxy
  otherwise.
* **High-pass at 80 Hz** to remove room rumble (optional).

## D. XTTS v2 parameter presets

All presets live in `saymo.tts.naturalness` and are forwarded through
`CoquiCloneTTS.synthesize(text, **preset)`.

### `NATURAL_PRESET` — recommended default

```python
{
    "speed": 0.93,
    "temperature": 0.82,
    "repetition_penalty": 4.0,
    "length_penalty": 1.0,
    "top_k": 50,
    "top_p": 0.85,
    "enable_text_splitting": False,
}
```

Use for: presentations, monologues, Q&A answers, anything where
"sounds like a deliberate native speaker" is the goal.

### `CONSERVATIVE_PRESET` — when text is technical or numeric

```python
{
    "speed": 0.95,
    "temperature": 0.75,
    "repetition_penalty": 5.0,
    "top_k": 50,
    "top_p": 0.85,
}
```

Use for: dense numeric reports, code snippets, anything where you can
NOT afford a hallucination. Less expressive, more accurate.

### `ENERGETIC_PRESET` — short, punchy callouts

```python
{
    "speed": 1.0,
    "temperature": 0.85,
    "repetition_penalty": 3.5,
    "top_k": 50,
    "top_p": 0.90,
}
```

Use for: greetings, single-sentence triggers, demo voiceovers.

### Tuning cheat-sheet

| Symptom | Fix |
|---|---|
| Too rushed | `speed: 0.90` |
| Too slow / lethargic | `speed: 0.97` |
| Monotone / robotic | `temperature: 0.85`, `repetition_penalty: 3.5` |
| Garbled / hallucinating | `temperature: 0.78`, `repetition_penalty: 5.0` |
| Stutters mid-word | Raise `repetition_penalty` |
| Same word repeated | Lower `repetition_penalty` |

Tune **one knob at a time**. If output is bad, audit the reference
recording and the source text first.

## E. Quality verification

* Always run `saymo review` after generation — sentence-by-sentence
  playback with regenerate-on-bad.
* For programmatic verification, transcribe the synthesised WAV with
  `faster-whisper` and compare WER to the input text. >5% WER means
  the clone is mispronouncing — usually a sign of bad reference or
  wrong language tag.

## F. When to fine-tune

The defaults clone with a 30–60 sec one-shot. Fine-tuning gets you
from ~7/10 to ~9/10 voice similarity but costs hours.

* `saymo train-prepare` — record 100+ guided prompts.
* `saymo train-voice --epochs 5` — fine-tune XTTS GPT decoder
  (~2–3 h on Apple Silicon).
* `saymo train-eval` — blind A/B vs base.
* For 9–10/10: stack RVC on top of XTTS. See `docs/RVC-VOICE-CLONING.md`.

## G. Where Whisper fits

Whisper / WhisperX is **not** used for voice generation in saymo.
It's used in two places:

1. **`auto`-mode STT** — transcribe the live call audio so the turn
   detector can match your name (`saymo/stt/whisper_local.py`).
2. **Fine-tune dataset prep** — transcribe the 100 training prompts
   you record via `saymo train-prepare` so the trainer has aligned
   text+audio pairs. F5-TTS uses the same trick via WhisperX.

You can also repurpose it as a quality check: after generation,
transcribe the WAV with Whisper and diff against the source text.

## H. References

* [ElevenLabs Voice Cloning Overview](https://elevenlabs.io/docs/eleven-creative/voices/voice-cloning)
* [Inworld AI Voice Cloning Best Practices](https://docs.inworld.ai/tts/best-practices/voice-cloning)
* [Coqui XTTS-v2 model card](https://huggingface.co/coqui/XTTS-v2)
* [F5-TTS Fine Tuning Guide](https://instavar.com/blog/ai-production-stack/F5_TTS_Fine_Tuning_Voice_Cloning)
* [HF blog: Multilingual Voice Cloning with XTTS v2](https://huggingface.co/blog/norwooodsystems/multilingual-voice-cloning-with-xtts-v2)
* Saymo internal: `docs/VOICE-TRAINING.md`, `docs/RVC-VOICE-CLONING.md`,
  `docs/F5TTS-VOICE-CLONING.md`.
