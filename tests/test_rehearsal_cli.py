"""CLI tests for pre-call rehearsal."""

import json
import textwrap

from click.testing import CliRunner

from saymo.commands import main
from saymo.commands.tests import PreflightCheck


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
              name: "John"
              name_variants:
                - "John"
            safety:
              require_confirmation: false
              hotkey_toggle: "<cmd>+<shift>+m"
              hotkey_stop: "<cmd>+<shift>+x"
              hotkey_speak: "<cmd>+<shift>+s"
              hotkey_takeover: "<cmd>+<shift>+u"
            meetings:
              personal:
                description: "Personal"
                provider: glip
                team: false
                source: obsidian
                trigger_phrases:
                  - "John"
            responses:
              enabled: false
            """
        ),
        encoding="utf-8",
    )
    return config_path


def _write_dry_run_launch_evidence(tmp_path, *, ready=False):
    path = tmp_path / ("ready-dry-run.json" if ready else "not-ready-dry-run.json")
    payload = {
        "schema_version": "1.0",
        "evidence_kind": "launch-readiness",
        "mode": "dry-run",
        "artifact_path": str(path),
        "created_at": "2026-07-10T14:35:00Z",
        "profile": "personal",
        "provider": "glip",
        "ready": ready,
        "check_count": 3,
        "ready_count": 3 if ready else 0,
        "block_count": 0 if ready else 2,
        "warn_count": 0 if ready else 1,
        "checks": [
            {
                "key": "response_cache_coverage",
                "label": "response cache coverage",
                "severity": "block",
                "ok": ready,
                "detail": "missing response cache PRIVATE_TRANSCRIPT",
                "action": "prepare cache without PRIVATE_PROMPT_TEXT",
                "rerun": "saymo dry-run -p personal --provider glip",
                "metadata": {
                    "category": "source-data",
                    "ready": 1 if not ready else 3,
                    "total": 3,
                    "missing": 2 if not ready else 0,
                    "raw_transcript": "PRIVATE_TRANSCRIPT",
                    "prompt_text": "PRIVATE_PROMPT_TEXT",
                    "generated_response_text": "PRIVATE_GENERATED_RESPONSE",
                    "audio_bytes": "PRIVATE_GENERATED_RESPONSE",
                },
            },
            {
                "key": "provider_meeting_tab",
                "label": "provider meeting tab",
                "severity": "block",
                "ok": ready,
                "detail": "provider tab missing SECRET_TOKEN",
                "action": "open tab without PRIVATE_GENERATED_RESPONSE",
                "rerun": "saymo dry-run -p personal --provider glip",
                "metadata": {"category": "provider", "meeting_found": ready},
            },
            {
                "key": "cloned_voice_metadata",
                "label": "cloned voice metadata",
                "severity": "info" if ready else "warn",
                "ok": ready,
                "detail": "voice metadata PRIVATE_VOICE_SAMPLE",
                "action": "check voice profile without PRIVATE_TRAINING_DATA",
                "rerun": "saymo voice-profile check --profile personal",
                "metadata": {
                    "category": "voice-cache",
                    "voice_sample_path": "PRIVATE_VOICE_SAMPLE",
                    "training_data_path": "PRIVATE_TRAINING_DATA",
                    "auth_token": "SECRET_TOKEN",
                },
            },
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _assert_no_private_content(value) -> None:
    rendered = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    for sentinel in PRIVATE_SENTINELS:
        assert sentinel not in rendered


def test_rehearsal_dry_run_writes_pass_artifact(tmp_path, monkeypatch):
    config_path = _write_config(tmp_path)
    monkeypatch.setattr(
        "saymo.commands.tests._collect_auto_preflight",
        lambda config, profile, provider_name=None: [
            PreflightCheck("capture input", True, "BlackHole 16ch"),
            PreflightCheck("response cache", False, "0/4 variants", blocking=False),
        ],
    )

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "rehearsal",
            "--profile",
            "personal",
            "--text",
            "John, status?",
            "--output-dir",
            str(tmp_path / "rehearsals"),
            "--no-hotkey-probe",
        ],
    )

    assert result.exit_code == 0
    assert "rehearsal: warn" in result.output
    assert "auto action: answer_now" in result.output
    assert "would speak: yes" in result.output
    assert "warn: preflight: response cache" in result.output
    assert "remediation:" in result.output
    assert "[source-data] Prepare response cache" in result.output
    assert "rerun: saymo rehearsal -p personal" in result.output
    artifact_path = tmp_path / "rehearsals" / "personal"
    artifacts = list(artifact_path.glob("*.json"))
    assert len(artifacts) == 1
    payload = json.loads(artifacts[0].read_text(encoding="utf-8"))
    assert payload["profile"] == "personal"
    assert payload["dry_run"] is True
    assert payload["status"] == "warn"
    assert payload["decision"]["auto_action"] == "answer_now"
    assert payload["decision"]["would_speak"] is True


def test_rehearsal_reports_blocking_preflight_failure(tmp_path, monkeypatch):
    config_path = _write_config(tmp_path)
    monkeypatch.setattr(
        "saymo.commands.tests._collect_auto_preflight",
        lambda config, profile, provider_name=None: [
            PreflightCheck("capture input", False, "missing BlackHole 16ch"),
        ],
    )

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "rehearsal",
            "--profile",
            "personal",
            "--text",
            "John, status?",
            "--output-dir",
            str(tmp_path / "rehearsals"),
            "--no-hotkey-probe",
        ],
    )

    assert result.exit_code == 0
    assert "rehearsal: fail" in result.output
    assert "fail: preflight: capture input: missing BlackHole 16ch" in result.output
    assert "would speak: no" in result.output
    assert "blocked: blocking preflight failure" in result.output
    assert "remediation:" in result.output
    assert "[audio-device] Fix capture input" in result.output


def test_rehearsal_records_dry_run_launch_evidence_without_private_content(
    tmp_path,
    monkeypatch,
):
    config_path = _write_config(tmp_path)
    launch_path = _write_dry_run_launch_evidence(tmp_path, ready=False)
    json_path = tmp_path / "rehearsal.json"
    monkeypatch.setattr(
        "saymo.commands.tests._collect_auto_preflight",
        lambda config, profile, provider_name=None: [
            PreflightCheck("capture input", True, "BlackHole 16ch"),
        ],
    )

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "rehearsal",
            "--profile",
            "personal",
            "--text",
            "John, status?",
            "--output-dir",
            str(tmp_path / "rehearsals"),
            "--json-output",
            str(json_path),
            "--launch-json",
            str(launch_path),
            "--no-hotkey-probe",
        ],
    )

    assert result.exit_code == 0
    assert "launch evidence: loaded ready=no blocks=2 warns=1" in result.output
    assert "fail: launch readiness" in result.output
    _assert_no_private_content(result.output)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert set(payload["launch_evidence"]) == {
        "path",
        "mode",
        "status",
        "ready",
        "block_count",
        "warn_count",
        "failed_labels",
        "rerun_commands",
    }
    assert payload["launch_evidence"]["path"] == str(launch_path)
    assert payload["launch_evidence"]["mode"] == "dry-run"
    assert payload["launch_evidence"]["status"] == "loaded"
    assert payload["launch_evidence"]["ready"] is False
    assert payload["launch_evidence"]["block_count"] == 2
    assert payload["launch_evidence"]["warn_count"] == 1
    assert "checks" not in payload["launch_evidence"]
    assert payload["transcript"] == ""
    _assert_no_private_content(payload)


def test_rehearsal_warns_on_missing_launch_evidence_without_crashing(
    tmp_path,
    monkeypatch,
):
    config_path = _write_config(tmp_path)
    missing_path = tmp_path / "missing-dry-run.json"
    monkeypatch.setattr(
        "saymo.commands.tests._collect_auto_preflight",
        lambda config, profile, provider_name=None: [
            PreflightCheck("capture input", True, "BlackHole 16ch"),
        ],
    )

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "rehearsal",
            "--profile",
            "personal",
            "--text",
            "John, status?",
            "--output-dir",
            str(tmp_path / "rehearsals"),
            "--launch-json",
            str(missing_path),
            "--no-hotkey-probe",
        ],
    )

    assert result.exit_code == 0
    assert "launch evidence: missing" in result.output
    assert "warn: launch readiness" in result.output
    assert "saymo dry-run" not in result.output
