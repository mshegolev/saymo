"""CLI tests for `saymo trigger-check` diagnostics."""

from types import SimpleNamespace
import textwrap

from click.testing import CliRunner

from saymo.commands import main


def _write_config(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        textwrap.dedent(
            """
            user:
              name: "John"
              name_variants:
                - "John"
              language: ru
            meetings:
              personal:
                description: "Personal"
                provider: glip
                team: false
                source: obsidian
                trigger_phrases:
                  - "John"
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
            "John, что по статусу?",
        ],
    )

    assert result.exit_code == 0
    assert "trigger: yes" in result.output
    assert "addressing: addressed_to_me" in result.output
    assert "question: yes" in result.output
    assert "response:" in result.output


def test_trigger_check_reports_confirmation_wait_for_first_trigger(tmp_path):
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
            "John, что по статусу?",
        ],
    )

    assert result.exit_code == 0
    assert "will answer: yes" in result.output
    assert "confirmation: required within 6.0s" in result.output
    assert "auto action: wait_for_confirmation" in result.output


def test_trigger_check_reports_answer_now_when_confirmation_disabled(tmp_path):
    import yaml

    config_path = _write_config(tmp_path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["safety"] = {"require_confirmation": False}
    config_path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
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
            "John, что по статусу?",
        ],
    )

    assert result.exit_code == 0
    assert "confirmation: disabled" in result.output
    assert "auto action: answer_now" in result.output


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
            "как John вчера говорил, надо проверить логи",
        ],
    )

    assert result.exit_code == 0
    assert "trigger: yes" in result.output
    assert "addressing: mentioned_not_addressed" in result.output
    assert "will answer: no" in result.output
    assert "auto action: skip" in result.output


def test_trigger_check_text_reports_third_person_question_as_skip(tmp_path):
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
            "что John думает по этой задаче?",
        ],
    )

    assert result.exit_code == 0
    assert "trigger: yes" in result.output
    assert "addressing: mentioned_not_addressed" in result.output
    assert "question: yes" in result.output
    assert "auto action: skip" in result.output


def test_trigger_check_text_reports_third_person_statement_as_skip(tmp_path):
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
            "John думает, что надо сначала проверить логи",
        ],
    )

    assert result.exit_code == 0
    assert "trigger: yes" in result.output
    assert "addressing: mentioned_not_addressed" in result.output
    assert "question: no" in result.output
    assert "auto action: skip" in result.output


def test_trigger_capture_help_is_available():
    result = CliRunner().invoke(main, ["trigger-capture", "--help"])

    assert result.exit_code == 0
    assert "Capture live call audio into classified trigger samples" in result.output


def test_trigger_capture_defaults_to_capture_device(monkeypatch):
    from saymo.commands.tests import _resolve_trigger_capture_device

    fake_device = SimpleNamespace(index=17)
    calls = []

    def fake_find_device(name, kind):
        calls.append((name, kind))
        return fake_device if name == "BlackHole 16ch" else None

    monkeypatch.setattr("saymo.audio.devices.find_device", fake_find_device)
    config = SimpleNamespace(
        audio=SimpleNamespace(
            capture_device="BlackHole 16ch",
            recording_device="MacBook Pro Microphone",
        )
    )

    name, device = _resolve_trigger_capture_device(config, None)

    assert name == "BlackHole 16ch"
    assert device is fake_device
    assert calls == [("BlackHole 16ch", "input")]


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
            "Jon",
        ],
    )

    assert result.exit_code == 0
    assert "learned: yes" in result.output
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert data["vocabulary"]["fuzzy_expansions"]["John"] == ["Jon"]


def test_trigger_learn_does_not_duplicate_existing_variant(tmp_path):
    import yaml

    config_path = _write_config(tmp_path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["vocabulary"] = {"fuzzy_expansions": {"John": ["Jon"]}}
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
            "Jon",
        ],
    )

    assert result.exit_code == 0
    assert "learned: no" in result.output
    updated = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert updated["vocabulary"]["fuzzy_expansions"]["John"] == ["Jon"]


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
            "Jon",
        ],
    )

    assert result.exit_code == 0
    assert "learned: yes" in result.output
    assert "trigger after learning: yes" in result.output
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert data["vocabulary"]["fuzzy_expansions"]["John"] == ["Jon"]


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
            "Jon, что по статусу?",
        ],
    )

    assert result.exit_code == 0
    assert "variant: Jon\n" in result.output
    assert "trigger after learning: yes" in result.output
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert data["vocabulary"]["fuzzy_expansions"]["John"] == ["Jon"]


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
            "Jon что по статусу",
        ],
    )

    assert result.exit_code == 0
    assert "variant: Jon\n" in result.output
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert data["vocabulary"]["fuzzy_expansions"]["John"] == ["Jon"]


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
            "Jon что?",
        ],
    )

    assert result.exit_code == 0
    assert "variant: Jon\n" in result.output
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert data["vocabulary"]["fuzzy_expansions"]["John"] == ["Jon"]
