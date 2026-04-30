"""One-off helper: synthesize a presentation text in the user's cloned voice.

Reuses saymo's CoquiCloneTTS pipeline (XTTS v2, fine-tuned if available)
and the project-wide naturalness presets in ``saymo.tts.naturalness``.
Splits the script into slide segments, synthesizes each segment
separately for stable prosody, then concatenates into one WAV.

The naturalness rulebook (parameter presets, breath splicing rationale,
text-writing rules) lives in ``docs/VOICE-NATURALNESS.md``. Keep this
script in sync with that doc — change presets there, not here, so all
TTS-generation jobs in the repo stay consistent.

Usage:
    .venv/bin/python scripts/synthesize_presentation.py [OUT_PATH] \\
        [--preset natural|conservative|energetic] [--language en]

``[pause:N]`` markers in the source text emit explicit silence of N
seconds at that point.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

from saymo.tts.coqui_clone import CoquiCloneTTS
from saymo.tts.naturalness import (
    INTER_PARAGRAPH_TAIL_S,
    INTER_SENTENCE_PAUSE_S,
    PARAGRAPH_FALLBACK_S,
    PRESETS,
    load_breath_sample,
    resolve_voice_sample,
    split_for_tts,
)


PRESENTATION = """Hello today im introduce QA team benefits.
This slide shows our QA results for Q1.
We resolved 50 bugs, and only 12 went to production.
We caught 76% of bugs before release — 38 out of 50.
We verified 35 new ETLs, 33 are already closed.
We had 11 critical and high bugs in NS2, ERR, MTA and Customer360.
Compared to Q4: releases grew from 15 to 28 — that is plus 87%.
But production incidents went down from 13 to 12 — minus 8%.
So, almost two times more releases, and fewer incidents.
Also: zero rollbacks across 35 ETL deployments, and we met the SLA for all critical releases.

Next slide please.
In Q1 we focused on AI tools for QA.
First — AI E2E Test Generator. It reads JIRA, wiki and the merge request, and makes a 3-phase test: populate, trigger, verify. Result — about 80% less manual scripting.
Second — AI Assistant for QA. We shipped more than 40 Claude Code skills for BDC vars, HDFS, Oozie, Jenkins, Snowflake and Impala.
Third — Auto Bug Triage. AI reads Airflow and Oozie logs and creates a JIRA bug with reproduction steps. Time to bug report is 60% shorter.
Also we improved the framework: local Docker runner with auto git-sync, unified fixtures, BDC variables via etcd and GitLab MR with auto-merge, and one-step slash q a release skill — build, comment, status, Glip notification.

Next slide please.
Quick recap of Q1: 35 ETLs verified end-to-end, 50 bugs fixed, 76% pre-prod detection, AI tools used by the whole QA team.
Now plans for Q2.
First — AI Regression Guard. LLM checks ETL output: row counts, distributions, SLA drift. Pilot on ERR and NS2.
Second — Self-healing tests. AI fixes fixtures when schema changes. Goal — 50% less maintenance.
Third — Synthetic LLM data for NS2, ERR and FDM edge cases. Plus 30% edge-case coverage.
Fourth — Real-time validation. 24/7 monitoring with AI alerts before users see a problem.
Strategic goals: shift-left quality with PR-level checks, less than 20% of QA time on manual scripting and triage, and production incidents below 10 per quarter.

Thank you."""


SR_FALLBACK = 22050  # XTTS v2 default; only used if a [pause:] marker fires first


async def synth(out_path: Path, preset_name: str, language: str) -> int:
    if preset_name not in PRESETS:
        print(
            f"Unknown preset {preset_name!r}. Available: {', '.join(PRESETS)}",
            file=sys.stderr,
        )
        return 2
    preset = PRESETS[preset_name]

    voice_sample = resolve_voice_sample(language)
    print(f"Voice sample: {voice_sample}", flush=True)
    print(f"Preset: {preset_name} -> {preset}", flush=True)

    tts = CoquiCloneTTS(voice_sample=str(voice_sample), language=language)

    chunks = split_for_tts(PRESENTATION)
    spoken = [c for c in chunks if isinstance(c, str) and c]
    print(f"Sentences to synthesize: {len(spoken)}", flush=True)

    audio_segments: list[np.ndarray] = []
    sample_rate: int | None = None
    breath: np.ndarray | None = None

    def _silence(seconds: float) -> np.ndarray:
        sr = sample_rate or SR_FALLBACK
        return np.zeros(int(sr * seconds), dtype=np.float32)

    def _paragraph_break() -> np.ndarray:
        """Inhale splice + tail silence — see VOICE-NATURALNESS.md sec C."""
        sr = sample_rate or SR_FALLBACK
        if breath is not None:
            tail = np.zeros(int(sr * INTER_PARAGRAPH_TAIL_S), dtype=np.float32)
            return np.concatenate([breath.astype(np.float32), tail])
        return _silence(PARAGRAPH_FALLBACK_S)

    for idx, chunk in enumerate(chunks):
        if isinstance(chunk, float):
            print(f"[{idx + 1}/{len(chunks)}] <pause {chunk:.2f}s>", flush=True)
            audio_segments.append(_silence(chunk))
            continue
        if not chunk:
            audio_segments.append(_paragraph_break())
            continue
        print(f"[{idx + 1}/{len(chunks)}] {chunk[:80]}", flush=True)
        wav_bytes = await tts.synthesize(chunk, **preset)
        data, sr = sf.read(io.BytesIO(wav_bytes), dtype="float32")
        if data.ndim > 1:
            data = data.mean(axis=1)
        if sample_rate is None:
            sample_rate = sr
            breath = load_breath_sample(target_sr=sr, sample_path=voice_sample)
            if breath is not None:
                print(f"[breath sample loaded: {len(breath) / sr:.2f}s]", flush=True)
            else:
                print(
                    "[no breath sample — falling back to silent paragraph breaks]",
                    flush=True,
                )
        audio_segments.append(data.astype(np.float32))
        audio_segments.append(
            np.zeros(int(sr * INTER_SENTENCE_PAUSE_S), dtype=np.float32)
        )

    if not audio_segments or sample_rate is None:
        print("No audio produced", file=sys.stderr)
        return 1

    full = np.concatenate(audio_segments)
    sf.write(str(out_path), full, sample_rate, subtype="PCM_16")
    duration = len(full) / sample_rate
    print(
        f"Wrote {out_path} ({duration:.1f}s, {sample_rate} Hz, "
        f"{out_path.stat().st_size // 1024} KB)",
        flush=True,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Synthesize the embedded presentation text in the user's cloned "
            "voice. See docs/VOICE-NATURALNESS.md for parameter rationale."
        )
    )
    parser.add_argument(
        "out",
        nargs="?",
        default=str(Path.home() / "Desktop" / "qa_presentation.wav"),
        help="Output WAV path (default: ~/Desktop/qa_presentation.wav).",
    )
    parser.add_argument(
        "--preset",
        default="natural",
        choices=sorted(PRESETS.keys()),
        help="XTTS prosody preset (default: natural).",
    )
    parser.add_argument(
        "--language",
        default="en",
        help=(
            "XTTS language code (default: en). The script picks "
            "voice_sample_<lang>.wav if it exists, else voice_sample.wav."
        ),
    )
    args = parser.parse_args()
    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    return asyncio.run(synth(out_path, args.preset, args.language))


if __name__ == "__main__":
    sys.exit(main())
