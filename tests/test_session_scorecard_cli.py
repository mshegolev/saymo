"""CLI tests for session reliability scorecards."""

from __future__ import annotations

import json
import textwrap

from click.testing import CliRunner

from saymo.analysis.realtime_events import RealtimeDecisionEvent
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


def _write_launch_evidence(tmp_path):
    path = tmp_path / "call-ready.json"
    payload = {
        "schema_version": "1.0",
        "evidence_kind": "launch-readiness",
        "mode": "call-ready",
        "artifact_path": str(path),
        "profile": "personal",
        "provider": "glip",
        "ready": False,
        "check_count": 2,
        "ready_count": 0,
        "block_count": 1,
        "warn_count": 1,
        "checks": [
            {
                "key": "response_cache_coverage",
                "label": "response cache coverage",
                "severity": "block",
                "ok": False,
                "detail": "missing response cache variants",
                "action": "prepare response cache",
                "rerun": "saymo call-ready -p personal --provider glip",
                "metadata": {
                    "category": "source-data",
                    "ready": 1,
                    "total": 3,
                    "missing": 2,
                },
            },
            {
                "key": "call_control_daemon",
                "label": "call-control daemon",
                "severity": "warn",
                "ok": False,
                "detail": "heartbeat stale",
                "action": "restart daemon",
                "rerun": "saymo call-control-agent status -p personal",
                "metadata": {
                    "category": "call-control",
                    "running": False,
                    "heartbeat_fresh": False,
                    "stdout_log_path": "/tmp/saymo/out.log",
                    "stderr_log_path": "/tmp/saymo/err.log",
                },
            },
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _write_realtime_events(tmp_path):
    path = tmp_path / "realtime-decisions.jsonl"
    events = [
        ("skipped", "launch-start", "launch_readiness"),
        ("blocked", "launch-readiness-blocked", "launch_readiness"),
        ("spoke", "response-cache-hit", "response_cache"),
        ("blocked", "fallback-blocked", "playback"),
        ("blocked", "provider-blocked", "provider"),
        ("blocked", "handbrake-blocked", "live_control"),
        ("spoke", "playback-attempted", "playback"),
    ]
    lines = [
        json.dumps(
            RealtimeDecisionEvent(
                created_at=f"2026-07-08T18:20:{index:02d}Z",
                profile="personal",
                provider="glip",
                outcome=outcome,
                label=label,
                source=source,
            ).to_dict()
        )
        for index, (outcome, label, source) in enumerate(events)
    ]
    path.write_text("\n".join([*lines, "{malformed"]) + "\n", encoding="utf-8")
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
    assert "rerun: saymo session-scorecard -p personal --rehearsal" in result.output
    assert rehearsal_path.name in result.output

    markdown = markdown_path.read_text(encoding="utf-8")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    combined = result.output + markdown + json.dumps(payload, ensure_ascii=False)

    assert payload["profile"] == "personal"
    assert payload["source_type"] == "rehearsal"
    assert payload["trigger_metrics"]["would_speak"] is True
    assert "Alice, share" not in combined
    assert "private project secret" not in combined
    assert "last_trigger" not in combined
    assert "launch_metrics" not in payload
    assert "realtime_metrics" not in payload
    assert "v1.9 Evidence" not in markdown


def test_session_scorecard_cli_accepts_launch_and_realtime_evidence_paths(tmp_path):
    config_path = _write_config(tmp_path)
    rehearsal_path = _write_rehearsal(tmp_path)
    launch_path = _write_launch_evidence(tmp_path)
    realtime_path = _write_realtime_events(tmp_path)
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
            "--launch-json",
            str(launch_path),
            "--realtime-jsonl",
            str(realtime_path),
            "--output",
            str(markdown_path),
            "--json-output",
            str(json_path),
        ],
    )

    assert result.exit_code == 0
    assert "Session Reliability Scorecard" in result.output
    assert "v1.9 Evidence" in result.output
    assert "launch: loaded ready=no blocks=1 warns=1" in result.output
    assert "runtime blocks: provider=1 handbrake=1 playback_attempts=1" in result.output
    assert "scorecard markdown:" in result.output
    assert "scorecard json:" in result.output

    markdown = markdown_path.read_text(encoding="utf-8")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    combined = result.output + markdown + json.dumps(payload, ensure_ascii=False)

    assert payload["launch_metrics"]["status"] == "loaded"
    assert payload["launch_metrics"]["cache_missing"] == 2
    assert payload["realtime_metrics"]["status"] == "loaded"
    assert payload["realtime_metrics"]["launch_blocks"] == 1
    assert payload["realtime_metrics"]["malformed_rows"] == 1
    assert "Alice, share" not in combined
    assert "private project secret" not in combined
    assert "last_trigger" not in combined


def test_session_scorecard_cli_accepts_evidence_alias_flags(tmp_path):
    config_path = _write_config(tmp_path)
    rehearsal_path = _write_rehearsal(tmp_path)
    launch_path = _write_launch_evidence(tmp_path)
    realtime_path = _write_realtime_events(tmp_path)
    json_path = tmp_path / "scorecard-alias.json"

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
            "--launch-readiness",
            str(launch_path),
            "--realtime",
            str(realtime_path),
            "--json-output",
            str(json_path),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["launch_metrics"]["status"] == "loaded"
    assert payload["realtime_metrics"]["status"] == "loaded"
