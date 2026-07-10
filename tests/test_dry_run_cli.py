"""RED CLI tests for `saymo dry-run`."""

from __future__ import annotations

import importlib.util
import json
import textwrap
from pathlib import Path

import pytest
from click.testing import CliRunner

from saymo.commands import main


COMMANDS_AT_IMPORT = frozenset(main.commands)

PRIVATE_STRINGS = (
    "PRIVATE_DAILY_NOTE",
    "PRIVATE_TRANSCRIPT",
    "PRIVATE_PROMPT_TEXT",
    "PRIVATE_GENERATED_ANSWER",
    "PRIVATE_GENERATED_RESPONSE",
    "SECRET_TOKEN",
    "PRIVATE_VOICE_SAMPLE",
    "PRIVATE_TRAINING_DATA",
)

ARTIFACT_ONLY_KEYS = {
    "artifact_path",
    "schema_version",
    "evidence_kind",
    "created_at",
}

FORBIDDEN_DRY_RUN_REFERENCES = (
    "_auto",
    "_run_auto_start",
    "_play_cached_audio",
    "_rotate_audio_cache",
    "_prepare",
    "_prepare_responses",
    "AudioCapture",
    "LocalWhisper",
    "synthesize",
    "train",
    "download",
    "delete",
    "unlink",
    "rmtree",
    "cache.build",
    "force=True",
    "activate_meeting",
    "toggle_mute",
    "switch_mic",
    "run_handbrake_reachability_probe",
    "install_launch_agent",
    "uninstall_launch_agent",
    "start_launch_agent",
    "stop_launch_agent",
    "restart_launch_agent",
    "bootstrap_argv",
    "bootout_argv",
    "kickstart_argv",
    "commands.jsonl",
    "audit.jsonl",
    "saymo.audio",
    "saymo.providers",
    "saymo.tts",
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
            audio:
              capture_device: "BlackHole 16ch"
              playback_device: "BlackHole 2ch"
              recording_device: "MacBook Pro Microphone"
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


def _report(*, ready: bool):
    from saymo.analysis.launch_readiness import (
        LaunchReadinessCheck,
        LaunchReadinessReport,
    )

    return LaunchReadinessReport(
        profile="standup",
        provider="glip",
        checks=(
            LaunchReadinessCheck(
                key="daily_note_source_ready",
                label="daily note source ready",
                severity="info" if ready else "block",
                ok=ready,
                detail="source_sha256=abc123 PRIVATE_DAILY_NOTE",
                action="Review source evidence without SECRET_TOKEN",
                rerun="saymo dry-run -p standup --provider glip",
                metadata={
                    "source_sha256": "abc123",
                    "ready_count": 1 if ready else 0,
                    "daily_note_body": "PRIVATE_DAILY_NOTE",
                    "raw_transcript": "PRIVATE_TRANSCRIPT",
                    "generated_answer": "PRIVATE_GENERATED_ANSWER",
                    "auth_token": "SECRET_TOKEN",
                },
            ),
        ),
    )


def _remediation_report():
    from saymo.analysis.launch_readiness import (
        LaunchReadinessCheck,
        LaunchReadinessReport,
    )

    return LaunchReadinessReport(
        profile="standup",
        provider="glip",
        checks=(
            LaunchReadinessCheck(
                key="daily_note_source_ready",
                label="daily note source ready",
                severity="block",
                ok=False,
                detail="placeholder_only PRIVATE_DAILY_NOTE",
                action="Add usable standup content, then rerun dry-run",
                rerun="saymo dry-run -p standup --provider glip",
                metadata={"category": "source-data", "source_sha256": "abc123"},
            ),
            LaunchReadinessCheck(
                key="provider_capabilities",
                label="provider capabilities",
                severity="warn",
                ok=False,
                detail="mic_switch_unsupported SECRET_TOKEN",
                action="Use takeover-check before relying on mic switching.",
                rerun="saymo takeover-check -p standup",
                metadata={"category": "provider"},
            ),
        ),
    )


def _complete_evidence_report():
    from saymo.analysis.launch_readiness import (
        LaunchReadinessCheck,
        LaunchReadinessReport,
    )

    return LaunchReadinessReport(
        profile="standup",
        provider="glip",
        checks=(
            LaunchReadinessCheck(
                key="response_cache_coverage",
                label="response cache coverage",
                severity="block",
                ok=False,
                detail="missing response cache PRIVATE_TRANSCRIPT",
                action="prepare cache without PRIVATE_PROMPT_TEXT",
                rerun="saymo dry-run -p standup --provider glip",
                metadata={
                    "category": "source-data",
                    "source_sha256": "abc123",
                    "stale_reason": "source_sha_mismatch",
                    "ready": 1,
                    "total": 3,
                    "missing": 2,
                    "raw_transcript": "PRIVATE_TRANSCRIPT",
                    "prompt_text": "PRIVATE_PROMPT_TEXT",
                    "generated_response_text": "PRIVATE_GENERATED_RESPONSE",
                    "audio_bytes": "PRIVATE_GENERATED_RESPONSE",
                    "voice_sample_path": "PRIVATE_VOICE_SAMPLE",
                    "training_data_path": "PRIVATE_TRAINING_DATA",
                    "auth_token": "SECRET_TOKEN",
                },
            ),
        ),
    )


def _write_compare_artifact(
    tmp_path,
    name,
    *,
    ready: bool,
    block_count: int,
    warn_count: int,
    cache_ready: int,
    cache_total: int,
    cache_missing: int,
    provider_ok: bool,
    daemon_ok: bool,
) -> Path:
    path = tmp_path / name
    payload = {
        "schema_version": "1.0",
        "evidence_kind": "launch-readiness",
        "mode": "dry-run",
        "artifact_path": str(path),
        "created_at": "2026-07-10T14:30:00Z",
        "profile": "personal",
        "provider": "glip",
        "ready": ready,
        "check_count": 3,
        "ready_count": 3 if ready else 0,
        "block_count": block_count,
        "warn_count": warn_count,
        "checks": [
            {
                "key": "response_cache_coverage",
                "label": "response cache coverage",
                "severity": "block",
                "ok": cache_missing == 0,
                "detail": "cache coverage PRIVATE_TRANSCRIPT",
                "action": "prepare without PRIVATE_PROMPT_TEXT",
                "rerun": "" if cache_missing == 0 else "saymo dry-run -p personal --provider glip",
                "metadata": {
                    "category": "source-data",
                    "ready": cache_ready,
                    "total": cache_total,
                    "missing": cache_missing,
                    "prompt_text": "PRIVATE_PROMPT_TEXT",
                },
            },
            {
                "key": "provider_meeting_tab",
                "label": "provider meeting tab",
                "severity": "block",
                "ok": provider_ok,
                "detail": "provider tab SECRET_TOKEN",
                "action": "open tab without PRIVATE_GENERATED_RESPONSE",
                "rerun": "" if provider_ok else "saymo dry-run -p personal --provider glip",
                "metadata": {"category": "provider", "meeting_found": provider_ok},
            },
            {
                "key": "call_control_daemon",
                "label": "call-control daemon",
                "severity": "block",
                "ok": daemon_ok,
                "detail": "daemon heartbeat SECRET_TOKEN",
                "action": "check daemon without PRIVATE_VOICE_SAMPLE",
                "rerun": "" if daemon_ok else "saymo call-control-agent status -p personal",
                "metadata": {
                    "category": "call-control",
                    "running": daemon_ok,
                    "heartbeat_fresh": daemon_ok,
                    "daemon_ok": daemon_ok,
                },
            },
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _assert_no_private_text(output: str) -> None:
    for value in PRIVATE_STRINGS:
        assert value not in output


def _dry_run_result_lines(output: str) -> list[str]:
    return [line for line in output.splitlines() if line.startswith("dry-run: ")]


def test_dry_run_calls_launch_readiness_without_prepare(tmp_path, monkeypatch):
    import saymo.commands.dry_run as dry_run_module

    config_path = _write_config(tmp_path)
    calls = []

    def fake_collect(
        config,
        *,
        profile: str,
        provider_name: str | None,
        prepare: bool,
        mode: str = "call-ready",
    ):
        assert profile == "standup"
        assert provider_name == "glip"
        assert prepare is False
        assert mode == "dry-run"
        calls.append((profile, provider_name, prepare, mode))
        return _report(ready=True)

    monkeypatch.setattr(dry_run_module, "collect_launch_readiness", fake_collect)

    result = CliRunner().invoke(
        main,
        ["--config", str(config_path), "dry-run", "-p", "standup", "--provider", "glip"],
    )

    assert result.exit_code == 0
    assert calls == [("standup", "glip", False, "dry-run")]
    assert _dry_run_result_lines(result.output) == ["dry-run: ready"]
    _assert_no_private_text(result.output)


def test_dry_run_prepare_source_calls_launch_readiness_with_prepare_true(
    tmp_path,
    monkeypatch,
):
    import saymo.commands.dry_run as dry_run_module

    config_path = _write_config(tmp_path)
    calls = []

    def fake_collect(
        config,
        *,
        profile: str,
        provider_name: str | None,
        prepare: bool,
        mode: str = "call-ready",
    ):
        assert prepare is True
        assert mode == "dry-run"
        calls.append((profile, provider_name, prepare, mode))
        return _report(ready=True)

    monkeypatch.setattr(dry_run_module, "collect_launch_readiness", fake_collect)

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "dry-run",
            "-p",
            "standup",
            "--provider",
            "glip",
            "--prepare-source",
        ],
    )

    assert result.exit_code == 0
    assert calls == [("standup", "glip", True, "dry-run")]
    assert _dry_run_result_lines(result.output) == ["dry-run: ready"]
    _assert_no_private_text(result.output)


def test_dry_run_cli_options_and_registration(tmp_path):
    assert "dry-run" in COMMANDS_AT_IMPORT

    result = CliRunner().invoke(main, ["dry-run", "--help"])
    config_path = _write_config(tmp_path)
    prepare_result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "dry-run",
            "-p",
            "standup",
            "--provider",
            "glip",
            "--prepare",
        ],
    )

    assert result.exit_code == 0
    assert "-p, --profile" in result.output
    assert "--provider" in result.output
    assert "--json" in result.output
    assert "--output" in result.output
    assert "--prepare-source" in result.output
    assert prepare_result.exit_code == 2
    assert "No such option: --prepare" in prepare_result.output


def test_dry_run_prints_top_level_result_and_exit_code(tmp_path, monkeypatch):
    import saymo.commands.dry_run as dry_run_module

    config_path = _write_config(tmp_path)
    reports = iter((_report(ready=True), _report(ready=False)))
    monkeypatch.setattr(
        dry_run_module,
        "collect_launch_readiness",
        lambda config, *, profile, provider_name, prepare, mode="call-ready": next(
            reports
        ),
    )

    ready = CliRunner().invoke(
        main,
        ["--config", str(config_path), "dry-run", "-p", "standup", "--provider", "glip"],
    )
    not_ready = CliRunner().invoke(
        main,
        ["--config", str(config_path), "dry-run", "-p", "standup", "--provider", "glip"],
    )

    assert ready.exit_code == 0
    assert not_ready.exit_code == 1
    assert _dry_run_result_lines(ready.output) == ["dry-run: ready"]
    assert _dry_run_result_lines(not_ready.output) == ["dry-run: not ready"]
    _assert_no_private_text(ready.output)
    _assert_no_private_text(not_ready.output)


def test_dry_run_groups_remediation_with_rerun_commands(tmp_path, monkeypatch):
    import saymo.commands.dry_run as dry_run_module

    config_path = _write_config(tmp_path)
    monkeypatch.setattr(
        dry_run_module,
        "collect_launch_readiness",
        lambda config, *, profile, provider_name, prepare, mode="call-ready": (
            _remediation_report()
        ),
    )

    result = CliRunner().invoke(
        main,
        ["--config", str(config_path), "dry-run", "-p", "standup", "--provider", "glip"],
    )

    assert result.exit_code == 1
    assert _dry_run_result_lines(result.output) == ["dry-run: not ready"]
    assert "remediation:" in result.output
    assert "block:" in result.output
    assert "warn:" in result.output
    assert "- [source-data] daily note source ready" in result.output
    assert "action: Add usable standup content, then rerun dry-run" in result.output
    assert "rerun: saymo dry-run -p standup --provider glip" in result.output
    assert "- [provider] provider capabilities" in result.output
    assert "rerun: saymo takeover-check -p standup" in result.output
    _assert_no_private_text(result.output)


def test_dry_run_json_is_sanitized_machine_contract(tmp_path, monkeypatch):
    import saymo.commands.dry_run as dry_run_module

    config_path = _write_config(tmp_path)
    monkeypatch.setattr(
        dry_run_module,
        "collect_launch_readiness",
        lambda config, *, profile, provider_name, prepare, mode="call-ready": _report(
            ready=True
        ),
    )

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "dry-run",
            "-p",
            "standup",
            "--provider",
            "glip",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["mode"] == "dry-run"
    assert payload["profile"] == "standup"
    assert payload["provider"] == "glip"
    assert payload["ready"] is True
    assert payload["check_count"] == 1
    assert payload["ready_count"] == 1
    assert payload["block_count"] == 0
    assert payload["warn_count"] == 0
    assert payload["checks"][0]["key"] == "daily_note_source_ready"
    for key in ARTIFACT_ONLY_KEYS:
        assert key not in payload
    _assert_no_private_text(result.output)


def test_dry_run_output_artifact_uses_dry_run_mode(tmp_path, monkeypatch):
    import saymo.commands.dry_run as dry_run_module

    config_path = _write_config(tmp_path)
    output_path = tmp_path / "dry-run.json"
    monkeypatch.setattr(
        dry_run_module,
        "collect_launch_readiness",
        lambda config, *, profile, provider_name, prepare, mode="call-ready": _report(
            ready=False
        ),
    )

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "dry-run",
            "-p",
            "standup",
            "--provider",
            "glip",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 1
    assert _dry_run_result_lines(result.output) == ["dry-run: not ready"]
    assert f"artifact: {output_path}" in result.output
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0"
    assert payload["evidence_kind"] == "launch-readiness"
    assert payload["mode"] == "dry-run"
    assert payload["artifact_path"] == str(output_path)
    assert payload["created_at"]
    assert payload["profile"] == "standup"
    assert payload["provider"] == "glip"
    assert payload["ready"] is False
    _assert_no_private_text(result.output)
    _assert_no_private_text(json.dumps(payload, ensure_ascii=False))


def test_dry_run_output_artifact_has_complete_sanitized_evidence_fields(
    tmp_path,
    monkeypatch,
):
    import saymo.commands.dry_run as dry_run_module

    config_path = _write_config(tmp_path)
    output_path = tmp_path / "dry-run-complete.json"
    monkeypatch.setattr(
        dry_run_module,
        "collect_launch_readiness",
        lambda config, *, profile, provider_name, prepare, mode="call-ready": (
            _complete_evidence_report()
        ),
    )

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "dry-run",
            "-p",
            "standup",
            "--provider",
            "glip",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert {
        "schema_version",
        "evidence_kind",
        "mode",
        "artifact_path",
        "created_at",
        "profile",
        "provider",
        "ready",
        "check_count",
        "ready_count",
        "block_count",
        "warn_count",
        "checks",
    }.issubset(payload)
    assert payload["mode"] == "dry-run"
    assert payload["artifact_path"] == str(output_path)
    assert payload["check_count"] == 1
    check = payload["checks"][0]
    assert {
        "key",
        "label",
        "severity",
        "ok",
        "detail",
        "action",
        "rerun",
        "metadata",
    }.issubset(check)
    assert check["key"] == "response_cache_coverage"
    assert check["label"] == "response cache coverage"
    assert check["severity"] == "block"
    assert check["ok"] is False
    assert check["rerun"] == "saymo dry-run -p standup --provider glip"
    assert check["metadata"]["category"] == "source-data"
    assert check["metadata"]["source_sha256"] == "abc123"
    assert check["metadata"]["stale_reason"] == "source_sha_mismatch"
    assert check["metadata"]["ready"] == 1
    assert check["metadata"]["total"] == 3
    assert check["metadata"]["missing"] == 2
    _assert_no_private_text(result.output)
    _assert_no_private_text(json.dumps(payload, ensure_ascii=False))


def test_dry_run_compare_cli_prints_human_and_json_without_private_content(tmp_path):
    current = _write_compare_artifact(
        tmp_path,
        "current.json",
        ready=True,
        block_count=0,
        warn_count=0,
        cache_ready=3,
        cache_total=3,
        cache_missing=0,
        provider_ok=True,
        daemon_ok=True,
    )
    previous = _write_compare_artifact(
        tmp_path,
        "previous.json",
        ready=False,
        block_count=3,
        warn_count=1,
        cache_ready=0,
        cache_total=3,
        cache_missing=3,
        provider_ok=False,
        daemon_ok=False,
    )

    human = CliRunner().invoke(
        main,
        ["dry-run-compare", "--current", str(current), "--previous", str(previous)],
    )
    machine = CliRunner().invoke(
        main,
        [
            "dry-run-compare",
            "--current",
            str(current),
            "--previous",
            str(previous),
            "--json",
        ],
    )

    assert "dry-run-compare" in main.commands
    assert human.exit_code == 0
    assert machine.exit_code == 0
    assert "dry-run comparison: improved" in human.output
    payload = json.loads(machine.output)
    assert payload["status"] == "improved"
    _assert_no_private_text(human.output)
    _assert_no_private_text(machine.output)


def test_dry_run_has_no_prepare_path(tmp_path):
    import saymo.commands.dry_run  # noqa: F401

    config_path = _write_config(tmp_path)
    prepare_result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "dry-run",
            "-p",
            "standup",
            "--provider",
            "glip",
            "--prepare",
        ],
    )

    assert prepare_result.exit_code == 2
    assert "No such option: --prepare" in prepare_result.output


def test_dry_run_path_is_non_destructive():
    spec = importlib.util.find_spec("saymo.commands.dry_run")
    if spec is None or spec.origin is None:
        pytest.fail("missing saymo.commands.dry_run module for dry-run guard")

    source = Path(spec.origin).read_text(encoding="utf-8")

    for forbidden in FORBIDDEN_DRY_RUN_REFERENCES:
        assert forbidden not in source
