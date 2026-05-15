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


def test_trigger_learn_adds_heard_variant_to_fuzzy_expansions(tmp_path):
    import yaml

    config_path = _write_config(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "trigger-learn",
            "--profile",
            "personal",
            "--heard",
            "Меша",
        ],
    )

    assert result.exit_code == 0
    assert "learned: yes" in result.output
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert data["vocabulary"]["fuzzy_expansions"]["Миша"] == ["Меша"]


def test_trigger_learn_does_not_duplicate_existing_variant(tmp_path):
    import yaml

    config_path = _write_config(tmp_path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["vocabulary"] = {"fuzzy_expansions": {"Миша": ["Меша"]}}
    config_path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "trigger-learn",
            "--profile",
            "personal",
            "--heard",
            "Меша",
        ],
    )

    assert result.exit_code == 0
    assert "learned: no" in result.output
    updated = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert updated["vocabulary"]["fuzzy_expansions"]["Миша"] == ["Меша"]


def test_trigger_setup_learns_and_verifies_heard_variant(tmp_path):
    import yaml

    config_path = _write_config(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "trigger-setup",
            "--profile",
            "personal",
            "--heard",
            "Меша",
        ],
    )

    assert result.exit_code == 0
    assert "learned: yes" in result.output
    assert "trigger after learning: yes" in result.output
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert data["vocabulary"]["fuzzy_expansions"]["Миша"] == ["Меша"]


def test_trigger_setup_extracts_name_variant_from_transcribed_question(tmp_path):
    import yaml

    config_path = _write_config(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "trigger-setup",
            "--profile",
            "personal",
            "--heard",
            "Меша, что по статусу?",
        ],
    )

    assert result.exit_code == 0
    assert "variant: Меша\n" in result.output
    assert "trigger after learning: yes" in result.output
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert data["vocabulary"]["fuzzy_expansions"]["Миша"] == ["Меша"]


def test_trigger_setup_extracts_name_variant_without_punctuation(tmp_path):
    import yaml

    config_path = _write_config(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "trigger-setup",
            "--profile",
            "personal",
            "--heard",
            "Меша что по статусу",
        ],
    )

    assert result.exit_code == 0
    assert "variant: Меша\n" in result.output
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert data["vocabulary"]["fuzzy_expansions"]["Миша"] == ["Меша"]


def test_trigger_setup_extracts_name_variant_before_final_question_word(tmp_path):
    import yaml

    config_path = _write_config(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "trigger-setup",
            "--profile",
            "personal",
            "--heard",
            "Меша что?",
        ],
    )

    assert result.exit_code == 0
    assert "variant: Меша\n" in result.output
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert data["vocabulary"]["fuzzy_expansions"]["Миша"] == ["Меша"]
