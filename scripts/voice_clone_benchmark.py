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
from typing import Any

from saymo.config import SaymoConfig, load_config
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
    settings: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", default="f5tts", choices=["f5tts"])
    parser.add_argument("--limit", type=int, default=len(PHRASES))
    parser.add_argument("--dry-run", action="store_true")
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
    }


async def generate_f5(run_dir: Path, limit: int, dry_run: bool) -> list[ClipRecord]:
    config = load_config()
    settings = _f5_settings(config, dry_run=dry_run)

    engine = None
    if not dry_run:
        if config.tts.engine != "f5tts_clone":
            raise SystemExit(
                f"Current config tts.engine is {config.tts.engine!r}; "
                "expected 'f5tts_clone' for real F5 generation."
            )
        engine = get_tts_engine(config)

    records: list[ClipRecord] = []
    for phrase_id, text in _selected_phrases(limit):
        output = run_dir / f"f5tts-{phrase_id:02d}.wav"
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
    (run_dir / "blind-review.md").write_text(
        "\n".join(review_lines) + "\n",
        encoding="utf-8",
    )


async def main() -> None:
    args = parse_args()
    run_dir = make_run_dir(args.out_root, args.engine)
    records = await generate_f5(run_dir, args.limit, args.dry_run)
    write_outputs(run_dir, records)
    print(run_dir)


if __name__ == "__main__":
    asyncio.run(main())
