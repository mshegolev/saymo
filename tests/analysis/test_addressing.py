"""Tests for deciding whether a trigger transcript is addressed to the user."""

from saymo.analysis.addressing import (
    AddressingDecision,
    classify_addressing,
    should_answer_decision,
)


def test_direct_question_after_name_is_addressed():
    decision = classify_addressing(
        "John, что думаешь по этой задаче?",
        trigger_phrases=["John"],
    )

    assert isinstance(decision, AddressingDecision)
    assert decision.label == "addressed_to_me"
    assert decision.is_question is True
    assert decision.trigger == "John"
    assert should_answer_decision(decision) is True


def test_plain_non_question_name_mention_is_not_handoff():
    decision = classify_addressing(
        "I helped John with the review yesterday",
        trigger_phrases=["John"],
    )

    assert decision.label == "mentioned_not_addressed"
    assert decision.reason == "plain trigger mention without handoff evidence"
    assert should_answer_decision(decision) is False


def test_full_name_statement_is_not_handoff():
    decision = classify_addressing(
        "John Doe prepared the first draft",
        trigger_phrases=["John"],
    )

    assert decision.label == "mentioned_not_addressed"
    assert decision.reason == "full-name or surname mention"
    assert should_answer_decision(decision) is False


def test_bare_name_call_is_addressed_for_confirmation():
    decision = classify_addressing("John", trigger_phrases=["John"])

    assert decision.label == "addressed_to_me"
    assert decision.reason == "bare trigger call"
    assert should_answer_decision(decision) is True


def test_configured_handoff_pattern_is_addressed():
    decision = classify_addressing(
        "пусть John ответит по этому вопросу",
        trigger_phrases=["John"],
        handoff_patterns=[r"\bпусть\s+{trigger}\s+ответит\b"],
    )

    assert decision.label == "addressed_to_me"
    assert decision.reason == "configured handoff pattern"
    assert should_answer_decision(decision) is True


def test_configured_mention_only_pattern_skips():
    decision = classify_addressing(
        "эскалировали John как владельцу задачи",
        trigger_phrases=["John"],
        mention_only_patterns=[r"\bэскалировали\s+{trigger}\b"],
    )

    assert decision.label == "mentioned_not_addressed"
    assert decision.reason == "configured mention-only pattern"
    assert should_answer_decision(decision) is False


def test_narrated_mention_is_not_addressed():
    decision = classify_addressing(
        "как John вчера говорил, надо сначала проверить логи",
        trigger_phrases=["John"],
    )

    assert decision.label == "mentioned_not_addressed"
    assert decision.is_question is False
    assert should_answer_decision(decision) is False


def test_name_mention_in_collaboration_phrase_is_not_handoff():
    decision = classify_addressing(
        "Что еще с валидационными рулами, там есть вопросы, взаимодействуем с Мишей.",
        trigger_phrases=["Миша", "Мише"],
    )

    assert decision.label == "mentioned_not_addressed"
    assert decision.is_question is True
    assert decision.reason == "collaboration mention pattern"
    assert should_answer_decision(decision) is False


def test_floor_handoff_phrase_is_addressed():
    decision = classify_addressing(
        "Спасибо. Словом, Миша.",
        trigger_phrases=["Миша", "Мише"],
    )

    assert decision.label == "addressed_to_me"
    assert decision.is_question is False
    assert decision.reason == "floor handoff phrase"
    assert should_answer_decision(decision) is True


def test_third_person_question_about_trigger_is_not_addressed():
    decision = classify_addressing(
        "что John думает по этой задаче?",
        trigger_phrases=["John"],
    )

    assert decision.label == "mentioned_not_addressed"
    assert decision.is_question is True
    assert should_answer_decision(decision) is False


def test_third_person_statement_about_trigger_is_not_addressed():
    decision = classify_addressing(
        "John думает, что надо сначала проверить логи",
        trigger_phrases=["John"],
    )

    assert decision.label == "mentioned_not_addressed"
    assert decision.is_question is False
    assert should_answer_decision(decision) is False


def test_team_trigger_question_is_allowed():
    decision = classify_addressing(
        "что по вашей команде, есть блокеры?",
        trigger_phrases=["вашей команде"],
    )

    assert decision.label == "generic_team_question"
    assert decision.is_question is True
    assert should_answer_decision(decision) is True


def test_empty_transcript_is_ignored():
    decision = classify_addressing("", trigger_phrases=["John"])

    assert decision.label == "ignore"
    assert decision.confidence == 0.0
    assert should_answer_decision(decision) is False
