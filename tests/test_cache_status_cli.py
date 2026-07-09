"""CLI tests for cache-status diagnostics."""

from __future__ import annotations

import textwrap
from datetime import date
from pathlib import Path

from click.testing import CliRunner

from saymo.analysis.cache_metadata import VoiceCacheMetadata, write_voice_cache_metadata
from saymo.commands import main


def _write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        textwrap.dedent(
            f"""
            tts:
              engine: f5tts_clone
            speech:
              source: obsidian
            responses:
              enabled: true
              cache_dir: "{tmp_path / 'responses'}"
              library:
                blockers_none:
                  triggers:
                    - "есть блокеры"
                  variants:
                    - "PRIVATE RESPONSE TEXT"
            meetings:
              standup:
                provider: glip
                team: false
                voice:
                  f5_pause_preset: crisp
                  f5_pause_presets:
                    prepared: calm
                    response_cache: deliberate
            """
        ),
        encoding="utf-8",
    )
    return config_path


def test_cache_status_cli_warns_with_targeted_commands(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_path = _write_config(tmp_path)
    prepared = tmp_path / ".saymo" / "audio_cache" / f"{date.today().isoformat()}.wav"
    prepared.parent.mkdir(parents=True, exist_ok=True)
    prepared.write_bytes(b"RIFF")
    write_voice_cache_metadata(
        prepared,
        VoiceCacheMetadata(
            purpose="prepare",
            selected_engine="f5tts_clone",
            attempted_engines=("f5tts_clone",),
            fingerprint="old",
        ),
    )

    result = CliRunner().invoke(
        main,
        ["--config", str(config_path), "cache-status", "-p", "standup"],
    )

    assert result.exit_code == 0
    assert "cache status: standup" in result.output.lower()
    assert "prepared audio" in result.output.lower()
    assert "response cache" in result.output.lower()
    assert "F5 regeneration can be expensive" in result.output
    assert "saymo prepare -p standup" in result.output
    assert "saymo prepare-responses -p standup" in result.output
    assert "preset: source_type=prepared" in result.output
    assert "preset: source_type=response_cache" in result.output
    assert "profile=crisp" in result.output
    assert "override=calm" in result.output
    assert "override=deliberate" in result.output
    assert "resolved=calm" in result.output
    assert "resolved=deliberate" in result.output
    assert "voice_metadata_stale" in result.output
    assert "PRIVATE RESPONSE TEXT" not in result.output
    assert "audio_bytes" not in result.output
    assert "voice_sample" not in result.output
    assert "training_dataset" not in result.output
    assert "secret" not in result.output.lower()


def test_source_type_preset_docs_cover_usage_and_safety_boundary():
    shootout = Path("docs/voice-clone-shootout.md").read_text(encoding="utf-8")
    naturalness = Path("docs/VOICE-NATURALNESS.md").read_text(encoding="utf-8")
    combined = f"{shootout}\n{naturalness}"

    assert "saymo f5-presets apply calm --profile standup --source-type prepared" in shootout
    assert "saymo f5-presets apply crisp --profile standup --source-type response_cache" in shootout
    assert "saymo f5-presets apply deliberate --profile standup --source-type spontaneous" in shootout
    assert "meetings.standup.voice.f5_pause_presets" in shootout
    assert "source-type override -> profile-level f5_pause_preset -> global tts.f5tts.pause_preset" in shootout
    assert "voice_metadata_stale" in shootout
    assert "saymo prepare -p standup" in shootout
    assert "saymo prepare-responses -p standup" in shootout

    for phrase in (
        "no retraining",
        "no automatic cache rebuilding",
        "no audible breath",
        "no cloud services",
        "no automatic preset recommendations",
    ):
        assert phrase in combined.lower()

    for phrase in (
        "prompt text",
        "response text",
        "audio bytes",
        "private meeting",
        "secrets",
    ):
        assert phrase in shootout.lower()
