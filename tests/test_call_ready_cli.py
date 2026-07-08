"""CLI tests for `saymo call-ready`."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from click.testing import CliRunner

from saymo.commands import main


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


def _report(*, ready: bool):
    from saymo.analysis.launch_readiness import (
        LaunchReadinessCheck,
        LaunchReadinessReport,
    )

    check = LaunchReadinessCheck(
        key="daily_note_source",
        label="daily note source",
        severity="info" if ready else "block",
        ok=ready,
        detail="source_sha256=abc123 ready_count=1",
        action="saymo call-ready -p standup --provider glip --prepare",
        rerun="saymo call-ready -p standup --provider glip",
        metadata={"source_sha256": "abc123", "ready_count": 1 if ready else 0},
    )
    return LaunchReadinessReport(
        profile="standup",
        provider="glip",
        checks=(check,),
    )


def _assert_no_private_text(output: str) -> None:
    for value in PRIVATE_STRINGS:
        assert value not in output


def _top_level_result_lines(output: str) -> list[str]:
    return [line for line in output.splitlines() if line.startswith("call-ready: ")]


def test_call_ready_prints_top_level_result(tmp_path, monkeypatch):
    import saymo.commands.call_ready as call_ready_module

    config_path = _write_config(tmp_path)
    reports = iter((_report(ready=True), _report(ready=False)))

    def fake_collect(config, *, profile: str, provider_name: str | None, prepare: bool):
        assert profile == "standup"
        assert provider_name == "glip"
        assert prepare is False
        return next(reports)

    monkeypatch.setattr(call_ready_module, "collect_launch_readiness", fake_collect)
    runner = CliRunner()

    ready = runner.invoke(
        main,
        ["--config", str(config_path), "call-ready", "-p", "standup", "--provider", "glip"],
    )
    not_ready = runner.invoke(
        main,
        ["--config", str(config_path), "call-ready", "-p", "standup", "--provider", "glip"],
    )

    assert ready.exit_code == 0
    assert not_ready.exit_code == 1
    assert _top_level_result_lines(ready.output) == ["call-ready: ready"]
    assert _top_level_result_lines(not_ready.output) == ["call-ready: not ready"]
    _assert_no_private_text(ready.output)
    _assert_no_private_text(not_ready.output)


def test_call_ready_json_is_sanitized(tmp_path, monkeypatch):
    import saymo.commands.call_ready as call_ready_module

    config_path = _write_config(tmp_path)
    monkeypatch.setattr(
        call_ready_module,
        "collect_launch_readiness",
        lambda config, *, profile, provider_name, prepare: _report(ready=True),
    )

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "call-ready",
            "-p",
            "standup",
            "--provider",
            "glip",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ready"] is True
    assert payload["profile"] == "standup"
    assert payload["provider"] == "glip"
    assert payload["checks"][0]["key"] == "daily_note_source"
    _assert_no_private_text(result.output)


def test_call_ready_prepare_creates_note_without_overwrite(tmp_path):
    from datetime import date

    vault = tmp_path / "Vault"
    vault.mkdir()
    today = vault / f"{date.today().strftime('%Y-%m-%d')}.md"
    existing = "already written\n"
    today.write_text(existing, encoding="utf-8")
    config_path = _write_config(tmp_path, vault_path=vault)

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "call-ready",
            "-p",
            "standup",
            "--provider",
            "glip",
            "--prepare",
        ],
    )

    assert today.read_text(encoding="utf-8") == existing
    assert "call-ready:" in result.output
    _assert_no_private_text(result.output)


def test_call_ready_groups_remediation_with_rerun_commands(tmp_path, monkeypatch):
    import saymo.commands.call_ready as call_ready_module
    from saymo.analysis.launch_readiness import LaunchReadinessCheck, LaunchReadinessReport

    config_path = _write_config(tmp_path)
    report = LaunchReadinessReport(
        profile="standup",
        provider="glip",
        checks=(
            LaunchReadinessCheck(
                key="daily_note_source",
                label="daily note source",
                severity="block",
                ok=False,
                detail="placeholder_only",
                action="Fill today's standup note",
                rerun="saymo call-ready -p standup --provider glip",
            ),
            LaunchReadinessCheck(
                key="provider_basic_scope",
                label="provider basic scope",
                severity="warn",
                ok=False,
                detail="deferred_to_phase=37",
                action="Run provider remediation in Phase 37",
                rerun="saymo call-ready -p standup --provider glip",
            ),
            LaunchReadinessCheck(
                key="profile",
                label="profile",
                severity="info",
                ok=True,
                detail="profile=standup",
            ),
        ),
    )
    monkeypatch.setattr(
        call_ready_module,
        "collect_launch_readiness",
        lambda config, *, profile, provider_name, prepare: report,
    )

    result = CliRunner().invoke(
        main,
        ["--config", str(config_path), "call-ready", "-p", "standup", "--provider", "glip"],
    )

    assert result.exit_code == 1
    assert "call-ready: not ready" in result.output
    assert "block:" in result.output
    assert "warn:" in result.output
    assert "info:" in result.output
    assert "rerun: saymo call-ready -p standup --provider glip" in result.output
    _assert_no_private_text(result.output)
