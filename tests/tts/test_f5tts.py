"""Tests for the F5-TTS adapter."""

from __future__ import annotations

from pathlib import Path

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
