"""CLI tests for voice clone inventory and profile commands."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import soundfile as sf
import yaml
from click.testing import CliRunner

from saymo.commands import main
from saymo.tts.f5_corpus import get_f5_preview_corpus_entry


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
    assert "f5_pause_presets" not in raw["meetings"]["standup"]["voice"]


def test_f5_presets_cli_apply_source_type_writes_profile_override_only(tmp_path):
    saymo_home = tmp_path / ".saymo"
    f5_root = tmp_path / "F5TTS"
    config_path = _write_config(tmp_path, saymo_home, f5_root)
    before = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    applied = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "f5-presets",
            "apply",
            "calm",
            "--profile",
            "standup",
            "--source-type",
            "prepared",
        ],
    )

    assert applied.exit_code == 0
    assert "calm" in applied.output
    assert "standup" in applied.output
    assert "prepared" in applied.output
    assert "config:" not in applied.output.lower()

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert raw["tts"]["f5tts"] == before["tts"]["f5tts"]
    voice = raw["meetings"]["standup"]["voice"]
    assert "f5_pause_preset" not in voice
    assert voice["f5_pause_presets"] == {"prepared": "calm"}


def test_f5_presets_cli_apply_source_type_preserves_existing_profile_and_global(tmp_path):
    saymo_home = tmp_path / ".saymo"
    f5_root = tmp_path / "F5TTS"
    config_path = _write_config(tmp_path, saymo_home, f5_root)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    raw["tts"]["f5tts"]["pause_preset"] = "approved"
    raw["meetings"] = {
        "standup": {
            "voice": {
                "f5_pause_preset": "calm",
                "f5_pause_presets": {"prepared": "deliberate"},
            }
        }
    }
    config_path.write_text(
        yaml.safe_dump(raw, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    applied = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "f5-presets",
            "apply",
            "crisp",
            "--profile",
            "standup",
            "--source-type",
            "response_cache",
        ],
    )

    assert applied.exit_code == 0
    updated = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert updated["tts"]["f5tts"]["pause_preset"] == "approved"
    voice = updated["meetings"]["standup"]["voice"]
    assert voice["f5_pause_preset"] == "calm"
    assert voice["f5_pause_presets"] == {
        "prepared": "deliberate",
        "response_cache": "crisp",
    }


def test_f5_presets_cli_apply_source_type_requires_profile_without_partial_write(tmp_path):
    saymo_home = tmp_path / ".saymo"
    f5_root = tmp_path / "F5TTS"
    config_path = _write_config(tmp_path, saymo_home, f5_root)
    before = config_path.read_text(encoding="utf-8")

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "f5-presets",
            "apply",
            "calm",
            "--source-type",
            "prepared",
        ],
    )

    assert result.exit_code != 0
    assert "--source-type requires --profile" in result.output
    assert config_path.read_text(encoding="utf-8") == before


def test_f5_presets_cli_apply_source_type_errors_do_not_partially_write(tmp_path):
    saymo_home = tmp_path / ".saymo"
    f5_root = tmp_path / "F5TTS"
    config_path = _write_config(tmp_path, saymo_home, f5_root)
    before = config_path.read_text(encoding="utf-8")

    bad_preset = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "f5-presets",
            "apply",
            "robot",
            "--profile",
            "standup",
            "--source-type",
            "prepared",
        ],
    )
    assert bad_preset.exit_code != 0
    assert "Unknown F5 pause preset" in bad_preset.output
    assert config_path.read_text(encoding="utf-8") == before

    bad_source = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "f5-presets",
            "apply",
            "calm",
            "--profile",
            "standup",
            "--source-type",
            "cache",
        ],
    )
    assert bad_source.exit_code != 0
    assert "Unknown F5 source type" in bad_source.output
    assert "prepared" in bad_source.output
    assert "response_cache" in bad_source.output
    assert "spontaneous" in bad_source.output
    assert config_path.read_text(encoding="utf-8") == before


def test_f5_presets_corpus_cli_list_shows_safe_metadata_only(tmp_path):
    saymo_home = tmp_path / ".saymo"
    f5_root = tmp_path / "F5TTS"
    config_path = _write_config(tmp_path, saymo_home, f5_root)

    listed = CliRunner().invoke(
        main,
        ["--config", str(config_path), "f5-presets", "corpus", "list"],
    )

    assert listed.exit_code == 0
    assert "standup-blocked" in listed.output
    assert "clause_heavy" in listed.output
    assert "Direct handoff" in listed.output
    assert "I am blocked on one dependency" not in listed.output


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
    manifest_text = (run_dir / "manifest.json").read_text(encoding="utf-8")
    assert "PRIVATE CLI TIMING TEXT" not in manifest_text
    manifest = json.loads(manifest_text)
    assert len(manifest["records"]) == 2
    assert {record["source_kind"] for record in manifest["records"]} == {"manual"}
    assert all("corpus" not in record for record in manifest["records"])

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
    report_text = (run_dir / "timing-report.md").read_text(encoding="utf-8")
    assert "## Current vs Candidate Deltas" in report_text
    assert "duration_delta=" in report_text
    assert "chars_per_second_delta=" in report_text
    assert "words_per_minute_delta=" in report_text
    assert "pause_total_delta=" in report_text
    assert "PRIVATE CLI TIMING TEXT" not in report_text


def test_f5_presets_preview_selected_corpus_category(tmp_path):
    saymo_home = tmp_path / ".saymo"
    f5_root = tmp_path / "F5TTS"
    config_path = _write_config(tmp_path, saymo_home, f5_root)
    run_dir = tmp_path / "timing-preview-standup"

    preview = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "f5-presets",
            "preview",
            "calm",
            "--corpus",
            "standup",
            "--output-dir",
            str(run_dir),
            "--dry-run",
        ],
    )

    assert preview.exit_code == 0
    manifest_text = (run_dir / "manifest.json").read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)
    assert len(manifest["records"]) == 4
    assert {record["source_kind"] for record in manifest["records"]} == {
        "builtin_corpus"
    }
    assert {record["corpus"]["category"] for record in manifest["records"]} == {
        "standup"
    }
    assert "I am blocked on one dependency" not in manifest_text
    assert "I am blocked on one dependency" not in (run_dir / "timing-report.md").read_text(
        encoding="utf-8"
    )


def test_f5_presets_preview_selected_corpus_id(tmp_path):
    saymo_home = tmp_path / ".saymo"
    f5_root = tmp_path / "F5TTS"
    config_path = _write_config(tmp_path, saymo_home, f5_root)
    run_dir = tmp_path / "timing-preview-id"

    preview = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "f5-presets",
            "preview",
            "calm",
            "--corpus-id",
            "standup-blocked",
            "--output-dir",
            str(run_dir),
            "--dry-run",
        ],
    )

    assert preview.exit_code == 0
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    records = manifest["records"]
    assert len(records) == 2
    assert [record["label"] for record in records] == [
        "standup-blocked:current",
        "standup-blocked:candidate",
    ]
    assert [Path(record["output_wav"]).name for record in records] == [
        "standup-blocked-current-approved.wav",
        "standup-blocked-candidate-calm.wav",
    ]
    assert all(record["corpus"]["id"] == "standup-blocked" for record in records)


def test_f5_presets_preview_selected_corpus_id_writes_sanitized_metrics(tmp_path):
    saymo_home = tmp_path / ".saymo"
    f5_root = tmp_path / "F5TTS"
    config_path = _write_config(tmp_path, saymo_home, f5_root)
    entry = get_f5_preview_corpus_entry("standup-blocked")
    run_dir = tmp_path / "timing-preview-id-metrics"
    artifact_names = ("manifest.json", "review.json", "timing-report.md")

    preview = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "f5-presets",
            "preview",
            "calm",
            "--corpus-id",
            "standup-blocked",
            "--output-dir",
            str(run_dir),
            "--dry-run",
        ],
    )

    assert preview.exit_code == 0
    artifact_text = "\n".join(
        (run_dir / name).read_text(encoding="utf-8") for name in artifact_names
    )
    report_text = (run_dir / "timing-report.md").read_text(encoding="utf-8")
    assert entry.text not in artifact_text
    assert "PRIVATE MANUAL PREVIEW TEXT" not in artifact_text
    assert "duration=" in report_text
    assert "chars/s" in report_text
    assert "wpm" in report_text
    assert (
        "sentence" in report_text
        and "clause" in report_text
        and "paragraph" in report_text
        and "silent_breath" in report_text
    )
    assert "## Current vs Candidate Deltas" in report_text
    assert "standup-blocked" in report_text
    assert "duration_delta=" in report_text
    assert "chars_per_second_delta=" in report_text
    assert "words_per_minute_delta=" in report_text
    assert "pause_total_delta=" in report_text

    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    records = manifest["records"]
    assert len(records) == 2
    for record in records:
        metrics = record["metrics"]
        assert metrics["audio_duration_seconds"] is None
        assert metrics["estimated_total_duration_seconds"] > 0
        assert metrics["chars_per_second"] > 0
        assert metrics["words_per_minute"] > 0
        assert set(metrics["pause_distribution"]) == {
            "sentence",
            "clause",
            "paragraph",
            "silent_breath",
        }


def test_f5_presets_corpus_preview_artifacts_omit_raw_text(tmp_path):
    saymo_home = tmp_path / ".saymo"
    f5_root = tmp_path / "F5TTS"
    config_path = _write_config(tmp_path, saymo_home, f5_root)
    entry = get_f5_preview_corpus_entry("standup-blocked")
    corpus_run = tmp_path / "timing-preview-corpus"
    manual_run = tmp_path / "timing-preview-manual"
    artifact_names = ("manifest.json", "review.json", "timing-report.md")

    corpus_preview = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "f5-presets",
            "preview",
            "calm",
            "--corpus-id",
            "standup-blocked",
            "--output-dir",
            str(corpus_run),
            "--dry-run",
        ],
    )

    assert corpus_preview.exit_code == 0
    corpus_artifacts = "\n".join(
        (corpus_run / name).read_text(encoding="utf-8") for name in artifact_names
    )
    assert "standup-blocked" in corpus_artifacts
    assert "standup" in corpus_artifacts
    assert "Standup blocked" in corpus_artifacts
    assert entry.text not in corpus_artifacts

    manual_preview = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "f5-presets",
            "preview",
            "calm",
            "--text",
            "PRIVATE MANUAL PREVIEW TEXT",
            "--output-dir",
            str(manual_run),
            "--dry-run",
        ],
    )

    assert manual_preview.exit_code == 0
    manual_artifacts = "\n".join(
        (manual_run / name).read_text(encoding="utf-8") for name in artifact_names
    )
    assert "PRIVATE MANUAL PREVIEW TEXT" not in manual_artifacts


def test_f5_presets_preview_selection_errors(tmp_path):
    saymo_home = tmp_path / ".saymo"
    f5_root = tmp_path / "F5TTS"
    config_path = _write_config(tmp_path, saymo_home, f5_root)

    mixed = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "f5-presets",
            "preview",
            "calm",
            "--text",
            "PRIVATE CLI TIMING TEXT",
            "--corpus",
            "standup",
            "--dry-run",
        ],
    )
    assert mixed.exit_code != 0
    assert "Choose either --text or corpus options" in mixed.output

    missing = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "f5-presets",
            "preview",
            "calm",
            "--dry-run",
        ],
    )
    assert missing.exit_code != 0
    assert "Provide --text, --corpus, or --corpus-id" in missing.output


def test_f5_timing_record_manual_source_is_sanitized(tmp_path):
    from saymo.analysis.f5_timing_review import build_f5_timing_record
    from saymo.config import load_config

    config_path = _write_config(tmp_path, tmp_path / ".saymo", tmp_path / "F5TTS")
    config = load_config(str(config_path))
    record = build_f5_timing_record(
        config,
        label="current",
        preset_id="approved",
        text="PRIVATE MANUAL TIMING TEXT",
        output_wav=tmp_path / "current-approved.wav",
        dry_run=True,
    )

    assert record["source_kind"] == "manual"
    assert "corpus" not in record
    assert record["text_sha256"]
    assert record["text_chars"] == len("PRIVATE MANUAL TIMING TEXT")
    assert "PRIVATE MANUAL TIMING TEXT" not in json.dumps(record)


def test_f5_timing_record_corpus_metadata_is_safe(tmp_path):
    from saymo.analysis.f5_timing_review import build_f5_timing_record
    from saymo.config import load_config

    config_path = _write_config(tmp_path, tmp_path / ".saymo", tmp_path / "F5TTS")
    config = load_config(str(config_path))
    record = build_f5_timing_record(
        config,
        label="standup-blocked:current",
        preset_id="approved",
        text="PRIVATE CORPUS TIMING TEXT",
        output_wav=tmp_path / "standup-blocked-current-approved.wav",
        dry_run=True,
        source_kind="builtin_corpus",
        corpus_id="standup-blocked",
        corpus_category="standup",
        corpus_label="Standup blocked",
    )

    assert record["source_kind"] == "builtin_corpus"
    assert record["corpus"] == {
        "id": "standup-blocked",
        "category": "standup",
        "label": "Standup blocked",
    }
    assert record["text_sha256"]
    assert record["text_chars"] == len("PRIVATE CORPUS TIMING TEXT")
    assert "PRIVATE CORPUS TIMING TEXT" not in json.dumps(record)


def test_f5_timing_record_accepts_measured_audio_duration(tmp_path):
    from saymo.analysis.f5_timing_review import build_f5_timing_record
    from saymo.config import load_config

    config_path = _write_config(tmp_path, tmp_path / ".saymo", tmp_path / "F5TTS")
    config = load_config(str(config_path))
    record = build_f5_timing_record(
        config,
        label="candidate",
        preset_id="calm",
        text="PRIVATE MEASURED TIMING TEXT",
        output_wav=tmp_path / "candidate-calm.wav",
        dry_run=False,
        audio_duration_seconds=1.234,
    )

    assert record["metrics"]["audio_duration_seconds"] == 1.23
    assert record["metrics"]["estimated_total_duration_seconds"] > 0
    assert record["metrics"]["words_per_minute"] > 0
    assert "PRIVATE MEASURED TIMING TEXT" not in json.dumps(record)


def test_f5_timing_report_older_records_without_metrics_are_backward_compatible():
    from saymo.analysis.f5_timing_review import render_f5_timing_report

    report = render_f5_timing_report(
        {
            "run_status": "complete",
            "records": [
                {
                    "label": "current",
                    "preset_id": "approved",
                    "timing": {
                        "sentence_pause_seconds": 0.38,
                        "clause_pause_seconds": 0.18,
                        "silent_breath_pause_seconds": 0.6,
                    },
                    "output_wav": "/tmp/current-approved.wav",
                }
            ],
        },
        {
            "score_status": "unscored",
            "preference": {"preferred": "", "notes": ""},
            "recommendation": {"preset_id": ""},
        },
    )

    assert "current" in report
    assert "metrics=unavailable" in report
    assert "## Current vs Candidate Deltas" in report


def test_f5_timing_metrics_docs_contract_is_sanitized():
    shootout = Path("docs/voice-clone-shootout.md").read_text(encoding="utf-8")
    naturalness = Path("docs/VOICE-NATURALNESS.md").read_text(encoding="utf-8")
    combined = f"{shootout}\n{naturalness}"

    for term in [
        "estimated_total_duration_seconds",
        "audio_duration_seconds",
        "chars_per_second",
        "words_per_minute",
        "pause_distribution",
        "timing-report.md",
        "duration_delta",
        "pause_total_delta",
    ]:
        assert term in combined

    assert "audio_duration_seconds appears only when a real WAV exists" in shootout
    for privacy_term in [
        "raw manual text",
        "corpus phrase text",
        "audio bytes",
        "private meeting",
        "secrets",
        "voice samples",
        "training data",
    ]:
        assert privacy_term in shootout
    assert "automatic preset recommendation" not in combined
