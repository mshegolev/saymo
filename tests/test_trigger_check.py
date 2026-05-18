"""CLI tests for `saymo trigger-check` diagnostics."""

from types import SimpleNamespace
import json
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


def _write_sample(
    samples_dir,
    *,
    profile="personal",
    category,
    name="sample",
    transcript,
    trigger=False,
    question=False,
    will_answer=False,
    rms=0.01,
    peak=0.1,
    speaker=None,
    decision=None,
):
    metadata = {
        "profile": profile,
        "created_at": "2026-05-15T10:00:00",
        "sample_rate": 16000,
        "wav": f"{name}.wav",
        "transcript": transcript,
        "category": category,
        "trigger": trigger,
        "addressing": "addressed_to_me" if will_answer else "ignore",
        "question": question,
        "will_answer": will_answer,
        "reason": "test",
        "rms": rms,
        "peak": peak,
    }
    if speaker is not None:
        metadata["speaker"] = speaker
    if decision is not None:
        metadata["answer_decision"] = decision
    sample_dir = samples_dir / profile / category
    sample_dir.mkdir(parents=True, exist_ok=True)
    path = sample_dir / f"{name}.json"
    path.write_text(
        json.dumps(metadata, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def test_trigger_eval_reports_counts_misses_and_false_positives(tmp_path):
    config_path = _write_config(tmp_path)
    samples_dir = tmp_path / "samples"
    _write_sample(
        samples_dir,
        category="asked_to_speak",
        name="miss",
        transcript="Jon, что по статусу?",
        trigger=True,
        question=True,
        will_answer=True,
    )
    _write_sample(
        samples_dir,
        category="speech",
        name="false_positive",
        transcript="John, что по статусу?",
    )
    _write_sample(
        samples_dir,
        category="question",
        name="question",
        transcript="что по статусу?",
        question=True,
    )
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "trigger-eval",
            "--profile",
            "personal",
            "--samples-dir",
            str(samples_dir),
        ],
    )

    assert result.exit_code == 0
    assert "records: 3" in result.output
    assert "stored asked_to_speak: 1" in result.output
    assert "stored question: 1" in result.output
    assert "stored speech: 1" in result.output
    assert "misses: 1" in result.output
    assert "false positives: 1" in result.output
    assert "speaker unknown: records=3" in result.output


def test_trigger_eval_groups_counts_by_speaker(tmp_path):
    config_path = _write_config(tmp_path)
    samples_dir = tmp_path / "samples"
    _write_sample(
        samples_dir,
        category="asked_to_speak",
        name="me_ok",
        transcript="John, что по статусу?",
        trigger=True,
        question=True,
        will_answer=True,
        speaker="me",
    )
    _write_sample(
        samples_dir,
        category="speech",
        name="other_false_positive",
        transcript="John, что по статусу?",
        speaker="other",
    )
    _write_sample(
        samples_dir,
        category="question",
        name="legacy_unknown",
        transcript="что по статусу?",
        question=True,
    )

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "trigger-eval",
            "--profile",
            "personal",
            "--samples-dir",
            str(samples_dir),
        ],
    )

    assert result.exit_code == 0
    assert "speaker me: records=1 misses=0 false positives=0 answers=1" in result.output
    assert "speaker other: records=1 misses=0 false positives=1 answers=1" in result.output
    assert "speaker unknown: records=1 misses=0 false positives=0 answers=0" in result.output


def test_trigger_eval_promotes_sample_variant_and_reruns(tmp_path):
    import yaml

    config_path = _write_config(tmp_path)
    samples_dir = tmp_path / "samples"
    sample_path = _write_sample(
        samples_dir,
        category="asked_to_speak",
        name="miss",
        transcript="Jon, что по статусу?",
        trigger=True,
        question=True,
        will_answer=True,
    )
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "trigger-eval",
            "--profile",
            "personal",
            "--samples-dir",
            str(samples_dir),
            "--promote",
            str(sample_path),
        ],
    )

    assert result.exit_code == 0
    assert "variant: Jon" in result.output
    assert "learned: yes" in result.output
    assert "misses: 0" in result.output
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert data["vocabulary"]["fuzzy_expansions"]["John"] == ["Jon"]


def test_trigger_samples_list_replay_and_sanitized_report(tmp_path):
    config_path = _write_config(tmp_path)
    samples_dir = tmp_path / "samples"
    sample_path = _write_sample(
        samples_dir,
        category="question",
        name="question",
        transcript="секретный текст вопроса",
        question=True,
    )
    report_path = tmp_path / "report.md"
    runner = CliRunner()

    listed = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "trigger-samples",
            "list",
            "--profile",
            "personal",
            "--samples-dir",
            str(samples_dir),
        ],
    )
    replayed = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "trigger-samples",
            "replay",
            str(sample_path),
            "--no-play",
        ],
    )
    reported = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "trigger-samples",
            "report",
            "--profile",
            "personal",
            "--samples-dir",
            str(samples_dir),
            "--output",
            str(report_path),
        ],
    )

    assert listed.exit_code == 0
    assert "samples: 1" in listed.output
    assert "speaker=unknown" in listed.output
    assert "transcript: секретный текст вопроса" in listed.output
    assert replayed.exit_code == 0
    assert "stored: category=question speaker=unknown" in replayed.output
    assert "current:" in replayed.output
    assert reported.exit_code == 0
    report = report_path.read_text(encoding="utf-8")
    assert "question.json" in report
    assert "speaker=unknown" in report
    assert "секретный текст вопроса" not in report


def test_trigger_samples_label_updates_speaker_metadata(tmp_path):
    config_path = _write_config(tmp_path)
    samples_dir = tmp_path / "samples"
    sample_path = _write_sample(
        samples_dir,
        category="question",
        name="question",
        transcript="что по статусу?",
        question=True,
    )

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "trigger-samples",
            "label",
            str(sample_path),
            "--speaker",
            "other",
        ],
    )

    assert result.exit_code == 0
    assert "speaker: unknown -> other" in result.output
    metadata = json.loads(sample_path.read_text(encoding="utf-8"))
    assert metadata["speaker"] == "other"


def test_trigger_samples_decision_updates_answer_metadata(tmp_path):
    config_path = _write_config(tmp_path)
    samples_dir = tmp_path / "samples"
    sample_path = _write_sample(
        samples_dir,
        category="asked_to_speak",
        name="accepted",
        transcript="John, что по статусу?",
        trigger=True,
        question=True,
        will_answer=True,
    )
    runner = CliRunner()

    updated = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "trigger-samples",
            "decision",
            str(sample_path),
            "--decision",
            "accepted",
        ],
    )
    listed = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "trigger-samples",
            "list",
            "--profile",
            "personal",
            "--samples-dir",
            str(samples_dir),
        ],
    )
    replayed = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "trigger-samples",
            "replay",
            str(sample_path),
            "--no-play",
        ],
    )

    assert updated.exit_code == 0
    assert "decision: unlabeled -> accepted" in updated.output
    metadata = json.loads(sample_path.read_text(encoding="utf-8"))
    assert metadata["answer_decision"] == "accepted"
    assert listed.exit_code == 0
    assert "decision=accepted" in listed.output
    assert replayed.exit_code == 0
    assert "decision=accepted" in replayed.output


def test_trigger_classifier_train_refuses_insufficient_labels(tmp_path):
    config_path = _write_config(tmp_path)
    samples_dir = tmp_path / "samples"
    _write_sample(
        samples_dir,
        category="asked_to_speak",
        name="accepted",
        transcript="John, что по статусу?",
        trigger=True,
        question=True,
        will_answer=True,
        decision="accepted",
    )

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "trigger-classifier",
            "train",
            "--profile",
            "personal",
            "--samples-dir",
            str(samples_dir),
            "--model-dir",
            str(tmp_path / "models"),
            "--min-total",
            "2",
            "--min-per-class",
            "1",
        ],
    )

    assert result.exit_code != 0
    assert "Need at least 2 labeled samples" in result.output


def test_trigger_classifier_train_inspect_and_delete(tmp_path):
    config_path = _write_config(tmp_path)
    samples_dir = tmp_path / "samples"
    model_dir = tmp_path / "models"
    _write_sample(
        samples_dir,
        category="asked_to_speak",
        name="accepted",
        transcript="John, что по статусу?",
        trigger=True,
        question=True,
        will_answer=True,
        decision="accepted",
        speaker="other",
    )
    _write_sample(
        samples_dir,
        category="speech",
        name="rejected",
        transcript="как John вчера говорил, надо проверить логи",
        trigger=True,
        question=False,
        will_answer=False,
        decision="rejected",
        speaker="other",
    )
    runner = CliRunner()

    trained = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "trigger-classifier",
            "train",
            "--profile",
            "personal",
            "--samples-dir",
            str(samples_dir),
            "--model-dir",
            str(model_dir),
            "--min-total",
            "2",
            "--min-per-class",
            "1",
        ],
    )
    inspected = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "trigger-classifier",
            "inspect",
            "--profile",
            "personal",
            "--model-dir",
            str(model_dir),
        ],
    )
    model_path = model_dir / "personal.json"
    assert trained.exit_code == 0
    assert "trained: yes" in trained.output
    assert "accepted=1 rejected=1" in trained.output
    assert model_path.exists()
    assert inspected.exit_code == 0
    assert "profile: personal" in inspected.output
    assert "accepted: 1" in inspected.output
    assert "rejected: 1" in inspected.output

    deleted = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "trigger-classifier",
            "delete",
            "--profile",
            "personal",
            "--model-dir",
            str(model_dir),
            "--yes",
        ],
    )

    assert deleted.exit_code == 0
    assert "deleted: yes" in deleted.output
    assert not model_path.exists()


def test_trigger_eval_shows_classifier_shadow_diagnostics(tmp_path):
    config_path = _write_config(tmp_path)
    samples_dir = tmp_path / "samples"
    model_dir = tmp_path / "models"
    _write_sample(
        samples_dir,
        category="asked_to_speak",
        name="accepted",
        transcript="John, что по статусу?",
        trigger=True,
        question=True,
        will_answer=True,
        decision="accepted",
    )
    _write_sample(
        samples_dir,
        category="speech",
        name="rejected",
        transcript="как John вчера говорил, надо проверить логи",
        trigger=True,
        question=False,
        will_answer=False,
        decision="rejected",
    )
    runner = CliRunner()
    trained = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "trigger-classifier",
            "train",
            "--profile",
            "personal",
            "--samples-dir",
            str(samples_dir),
            "--model-dir",
            str(model_dir),
            "--min-total",
            "2",
            "--min-per-class",
            "1",
        ],
    )

    result = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "trigger-eval",
            "--profile",
            "personal",
            "--samples-dir",
            str(samples_dir),
            "--classifier-shadow",
            "--model-dir",
            str(model_dir),
        ],
    )

    assert trained.exit_code == 0
    assert result.exit_code == 0
    assert "classifier shadow: model=" in result.output
    assert "classifier accepted:" in result.output
    assert "classifier rejected:" in result.output
    assert "classifier disagreements:" in result.output
    assert "records: 2" in result.output


def test_trigger_check_shows_classifier_shadow_diagnostics(tmp_path):
    config_path = _write_config(tmp_path)
    samples_dir = tmp_path / "samples"
    model_dir = tmp_path / "models"
    _write_sample(
        samples_dir,
        category="asked_to_speak",
        name="accepted",
        transcript="John, что по статусу?",
        trigger=True,
        question=True,
        will_answer=True,
        decision="accepted",
    )
    _write_sample(
        samples_dir,
        category="speech",
        name="rejected",
        transcript="как John вчера говорил, надо проверить логи",
        trigger=True,
        question=False,
        will_answer=False,
        decision="rejected",
    )
    runner = CliRunner()
    trained = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "trigger-classifier",
            "train",
            "--profile",
            "personal",
            "--samples-dir",
            str(samples_dir),
            "--model-dir",
            str(model_dir),
            "--min-total",
            "2",
            "--min-per-class",
            "1",
        ],
    )

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
            "--classifier-shadow",
            "--model-dir",
            str(model_dir),
        ],
    )

    assert trained.exit_code == 0
    assert result.exit_code == 0
    assert "classifier: " in result.output
    assert "model=" in result.output


def test_auto_preflight_reports_ready_with_nonblocking_cache_warning(tmp_path, monkeypatch):
    from datetime import date
    import yaml

    config_path = _write_config(tmp_path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["responses"]["cache_dir"] = str(tmp_path / "empty_responses")
    config_path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    cache_dir = tmp_path / ".saymo" / "audio_cache"
    cache_dir.mkdir(parents=True)
    cached = cache_dir / f"{date.today().isoformat()}.wav"
    cached.write_bytes(b"wav")

    monkeypatch.setattr("saymo.commands._get_cached_audio_path", lambda team=False: cached)
    monkeypatch.setattr(
        "saymo.audio.devices.find_device",
        lambda name, kind=None: SimpleNamespace(index=1) if name else None,
    )

    class Provider:
        name = "Glip"

        def check_ready(self):
            return SimpleNamespace(meeting_found=True, tab_info=(1, 2))

    monkeypatch.setattr("saymo.providers.factory.get_provider", lambda name: Provider())

    result = CliRunner().invoke(
        main,
        [
            "--config",
            str(config_path),
            "auto-preflight",
            "--profile",
            "personal",
        ],
    )

    assert result.exit_code == 0
    assert "ok: prepared standup:" in result.output
    assert "ok: provider tab:" in result.output
    assert "warn: response cache:" in result.output
    assert "preflight: ready" in result.output
