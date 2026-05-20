import pytest

from saymo.analysis.trigger_classifier import (
    InsufficientTrainingData,
    TriggerClassifierSample,
    load_model,
    predict,
    predict_live_assist,
    save_model,
    train_classifier,
)


def test_trigger_classifier_requires_minimum_labeled_samples():
    samples = [
        TriggerClassifierSample(
            transcript="John, что по статусу?",
            speaker="other",
            category="asked_to_speak",
            trigger=True,
            question=True,
            will_answer=True,
            addressing="addressed_to_me",
            decision="accepted",
        )
    ]

    with pytest.raises(InsufficientTrainingData) as exc:
        train_classifier(samples, profile="personal", min_total=2, min_per_class=1)

    assert "Need at least 2 labeled samples" in str(exc.value)


def test_trigger_classifier_predicts_and_persists(tmp_path):
    samples = [
        TriggerClassifierSample(
            transcript="John, что по статусу?",
            speaker="other",
            category="asked_to_speak",
            trigger=True,
            question=True,
            will_answer=True,
            addressing="addressed_to_me",
            decision="accepted",
        ),
        TriggerClassifierSample(
            transcript="как John вчера говорил, надо проверить логи",
            speaker="other",
            category="speech",
            trigger=True,
            question=False,
            will_answer=False,
            addressing="mentioned_not_addressed",
            decision="rejected",
        ),
    ]
    model = train_classifier(samples, profile="personal", min_total=2, min_per_class=1)

    prediction = predict(
        model,
        TriggerClassifierSample(
            transcript="John, что по статусу?",
            speaker="other",
            category="asked_to_speak",
            trigger=True,
            question=True,
            will_answer=True,
            addressing="addressed_to_me",
            decision="unlabeled",
        ),
    )

    assert prediction.label == "accepted"
    assert prediction.confidence >= 0.5
    model_path = tmp_path / "personal.json"
    save_model(model, model_path)
    loaded = load_model(model_path)
    assert loaded.profile == "personal"
    assert loaded.label_counts == {"accepted": 1, "rejected": 1}


def test_live_assist_prediction_ignores_deterministic_gate_features():
    samples = [
        TriggerClassifierSample(
            transcript="John, что по статусу?",
            speaker="other",
            category="asked_to_speak",
            trigger=True,
            question=True,
            will_answer=True,
            addressing="addressed_to_me",
            decision="accepted",
        ),
        TriggerClassifierSample(
            transcript="как John вчера говорил, надо проверить логи",
            speaker="other",
            category="mentioned_me",
            trigger=True,
            question=False,
            will_answer=False,
            addressing="mentioned_not_addressed",
            decision="rejected",
        ),
    ]
    model = train_classifier(samples, profile="personal", min_total=2, min_per_class=1)

    deterministic_answer = TriggerClassifierSample(
        transcript="John, что по статусу?",
        speaker="other",
        category="asked_to_speak",
        trigger=True,
        question=True,
        will_answer=True,
        addressing="addressed_to_me",
        decision="unlabeled",
    )
    deterministic_skip = TriggerClassifierSample(
        transcript="John, что по статусу?",
        speaker="other",
        category="speech",
        trigger=False,
        question=False,
        will_answer=False,
        addressing="ignore",
        decision="unlabeled",
    )

    assert predict_live_assist(model, deterministic_answer) == predict_live_assist(
        model,
        deterministic_skip,
    )
