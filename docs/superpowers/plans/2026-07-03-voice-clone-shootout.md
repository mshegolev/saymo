# Voice Clone Shootout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repeatable local benchmark that compares F5-TTS Russian against a small number of challenger voice-cloning engines before changing Saymo's production TTS engine.

**Architecture:** Keep Saymo on `f5tts_clone` while adding benchmark-only wrappers and reports. Generated clips, manifests, and scores live under `~/.saymo/voice_benchmarks/<run_id>/`; repo changes are limited to scripts/docs unless a challenger passes the promotion gate.

**Tech Stack:** Python 3.11+, Click/Rich patterns from Saymo, existing `saymo.tts.factory`, F5-TTS subprocess integration, JSON manifests, WAV output, optional isolated external environments for Qwen3/CosyVoice.

---

## File Structure

- Create: `scripts/voice_clone_benchmark.py`  
  CLI harness that generates candidate audio, writes manifest JSON, and prepares a blind review order.
- Create: `docs/voice-clone-shootout.md`  
  Operator guide for running the benchmark and interpreting results.
- Modify: `docs/F5TTS-VOICE-CLONING.md`  
  Add a short note that F5 is the current baseline and must be benchmarked before changing engines.
- Optional later create: `saymo/tts/qwen3_base_adapter.py`  
  Only after the F5 baseline report exists and Qwen3 Base is approved for download.
- Optional later create: `saymo/tts/cosyvoice_adapter.py`  
  Only if Qwen3 is blocked or loses the benchmark.

## Task 1: Add F5 Baseline Benchmark Harness

**Files:**
- Create: `scripts/voice_clone_benchmark.py`
- Test manually with: `uv run python scripts/voice_clone_benchmark.py --engine f5tts --limit 1 --dry-run`

- [ ] **Step 1: Create CLI skeleton**

Create `scripts/voice_clone_benchmark.py` with:

```python
#!/usr/bin/env python3
"""Generate voice-clone benchmark clips for Saymo engines."""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from saymo.config import load_config
from saymo.tts.factory import get_tts_engine


PHRASES = [
    "Доброе утро, коллеги. Вчера я закрыл проверку релиза.",
    "Сегодня планирую пройтись по логам и добить автотесты.",
    "Блокеров сейчас нет, но есть риск по стабильности окружения.",
    "Если деплой пройдет без ошибок, я обновлю статус задачи.",
    "Да, я проверял этот сценарий на стейдже.",
    "Можно уточнить, какой именно кейс сейчас воспроизводится?",
    "По моим данным, проблема не в конфиге, а в данных.",
    "Я вернусь с результатом после повторного прогона.",
    "Сейчас лучше не трогать прод, пока не закроем проверку.",
    "Коротко: тесты зеленые, но нужен еще один контрольный запуск.",
]


@dataclass
class ClipRecord:
    engine: str
    phrase_id: int
    text: str
    output_wav: str
    latency_ms: int
    settings: dict


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", default="f5tts", choices=["f5tts"])
    parser.add_argument("--limit", type=int, default=len(PHRASES))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--out-root",
        default=str(Path.home() / ".saymo" / "voice_benchmarks"),
    )
    return parser.parse_args()


def make_run_dir(out_root: str, engine: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = Path(out_root).expanduser() / f"{ts}-{engine}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


async def generate_f5(run_dir: Path, limit: int, dry_run: bool) -> list[ClipRecord]:
    config = load_config()
    if config.tts.engine != "f5tts_clone":
        raise SystemExit(
            f"Current config tts.engine is {config.tts.engine!r}; expected 'f5tts_clone'."
        )
    engine = get_tts_engine(config)
    records: list[ClipRecord] = []

    for idx, text in enumerate(PHRASES[:limit], start=1):
        output = run_dir / f"f5tts-{idx:02d}.wav"
        if dry_run:
            latency_ms = 0
            output.write_bytes(b"")
        else:
            start = time.perf_counter()
            audio = await engine.synthesize(text)
            latency_ms = int((time.perf_counter() - start) * 1000)
            output.write_bytes(audio)
        records.append(
            ClipRecord(
                engine="f5tts",
                phrase_id=idx,
                text=text,
                output_wav=str(output),
                latency_ms=latency_ms,
                settings={
                    "tts_engine": config.tts.engine,
                    "nfe_step": config.tts.f5tts.nfe_step,
                    "speed": config.tts.f5tts.speed,
                    "device": config.tts.f5tts.device,
                    "ckpt_file": config.tts.f5tts.ckpt_file,
                    "vocab_file": config.tts.f5tts.vocab_file,
                },
            )
        )
    return records


def write_outputs(run_dir: Path, records: list[ClipRecord]) -> None:
    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "records": [asdict(record) for record in records],
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    review = records[:]
    random.shuffle(review)
    review_lines = [
        "# Blind Review Order",
        "",
        "Score each clip 1-5 for similarity, naturalness, pronunciation, artifacts.",
        "",
    ]
    for index, record in enumerate(review, start=1):
        review_lines.append(f"{index}. `{record.output_wav}`")
    (run_dir / "blind-review.md").write_text("\n".join(review_lines), encoding="utf-8")


async def main() -> None:
    args = parse_args()
    run_dir = make_run_dir(args.out_root, args.engine)
    if args.engine == "f5tts":
        records = await generate_f5(run_dir, args.limit, args.dry_run)
    else:
        raise SystemExit(f"Unsupported engine: {args.engine}")
    write_outputs(run_dir, records)
    print(run_dir)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Run dry-run**

Run:

```bash
uv run python scripts/voice_clone_benchmark.py --engine f5tts --limit 1 --dry-run
```

Expected:

- Command exits `0`.
- It prints a path under `~/.saymo/voice_benchmarks/`.
- That path contains `manifest.json` and `blind-review.md`.

- [ ] **Step 3: Run real F5 baseline**

Run:

```bash
uv run python scripts/voice_clone_benchmark.py --engine f5tts
```

Expected:

- Command exits `0`.
- Ten WAV files are created.
- `manifest.json` includes latency for each phrase.

- [ ] **Step 4: Commit harness**

Run:

```bash
git add scripts/voice_clone_benchmark.py
git commit -m "feat(tts): add voice clone benchmark harness"
```

## Task 2: Add Operator Guide

**Files:**
- Create: `docs/voice-clone-shootout.md`
- Modify: `docs/F5TTS-VOICE-CLONING.md`

- [ ] **Step 1: Create guide**

Create `docs/voice-clone-shootout.md` with:

```markdown
# Voice Clone Shootout

This guide explains how to compare Saymo voice-cloning engines before changing the production `tts.engine`.

## Baseline

The current baseline is F5-TTS Russian:

- `tts.engine: f5tts_clone`
- `~/F5TTS/models/ru/F5TTS_v1_Base_v2/model_last.pt`
- `~/F5TTS/models/ru/F5TTS_v1_Base/vocab.txt`

Do not change production config until a challenger wins blind A/B.

## Reference Recordings

Keep these files:

- `~/.saymo/voice_samples/voice_sample.wav`
- `~/.saymo/voice_samples/voice_sample.txt`

For a serious benchmark, record two additional clean references:

- 15 seconds: normal standup voice
- 45-60 seconds: statement, question, list, mild emphasis

## Run F5 Baseline

```bash
uv run python scripts/voice_clone_benchmark.py --engine f5tts
```

The command prints a run directory under:

```text
~/.saymo/voice_benchmarks/
```

Open `blind-review.md`, listen to each WAV, and score:

- similarity
- naturalness
- Russian pronunciation
- artifacts
- latency

## Promotion Gate

A challenger can replace F5 only if:

- it wins at least 7 of 10 blind A/B comparisons on similarity,
- it has no worse artifacts than F5,
- it is repeatable from documented commands,
- for live-call use, it supports sub-8-second end-to-end answers or a cached fallback.

## Candidate Order

1. F5-TTS Russian baseline.
2. Qwen3-TTS Base zero-shot.
3. CosyVoice 3 zero-shot.
4. GPT-SoVITS fine-tune only if zero-shot candidates fail.

Do not install the next candidate until the previous candidate has a report.
```

- [ ] **Step 2: Add cross-link to F5 guide**

Append this section to `docs/F5TTS-VOICE-CLONING.md`:

```markdown
## Benchmark Policy

F5-TTS Russian is the current Saymo baseline. Before replacing it with another engine, run the voice clone shootout in `docs/voice-clone-shootout.md` and keep the generated report under `~/.saymo/voice_benchmarks/`.
```

- [ ] **Step 3: Commit guide**

Run:

```bash
git add docs/voice-clone-shootout.md docs/F5TTS-VOICE-CLONING.md
git commit -m "docs(tts): document voice clone benchmark policy"
```

## Task 3: Qwen3 Base Challenger Gate

**Files:**
- Modify: `scripts/voice_clone_benchmark.py`
- Create only after approval: `docs/qwen3-base-voice-clone-notes.md`

- [ ] **Step 1: Confirm model choice before download**

Run no install commands yet. Confirm that the challenger is Qwen3-TTS Base, not the already-tested CustomVoice cache.

Decision text to record in `docs/qwen3-base-voice-clone-notes.md`:

```markdown
# Qwen3 Base Voice Clone Notes

Qwen3-TTS Base is the first challenger because it is the Qwen3 variant intended for rapid voice cloning from user audio. The benchmark starts with zero-shot generation only. LoRA training is out of scope until zero-shot output beats or nearly matches F5.
```

- [ ] **Step 2: Install Qwen3 only after F5 report exists**

Precondition:

```bash
find ~/.saymo/voice_benchmarks -name manifest.json | tail -1
```

Expected:

- At least one F5 baseline `manifest.json` exists.

Installation command is intentionally not listed here because model install instructions must be verified against the current Qwen3 upstream docs at execution time.

- [ ] **Step 3: Extend benchmark with a Qwen adapter**

Add an adapter only after the upstream command is known. The adapter must:

- accept the same `PHRASES`,
- use the same reference audio path,
- write WAVs under the same run directory shape,
- write latency and model settings into `manifest.json`.

- [ ] **Step 4: Compare Qwen against F5**

Run both engines, then create a manual score report:

```text
~/.saymo/voice_benchmarks/<run_id>/score-report.md
```

Required result fields:

```markdown
# Score Report

Winner: F5-TTS Russian or Qwen3-TTS Base

## Summary

| Metric | F5 | Qwen3 Base | Winner |
|---|---:|---:|---|
| Similarity |  |  |  |
| Naturalness |  |  |  |
| Russian pronunciation |  |  |  |
| Artifacts |  |  |  |
| Latency |  |  |  |

## Decision

Keep F5 unless Qwen3 wins at least 7 of 10 blind A/B pairs on similarity.
```

## Task 4: CosyVoice Challenger Gate

**Files:**
- Modify: `scripts/voice_clone_benchmark.py`
- Create only after Qwen report: `docs/cosyvoice-voice-clone-notes.md`

- [ ] **Step 1: Start only if Qwen is blocked or loses**

Precondition:

```bash
find ~/.saymo/voice_benchmarks -name score-report.md | tail -1
```

Expected:

- A score report exists showing Qwen was blocked or did not beat F5.

- [ ] **Step 2: Record CosyVoice decision**

Create `docs/cosyvoice-voice-clone-notes.md`:

```markdown
# CosyVoice Voice Clone Notes

CosyVoice is tested only after the F5 baseline and Qwen3 Base challenger. It must run in an isolated environment and produce the same benchmark outputs: WAV files, `manifest.json`, and `score-report.md`.
```

- [ ] **Step 3: Add CosyVoice adapter**

Adapter requirements:

- no changes to production `tts.engine`,
- isolated dependency environment,
- same phrase set,
- same output manifest schema,
- same blind review process.

- [ ] **Step 4: Stop after CosyVoice report**

If CosyVoice does not beat F5, do not install more zero-shot engines in this pass. Move to Task 5.

## Task 5: Fine-Tune Track Decision

**Files:**
- Create: `docs/voice-clone-finetune-decision.md`

- [ ] **Step 1: Create decision doc**

Create `docs/voice-clone-finetune-decision.md`:

```markdown
# Voice Clone Fine-Tune Decision

## Trigger

Start this track only if F5, Qwen3 Base, and CosyVoice fail the similarity gate.

## Preserved Assets

- `~/.saymo/training_dataset/`
- `~/.saymo/training_dataset_backup_20260422/`
- `~/.saymo/training_dataset_backup_bigdata_20260422/`
- `~/.saymo/voice_samples/`

## Candidate

GPT-SoVITS is the first fine-tune candidate. XTTS/RVC/Applio is not restored unless GPT-SoVITS is blocked.

## Gate

Fine-tune work starts only after a clean reference/dataset audit confirms the existing recordings are good enough.
```

- [ ] **Step 2: Commit decision doc**

Run:

```bash
git add docs/voice-clone-finetune-decision.md
git commit -m "docs(tts): define voice clone fine-tune gate"
```

## Self-Review Checklist

- [ ] The plan keeps current production TTS on F5 until a challenger passes A/B.
- [ ] The plan avoids reinstalling XTTS/RVC/Applio.
- [ ] Training datasets and voice samples are preserved.
- [ ] Every model download is gated by a previous benchmark report.
- [ ] The first executable task produces a useful F5 baseline report without adding a new dependency.
- [ ] The plan has no unfinished sections.
