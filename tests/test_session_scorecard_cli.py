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


PRIVATE_SENTINELS = (
    "PRIVATE_TRANSCRIPT",
    "PRIVATE_PROMPT_TEXT",
    "PRIVATE_GENERATED_RESPONSE",
    "SECRET_TOKEN",
    "PRIVATE_VOICE_SAMPLE",
    "PRIVATE_TRAINING_DATA",
)


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


def _write_launch_evidence(
    tmp_path,
    *,
    mode="call-ready",
    rerun="saymo call-ready -p personal --provider glip",
    include_provider=False,
):
    path = tmp_path / f"{mode}.json"
    checks = [
        {
            "key": "response_cache_coverage",
            "label": "response cache coverage",
            "severity": "block",
            "ok": False,
            "detail": "missing response cache variants PRIVATE_TRANSCRIPT",
            "action": "prepare response cache without PRIVATE_PROMPT_TEXT",
            "rerun": rerun,
            "metadata": {
                "category": "source-data",
                "ready": 1,
                "total": 3,
                "missing": 2,
                "raw_transcript": "PRIVATE_TRANSCRIPT",
                "prompt_text": "PRIVATE_PROMPT_TEXT",
                "generated_response_text": "PRIVATE_GENERATED_RESPONSE",
                "audio_bytes": "PRIVATE_GENERATED_RESPONSE",
            },
        },
        {
            "key": "call_control_daemon",
            "label": "call-control daemon",
            "severity": "warn",
            "ok": False,
            "detail": "heartbeat stale SECRET_TOKEN",
            "action": "restart daemon",
            "rerun": "" if mode == "dry-run" else "saymo call-control-agent status -p personal",
            "metadata": {
                "category": "call-control",
                "running": False,
                "heartbeat_fresh": False,
                "daemon_ok": False,
                "stdout_log_path": "/tmp/saymo/out.log",
                "stderr_log_path": "/tmp/saymo/err.log",
                "voice_sample_path": "PRIVATE_VOICE_SAMPLE",
                "training_data_path": "PRIVATE_TRAINING_DATA",
            },
        },
    ]
    if include_provider:
        checks.insert(
            1,
            {
                "key": "provider_meeting_tab",
                "label": "provider meeting tab",
                "severity": "warn",
                "ok": False,
                "detail": "provider tab missing SECRET_TOKEN",
                "action": "open provider tab",
                "rerun": rerun,
                "metadata": {"category": "provider", "meeting_found": False},
            },
        )
    payload = {
        "schema_version": "1.0",
        "evidence_kind": "launch-readiness",
        "mode": mode,
        "artifact_path": str(path),
        "profile": "personal",
        "provider": "glip",
        "ready": False,
        "check_count": len(checks),
        "ready_count": 0,
        "block_count": 1,
        "warn_count": 1,
        "checks": checks,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _write_rehearsal_with_launch_evidence(tmp_path, launch_path):
    path = _write_rehearsal(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["launch_evidence"] = {
        "path": str(launch_path),
        "mode": "dry-run",
        "status": "loaded",
        "ready": False,
        "block_count": 1,
        "warn_count": 1,
        "failed_labels": ["response cache coverage"],
        "rerun_commands": ["saymo dry-run -p personal --provider glip"],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _assert_no_private_content(value) -> None:
    rendered = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    for sentinel in PRIVATE_SENTINELS:
        assert sentinel not in rendered


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
    assert "remediation:" in result.output
    assert "response cache coverage" in result.output
    assert "source-data=1" in result.output
    assert "provider_blocks=1 fallback_blocks=1 handbrake_blocks=1" in result.output
    assert "saymo call-ready -p personal --provider glip" in result.output
    assert "saymo call-control-agent status -p personal" in result.output
    assert (
        f"rerun: saymo session-scorecard -p personal --rehearsal {rehearsal_path} "
        f"--launch-json {launch_path} --realtime-jsonl {realtime_path}"
    ) in result.output
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
    assert markdown_path.exists()
    assert json_path.exists()
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


def test_session_scorecard_cli_accepts_dry_run_launch_evidence(tmp_path):
    config_path = _write_config(tmp_path)
    rehearsal_path = _write_rehearsal(tmp_path)
    launch_path = _write_launch_evidence(
        tmp_path,
        mode="dry-run",
        rerun="saymo dry-run -p personal --provider glip",
        include_provider=True,
    )
    markdown_path = tmp_path / "dry-run-scorecard.md"
    json_path = tmp_path / "dry-run-scorecard.json"

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
            "--output",
            str(markdown_path),
            "--json-output",
            str(json_path),
        ],
    )

    assert result.exit_code == 0
    markdown = markdown_path.read_text(encoding="utf-8")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    combined = result.output + markdown + json.dumps(payload, ensure_ascii=False)

    assert "launch: loaded ready=no blocks=1 warns=1" in combined
    assert "launch rerun commands: 1" in combined
    assert "saymo dry-run -p personal --provider glip" in combined
    assert payload["launch_metrics"]["status"] == "loaded"
    assert payload["launch_metrics"]["ready"] is False
    assert payload["launch_metrics"]["cache_missing"] == 2
    assert payload["launch_metrics"]["provider_ready"] is False
    assert payload["launch_metrics"]["daemon_ready"] is False
    assert payload["launch_metrics"]["rerun_commands"] == [
        "saymo dry-run -p personal --provider glip"
    ]
    _assert_no_private_content(combined)

    recorded_rehearsal_path = _write_rehearsal_with_launch_evidence(tmp_path, launch_path)
    fallback_json_path = tmp_path / "dry-run-scorecard-fallback.json"
    fallback = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "session-scorecard",
            "--profile",
            "personal",
            "--rehearsal",
            str(recorded_rehearsal_path),
            "--json-output",
            str(fallback_json_path),
        ],
    )

    assert fallback.exit_code == 0
    fallback_payload = json.loads(fallback_json_path.read_text(encoding="utf-8"))
    assert fallback_payload["launch_metrics"]["status"] == "loaded"
    assert fallback_payload["launch_metrics"]["rerun_commands"] == [
        "saymo dry-run -p personal --provider glip"
    ]
    _assert_no_private_content(fallback.output)
