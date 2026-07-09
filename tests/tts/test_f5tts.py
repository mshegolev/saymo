"""Tests for the F5-TTS adapter."""

from __future__ import annotations

import asyncio
import io
from pathlib import Path

import numpy as np
import soundfile as sf

from saymo.config import F5TTSConfig
from saymo.tts import f5tts
from saymo.tts.f5tts import F5TTSCloneTTS


def test_f5tts_none_ref_text_uses_fallback_text(tmp_path, monkeypatch):
    voice_sample = tmp_path / "voice.wav"
    voice_sample.write_bytes(b"not a real wav")
    venv_python = tmp_path / "venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("#!/usr/bin/env python\n", encoding="utf-8")
    ckpt = tmp_path / "model.pt"
    ckpt.write_bytes(b"fake checkpoint")

    monkeypatch.setattr(f5tts, "DEFAULT_VENV_PYTHON", Path(venv_python))

    cfg = F5TTSConfig(ckpt_file=str(ckpt))
    cfg.ref_text = None

    engine = F5TTSCloneTTS(f5tts=cfg, voice_sample=str(voice_sample))

    assert engine._ref_text == "Это пример референтного аудио для клонирования голоса."


def test_f5tts_natural_pacing_inserts_sentence_silence(tmp_path):
    engine, calls = _fake_engine(tmp_path)
    engine.cfg.sentence_pause_seconds = 0.2
    engine.cfg.breath_interval_sentences = 0

    audio = asyncio.run(engine.synthesize("Первое. Второе."))

    data, sr = sf.read(io.BytesIO(audio), dtype="float32")
    assert sr == 1000
    assert calls == ["Первое.", "Второе."]
    assert len(data) == 400
    np.testing.assert_allclose(data[:100], 0.5, atol=0.01)
    np.testing.assert_allclose(data[100:300], 0.0, atol=0.001)
    np.testing.assert_allclose(data[300:], -0.5, atol=0.01)


def test_f5tts_natural_pacing_uses_silent_breath_pause_for_paragraph_break(tmp_path):
    engine, calls = _fake_engine(tmp_path)
    engine.cfg.sentence_pause_seconds = 0.1
    engine.cfg.silent_breath_pause_seconds = 0.6
    engine.cfg.breath_interval_sentences = 0

    audio = asyncio.run(engine.synthesize("Первое.\n\nВторое."))

    data, sr = sf.read(io.BytesIO(audio), dtype="float32")
    assert sr == 1000
    assert calls == ["Первое.", "Второе."]
    assert len(data) == 800
    silent_breath_pause = data[100:700]
    np.testing.assert_allclose(silent_breath_pause, 0.0, atol=0.001)
    np.testing.assert_allclose(data[700:], -0.5, atol=0.01)


def test_f5tts_natural_pacing_uses_silent_breath_pause_for_continuation_interval(tmp_path):
    engine, calls = _fake_engine(tmp_path)
    engine.cfg.sentence_pause_seconds = 0.1
    engine.cfg.silent_breath_pause_seconds = 0.6
    engine.cfg.breath_interval_sentences = 2

    audio = asyncio.run(engine.synthesize("Первое. Второе. Третье."))

    data, sr = sf.read(io.BytesIO(audio), dtype="float32")
    assert sr == 1000
    assert calls == ["Первое.", "Второе.", "Третье."]
    assert len(data) == 1000
    np.testing.assert_allclose(data[:100], 0.5, atol=0.01)
    np.testing.assert_allclose(data[100:200], 0.0, atol=0.001)
    np.testing.assert_allclose(data[200:300], -0.5, atol=0.01)
    np.testing.assert_allclose(data[300:900], 0.0, atol=0.001)
    np.testing.assert_allclose(data[900:], -0.5, atol=0.01)


def test_f5tts_natural_pacing_batches_spoken_chunks_once(tmp_path):
    engine, _ = _fake_engine(tmp_path)
    batches: list[tuple[str, ...]] = []

    def fake_synthesize_chunks_sync(chunks: list[str], output_dir: Path) -> list[Path]:
        batches.append(tuple(chunks))
        paths = []
        for index, _chunk in enumerate(chunks):
            out = output_dir / f"chunk-{index}.wav"
            sf.write(out, np.full(100, 0.25, dtype=np.float32), 1000)
            paths.append(out)
        return paths

    def forbidden_single_chunk_call(_text: str, _output_dir: Path) -> Path:
        raise AssertionError("natural pacing should batch F5 chunks in one model load")

    engine._synthesize_chunks_sync = fake_synthesize_chunks_sync
    engine._synthesize_sync = forbidden_single_chunk_call

    asyncio.run(engine.synthesize("Первое. Второе."))

    assert batches == [("Первое.", "Второе.")]


def _fake_engine(tmp_path):
    voice_sample = tmp_path / "voice.wav"
    sf.write(voice_sample, np.full(2000, 0.01, dtype=np.float32), 1000)
    (tmp_path / "voice.txt").write_text("референс", encoding="utf-8")

    venv_python = tmp_path / "venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("#!/usr/bin/env python\n", encoding="utf-8")

    ckpt = tmp_path / "model.pt"
    ckpt.write_bytes(b"fake checkpoint")

    cfg = F5TTSConfig(
        venv_python=str(venv_python),
        ckpt_file=str(ckpt),
    )
    engine = F5TTSCloneTTS(f5tts=cfg, voice_sample=str(voice_sample))
    calls: list[str] = []

    def fake_synthesize_chunks_sync(chunks: list[str], output_dir: Path) -> list[Path]:
        paths = []
        for text in chunks:
            calls.append(text)
            value = 0.5 if len(calls) == 1 else -0.5
            out = output_dir / f"out-{len(calls)}.wav"
            sf.write(out, np.full(100, value, dtype=np.float32), 1000)
            paths.append(out)
        return paths

    engine._synthesize_chunks_sync = fake_synthesize_chunks_sync
    return engine, calls
