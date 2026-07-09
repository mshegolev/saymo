"""CLI tests for voice clone inventory and profile commands."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import soundfile as sf
import yaml
from click.testing import CliRunner

from saymo.commands import main


def _write_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, [0.0, 0.1, -0.1, 0.0], 16000)


def _write_config(tmp_path: Path, saymo_home: Path, f5_root: Path) -> Path:
    ckpt = f5_root / "models" / "ru" / "model_last.pt"
    vocab = f5_root / "models" / "ru" / "vocab.txt"
    ckpt.parent.mkdir(parents=True, exist_ok=True)
    ckpt.write_bytes(b"checkpoint")
    vocab.write_text("vocab", encoding="utf-8")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        textwrap.dedent(
            f"""
            speech:
              language: ru
            tts:
              engine: f5tts_clone
              realtime_engine: qwen3_clone
              f5tts:
                ckpt_file: "{ckpt}"
                vocab_file: "{vocab}"
            """
        ),
        encoding="utf-8",
    )
    return config_path


def test_voice_inventory_cli_writes_sanitized_json(tmp_path):
    saymo_home = tmp_path / ".saymo"
    f5_root = tmp_path / "F5TTS"
    config_path = _write_config(tmp_path, saymo_home, f5_root)
    sample = saymo_home / "voice_samples" / "voice_sample.wav"
    _write_wav(sample)
    sample.with_suffix(".txt").write_text("PRIVATE CLI TRANSCRIPT", encoding="utf-8")
    output = tmp_path / "inventory.json"

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "voice-inventory",
            "--saymo-home",
            str(saymo_home),
            "--f5-root",
            str(f5_root),
            "--json-output",
            str(output),
        ],
    )

    assert result.exit_code == 0
    assert "voice inventory" in result.output.lower()
    assert "f5tts_clone" in result.output
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["active_engine"] == "f5tts_clone"
    assert "PRIVATE CLI TRANSCRIPT" not in output.read_text(encoding="utf-8")


def test_voice_profile_cli_dry_run_apply_show_and_check(tmp_path):
    saymo_home = tmp_path / ".saymo"
    f5_root = tmp_path / "F5TTS"
    config_path = _write_config(tmp_path, saymo_home, f5_root)
    sample = saymo_home / "voice_samples" / "voice_sample.wav"
    _write_wav(sample)
    transcript = sample.with_suffix(".txt")
    transcript.write_text("PRIVATE PROFILE CLI TRANSCRIPT", encoding="utf-8")
    profiles_dir = tmp_path / "profiles"

    dry = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "voice-profile",
            "init",
            "--profile",
            "personal",
            "--voice-sample",
            str(sample),
            "--ref-text-file",
            str(transcript),
            "--engine",
            "f5tts_clone",
            "--profiles-dir",
            str(profiles_dir),
            "--dry-run",
        ],
    )

    assert dry.exit_code == 0
    assert "dry-run" in dry.output.lower()
    assert not (profiles_dir / "personal" / "profile.json").exists()

    apply = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "voice-profile",
            "init",
            "--profile",
            "personal",
            "--voice-sample",
            str(sample),
            "--ref-text-file",
            str(transcript),
            "--engine",
            "f5tts_clone",
            "--profiles-dir",
            str(profiles_dir),
            "--apply",
        ],
    )

    assert apply.exit_code == 0
    profile_path = profiles_dir / "personal" / "profile.json"
    assert profile_path.exists()
    assert "PRIVATE PROFILE CLI TRANSCRIPT" not in profile_path.read_text(encoding="utf-8")

    show = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "voice-profile",
            "show",
            "--profile",
            "personal",
            "--profiles-dir",
            str(profiles_dir),
        ],
    )
    assert show.exit_code == 0
    assert "personal" in show.output
    assert "approved for calls: no" in show.output.lower()

    check = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "voice-profile",
            "check",
            "--profile",
            "personal",
            "--profiles-dir",
            str(profiles_dir),
        ],
    )
    assert check.exit_code == 0
    assert "ready" in check.output.lower()


def test_voice_profile_cli_approve_reject_and_preview_dry_run(tmp_path):
    saymo_home = tmp_path / ".saymo"
    f5_root = tmp_path / "F5TTS"
    config_path = _write_config(tmp_path, saymo_home, f5_root)
    sample = saymo_home / "voice_samples" / "voice_sample.wav"
    _write_wav(sample)
    transcript = sample.with_suffix(".txt")
    transcript.write_text("PRIVATE PROFILE CLI TRANSCRIPT", encoding="utf-8")
    profiles_dir = tmp_path / "profiles"
    score_report = tmp_path / "score-report.md"
    score_report.write_text(
        "\n".join(
            [
                "# Voice Benchmark Score Report",
                "",
                "run status: complete",
                "score status: scored",
                "decision: approved",
                "promotion ready: yes",
                "",
            ]
        ),
        encoding="utf-8",
    )

    init = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "voice-profile",
            "init",
            "--profile",
            "personal",
            "--voice-sample",
            str(sample),
            "--ref-text-file",
            str(transcript),
            "--engine",
            "f5tts_clone",
            "--profiles-dir",
            str(profiles_dir),
            "--apply",
        ],
    )
    assert init.exit_code == 0

    approve = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "voice-profile",
            "approve",
            "--profile",
            "personal",
            "--profiles-dir",
            str(profiles_dir),
            "--score-report",
            str(score_report),
            "--similarity",
            "8",
            "--artifacts",
            "8",
            "--call-readiness",
            "8",
            "--apply",
        ],
    )
    assert approve.exit_code == 0
    assert "approved for calls: yes" in approve.output.lower()

    preview = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "voice-preview",
            "--profile",
            "personal",
            "--profiles-dir",
            str(profiles_dir),
            "--text",
            "PRIVATE PREVIEW TEXT",
            "--dry-run",
        ],
    )
    assert preview.exit_code == 0
    assert "preview-only audit" in preview.output.lower()
    assert "PRIVATE PREVIEW TEXT" not in preview.output

    reject = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "voice-profile",
            "reject",
            "--profile",
            "personal",
            "--profiles-dir",
            str(profiles_dir),
            "--score-report",
            str(score_report),
            "--reason",
            "too metallic",
            "--apply",
        ],
    )
    assert reject.exit_code == 0
    assert "approved for calls: no" in reject.output.lower()


def test_f5_presets_cli_list_show_and_apply_updates_config(tmp_path):
    saymo_home = tmp_path / ".saymo"
    f5_root = tmp_path / "F5TTS"
    config_path = _write_config(tmp_path, saymo_home, f5_root)

    listed = CliRunner().invoke(main, ["--config", str(config_path), "f5-presets", "list"])
    assert listed.exit_code == 0
    assert "approved" in listed.output
    assert "deliberate" in listed.output
    assert "sentence" in listed.output.lower()

    shown = CliRunner().invoke(
        main,
        ["--config", str(config_path), "f5-presets", "show", "calm"],
    )
    assert shown.exit_code == 0
    assert "sentence_pause_seconds" in shown.output
    assert "0.44" in shown.output

    applied = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "f5-presets",
            "apply",
            "deliberate",
            "--profile",
            "standup",
        ],
    )
    assert applied.exit_code == 0
    assert "deliberate" in applied.output

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    f5 = raw["tts"]["f5tts"]
    assert f5["pause_preset"] == "deliberate"
    assert f5["sentence_pause_seconds"] == 0.55
    assert f5["clause_pause_seconds"] == 0.28
    assert f5["silent_breath_pause_seconds"] == 0.85
    assert f5["breath_interval_sentences"] == 2
    assert raw["meetings"]["standup"]["voice"]["f5_pause_preset"] == "deliberate"


def test_f5_presets_cli_preview_and_review_are_sanitized(tmp_path):
    saymo_home = tmp_path / ".saymo"
    f5_root = tmp_path / "F5TTS"
    config_path = _write_config(tmp_path, saymo_home, f5_root)
    run_dir = tmp_path / "timing-preview"

    preview = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "f5-presets",
            "preview",
            "calm",
            "--text",
            "PRIVATE CLI TIMING TEXT",
            "--output-dir",
            str(run_dir),
            "--dry-run",
        ],
    )
    assert preview.exit_code == 0
    assert "timing preview" in preview.output.lower()
    assert "PRIVATE CLI TIMING TEXT" not in preview.output
    assert (run_dir / "manifest.json").exists()
    assert "PRIVATE CLI TIMING TEXT" not in (run_dir / "manifest.json").read_text(
        encoding="utf-8"
    )

    review = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "f5-presets",
            "review",
            str(run_dir),
            "--preferred",
            "calm",
            "--notes",
            "best natural pauses",
        ],
    )
    assert review.exit_code == 0
    assert "recommended preset: calm" in review.output.lower()
    assert "PRIVATE CLI TIMING TEXT" not in (run_dir / "timing-report.md").read_text(
        encoding="utf-8"
    )
