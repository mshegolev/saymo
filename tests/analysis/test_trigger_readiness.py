from dataclasses import dataclass

import pytest

from saymo.analysis.trigger_classifier import (
    TriggerClassifierSample,
    classifier_model_path,
    save_model,
    train_classifier,
)
from saymo.analysis.trigger_readiness import (
    LiveAssistReadinessError,
    TriggerReadinessThresholds,
    apply_live_assist_decision,
    disable_live_assist,
    enable_live_assist,
    evaluate_holdout,
    live_assist_artifact_path,
    live_assist_status,
    load_live_assist_artifact,
    readiness_metrics,
)


@dataclass(frozen=True)
class SampleRecord:
    transcript: str
    category: str
    answer_decision: str
    will_answer: bool
    addressing: str
    speaker: str = "other"
    trigger: bool = True
    question: bool = True


def test_readiness_metrics_report_ready_counts_and_coverage():
    thresholds = TriggerReadinessThresholds(
        min_labeled=4,
        min_accepted=2,
        min_rejected=2,
        min_categories=2,
    )
    samples = [
        _record("John, what is the release status?", "asked_to_speak", "accepted", True),
        _record("John, can you take the deploy?", "asked_to_speak", "accepted", True),
        _record(
            "I mentioned John in the handoff notes",
            "mentioned_me",
            "rejected",
            False,
            addressing="mentioned_not_addressed",
        ),
        _record("The deploy finished yesterday", "speech", "rejected", False),
        _record("Unreviewed sample", "speech", "unlabeled", False),
    ]

    report = readiness_metrics(samples, thresholds)

    assert report.passed is True
    assert report.total_samples == 5
    assert report.total_labeled == 4
    assert report.accepted == 2
    assert report.rejected == 2
    assert report.unlabeled == 1
    assert report.category_counts == {
        "asked_to_speak": 2,
        "mentioned_me": 1,
        "speech": 1,
    }
    assert report.category_coverage == 3
    assert report.has_asked_to_speak is True
    assert report.has_mentioned_me is True
    assert report.accepted_ratio == pytest.approx(0.5)
    assert report.rejected_ratio == pytest.approx(0.5)
    assert report.missing_items == []


def test_readiness_metrics_report_missing_thresholds_and_coverage():
    thresholds = TriggerReadinessThresholds(
        min_labeled=4,
        min_accepted=2,
        min_rejected=2,
        min_categories=2,
    )
    samples = [
        _record("John, what is the release status?", "asked_to_speak", "accepted", True),
        _record("The deploy finished yesterday", "speech", "unlabeled", False),
    ]

    report = readiness_metrics(samples, thresholds)

    assert report.passed is False
    assert report.total_labeled == 1
    assert report.accepted == 1
    assert report.rejected == 0
    assert report.category_counts == {"asked_to_speak": 1}
    assert report.missing_items == [
        "labeled>=4",
        "accepted>=2",
        "rejected>=2",
        "categories>=2",
        "category:mentioned_me",
    ]


def test_holdout_evaluation_is_deterministic_and_reports_metrics():
    samples = [
        _classifier("please answer release status", "asked_to_speak", "accepted", True),
        _classifier("please answer deploy owner", "asked_to_speak", "accepted", True),
        _classifier("please answer incidents", "asked_to_speak", "accepted", True),
        _classifier(
            "just mentioned you in notes",
            "mentioned_me",
            "rejected",
            False,
            addressing="mentioned_not_addressed",
        ),
        _classifier(
            "mentioned you during planning",
            "mentioned_me",
            "rejected",
            False,
            addressing="mentioned_not_addressed",
        ),
        _classifier(
            "mentioned you in retro",
            "mentioned_me",
            "rejected",
            False,
            addressing="mentioned_not_addressed",
        ),
    ]

    first = evaluate_holdout(
        samples,
        profile="personal",
        holdout_fraction=1 / 3,
        min_total=4,
        min_per_class=1,
    )
    second = evaluate_holdout(
        reversed(samples),
        profile="personal",
        holdout_fraction=1 / 3,
        min_total=4,
        min_per_class=1,
    )

    assert first == second
    assert first.train_count == 4
    assert first.holdout_count == 2
    assert first.confusion_matrix == {
        "accepted": {"accepted": 1, "rejected": 0},
        "rejected": {"accepted": 0, "rejected": 1},
    }
    assert first.precision == {"accepted": 1.0, "rejected": 1.0}
    assert first.recall == {"accepted": 1.0, "rejected": 1.0}
    assert first.accuracy == 1.0


def test_live_assist_artifact_roundtrip_and_readiness_gate(tmp_path):
    not_ready = readiness_metrics(
        [_record("John, can you answer?", "asked_to_speak", "accepted", True)],
        TriggerReadinessThresholds(min_labeled=2, min_accepted=1, min_rejected=1),
    )

    with pytest.raises(LiveAssistReadinessError):
        enable_live_assist("personal", tmp_path, not_ready)

    ready = readiness_metrics(
        [
            _record("John, can you answer?", "asked_to_speak", "accepted", True),
            _record(
                "we mentioned John earlier",
                "mentioned_me",
                "rejected",
                False,
                addressing="mentioned_not_addressed",
            ),
        ],
        TriggerReadinessThresholds(min_labeled=2, min_accepted=1, min_rejected=1),
    )

    with pytest.raises(FileNotFoundError):
        enable_live_assist("personal", tmp_path, ready)

    model_path = _save_model(tmp_path)

    enabled = enable_live_assist("personal", tmp_path, ready)
    path = live_assist_artifact_path("personal", tmp_path)
    loaded = load_live_assist_artifact(path)
    status = live_assist_status("personal", tmp_path)

    assert path.exists()
    assert model_path.exists()
    assert loaded == enabled
    assert status.exists is True
    assert status.enabled is True
    assert status.model_valid is True
    assert status.reason == "model_ok"
    assert status.artifact == enabled
    assert enabled.readiness["passed"] is True
    assert enabled.readiness["total_labeled"] == 2
    assert enabled.model_sha256
    assert enabled.model_label_counts == {"accepted": 1, "rejected": 1}

    model_path.write_text(model_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    stale_status = live_assist_status("personal", tmp_path)
    assert stale_status.enabled is False
    assert stale_status.reason == "model_mismatch"

    disabled = disable_live_assist("personal", tmp_path)
    disabled_status = live_assist_status("personal", tmp_path)

    assert disabled.enabled is False
    assert disabled_status.enabled is False
    assert disabled_status.artifact == disabled


def test_live_assist_enable_refuses_model_label_count_mismatch(tmp_path):
    _save_model(tmp_path)
    readiness = readiness_metrics(
        [
            _record("John, can you answer?", "asked_to_speak", "accepted", True),
            _record("John, can you own this?", "asked_to_speak", "accepted", True),
            _record(
                "we mentioned John earlier",
                "mentioned_me",
                "rejected",
                False,
                addressing="mentioned_not_addressed",
            ),
        ],
        TriggerReadinessThresholds(
            min_labeled=3,
            min_accepted=2,
            min_rejected=1,
        ),
    )

    with pytest.raises(ValueError) as exc:
        enable_live_assist("personal", tmp_path, readiness)

    assert "retrain before enabling live assist" in str(exc.value)


def test_live_assist_decision_never_bypasses_deterministic_skip():
    bypass_attempt = apply_live_assist_decision(False, "accepted", confidence=0.99)
    downgrade = apply_live_assist_decision(True, "rejected", confidence=0.75)
    confirmed = apply_live_assist_decision(True, "accepted", confidence=0.8)

    assert bypass_attempt.deterministic_action == "skip"
    assert bypass_attempt.final_action == "skip"
    assert bypass_attempt.reason == "deterministic_skip"
    assert downgrade.deterministic_action == "answer"
    assert downgrade.final_action == "skip"
    assert downgrade.reason == "classifier_downgrade"
    assert confirmed.final_action == "answer"
    assert confirmed.reason == "classifier_confirmed"


def _record(
    transcript: str,
    category: str,
    decision: str,
    will_answer: bool,
    *,
    addressing: str = "addressed_to_me",
) -> SampleRecord:
    return SampleRecord(
        transcript=transcript,
        category=category,
        answer_decision=decision,
        will_answer=will_answer,
        addressing=addressing,
    )


def _classifier(
    transcript: str,
    category: str,
    decision: str,
    will_answer: bool,
    *,
    addressing: str = "addressed_to_me",
) -> TriggerClassifierSample:
    return TriggerClassifierSample(
        transcript=transcript,
        speaker="other",
        category=category,
        trigger=True,
        question=will_answer,
        will_answer=will_answer,
        addressing=addressing,
        decision=decision,
    )


def _save_model(model_dir):
    samples = [
        _classifier("John can you answer?", "asked_to_speak", "accepted", True),
        _classifier(
            "we mentioned John earlier",
            "mentioned_me",
            "rejected",
            False,
            addressing="mentioned_not_addressed",
        ),
    ]
    model = train_classifier(samples, profile="personal", min_total=2, min_per_class=1)
    return save_model(model, classifier_model_path("personal", model_dir))
