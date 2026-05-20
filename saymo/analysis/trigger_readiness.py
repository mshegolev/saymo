"""Readiness, evaluation, and live-assist helpers for trigger classifiers.

This module is intentionally dependency-free. CLI commands can use these
helpers to report whether local labeled samples are strong enough for live
classifier assist while keeping deterministic trigger/addressing checks as the
hard safety boundary.
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from saymo.analysis.trigger_classifier import (
    DECISION_LABELS,
    InsufficientTrainingData,
    TriggerClassifierPrediction,
    TriggerClassifierSample,
    classifier_model_path,
    load_model,
    normalize_decision_label,
    predict_live_assist,
    train_classifier,
)


@dataclass(frozen=True)
class TriggerReadinessThresholds:
    min_labeled: int = 10
    min_accepted: int = 3
    min_rejected: int = 3
    min_categories: int = 2
    required_categories: tuple[str, ...] = ("asked_to_speak", "mentioned_me")


@dataclass(frozen=True)
class TriggerReadinessReport:
    total_samples: int
    total_labeled: int
    accepted: int
    rejected: int
    unlabeled: int
    category_counts: dict[str, int]
    category_coverage: int
    has_asked_to_speak: bool
    has_mentioned_me: bool
    accepted_ratio: float
    rejected_ratio: float
    thresholds: TriggerReadinessThresholds
    passed: bool
    missing_items: list[str]


@dataclass(frozen=True)
class TriggerHoldoutSplit:
    train_samples: tuple[TriggerClassifierSample, ...]
    holdout_samples: tuple[TriggerClassifierSample, ...]
    labeled_count: int


@dataclass(frozen=True)
class TriggerHoldoutEvaluation:
    profile: str
    train_count: int
    holdout_count: int
    labeled_count: int
    confusion_matrix: dict[str, dict[str, int]]
    precision: dict[str, float | None]
    recall: dict[str, float | None]
    accuracy: float | None


@dataclass(frozen=True)
class TriggerLiveAssistArtifact:
    profile: str
    enabled: bool
    updated_at: str
    readiness: dict[str, Any]
    model_path: str = ""
    model_sha256: str = ""
    model_trained_at: str = ""
    model_label_counts: dict[str, int] = field(default_factory=dict)
    version: int = 1


@dataclass(frozen=True)
class TriggerLiveAssistStatus:
    path: Path
    exists: bool
    enabled: bool
    artifact: TriggerLiveAssistArtifact | None
    model_valid: bool = False
    reason: str = ""


@dataclass(frozen=True)
class TriggerLiveAssistModelSnapshot:
    path: Path
    sha256: str
    trained_at: str
    label_counts: dict[str, int]


@dataclass(frozen=True)
class TriggerLiveAssistDecision:
    deterministic_will_answer: bool
    deterministic_action: str
    classifier_label: str
    classifier_confidence: float | None
    final_action: str
    reason: str


class LiveAssistReadinessError(ValueError):
    """Raised when live assist is enabled before readiness gates pass."""


def readiness_metrics(
    samples: Iterable[Any],
    thresholds: TriggerReadinessThresholds | None = None,
) -> TriggerReadinessReport:
    """Compute readiness metrics from trigger sample-like objects.

    Samples may be ``TriggerClassifierSample`` instances or records with the
    fields used by ``TriggerSampleRecord`` in ``saymo.commands.tests``.
    Category coverage is counted only for accepted/rejected labeled samples,
    because only labeled examples train the classifier.
    """
    thresholds = thresholds or TriggerReadinessThresholds()
    total_samples = 0
    accepted = 0
    rejected = 0
    category_counts: dict[str, int] = {}

    for sample in samples:
        total_samples += 1
        label = _sample_decision(sample)
        if label == "accepted":
            accepted += 1
        elif label == "rejected":
            rejected += 1
        else:
            continue

        category = _sample_category(sample)
        category_counts[category] = category_counts.get(category, 0) + 1

    total_labeled = accepted + rejected
    unlabeled = total_samples - total_labeled
    category_coverage = len(category_counts)
    missing_items: list[str] = []

    if total_labeled < thresholds.min_labeled:
        missing_items.append(f"labeled>={thresholds.min_labeled}")
    if accepted < thresholds.min_accepted:
        missing_items.append(f"accepted>={thresholds.min_accepted}")
    if rejected < thresholds.min_rejected:
        missing_items.append(f"rejected>={thresholds.min_rejected}")
    if category_coverage < thresholds.min_categories:
        missing_items.append(f"categories>={thresholds.min_categories}")

    for category in thresholds.required_categories:
        if category_counts.get(category, 0) < 1:
            missing_items.append(f"category:{category}")

    return TriggerReadinessReport(
        total_samples=total_samples,
        total_labeled=total_labeled,
        accepted=accepted,
        rejected=rejected,
        unlabeled=unlabeled,
        category_counts=dict(sorted(category_counts.items())),
        category_coverage=category_coverage,
        has_asked_to_speak=category_counts.get("asked_to_speak", 0) > 0,
        has_mentioned_me=category_counts.get("mentioned_me", 0) > 0,
        accepted_ratio=_ratio(accepted, total_labeled),
        rejected_ratio=_ratio(rejected, total_labeled),
        thresholds=thresholds,
        passed=not missing_items,
        missing_items=missing_items,
    )


def split_labeled_holdout(
    samples: Iterable[Any],
    *,
    holdout_fraction: float = 0.25,
    min_holdout_per_class: int = 1,
    min_train_per_class: int = 1,
) -> TriggerHoldoutSplit:
    """Split labeled samples into deterministic train and holdout sets."""
    if not 0 < holdout_fraction < 1:
        raise ValueError("holdout_fraction must be between 0 and 1")
    if min_holdout_per_class < 1:
        raise ValueError("min_holdout_per_class must be at least 1")
    if min_train_per_class < 1:
        raise ValueError("min_train_per_class must be at least 1")

    grouped: dict[str, list[tuple[tuple[str, ...], TriggerClassifierSample]]] = {
        label: []
        for label in DECISION_LABELS
    }
    for sample in samples:
        classifier_sample = _to_classifier_sample(sample)
        label = normalize_decision_label(classifier_sample.decision)
        if label in DECISION_LABELS:
            grouped[label].append(
                (_source_sample_sort_key(sample, classifier_sample), classifier_sample)
            )

    train: list[TriggerClassifierSample] = []
    holdout: list[TriggerClassifierSample] = []
    for label in DECISION_LABELS:
        label_samples = [sample for _, sample in sorted(grouped[label], key=lambda item: item[0])]
        if len(label_samples) < min_train_per_class + min_holdout_per_class:
            raise InsufficientTrainingData(
                "Need enough labeled samples for train and holdout splits; "
                f"{label} has {len(label_samples)}"
            )

        requested_holdout = max(
            min_holdout_per_class,
            round(len(label_samples) * holdout_fraction),
        )
        holdout_count = min(requested_holdout, len(label_samples) - min_train_per_class)
        if holdout_count < min_holdout_per_class:
            raise InsufficientTrainingData(
                "Need enough labeled samples for train and holdout splits; "
                f"{label} has {len(label_samples)}"
            )

        split_at = len(label_samples) - holdout_count
        train.extend(label_samples[:split_at])
        holdout.extend(label_samples[split_at:])

    return TriggerHoldoutSplit(
        train_samples=tuple(sorted(train, key=_sample_sort_key)),
        holdout_samples=tuple(sorted(holdout, key=_sample_sort_key)),
        labeled_count=sum(len(label_samples) for label_samples in grouped.values()),
    )


def evaluate_holdout(
    samples: Iterable[Any],
    *,
    profile: str,
    holdout_fraction: float = 0.25,
    min_total: int = 4,
    min_per_class: int = 1,
    min_holdout_per_class: int = 1,
) -> TriggerHoldoutEvaluation:
    """Train on a deterministic split and evaluate accepted/rejected holdout."""
    split = split_labeled_holdout(
        samples,
        holdout_fraction=holdout_fraction,
        min_holdout_per_class=min_holdout_per_class,
        min_train_per_class=min_per_class,
    )
    model = train_classifier(
        list(split.train_samples),
        profile=profile,
        min_total=min_total,
        min_per_class=min_per_class,
    )

    confusion = _empty_confusion_matrix()
    for sample in split.holdout_samples:
        actual = normalize_decision_label(sample.decision)
        prediction = predict_live_assist(model, sample)
        predicted = normalize_decision_label(prediction.label)
        if actual in DECISION_LABELS and predicted in DECISION_LABELS:
            confusion[actual][predicted] += 1

    precision = {
        label: _label_precision(confusion, label)
        for label in DECISION_LABELS
    }
    recall = {
        label: _label_recall(confusion, label)
        for label in DECISION_LABELS
    }
    correct = sum(confusion[label][label] for label in DECISION_LABELS)
    holdout_count = sum(
        confusion[actual][predicted]
        for actual in DECISION_LABELS
        for predicted in DECISION_LABELS
    )

    return TriggerHoldoutEvaluation(
        profile=profile,
        train_count=len(split.train_samples),
        holdout_count=holdout_count,
        labeled_count=split.labeled_count,
        confusion_matrix=confusion,
        precision=precision,
        recall=recall,
        accuracy=_ratio_or_none(correct, holdout_count),
    )


def live_assist_artifact_path(profile: str, model_dir: str | Path | None = None) -> Path:
    """Return the per-profile live-assist artifact path under the model dir."""
    model_path = classifier_model_path(profile, model_dir)
    return model_path.with_name(f"{model_path.stem}.live_assist.json")


def live_assist_status(
    profile: str,
    model_dir: str | Path | None = None,
) -> TriggerLiveAssistStatus:
    """Return the saved live-assist state for a profile, if present."""
    path = live_assist_artifact_path(profile, model_dir)
    if not path.exists():
        return TriggerLiveAssistStatus(
            path=path,
            exists=False,
            enabled=False,
            artifact=None,
            reason="artifact_missing",
        )
    artifact = load_live_assist_artifact(path)
    model_valid, reason = _live_assist_model_valid(artifact, model_dir)
    return TriggerLiveAssistStatus(
        path=path,
        exists=True,
        enabled=artifact.enabled and model_valid,
        artifact=artifact,
        model_valid=model_valid,
        reason=reason,
    )


def load_live_assist_artifact(
    path_or_profile: str | Path,
    model_dir: str | Path | None = None,
) -> TriggerLiveAssistArtifact:
    """Load a live-assist artifact by path or by profile plus model dir."""
    path = _resolve_artifact_path(path_or_profile, model_dir)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Live-assist artifact is not a JSON object: {path}")
    readiness = data.get("readiness")
    return TriggerLiveAssistArtifact(
        profile=str(data.get("profile") or ""),
        enabled=bool(data.get("enabled")),
        updated_at=str(data.get("updated_at") or ""),
        readiness=dict(readiness) if isinstance(readiness, Mapping) else {},
        model_path=str(data.get("model_path") or ""),
        model_sha256=str(data.get("model_sha256") or ""),
        model_trained_at=str(data.get("model_trained_at") or ""),
        model_label_counts={
            str(label): int(count)
            for label, count in (data.get("model_label_counts") or {}).items()
        },
        version=int(data.get("version") or 1),
    )


def save_live_assist_artifact(
    artifact: TriggerLiveAssistArtifact,
    path: str | Path | None = None,
    *,
    model_dir: str | Path | None = None,
) -> Path:
    """Persist a live-assist artifact as local JSON."""
    out_path = Path(path).expanduser() if path else live_assist_artifact_path(
        artifact.profile,
        model_dir,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(asdict(artifact), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return out_path


def enable_live_assist(
    profile: str,
    model_dir: str | Path | TriggerReadinessReport | Mapping[str, Any] | None = None,
    readiness: TriggerReadinessReport | Mapping[str, Any] | None = None,
) -> TriggerLiveAssistArtifact:
    """Enable live assist for a profile after readiness has passed."""
    if readiness is None:
        readiness = model_dir
        model_dir = None
    if readiness is None:
        raise ValueError("readiness is required")
    if not _readiness_passed(readiness):
        raise LiveAssistReadinessError("Classifier readiness has not passed")
    snapshot = live_assist_model_snapshot(
        profile,
        model_dir if _is_path_like(model_dir) else None,
    )
    expected_counts = _readiness_label_counts(readiness)
    if expected_counts and snapshot.label_counts != expected_counts:
        raise ValueError(
            "Classifier model label counts do not match readiness labels; "
            "retrain before enabling live assist"
        )

    artifact = TriggerLiveAssistArtifact(
        profile=profile,
        enabled=True,
        updated_at=_utc_now(),
        readiness=_readiness_snapshot(readiness),
        model_path=str(snapshot.path),
        model_sha256=snapshot.sha256,
        model_trained_at=snapshot.trained_at,
        model_label_counts=snapshot.label_counts,
    )
    save_live_assist_artifact(
        artifact,
        live_assist_artifact_path(profile, model_dir if _is_path_like(model_dir) else None),
    )
    return artifact


def live_assist_model_snapshot(
    profile: str,
    model_dir: str | Path | None = None,
) -> TriggerLiveAssistModelSnapshot:
    """Return identifying metadata for the current trained classifier model."""
    path = classifier_model_path(profile, model_dir)
    if not path.exists():
        raise FileNotFoundError(f"Classifier artifact not found: {path}")
    data = path.read_bytes()
    model = load_model(path)
    if model.profile and model.profile != profile:
        raise ValueError(
            f"Classifier profile mismatch: artifact={model.profile!r} expected={profile!r}"
        )
    return TriggerLiveAssistModelSnapshot(
        path=path,
        sha256=hashlib.sha256(data).hexdigest(),
        trained_at=model.trained_at,
        label_counts=dict(model.label_counts),
    )


def disable_live_assist(
    profile: str,
    model_dir: str | Path | None = None,
) -> TriggerLiveAssistArtifact:
    """Disable live assist while preserving the last readiness snapshot."""
    path = live_assist_artifact_path(profile, model_dir)
    readiness: dict[str, Any] = {}
    if path.exists():
        readiness = load_live_assist_artifact(path).readiness

    artifact = TriggerLiveAssistArtifact(
        profile=profile,
        enabled=False,
        updated_at=_utc_now(),
        readiness=readiness,
    )
    save_live_assist_artifact(artifact, path)
    return artifact


def apply_live_assist_decision(
    deterministic_will_answer: bool,
    classifier_prediction: TriggerClassifierPrediction | str,
    *,
    confidence: float | None = None,
) -> TriggerLiveAssistDecision:
    """Combine deterministic and classifier decisions without bypassing skip."""
    label, resolved_confidence = _prediction_label_and_confidence(
        classifier_prediction,
        confidence,
    )
    deterministic_action = "answer" if deterministic_will_answer else "skip"
    if not deterministic_will_answer:
        return TriggerLiveAssistDecision(
            deterministic_will_answer=False,
            deterministic_action=deterministic_action,
            classifier_label=label,
            classifier_confidence=resolved_confidence,
            final_action="skip",
            reason="deterministic_skip",
        )

    if label == "accepted":
        return TriggerLiveAssistDecision(
            deterministic_will_answer=True,
            deterministic_action=deterministic_action,
            classifier_label=label,
            classifier_confidence=resolved_confidence,
            final_action="answer",
            reason="classifier_confirmed",
        )

    reason = "classifier_downgrade" if label == "rejected" else "classifier_unlabeled"
    return TriggerLiveAssistDecision(
        deterministic_will_answer=True,
        deterministic_action=deterministic_action,
        classifier_label=label,
        classifier_confidence=resolved_confidence,
        final_action="skip",
        reason=reason,
    )


def _sample_decision(sample: Any) -> str:
    if hasattr(sample, "decision"):
        return normalize_decision_label(getattr(sample, "decision"))
    return normalize_decision_label(getattr(sample, "answer_decision", None))


def _sample_category(sample: Any) -> str:
    return str(getattr(sample, "category", "") or "unknown")


def _to_classifier_sample(sample: Any) -> TriggerClassifierSample:
    return TriggerClassifierSample(
        transcript=str(getattr(sample, "transcript", "") or ""),
        speaker=str(getattr(sample, "speaker", "") or "unknown"),
        category=_sample_category(sample),
        trigger=_bool_field(sample, "trigger"),
        question=_bool_field(sample, "question"),
        will_answer=_bool_field(sample, "will_answer"),
        addressing=str(getattr(sample, "addressing", "") or ""),
        decision=_sample_decision(sample),
    )


def _bool_field(sample: Any, field: str) -> bool:
    value = getattr(sample, field, False)
    if isinstance(value, str):
        return value.strip().casefold() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _sample_sort_key(sample: TriggerClassifierSample) -> tuple[str, ...]:
    return (
        normalize_decision_label(sample.decision),
        sample.category,
        sample.speaker,
        "1" if sample.trigger else "0",
        "1" if sample.question else "0",
        "1" if sample.will_answer else "0",
        sample.addressing,
        " ".join(sample.transcript.split()).casefold(),
    )


def _source_sample_sort_key(
    source: Any,
    sample: TriggerClassifierSample,
) -> tuple[str, ...]:
    return (
        str(getattr(source, "path", "") or ""),
        str(getattr(source, "created_at", "") or ""),
        str(getattr(source, "session_id", "") or ""),
        str(getattr(source, "session_sequence", "") or ""),
        *_sample_sort_key(sample),
    )


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _ratio_or_none(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _empty_confusion_matrix() -> dict[str, dict[str, int]]:
    return {
        actual: {predicted: 0 for predicted in DECISION_LABELS}
        for actual in DECISION_LABELS
    }


def _label_precision(
    confusion: dict[str, dict[str, int]],
    label: str,
) -> float | None:
    true_positive = confusion[label][label]
    predicted_positive = sum(confusion[actual][label] for actual in DECISION_LABELS)
    return _ratio_or_none(true_positive, predicted_positive)


def _label_recall(
    confusion: dict[str, dict[str, int]],
    label: str,
) -> float | None:
    true_positive = confusion[label][label]
    actual_positive = sum(confusion[label][predicted] for predicted in DECISION_LABELS)
    return _ratio_or_none(true_positive, actual_positive)


def _resolve_artifact_path(
    path_or_profile: str | Path,
    model_dir: str | Path | None,
) -> Path:
    if model_dir is not None:
        return live_assist_artifact_path(str(path_or_profile), model_dir)
    path = Path(path_or_profile).expanduser()
    if path.suffix:
        return path
    return live_assist_artifact_path(str(path_or_profile))


def _readiness_passed(readiness: TriggerReadinessReport | Mapping[str, Any]) -> bool:
    if isinstance(readiness, Mapping):
        return bool(readiness.get("passed"))
    return bool(getattr(readiness, "passed", False))


def _readiness_snapshot(
    readiness: TriggerReadinessReport | Mapping[str, Any],
) -> dict[str, Any]:
    if isinstance(readiness, Mapping):
        return _json_ready(dict(readiness))
    if is_dataclass(readiness):
        return _json_ready(asdict(readiness))
    return {"passed": bool(getattr(readiness, "passed", False))}


def _readiness_label_counts(
    readiness: TriggerReadinessReport | Mapping[str, Any],
) -> dict[str, int]:
    if isinstance(readiness, Mapping):
        accepted = readiness.get("accepted")
        rejected = readiness.get("rejected")
    else:
        accepted = getattr(readiness, "accepted", None)
        rejected = getattr(readiness, "rejected", None)
    if accepted is None or rejected is None:
        return {}
    return {"accepted": int(accepted), "rejected": int(rejected)}


def _is_path_like(value: Any) -> bool:
    return isinstance(value, (str, Path))


def _prediction_label_and_confidence(
    classifier_prediction: TriggerClassifierPrediction | str,
    confidence: float | None,
) -> tuple[str, float | None]:
    if isinstance(classifier_prediction, str):
        return normalize_decision_label(classifier_prediction), confidence
    label = normalize_decision_label(getattr(classifier_prediction, "label", ""))
    resolved_confidence = (
        confidence
        if confidence is not None
        else getattr(classifier_prediction, "confidence", None)
    )
    return label, resolved_confidence


def _live_assist_model_valid(
    artifact: TriggerLiveAssistArtifact,
    model_dir: str | Path | None,
) -> tuple[bool, str]:
    if not artifact.enabled:
        return False, "disabled"
    if not artifact.model_sha256:
        return False, "model_fingerprint_missing"
    try:
        snapshot = live_assist_model_snapshot(artifact.profile, model_dir)
    except FileNotFoundError:
        return False, "model_missing"
    except ValueError as e:
        return False, str(e)
    if snapshot.sha256 != artifact.model_sha256:
        return False, "model_mismatch"
    return True, "model_ok"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_ready(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, ensure_ascii=False))
