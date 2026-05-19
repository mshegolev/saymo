"""Classify and persist live-call trigger training samples."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

from saymo.analysis.addressing import (
    classify_addressing,
    expand_trigger_phrases,
    looks_like_question,
    should_answer_decision,
)
from saymo.analysis.turn_detector import TurnDetector


@dataclass(frozen=True)
class TriggerCaptureSample:
    """Metadata for one captured call-audio window."""

    transcript: str
    category: str
    speaker: str
    trigger: bool
    addressing: str
    question: bool
    will_answer: bool
    reason: str
    rms: float
    peak: float


def audio_stats(audio: np.ndarray) -> tuple[float, float]:
    """Return RMS and peak amplitude for a mono float audio buffer."""
    if audio.size == 0:
        return 0.0, 0.0
    flat = np.asarray(audio, dtype=np.float32).flatten()
    rms = float(np.sqrt(np.mean(flat ** 2)))
    peak = float(np.max(np.abs(flat)))
    return rms, peak


def classify_trigger_sample(
    transcript: str,
    trigger_phrases: list[str],
    fuzzy_expansions: dict[str, list[str]] | None = None,
    *,
    rms: float = 0.0,
    peak: float = 0.0,
    silence_peak_threshold: float = 0.001,
) -> TriggerCaptureSample:
    """Classify a transcribed call window for trigger-training review.

    Categories:
    - ``asked_to_speak``: the window looks addressed to the configured user.
    - ``mentioned_me``: the configured user is mentioned but not called to speak.
    - ``question``: a question was asked, but not specifically to the user.
    - ``speech``: ordinary speech with no question/trigger.
    - ``silence``: no transcript and negligible signal.
    """
    text = " ".join((transcript or "").split())
    fuzzy_expansions = fuzzy_expansions or {}
    expanded = expand_trigger_phrases(trigger_phrases, fuzzy_expansions)

    if not text and peak < silence_peak_threshold:
        return TriggerCaptureSample(
            transcript="",
            category="silence",
            speaker="unknown",
            trigger=False,
            addressing="ignore",
            question=False,
            will_answer=False,
            reason="empty transcript and low signal",
            rms=rms,
            peak=peak,
        )

    detector = TurnDetector(
        name_variants=trigger_phrases,
        cooldown_seconds=0,
        fuzzy_expansions=fuzzy_expansions,
    )
    triggered = detector.check(text) if text else False
    decision = classify_addressing(text, expanded)
    question = bool(decision.is_question or looks_like_question(text))
    will_answer = bool(triggered and should_answer_decision(decision))

    if will_answer:
        category = "asked_to_speak"
    elif triggered and decision.label == "mentioned_not_addressed":
        category = "mentioned_me"
    elif question:
        category = "question"
    elif text:
        category = "speech"
    else:
        category = "silence"

    return TriggerCaptureSample(
        transcript=text,
        category=category,
        speaker="unknown",
        trigger=triggered,
        addressing=decision.label,
        question=question,
        will_answer=will_answer,
        reason=decision.reason,
        rms=rms,
        peak=peak,
    )


def save_trigger_sample(
    audio: np.ndarray,
    *,
    sample_rate: int,
    sample: TriggerCaptureSample,
    base_dir: Path,
    profile: str,
    sequence: int,
    created_at: str,
) -> tuple[Path, Path]:
    """Write a captured window as ``.wav`` plus adjacent JSON metadata."""
    category_dir = Path(base_dir).expanduser() / profile / sample.category
    category_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{_timestamp_stem(created_at)}_{sequence:04d}"
    wav_path = category_dir / f"{stem}.wav"
    meta_path = category_dir / f"{stem}.json"

    sf.write(
        str(wav_path),
        np.asarray(audio, dtype=np.float32),
        sample_rate,
        subtype="PCM_16",
    )
    metadata = {
        "profile": profile,
        "created_at": created_at,
        "sample_rate": sample_rate,
        "wav": wav_path.name,
        **asdict(sample),
    }
    meta_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return wav_path, meta_path


def _timestamp_stem(created_at: str) -> str:
    digits = re.sub(r"\D", "", created_at)
    if len(digits) >= 14:
        return f"{digits[:8]}_{digits[8:14]}"
    return digits or "sample"
