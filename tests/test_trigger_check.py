"""CLI tests for `saymo trigger-check` diagnostics."""

import textwrap

from click.testing import CliRunner

from saymo.commands import main


def _write_config(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        textwrap.dedent(
            """
            user:
              name: "Миша"
              name_variants:
                - "Миша"
              language: ru
            meetings:
              personal:
                description: "Personal"
                provider: glip
                team: false
                source: obsidian
                trigger_phrases:
                  - "Миша"
            responses:
              enabled: true
              confidence_threshold: 0.6
              live_fallback: false
              intent_classifier: false
              library: {}
            """
        ),
        encoding="utf-8",
    )
    return config_path


def test_trigger_check_text_reports_addressed_question(tmp_path):
    config_path = _write_config(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "trigger-check",
            "--profile",
            "personal",
            "--text",
            "Миша, что по статусу?",
        ],
    )

    assert result.exit_code == 0
    assert "trigger: yes" in result.output
    assert "addressing: addressed_to_me" in result.output
    assert "question: yes" in result.output
    assert "response:" in result.output


def test_trigger_check_text_reports_ignored_mention(tmp_path):
    config_path = _write_config(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "trigger-check",
            "--profile",
            "personal",
            "--text",
            "как Миша вчера говорил, надо проверить логи",
        ],
    )

    assert result.exit_code == 0
    assert "trigger: yes" in result.output
    assert "addressing: mentioned_not_addressed" in result.output
    assert "will answer: no" in result.output
