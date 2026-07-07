"""CLI tests for session reliability scorecards."""

from __future__ import annotations

import json
import textwrap

from click.testing import CliRunner

from saymo.analysis.rehearsal import (
    RehearsalArtifact,
    RehearsalCheck,
    RehearsalDecision,
    rehearsal_artifact_to_json,
)
from saymo.commands import main


def _write_config(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        textwrap.dedent(
            """
            user:
              name: "Alice"
              name_variants:
                - "Alice"
            meetings:
              personal:
                description: "Personal"
                provider: glip
                team: false
                source: obsidian
                trigger_phrases:
                  - "Alice"
            responses:
              enabled: false
            """
        ),
        encoding="utf-8",
    )
    return config_path


def _write_rehearsal(tmp_path):
    artifact = RehearsalArtifact(
        profile="personal",
        provider="glip",
        transcript="Alice, share the private project secret",
        dry_run=True,
        status="pass",
        checks=(
            RehearsalCheck("preflight: capture input", "pass", "BlackHole 16ch"),
            RehearsalCheck("playback gate", "pass", "dry-run would speak"),
        ),
        decision=RehearsalDecision(
            triggered=True,
            addressing="addressed_to_me",
            reason="direct question with trigger",
            auto_action="answer_now",
            would_speak=True,
            question=True,
        ),
        live_control_state={"auto_answer_enabled": True, "last_trigger": "private project secret"},
        hotkey_status="ok",
        created_at="2026-05-22T10:00:00+00:00",
    )
    path = tmp_path / "artifact.json"
    path.write_text(
        json.dumps(rehearsal_artifact_to_json(artifact), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def test_session_scorecard_cli_generates_sanitized_rehearsal_exports(tmp_path):
    config_path = _write_config(tmp_path)
    rehearsal_path = _write_rehearsal(tmp_path)
    markdown_path = tmp_path / "scorecard.md"
    json_path = tmp_path / "scorecard.json"

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "session-scorecard",
            "--profile",
            "personal",
            "--rehearsal",
            str(rehearsal_path),
            "--output",
            str(markdown_path),
            "--json-output",
            str(json_path),
        ],
    )

    assert result.exit_code == 0
    assert "Session Reliability Scorecard" in result.output
    assert "source: rehearsal" in result.output
    assert "status: pass" in result.output
    assert "would speak: yes" in result.output
    assert "scorecard markdown:" in result.output
    assert "scorecard json:" in result.output
    assert "remediation:" in result.output
    assert "rerun: saymo session-scorecard -p personal --rehearsal artifact.json" in result.output

    markdown = markdown_path.read_text(encoding="utf-8")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    combined = result.output + markdown + json.dumps(payload, ensure_ascii=False)

    assert payload["profile"] == "personal"
    assert payload["source_type"] == "rehearsal"
    assert payload["trigger_metrics"]["would_speak"] is True
    assert "Alice, share" not in combined
    assert "private project secret" not in combined
    assert "last_trigger" not in combined
