"""Tests for the voice clone benchmark helper script."""

from __future__ import annotations

import builtins
import importlib.util
import json
import sys
import types
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

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
    assert (tmp_path / "review.json").exists()
    assert (tmp_path / "score-report.md").exists()

    manifest_text = (tmp_path / "manifest.json").read_text(encoding="utf-8")
    assert transcript not in manifest_text
    manifest = json.loads(manifest_text)
    assert manifest["expected_clips"] == 2
    assert manifest["run_status"] == "dry-run"
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


def test_resolve_qwen_ref_text_prefers_explicit_then_sidecar_then_empty_dry_run(tmp_path):
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
    ) == ""


def test_resolve_qwen_ref_text_requires_transcript_for_real_generation(tmp_path):
    benchmark = _load_benchmark_module()
    voice_sample = tmp_path / "voice_sample.wav"
    voice_sample.write_bytes(b"RIFFfake")

    with pytest.raises(SystemExit, match="--ref-text"):
        benchmark._resolve_qwen_ref_text(
            voice_sample=str(voice_sample),
            ref_text=None,
            ref_text_file=None,
            require_transcript=True,
        )


@pytest.mark.anyio
async def test_generate_qwen3_base_reuses_model_prompt_and_writes_official_tuple(
    tmp_path, monkeypatch
):
    benchmark = _load_benchmark_module()
    voice_sample = tmp_path / "voice_sample.wav"
    voice_sample.write_bytes(b"RIFFfake")
    load_calls = []
    prompt_calls = []
    generate_calls = []
    audio = np.array([0.0, 0.25, -0.25, 0.0], dtype=np.float32)

    class FakeQwenModel:
        def create_voice_clone_prompt(self, *, ref_audio: str, ref_text: str):
            prompt_calls.append({"ref_audio": ref_audio, "ref_text": ref_text})
            return {"prompt_id": "prompt-1"}

        def generate_voice_clone(self, *, text: str, language: str, voice_clone_prompt):
            generate_calls.append(
                {
                    "text": text,
                    "language": language,
                    "voice_clone_prompt": voice_clone_prompt,
                }
            )
            return [audio], 16000

    class FakeQwen3TTSModel:
        @classmethod
        def from_pretrained(cls, model: str, *, device_map: str, dtype: str):
            load_calls.append(
                {"model": model, "device_map": device_map, "dtype": dtype}
            )
            return FakeQwenModel()

    fake_module = types.SimpleNamespace(Qwen3TTSModel=FakeQwen3TTSModel)
    monkeypatch.setitem(sys.modules, "qwen_tts", fake_module)

    records = await benchmark.generate_qwen3_base(
        tmp_path,
        limit=2,
        dry_run=False,
        model="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        device_map="cpu",
        dtype="float16",
        voice_sample=str(voice_sample),
        ref_text="reference transcript",
    )

    assert load_calls == [
        {
            "model": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            "device_map": "cpu",
            "dtype": "float16",
        }
    ]
    assert prompt_calls == [
        {"ref_audio": str(voice_sample), "ref_text": "reference transcript"}
    ]
    assert [call["text"] for call in generate_calls] == benchmark.PHRASES[:2]
    assert {id(call["voice_clone_prompt"]) for call in generate_calls} == {
        id(generate_calls[0]["voice_clone_prompt"])
    }
    assert all(call["language"] == benchmark.QWEN_LANGUAGE for call in generate_calls)

    generated_audio, sample_rate = sf.read(records[0].output_wav)
    assert sample_rate == 16000
    assert generated_audio.shape == audio.shape

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["records"]) == 2
    assert manifest["records"][0]["settings"]["dtype"] == "float16"
    assert "reference transcript" not in (tmp_path / "manifest.json").read_text(
        encoding="utf-8"
    )


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
    assert manifest["expected_clips"] == 2
    assert manifest["run_status"] == "partial"
    assert (tmp_path / "blind-review.md").exists()
    assert (tmp_path / "review.json").exists()
    assert "run status: partial" in (tmp_path / "score-report.md").read_text(
        encoding="utf-8"
    )
