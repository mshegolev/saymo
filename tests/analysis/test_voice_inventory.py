"""Tests for read-only local voice asset inventory."""

from __future__ import annotations

import json
import os
from pathlib import Path

import soundfile as sf

from saymo.config import SaymoConfig


def _write_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, [0.0, 0.1, -0.1, 0.0], 16000)


def test_voice_inventory_classifies_assets_without_mutating_or_leaking_transcript(tmp_path):
    from saymo.analysis.voice_inventory import (
        build_voice_inventory,
        render_voice_inventory_markdown,
        voice_inventory_to_json,
    )

    saymo_home = tmp_path / ".saymo"
    f5_root = tmp_path / "F5TTS"
    voice_sample = saymo_home / "voice_samples" / "voice_sample.wav"
    transcript = voice_sample.with_suffix(".txt")
    training = saymo_home / "training_dataset"
    benchmark = saymo_home / "voice_benchmarks" / "20260707-120000-f5tts"
    cache = saymo_home / "audio_cache"
    ckpt = f5_root / "models" / "ru" / "F5TTS_v1_Base_v2" / "model_last.pt"
    vocab = f5_root / "models" / "ru" / "F5TTS_v1_Base" / "vocab.txt"

    _write_wav(voice_sample)
    transcript.write_text("PRIVATE TRANSCRIPT TEXT", encoding="utf-8")
    training.mkdir(parents=True)
    (training / "manifest.json").write_text("{}", encoding="utf-8")
    benchmark.mkdir(parents=True)
    (benchmark / "manifest.json").write_text("{}", encoding="utf-8")
    cache.mkdir(parents=True)
    ckpt.parent.mkdir(parents=True)
    ckpt.write_bytes(b"checkpoint")
    vocab.parent.mkdir(parents=True)
    vocab.write_text("vocab", encoding="utf-8")

    before = {
        path: (path.stat().st_mtime_ns, path.read_bytes())
        for path in (voice_sample, transcript, ckpt, vocab)
    }

    config = SaymoConfig()
    config.tts.engine = "f5tts_clone"
    config.tts.realtime_engine = "qwen3_clone"
    config.tts.f5tts.ckpt_file = str(ckpt)
    config.tts.f5tts.vocab_file = str(vocab)

    report = build_voice_inventory(config, saymo_home=saymo_home, f5_root=f5_root)
    payload = voice_inventory_to_json(report)
    rendered = render_voice_inventory_markdown(report)

    roles = {asset.role: asset for asset in report.assets}
    assert roles["voice_sample"].status == "usable"
    assert roles["voice_sample"].classification == "protected"
    assert roles["voice_transcript"].metadata["chars"] == len("PRIVATE TRANSCRIPT TEXT")
    assert roles["training_dataset"].classification == "protected"
    assert roles["f5_checkpoint"].status == "usable"
    assert roles["f5_vocab"].status == "usable"
    assert roles["benchmark_root"].status == "usable"
    assert roles["audio_cache"].status == "usable"
    assert report.active_engine == "f5tts_clone"
    assert report.realtime_engine == "qwen3_clone"

    serialized = json.dumps(payload, ensure_ascii=False)
    assert "PRIVATE TRANSCRIPT TEXT" not in serialized
    assert "PRIVATE TRANSCRIPT TEXT" not in rendered

    for path, (mtime, content) in before.items():
        assert path.stat().st_mtime_ns == mtime
        assert path.read_bytes() == content


def test_voice_inventory_marks_missing_paths_as_requires_user_action(tmp_path):
    from saymo.analysis.voice_inventory import build_voice_inventory

    config = SaymoConfig()
    config.tts.engine = "f5tts_clone"
    config.tts.f5tts.ckpt_file = str(tmp_path / "missing.pt")

    report = build_voice_inventory(
        config,
        saymo_home=tmp_path / ".saymo",
        f5_root=tmp_path / "F5TTS",
    )

    by_role = {asset.role: asset for asset in report.assets}
    assert by_role["voice_sample"].status == "missing"
    assert by_role["voice_sample"].classification == "requires_user_action"
    assert by_role["f5_checkpoint"].status == "missing"
    assert by_role["f5_checkpoint"].classification == "requires_user_action"
    assert os.fspath(tmp_path / "missing.pt") == by_role["f5_checkpoint"].path
