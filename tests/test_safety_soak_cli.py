"""CLI tests for safety soak gates."""

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
from saymo.analysis.safety_soak import build_safety_soak_report, write_safety_soak_json
from saymo.analysis.session_scorecard import build_scorecard_from_rehearsal, write_scorecard_json
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


def _write_rehearsal(tmp_path, *, auto_answer_enabled: bool = True):
    artifact = RehearsalArtifact(
        profile="personal",
        provider="glip",
        transcript="Alice, share the private project secret",
        dry_run=True,
        status="pass",
        checks=(
            RehearsalCheck("playback gate", "pass", "dry-run would speak"),
            RehearsalCheck("latency", "pass", "decision=120ms playback_start=480ms"),
        ),
        decision=RehearsalDecision(
            triggered=True,
            addressing="addressed_to_me",
            reason="direct question with trigger",
            auto_action="answer_now",
            would_speak=True,
            question=True,
        ),
        live_control_state={
            "auto_answer_enabled": auto_answer_enabled,
            "last_trigger": "private project secret",
        },
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
        "check_count": 3,
        "ready_count": 0,
        "block_count": 3,
        "warn_count": 0,
        "checks": [
            {
                "key": "response_cache_coverage",
                "label": "response cache coverage",
                "severity": "block",
                "ok": False,
                "detail": "missing response cache variants",
                "action": "prepare response cache",
                "metadata": {
                    "category": "source-data",
                    "ready": 1,
                    "total": 3,
                    "missing": 2,
                },
            },
            {
                "key": "provider_meeting_tab",
                "label": "provider meeting tab",
                "severity": "block",
                "ok": False,
                "detail": "meeting tab missing",
                "action": "open meeting tab",
                "metadata": {"category": "provider", "meeting_found": False},
            },
            {
                "key": "call_control_daemon",
                "label": "call-control daemon",
                "severity": "block",
                "ok": False,
                "detail": "heartbeat stale",
                "action": "restart daemon",
                "metadata": {
                    "category": "call-control",
                    "daemon_ok": False,
                    "running": False,
                    "heartbeat_fresh": False,
                },
            },
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _write_realtime_events(tmp_path):
    path = tmp_path / "realtime-decisions.jsonl"
    events = [
        ("blocked", "cache-miss-blocked", "response_cache"),
        ("blocked", "fallback-blocked", "playback"),
        ("blocked", "provider-blocked", "provider"),
        ("blocked", "handbrake-blocked", "live_control"),
    ]
    lines = [
        json.dumps(
            RealtimeDecisionEvent(
                created_at=f"2026-07-08T19:20:{index:02d}Z",
                profile="personal",
                provider="glip",
                outcome=outcome,
                label=label,
                source=source,
            ).to_dict(),
            ensure_ascii=False,
        )
        for index, (outcome, label, source) in enumerate(events)
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_safety_soak_cli_generates_gate_exports(tmp_path):
    config_path = _write_config(tmp_path)
    rehearsal_path = _write_rehearsal(tmp_path)
    markdown_path = tmp_path / "soak.md"
    json_path = tmp_path / "soak.json"

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "safety-soak",
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
    assert "Saymo Safety Soak Gate" in result.output
    assert "status: pass" in result.output
    assert "Next Actions" in result.output
    assert "scorecard or rehearsal artifact" in result.output
    assert "remediation:" in result.output
    assert "soak markdown:" in result.output
    assert "soak json:" in result.output

    markdown = markdown_path.read_text(encoding="utf-8")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    combined = result.output + markdown + json.dumps(payload, ensure_ascii=False)

    assert payload["profile"] == "personal"
    assert payload["status"] == "pass"
    assert payload["totals"]["would_speak"] == 1
    assert "Alice, share" not in combined
    assert "private project secret" not in combined
    assert "last_trigger" not in combined


def test_safety_soak_cli_exits_nonzero_when_gate_fails(tmp_path):
    config_path = _write_config(tmp_path)
    rehearsal_path = _write_rehearsal(tmp_path, auto_answer_enabled=False)

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "safety-soak",
            "--profile",
            "personal",
            "--rehearsal",
            str(rehearsal_path),
        ],
    )

    assert result.exit_code == 1
    assert "status: fail" in result.output
    assert "auto_answer_off" in result.output


def test_safety_soak_cli_accepts_scorecard_json_and_baseline_json(tmp_path):
    config_path = _write_config(tmp_path)
    rehearsal_path = _write_rehearsal(tmp_path)
    scorecard = build_scorecard_from_rehearsal(rehearsal_path)
    scorecard_path = write_scorecard_json(tmp_path / "scorecard.json", scorecard)
    baseline_path = write_safety_soak_json(
        tmp_path / "baseline-soak.json",
        build_safety_soak_report(profile="personal", scorecards=(scorecard,)),
    )

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "safety-soak",
            "--profile",
            "personal",
            "--scorecard-json",
            str(scorecard_path),
            "--baseline-json",
            str(baseline_path),
        ],
    )

    assert result.exit_code == 0
    assert "status: pass" in result.output
    assert "Baseline Drift" in result.output


def test_safety_soak_cli_fails_from_scorecard_json_v19_metrics_preserving_exports(tmp_path):
    config_path = _write_config(tmp_path)
    rehearsal_path = _write_rehearsal(tmp_path)
    launch_path = _write_launch_evidence(tmp_path)
    realtime_path = _write_realtime_events(tmp_path)
    scorecard = build_scorecard_from_rehearsal(
        rehearsal_path,
        launch_json=launch_path,
        realtime_jsonl=realtime_path,
    )
    scorecard_path = write_scorecard_json(tmp_path / "v19-scorecard.json", scorecard)
    markdown_path = tmp_path / "v19-soak.md"
    json_path = tmp_path / "v19-soak.json"

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "safety-soak",
            "--profile",
            "personal",
            "--scorecard-json",
            str(scorecard_path),
            "--output",
            str(markdown_path),
            "--json-output",
            str(json_path),
        ],
    )

    assert result.exit_code == 1
    assert "status: fail" in result.output
    assert "launch_not_ready" in result.output
    assert "stale_or_missing_response_cache" in result.output
    assert "call_control_daemon_not_ready" in result.output
    assert "provider_blocked" in result.output
    assert "fallback_blocked" in result.output
    assert "handbrake_blocked" in result.output
    assert "soak markdown:" in result.output
    assert "soak json:" in result.output

    markdown = markdown_path.read_text(encoding="utf-8")
    payload = json.loads(json_path.read_text(encoding="utf-8"))

    assert "## v1.9 Evidence Totals" in markdown
    assert payload["status"] == "fail"
    assert payload["totals"]["launch_not_ready"] == 1
    assert payload["totals"]["cache_missing"] == 2
    assert payload["totals"]["provider_blocks"] == 2


def test_safety_soak_cli_passes_rehearsal_evidence_paths_into_scorecard_builder(tmp_path):
    config_path = _write_config(tmp_path)
    rehearsal_path = _write_rehearsal(tmp_path)
    launch_path = _write_launch_evidence(tmp_path)
    realtime_path = _write_realtime_events(tmp_path)

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "safety-soak",
            "--profile",
            "personal",
            "--rehearsal",
            str(rehearsal_path),
            "--launch-json",
            str(launch_path),
            "--realtime-jsonl",
            str(realtime_path),
        ],
    )

    assert result.exit_code == 1
    assert "status: fail" in result.output
    assert "launch_not_ready" in result.output
    assert "provider_blocked" in result.output
