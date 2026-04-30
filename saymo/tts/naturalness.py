"""Reusable presets and helpers that make XTTS v2 output sound human.

The full reasoning lives in ``docs/VOICE-NATURALNESS.md``. This module
just exposes the bits of that guide that any future TTS-generation
script (one-shot helpers, batch jobs, response-cache builders, …)
should reach for instead of re-deriving the same numbers.

Quick usage::

    from saymo.tts.naturalness import (
        NATURAL_PRESET,
        load_breath_sample,
        resolve_voice_sample,
        split_for_tts,
    )
    from saymo.tts.coqui_clone import CoquiCloneTTS

    tts = CoquiCloneTTS(
        voice_sample=str(resolve_voice_sample("en")),
        language="en",
    )
    breath = load_breath_sample(target_sr=22050)
    for chunk in split_for_tts(my_text):
        if isinstance(chunk, float):
            ...  # emit chunk seconds of silence
        elif chunk == "":
            ...  # emit breath + ~350ms silence
        else:
            audio_bytes = await tts.synthesize(chunk, **NATURAL_PRESET)

When tweaking a preset, also update the cheat-sheet in
``docs/VOICE-NATURALNESS.md`` so the rationale stays in one place.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import numpy as np
import soundfile as sf

from saymo.tts.coqui_clone import DEFAULT_VOICE_SAMPLE


# ---------------------------------------------------------------------------
# XTTS v2 parameter presets
# ---------------------------------------------------------------------------

# Recommended default. Slightly slower than 1.0 reads as "deliberate native
# speaker"; slightly higher temperature than the safe 0.75 default adds
# noticeable contour without going off the rails.
NATURAL_PRESET: dict[str, float | bool | int] = {
    "speed": 0.93,
    "temperature": 0.82,
    "repetition_penalty": 4.0,
    "length_penalty": 1.0,
    "top_k": 50,
    "top_p": 0.85,
    "enable_text_splitting": False,
}

# When you can NOT afford a hallucination (numeric tables, technical Q&A,
# code snippets read aloud). Less expressive but predictable.
CONSERVATIVE_PRESET: dict[str, float | bool | int] = {
    "speed": 0.95,
    "temperature": 0.75,
    "repetition_penalty": 5.0,
    "length_penalty": 1.0,
    "top_k": 50,
    "top_p": 0.85,
    "enable_text_splitting": False,
}

# Short, punchy callouts and demo voiceovers.
ENERGETIC_PRESET: dict[str, float | bool | int] = {
    "speed": 1.0,
    "temperature": 0.85,
    "repetition_penalty": 3.5,
    "length_penalty": 1.0,
    "top_k": 50,
    "top_p": 0.90,
    "enable_text_splitting": False,
}

PRESETS: dict[str, dict[str, float | bool | int]] = {
    "natural": NATURAL_PRESET,
    "conservative": CONSERVATIVE_PRESET,
    "energetic": ENERGETIC_PRESET,
}


# ---------------------------------------------------------------------------
# Reference-sample resolution (per-language fallback)
# ---------------------------------------------------------------------------

VOICE_SAMPLES_DIR = DEFAULT_VOICE_SAMPLE.parent


def resolve_voice_sample(language: str | None = None) -> Path:
    """Pick the best reference WAV for ``language``.

    Lookup order:
      1. ``~/.saymo/voice_samples/voice_sample_<lang>.wav``
      2. ``~/.saymo/voice_samples/voice_sample.wav`` (default)

    Falls through to the default sample if no language-specific file
    exists, which matches how ``CoquiCloneTTS`` behaves today. Per-
    language samples are recommended for cross-lingual quality — see
    ``docs/VOICE-NATURALNESS.md`` section "A. Reference recording".
    """
    if language:
        candidate = VOICE_SAMPLES_DIR / f"voice_sample_{language.lower()}.wav"
        if candidate.exists():
            return candidate
    return DEFAULT_VOICE_SAMPLE


# ---------------------------------------------------------------------------
# Breath splicing (Tier-3 polish — sounds way more human than np.zeros)
# ---------------------------------------------------------------------------

DEFAULT_BREATH_GAIN = 0.18  # quieter than speech, just a hint of inhale
DEFAULT_BREATH_DURATION_S = 0.25
DEFAULT_BREATH_SCAN_S = 1.5
DEFAULT_BREATH_FADE_S = 0.03


def load_breath_sample(
    target_sr: int,
    sample_path: Path | None = None,
    duration_s: float = DEFAULT_BREATH_DURATION_S,
    gain: float = DEFAULT_BREATH_GAIN,
    scan_window_s: float = DEFAULT_BREATH_SCAN_S,
    fade_s: float = DEFAULT_BREATH_FADE_S,
) -> np.ndarray | None:
    """Pull a low-energy slice out of the user's reference voice sample.

    Returns ``duration_s`` of audio that sounds like a soft inhale:
    we look at the first ``scan_window_s`` of the reference and pick
    the quietest ``duration_s`` window (typically the breath/lead-in
    before the speaker started). The slice is normalised, attenuated
    to ``gain`` of speech volume, and given a ``fade_s`` fade in/out
    so it splices seamlessly between sentences.

    Returns ``None`` if the sample is missing or shorter than the scan
    window — callers should fall back to ``np.zeros(...)`` in that
    case.
    """
    path = sample_path or DEFAULT_VOICE_SAMPLE
    if not path.exists():
        return None
    try:
        data, sr = sf.read(str(path), dtype="float32")
    except Exception:
        return None
    if data.ndim > 1:
        data = data.mean(axis=1)
    # Cheap nearest-neighbour resample; the segment is tiny so quality
    # of the resampler doesn't matter — it'll be attenuated to ~18%
    # anyway.
    if sr != target_sr and sr > 0:
        ratio = target_sr / sr
        data = np.interp(
            np.arange(int(len(data) * ratio)),
            np.arange(len(data)) * ratio,
            data,
        ).astype(np.float32)
    win = int(duration_s * target_sr)
    head = data[: max(int(scan_window_s * target_sr), win + 1)]
    if len(head) <= win:
        return None
    # Sliding-window mean energy → argmin = quietest window.
    energies = np.convolve(head ** 2, np.ones(win) / win, mode="valid")
    start = int(np.argmin(energies))
    seg = head[start : start + win].copy()
    peak = float(np.max(np.abs(seg)) or 1.0)
    seg = (seg / peak) * gain
    fade = max(int(fade_s * target_sr), 1)
    seg[:fade] *= np.linspace(0.0, 1.0, fade, dtype=np.float32)
    seg[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
    return seg.astype(np.float32)


# ---------------------------------------------------------------------------
# Source-text splitter
# ---------------------------------------------------------------------------

PAUSE_TOKEN = re.compile(r"\[pause:(\d+(?:\.\d+)?)\]")


def split_for_tts(text: str) -> list[str | float]:
    """Split source text into TTS-friendly chunks.

    Items in the returned list are one of:

    * non-empty ``str``  — sentence to synthesise (always ≤250 chars
      because XTTS quality drops past that — split long lines on
      ``.!?`` boundaries while keeping the punctuation).
    * empty ``str``      — paragraph break (caller should emit a
      breath sample + ~350 ms silence).
    * ``float``          — explicit silence in seconds, parsed from
      ``[pause:N]`` markers like ``[pause:1.5]``.
    """
    chunks: list[str | float] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            chunks.append("")
            continue
        for part in re.split(r"(?<=[.!?])\s+", line):
            part = part.strip()
            if not part:
                continue
            last = 0
            for m in PAUSE_TOKEN.finditer(part):
                head = part[last : m.start()].strip()
                if head:
                    chunks.append(head)
                chunks.append(float(m.group(1)))
                last = m.end()
            tail = part[last:].strip()
            if tail:
                chunks.append(tail)
    return chunks


# ---------------------------------------------------------------------------
# Discourse-marker primer
# ---------------------------------------------------------------------------

# XTTS first-word energy is sometimes flat. Starting a sentence with one of
# these soft fillers primes the prosody contour. Used by writers / scripted
# generators that want to sprinkle natural openers without hand-editing.
ENGLISH_DISCOURSE_MARKERS = (
    "So,", "Now,", "Also,", "Right,", "Look,", "Listen,", "Well,", "And,", "Plus,",
)
RUSSIAN_DISCOURSE_MARKERS = (
    "Итак,", "Так,", "Ну,", "Также,", "Кстати,", "Слушай,", "Смотри,", "Кроме того,",
)


def discourse_markers(language: str) -> Iterable[str]:
    """Return the discourse-marker pool for ``language`` (best-effort)."""
    return RUSSIAN_DISCOURSE_MARKERS if language.lower().startswith("ru") else ENGLISH_DISCOURSE_MARKERS


# ---------------------------------------------------------------------------
# Inter-segment silence defaults (kept here so all scripts agree)
# ---------------------------------------------------------------------------

INTER_SENTENCE_PAUSE_S = 0.25   # gap after `.`, `?`, `!`
INTER_PARAGRAPH_TAIL_S = 0.35   # silence appended after the breath splice
PARAGRAPH_FALLBACK_S = 0.6      # used when no breath sample is available


__all__ = [
    "NATURAL_PRESET",
    "CONSERVATIVE_PRESET",
    "ENERGETIC_PRESET",
    "PRESETS",
    "VOICE_SAMPLES_DIR",
    "resolve_voice_sample",
    "load_breath_sample",
    "split_for_tts",
    "PAUSE_TOKEN",
    "ENGLISH_DISCOURSE_MARKERS",
    "RUSSIAN_DISCOURSE_MARKERS",
    "discourse_markers",
    "INTER_SENTENCE_PAUSE_S",
    "INTER_PARAGRAPH_TAIL_S",
    "PARAGRAPH_FALLBACK_S",
]
