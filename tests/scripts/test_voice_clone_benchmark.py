"""Tests for the voice clone benchmark helper script."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from saymo.config import SaymoConfig


def _load_benchmark_module():
    script = Path(__file__).resolve().parents[2] / "scripts" / "voice_clone_benchmark.py"
    spec = importlib.util.spec_from_file_location("voice_clone_benchmark", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_apply_f5_overrides_returns_copy_without_mutating_config():
    benchmark = _load_benchmark_module()
    config = SaymoConfig()
    config.tts.f5tts.nfe_step = 32
    config.tts.f5tts.speed = 1.0
    config.tts.f5tts.device = "cpu"

    overridden = benchmark.apply_f5_overrides(
        config,
        nfe_step=16,
        speed=0.95,
        device="mps",
        ref_text="короткий референс",
    )

    assert overridden is not config
    assert overridden.tts.f5tts.nfe_step == 16
    assert overridden.tts.f5tts.speed == 0.95
    assert overridden.tts.f5tts.device == "mps"
    assert overridden.tts.f5tts.ref_text == "короткий референс"

    assert config.tts.f5tts.nfe_step == 32
    assert config.tts.f5tts.speed == 1.0
    assert config.tts.f5tts.device == "cpu"
    assert config.tts.f5tts.ref_text == ""


def test_f5_settings_treats_none_ref_text_as_empty():
    benchmark = _load_benchmark_module()
    config = SaymoConfig()
    config.tts.f5tts.ref_text = None

    settings = benchmark._f5_settings(config, dry_run=True)

    assert settings["ref_text_override_chars"] == 0


@pytest.mark.anyio
async def test_generate_f5_writes_manifest_after_each_successful_clip(tmp_path, monkeypatch):
    benchmark = _load_benchmark_module()
    config = SaymoConfig()
    config.tts.engine = "f5tts_clone"

    class FakeEngine:
        def __init__(self):
            self.calls = 0

        async def synthesize(self, text: str) -> bytes:
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("stop after first clip")
            return b"RIFFfake"

    monkeypatch.setattr(benchmark, "load_config", lambda: config)
    monkeypatch.setattr(benchmark, "_build_f5_engine", lambda *_args, **_kwargs: FakeEngine())

    with pytest.raises(RuntimeError, match="stop after first clip"):
        await benchmark.generate_f5(
            tmp_path,
            limit=2,
            dry_run=False,
            nfe_step=None,
            speed=None,
            device=None,
            voice_sample=None,
            ref_text=None,
        )

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert [record["phrase_id"] for record in manifest["records"]] == [1]
    assert (tmp_path / "blind-review.md").exists()
