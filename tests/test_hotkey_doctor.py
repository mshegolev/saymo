"""CLI tests for hotkey diagnostics."""

import textwrap

from click.testing import CliRunner

from saymo.commands import main


def test_hotkey_doctor_reports_bindings_without_probe(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        textwrap.dedent(
            """
            safety:
              hotkey_toggle: "<cmd>+<shift>+m"
              hotkey_hard_disable: "<cmd>+<shift>+h"
            meetings:
              personal:
                description: "Personal"
                provider: glip
                team: false
                source: obsidian
                trigger_phrases:
                  - "John"
            """
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "hotkey-doctor",
            "--profile",
            "personal",
            "--no-probe",
        ],
    )

    assert result.exit_code == 0
    assert "profile: personal" in result.output
    assert "terminal focus: not required" in result.output
    assert "toggle_auto_answer: <cmd>+<shift>+m" in result.output
    assert "hard_disable: <cmd>+<shift>+h" in result.output
    assert "remediation:" in result.output
    assert "[retest] Start Saymo auto listener" in result.output
    assert "rerun: saymo hotkey-doctor -p personal --no-probe" in result.output
