"""Tests for the voice clone benchmark helper script."""

from __future__ import annotations

import builtins
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
async def test_generate_qwen3_base_dry_run_writes_manifest_without_importing_qwen(
    tmp_path, monkeypatch
):
    benchmark = _load_benchmark_module()
    transcript = "TRANSCRIPT_SHOULD_NOT_LEAK"
    voice_sample = tmp_path / "voice_sample.wav"
    real_import = builtins.__import__

    def guard_import(name, *args, **kwargs):
        if name == "qwen_tts" or name.startswith("qwen_tts."):
            raise AssertionError("qwen_tts must not be imported in dry-run mode")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guard_import)

    records = await benchmark.generate_qwen3_base(
        tmp_path,
        limit=2,
        dry_run=True,
        model="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        device_map="auto",
        dtype="auto",
        voice_sample=str(voice_sample),
        ref_text=transcript,
    )

    assert [record.phrase_id for record in records] == [1, 2]
    assert (tmp_path / "qwen3_base-01.wav").read_bytes() == b""
    assert (tmp_path / "qwen3_base-02.wav").read_bytes() == b""
    assert (tmp_path / "blind-review.md").exists()

    manifest_text = (tmp_path / "manifest.json").read_text(encoding="utf-8")
    assert transcript not in manifest_text
    manifest = json.loads(manifest_text)
    assert len(manifest["records"]) == 2
    assert manifest["records"][0]["engine"] == "qwen3_base"
    assert manifest["records"][0]["text"] == benchmark.PHRASES[0]
    assert manifest["records"][0]["settings"] == {
        "dry_run": True,
        "model": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "device_map": "auto",
        "dtype": "auto",
        "voice_sample": str(voice_sample),
        "ref_text_chars": len(transcript),
    }


@pytest.mark.anyio
async def test_generate_qwen3_base_missing_package_exits_with_install_instruction(
    tmp_path, monkeypatch
):
    benchmark = _load_benchmark_module()
    voice_sample = tmp_path / "voice_sample.wav"
    voice_sample.write_bytes(b"RIFFfake")
    real_import = builtins.__import__

    def missing_qwen_import(name, *args, **kwargs):
        if name == "qwen_tts" or name.startswith("qwen_tts."):
            raise ModuleNotFoundError("No module named 'qwen_tts'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing_qwen_import)

    with pytest.raises(SystemExit, match="pip install -U qwen-tts"):
        await benchmark.generate_qwen3_base(
            tmp_path,
            limit=1,
            dry_run=False,
            model="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            device_map="auto",
            dtype="auto",
            voice_sample=str(voice_sample),
            ref_text="short transcript",
        )


def test_resolve_qwen_ref_text_prefers_explicit_then_sidecar_then_fallback(tmp_path):
    benchmark = _load_benchmark_module()
    voice_sample = tmp_path / "voice_sample.wav"
    voice_sample.write_bytes(b"RIFFfake")
    sidecar = tmp_path / "voice_sample.txt"
    sidecar.write_text("sidecar transcript\n", encoding="utf-8")
    ref_file = tmp_path / "explicit.txt"
    ref_file.write_text("file transcript\n", encoding="utf-8")

    assert (
        benchmark._resolve_qwen_ref_text(
            voice_sample=str(voice_sample),
            ref_text=" inline transcript ",
            ref_text_file=None,
        )
        == "inline transcript"
    )
    assert (
        benchmark._resolve_qwen_ref_text(
            voice_sample=str(voice_sample),
            ref_text=None,
            ref_text_file=str(ref_file),
        )
        == "file transcript"
    )
    assert (
        benchmark._resolve_qwen_ref_text(
            voice_sample=str(voice_sample),
            ref_text=None,
            ref_text_file=None,
        )
        == "sidecar transcript"
    )

    sidecar.unlink()

    assert benchmark._resolve_qwen_ref_text(
        voice_sample=str(voice_sample),
        ref_text=None,
        ref_text_file=None,
    ) == benchmark.QWEN_FALLBACK_REF_TEXT


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
