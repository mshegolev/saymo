"""Tests for deciding whether a trigger transcript is addressed to the user."""

from saymo.analysis.addressing import (
    AddressingDecision,
    classify_addressing,
    should_answer_decision,
)


def test_direct_question_after_name_is_addressed():
    decision = classify_addressing(
        "Миша, что думаешь по этой задаче?",
        trigger_phrases=["Миша"],
    )

    assert isinstance(decision, AddressingDecision)
    assert decision.label == "addressed_to_me"
    assert decision.is_question is True
    assert decision.trigger == "Миша"
    assert should_answer_decision(decision) is True


def test_narrated_mention_is_not_addressed():
    decision = classify_addressing(
        "как Миша вчера говорил, надо сначала проверить логи",
        trigger_phrases=["Миша"],
    )

    assert decision.label == "mentioned_not_addressed"
    assert decision.is_question is False
    assert should_answer_decision(decision) is False


def test_third_person_question_about_trigger_is_not_addressed():
    decision = classify_addressing(
        "что Миша думает по этой задаче?",
        trigger_phrases=["Миша"],
    )

    assert decision.label == "mentioned_not_addressed"
    assert decision.is_question is True
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
    decision = classify_addressing("", trigger_phrases=["Миша"])

    assert decision.label == "ignore"
    assert decision.confidence == 0.0
    assert should_answer_decision(decision) is False
