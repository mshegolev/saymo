"""CLI tests for pre-call rehearsal."""

import json
import textwrap

from click.testing import CliRunner

from saymo.commands import main
from saymo.commands.tests import PreflightCheck


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

