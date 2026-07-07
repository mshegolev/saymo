#!/usr/bin/env python3
"""Generate voice-clone benchmark clips for Saymo engines."""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import random
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from saymo.analysis.voice_benchmark import (
    require_completed_score_report,
    write_benchmark_artifacts,
)
from saymo.config import SaymoConfig, load_config

QWEN_DEFAULT_MODEL = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
QWEN_DEFAULT_DEVICE_MAP = "auto"
QWEN_DEFAULT_DTYPE = "auto"
QWEN_DEFAULT_VOICE_SAMPLE = Path.home() / ".saymo" / "voice_samples" / "voice_sample.wav"
QWEN_LANGUAGE = "Russian"

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
    settings: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", default="f5tts", choices=["f5tts", "qwen3_base"])
    parser.add_argument("--limit", type=int, default=len(PHRASES))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--voice-sample",
        help=(
            "Reference WAV to use for voice cloning. Defaults to Saymo's F5-TTS "
            "default for F5 and ~/.saymo/voice_samples/voice_sample.wav for Qwen3 Base."
        ),
    )
    parser.add_argument(
        "--f5-nfe-step",
        dest="nfe_step",
        type=int,
        help="Override F5-TTS denoising steps for this benchmark run only.",
    )
    parser.add_argument(
        "--f5-speed",
        dest="speed",
        type=float,
        help="Override F5-TTS speed for this benchmark run only.",
    )
    parser.add_argument(
        "--f5-device",
        dest="device",
        help="Override F5-TTS device for this benchmark run only, e.g. cpu, mps, cuda.",
    )
    parser.add_argument(
        "--qwen-model",
        default=QWEN_DEFAULT_MODEL,
        help="Qwen3 Base model id for benchmark-only generation.",
    )
    parser.add_argument(
        "--qwen-device-map",
        default=QWEN_DEFAULT_DEVICE_MAP,
        help="Device map passed to Qwen3TTSModel.from_pretrained.",
    )
    parser.add_argument(
        "--qwen-dtype",
        default=QWEN_DEFAULT_DTYPE,
        help="Torch dtype passed to Qwen3TTSModel.from_pretrained.",
    )
    parser.add_argument(
        "--baseline-report",
        help=(
            "Completed and scored F5 baseline score-report.md required before "
            "real Qwen3 Base generation. Not needed for --dry-run."
        ),
    )
    ref_group = parser.add_mutually_exclusive_group()
    ref_group.add_argument(
        "--ref-text",
        help="Transcript override for the reference WAV. Not written to the manifest.",
    )
    ref_group.add_argument(
        "--ref-text-file",
        help="Read transcript override for the reference WAV from a UTF-8 text file.",
    )
    parser.add_argument(
        "--out-root",
        default=str(Path.home() / ".saymo" / "voice_benchmarks"),
        help="Directory where timestamped benchmark runs are created.",
    )
    return parser.parse_args()


def make_run_dir(out_root: str, engine: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = Path(out_root).expanduser() / f"{timestamp}-{engine}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def _selected_phrases(limit: int) -> list[tuple[int, str]]:
    if limit < 0:
        raise SystemExit("--limit must be greater than or equal to 0.")
    return list(enumerate(PHRASES[:limit], start=1))


def _f5_settings(config: SaymoConfig, *, dry_run: bool) -> dict[str, Any]:
    f5tts = config.tts.f5tts
    return {
        "dry_run": dry_run,
        "tts_engine": config.tts.engine,
        "nfe_step": f5tts.nfe_step,
        "speed": f5tts.speed,
        "device": f5tts.device,
        "ckpt_file": f5tts.ckpt_file,
        "vocab_file": f5tts.vocab_file,
        "ref_text_override_chars": len(f5tts.ref_text or ""),
    }


def _qwen3_base_settings(
    *,
    dry_run: bool,
    model: str,
    device_map: str,
    dtype: str,
    voice_sample: str,
    ref_text: str,
    baseline_report: str | None = None,
) -> dict[str, Any]:
    return {
        "dry_run": dry_run,
        "model": model,
        "device_map": device_map,
        "dtype": dtype,
        "voice_sample": voice_sample,
        "ref_text_chars": len(ref_text or ""),
        "baseline_report": baseline_report or "",
        "benchmark_path": "official_qwen_tts_base",
        "runtime_engine": "not_qwen3_clone",
    }


def apply_f5_overrides(
    config: SaymoConfig,
    *,
    nfe_step: int | None,
    speed: float | None,
    device: str | None,
    ref_text: str | None,
) -> SaymoConfig:
    overridden = copy.deepcopy(config)
    if nfe_step is not None:
        if nfe_step <= 0:
            raise SystemExit("--f5-nfe-step must be greater than 0.")
        overridden.tts.f5tts.nfe_step = nfe_step
    if speed is not None:
        if speed <= 0:
            raise SystemExit("--f5-speed must be greater than 0.")
        overridden.tts.f5tts.speed = speed
    if device:
        overridden.tts.f5tts.device = device
    if ref_text is not None:
        overridden.tts.f5tts.ref_text = ref_text.strip()
    return overridden


def _build_f5_engine(config: SaymoConfig, *, voice_sample: str | None):
    from saymo.tts.f5tts import F5TTSCloneTTS

    return F5TTSCloneTTS(
        language=config.speech.language,
        f5tts=config.tts.f5tts,
        voice_sample=voice_sample,
    )


def _resolve_ref_text(args: argparse.Namespace) -> str | None:
    if args.ref_text_file:
        return Path(args.ref_text_file).expanduser().read_text(encoding="utf-8").strip()
    if args.ref_text is not None:
        return args.ref_text.strip()
    return None


def _resolve_qwen_voice_sample(voice_sample: str | None) -> str:
    return str(Path(voice_sample).expanduser() if voice_sample else QWEN_DEFAULT_VOICE_SAMPLE)


def _resolve_qwen_ref_text(
    *,
    voice_sample: str,
    ref_text: str | None,
    ref_text_file: str | None,
    require_transcript: bool = False,
) -> str:
    if ref_text_file:
        return Path(ref_text_file).expanduser().read_text(encoding="utf-8").strip()
    if ref_text is not None:
        return ref_text.strip()

    sidecar = Path(voice_sample).expanduser().with_suffix(".txt")
    if sidecar.exists():
        return sidecar.read_text(encoding="utf-8").strip()

    if require_transcript:
        raise SystemExit(
            "Qwen3 real generation requires a transcript for the reference WAV. "
            "Pass --ref-text, --ref-text-file, or create a sidecar .txt next to --voice-sample."
        )
    return ""


async def generate_f5(
    run_dir: Path,
    limit: int,
    dry_run: bool,
    *,
    nfe_step: int | None,
    speed: float | None,
    device: str | None,
    voice_sample: str | None,
    ref_text: str | None,
) -> list[ClipRecord]:
    config = apply_f5_overrides(
        load_config(),
        nfe_step=nfe_step,
        speed=speed,
        device=device,
        ref_text=ref_text,
    )
    settings = _f5_settings(config, dry_run=dry_run)

    engine = None
    if not dry_run:
        if config.tts.engine != "f5tts_clone":
            raise SystemExit(
                f"Current config tts.engine is {config.tts.engine!r}; "
                "expected 'f5tts_clone' for real F5 generation."
            )
        engine = _build_f5_engine(config, voice_sample=voice_sample)

    records: list[ClipRecord] = []
    selected_phrases = _selected_phrases(limit)
    for index, (phrase_id, text) in enumerate(selected_phrases, start=1):
        output = run_dir / f"f5tts-{phrase_id:02d}.wav"
        print(f"[{index}/{len(selected_phrases)}] f5tts phrase {phrase_id}", flush=True)
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
                phrase_id=phrase_id,
                text=text,
                output_wav=str(output),
                latency_ms=latency_ms,
                settings=settings,
            )
        )
        write_outputs(run_dir, records, expected_clips=len(selected_phrases))

    if not records:
        write_outputs(run_dir, records, expected_clips=len(selected_phrases))
    return records


def _load_qwen3_base_model(*, model: str, device_map: str, dtype: str):
    try:
        from qwen_tts import Qwen3TTSModel
    except ModuleNotFoundError as exc:
        if exc.name == "qwen_tts" or "qwen_tts" in str(exc):
            raise SystemExit(
                "qwen_tts is not installed. Install Qwen3 benchmark support with: "
                "pip install -U qwen-tts"
            ) from None
        raise

    factory = getattr(Qwen3TTSModel, "from_pretrained", None)
    if factory is not None:
        return factory(model, device_map=device_map, dtype=dtype)
    return Qwen3TTSModel(model=model, device_map=device_map, dtype=dtype)


def _write_qwen_audio_result(result: Any, output: Path) -> None:
    if result is None and output.exists():
        return
    if isinstance(result, (bytes, bytearray)):
        output.write_bytes(bytes(result))
        return
    if isinstance(result, (str, Path)):
        output.write_bytes(Path(result).expanduser().read_bytes())
        return
    if isinstance(result, dict):
        audio = None
        for audio_key in ("audio", "wav", "waveform"):
            if audio_key in result and result[audio_key] is not None:
                audio = result[audio_key]
                break
        sample_rate = result.get("sample_rate") or result.get("sampling_rate") or 24000
        if audio is not None:
            _write_audio_array(output, audio, int(sample_rate))
            return
    if isinstance(result, tuple) and len(result) == 2:
        first, second = result
        if isinstance(first, int):
            _write_audio_array(output, second, first)
        elif isinstance(first, list) and first:
            _write_audio_array(output, first[0], int(second))
        else:
            _write_audio_array(output, first, int(second))
        return
    if hasattr(result, "save"):
        result.save(str(output))
        return
    raise TypeError(f"Unsupported Qwen3 voice clone result type: {type(result).__name__}")


def _write_audio_array(output: Path, audio: Any, sample_rate: int) -> None:
    import soundfile as sf

    sf.write(output, audio, sample_rate)


def _generate_qwen3_base_wav(
    *,
    output: Path,
    text: str,
    qwen_model: Any,
    voice_clone_prompt: Any,
) -> None:
    result = qwen_model.generate_voice_clone(
        text=text,
        language=QWEN_LANGUAGE,
        voice_clone_prompt=voice_clone_prompt,
    )
    _write_qwen_audio_result(result, output)


def _prepare_qwen3_base(
    *,
    model: str,
    device_map: str,
    dtype: str,
    voice_sample: str,
    ref_text: str,
) -> tuple[Any, Any, int]:
    start = time.perf_counter()
    qwen_model = _load_qwen3_base_model(model=model, device_map=device_map, dtype=dtype)
    if not hasattr(qwen_model, "create_voice_clone_prompt"):
        raise SystemExit(
            "Installed qwen_tts package does not expose create_voice_clone_prompt; "
            "upgrade Qwen3 benchmark support with: pip install -U qwen-tts"
        )
    voice_clone_prompt = qwen_model.create_voice_clone_prompt(
        ref_audio=voice_sample,
        ref_text=ref_text,
    )
    setup_latency_ms = int((time.perf_counter() - start) * 1000)
    return qwen_model, voice_clone_prompt, setup_latency_ms


async def generate_qwen3_base(
    run_dir: Path,
    limit: int,
    dry_run: bool,
    *,
    model: str,
    device_map: str,
    dtype: str,
    voice_sample: str,
    ref_text: str,
    baseline_report: str | None = None,
) -> list[ClipRecord]:
    settings = _qwen3_base_settings(
        dry_run=dry_run,
        model=model,
        device_map=device_map,
        dtype=dtype,
        voice_sample=voice_sample,
        ref_text=ref_text,
        baseline_report=baseline_report,
    )

    qwen_model = None
    voice_clone_prompt = None
    if not dry_run:
        if not baseline_report:
            raise SystemExit(
                "Real Qwen3 Base generation requires a completed F5 baseline score report. "
                "Pass --baseline-report ~/.saymo/voice_benchmarks/<f5-run>/score-report.md."
            )
        try:
            require_completed_score_report(baseline_report, label="F5 baseline")
        except ValueError as exc:
            raise SystemExit(str(exc)) from None
        qwen_model, voice_clone_prompt, setup_latency_ms = await asyncio.to_thread(
            _prepare_qwen3_base,
            model=model,
            device_map=device_map,
            dtype=dtype,
            voice_sample=voice_sample,
            ref_text=ref_text,
        )
        settings = {**settings, "setup_latency_ms": setup_latency_ms}

    records: list[ClipRecord] = []
    selected_phrases = _selected_phrases(limit)
    for index, (phrase_id, text) in enumerate(selected_phrases, start=1):
        output = run_dir / f"qwen3_base-{phrase_id:02d}.wav"
        print(f"[{index}/{len(selected_phrases)}] qwen3_base phrase {phrase_id}", flush=True)
        if dry_run:
            latency_ms = 0
            output.write_bytes(b"")
        else:
            start = time.perf_counter()
            await asyncio.to_thread(
                _generate_qwen3_base_wav,
                output=output,
                text=text,
                qwen_model=qwen_model,
                voice_clone_prompt=voice_clone_prompt,
            )
            latency_ms = int((time.perf_counter() - start) * 1000)

        records.append(
            ClipRecord(
                engine="qwen3_base",
                phrase_id=phrase_id,
                text=text,
                output_wav=str(output),
                latency_ms=latency_ms,
                settings=settings,
            )
        )
        write_outputs(run_dir, records, expected_clips=len(selected_phrases))

    if not records:
        write_outputs(run_dir, records, expected_clips=len(selected_phrases))
    return records


def write_outputs(
    run_dir: Path,
    records: list[ClipRecord],
    *,
    expected_clips: int | None = None,
) -> None:
    expected = len(records) if expected_clips is None else expected_clips
    write_benchmark_artifacts(
        run_dir,
        [asdict(record) for record in records],
        expected_clips=expected,
    )
    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "expected_clips": expected,
        "run_status": _run_status(records, expected),
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
    (run_dir / "blind-review.md").write_text(
        "\n".join(review_lines) + "\n",
        encoding="utf-8",
    )


def _run_status(records: list[ClipRecord], expected_clips: int) -> str:
    if records and all(record.settings.get("dry_run") for record in records):
        return "dry-run"
    if len(records) >= expected_clips:
        return "complete"
    return "partial"


async def main() -> None:
    args = parse_args()
    run_dir = make_run_dir(args.out_root, args.engine)
    if args.engine == "f5tts":
        await generate_f5(
            run_dir,
            args.limit,
            args.dry_run,
            nfe_step=args.nfe_step,
            speed=args.speed,
            device=args.device,
            voice_sample=args.voice_sample,
            ref_text=_resolve_ref_text(args),
        )
    elif args.engine == "qwen3_base":
        voice_sample = _resolve_qwen_voice_sample(args.voice_sample)
        await generate_qwen3_base(
            run_dir,
            args.limit,
            args.dry_run,
            model=args.qwen_model,
            device_map=args.qwen_device_map,
            dtype=args.qwen_dtype,
            voice_sample=voice_sample,
            ref_text=_resolve_qwen_ref_text(
                voice_sample=voice_sample,
                ref_text=args.ref_text,
                ref_text_file=args.ref_text_file,
                require_transcript=not args.dry_run,
            ),
            baseline_report=args.baseline_report,
        )
    print(run_dir)


if __name__ == "__main__":
    asyncio.run(main())
