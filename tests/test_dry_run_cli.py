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
    "PRIVATE_GENERATED_ANSWER",
    "SECRET_TOKEN",
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
