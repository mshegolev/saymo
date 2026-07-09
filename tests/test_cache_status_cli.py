"""CLI tests for cache-status diagnostics."""

from __future__ import annotations

import textwrap
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
            """
        ),
        encoding="utf-8",
    )
    return config_path


def test_cache_status_cli_warns_with_targeted_commands(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_path = _write_config(tmp_path)
    prepared = tmp_path / ".saymo" / "audio_cache" / "2026-07-09.wav"
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
    assert "saymo prepare-responses" in result.output
    assert "PRIVATE RESPONSE TEXT" not in result.output
