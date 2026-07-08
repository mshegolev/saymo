"""Tests for shared launch-readiness contracts."""

from __future__ import annotations

import json
import textwrap
from datetime import date
from pathlib import Path

from saymo.config import load_config


PRIVATE_STRINGS = (
    "PRIVATE_DAILY_NOTE",
    "PRIVATE_TRANSCRIPT",
    "PRIVATE_GENERATED_ANSWER",
    "SECRET_TOKEN",
)


def _write_config(tmp_path, *, vault_path: Path | None = None) -> Path:
    config_path = tmp_path / "config.yaml"
    vault = vault_path or (tmp_path / "Vault")
    config_path.write_text(
        textwrap.dedent(
            f"""
            user:
              name: "John"
              name_variants:
                - "John"
            speech:
              source: obsidian
            obsidian:
              vault_path: "{vault}"
              subfolder: ""
              date_format: "%Y-%m-%d"
            meetings:
              standup:
                description: "Standup"
                provider: glip
                team: false
                source: obsidian
                trigger_phrases:
                  - "John"
            responses:
              enabled: true
              cache_dir: "{tmp_path / 'responses'}"
              library: {{}}
            """
        ),
        encoding="utf-8",
    )
    return config_path


def _assert_private_absent(text: str) -> None:
    for value in PRIVATE_STRINGS:
        assert value not in text


def _check_by_key(report, key: str):
    matches = [check for check in report.checks if check.key == key]
    assert matches, f"missing launch readiness check: {key}"
    return matches[0]


def test_report_ready_false_when_blocking_check_fails():
    from saymo.analysis.launch_readiness import (
        LaunchReadinessCheck,
        LaunchReadinessReport,
    )

    warning_only = LaunchReadinessReport(
        profile="standup",
        provider="glip",
        checks=(
            LaunchReadinessCheck(
                key="response_cache_partial",
                label="response cache",
                severity="warn",
                ok=False,
                detail="ready_count=1 total_count=2",
            ),
        ),
    )
    blocked = LaunchReadinessReport(
        profile="standup",
        provider="glip",
        checks=(
            LaunchReadinessCheck(
                key="daily_note_source",
                label="daily note source",
                severity="block",
                ok=False,
                detail="placeholder_only",
            ),
        ),
    )

    assert warning_only.ready is True
    assert blocked.ready is False


def test_report_serializes_without_private_text():
    from saymo.analysis.launch_readiness import (
        LaunchReadinessCheck,
        LaunchReadinessReport,
    )

    unsafe_blob = " ".join(PRIVATE_STRINGS)
    report = LaunchReadinessReport(
        profile="standup",
        provider="glip",
        checks=(
            LaunchReadinessCheck(
                key="daily_note_source",
                label="daily note source",
                severity="block",
                ok=False,
                detail=unsafe_blob,
                action=unsafe_blob,
                metadata={
                    "source_sha256": "abc123",
                    "ready_count": 0,
                    "raw_source": unsafe_blob,
                },
            ),
        ),
    )

    serialized = json.dumps(report.to_dict(), ensure_ascii=False)

    assert "daily_note_source" in serialized
    assert "source_sha256" in serialized
    assert "ready_count" in serialized
    _assert_private_absent(serialized)


def test_placeholder_daily_note_blocks_source_readiness(tmp_path):
    from saymo.analysis.launch_readiness import collect_launch_readiness

    vault = tmp_path / "Vault"
    vault.mkdir()
    today = date.today().strftime("%Y-%m-%d")
    (vault / f"{today}.md").write_text(
        textwrap.dedent(
            f"""
            # {today}
            ## Standup
            ### Yesterday
            -
            ### Today
            -
            ### Blockers
            -
            """
        ),
        encoding="utf-8",
    )
    config = load_config(config_path=str(_write_config(tmp_path, vault_path=vault)))

    report = collect_launch_readiness(config, profile="standup", provider_name="glip")
    source = _check_by_key(report, "daily_note_source")

    assert source.severity == "block"
    assert source.ok is False
    assert source.metadata["note_path"].endswith(f"{today}.md")
    assert source.metadata["source_sha256"]
    _assert_private_absent(json.dumps(report.to_dict(), ensure_ascii=False))


def test_prepared_audio_requires_current_metadata_and_source_digest(tmp_path):
    from saymo.analysis.launch_readiness import collect_launch_readiness

    vault = tmp_path / "Vault"
    vault.mkdir()
    today = date.today().strftime("%Y-%m-%d")
    (vault / f"{today}.md").write_text(
        "# Standup\n\nPRIVATE_DAILY_NOTE\n",
        encoding="utf-8",
    )
    config = load_config(config_path=str(_write_config(tmp_path, vault_path=vault)))

    report = collect_launch_readiness(config, profile="standup", provider_name="glip")
    prepared = _check_by_key(report, "prepared_audio")

    assert prepared.severity == "block"
    assert prepared.ok is False
    assert prepared.metadata["source_sha256"]
    assert prepared.metadata["stale_reason"] in {
        "audio_missing",
        "voice_metadata_missing",
        "voice_metadata_stale",
        "source_digest_stale",
    }
    _assert_private_absent(json.dumps(report.to_dict(), ensure_ascii=False))


def test_voice_metadata_is_sanitized_and_actionable(tmp_path):
    from saymo.analysis.launch_readiness import collect_launch_readiness

    config = load_config(config_path=str(_write_config(tmp_path)))

    report = collect_launch_readiness(config, profile="standup", provider_name="glip")
    voice = _check_by_key(report, "cloned_voice")

    assert "selected_engine" in voice.metadata
    assert "voice_profile" in voice.metadata
    assert "approved_for_calls" in voice.metadata
    assert (
        "reference_audio_sha256" in voice.metadata
        or "reference_text_sha256" in voice.metadata
        or "stale_reason" in voice.metadata
    )
    _assert_private_absent(json.dumps(report.to_dict(), ensure_ascii=False))
