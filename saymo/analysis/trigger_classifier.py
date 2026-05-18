"""Local sample-based trigger classifier.

The classifier is intentionally small and dependency-free. It is trained from
local trigger-sample metadata and runs in shadow mode only; deterministic
trigger/addressing gates remain the source of live-call decisions.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


DECISION_LABELS = ("accepted", "rejected")
ALL_DECISION_LABELS = (*DECISION_LABELS, "unlabeled")


class InsufficientTrainingData(ValueError):
    """Raised when accepted/rejected labels do not satisfy training thresholds."""


@dataclass(frozen=True)
class TriggerClassifierSample:
    transcript: str
    speaker: str = "unknown"
    category: str = "speech"
    trigger: bool = False
    question: bool = False
    will_answer: bool = False
    addressing: str = ""
    decision: str = "unlabeled"


@dataclass(frozen=True)
class TriggerClassifierModel:
    profile: str
    trained_at: str
    labels: list[str]
    label_counts: dict[str, int]
    feature_counts: dict[str, dict[str, int]]
    feature_totals: dict[str, int]
    vocabulary: list[str]
    min_total: int
    min_per_class: int
    version: int = 1


@dataclass(frozen=True)
class TriggerClassifierPrediction:
    label: str
    confidence: float
    scores: dict[str, float]


def normalize_decision_label(value) -> str:
    """Normalize a sample answer label to accepted/rejected/unlabeled."""
    label = str(value or "").strip().lower()
    if label in ALL_DECISION_LABELS:
        return label
    return "unlabeled"


def classifier_model_path(profile: str, model_dir: str | Path | None = None) -> Path:
    """Return the local JSON artifact path for a profile classifier."""
    base_dir = (
        Path(model_dir).expanduser()
        if model_dir
        else Path.home() / ".saymo" / "models" / "trigger_classifier"
    )
    return base_dir / f"{_safe_profile_name(profile)}.json"


def extract_features(sample: TriggerClassifierSample) -> list[str]:
    """Extract sparse text + metadata features for the local classifier."""
    features: list[str] = []
    text = " ".join((sample.transcript or "").split()).casefold()
    for token in re.findall(r"[\w']+", text, flags=re.UNICODE):
        features.append(f"tok={token}")

    features.extend(
        [
            f"speaker={_clean_feature_value(sample.speaker or 'unknown')}",
            f"category={_clean_feature_value(sample.category or 'speech')}",
            f"addressing={_clean_feature_value(sample.addressing or 'unknown')}",
            f"trigger={'yes' if sample.trigger else 'no'}",
            f"question={'yes' if sample.question else 'no'}",
            f"will_answer={'yes' if sample.will_answer else 'no'}",
        ]
    )
    return features


def train_classifier(
    samples: list[TriggerClassifierSample],
    *,
    profile: str,
    min_total: int = 4,
    min_per_class: int = 1,
) -> TriggerClassifierModel:
    """Train a small multinomial Naive Bayes classifier from labeled samples."""
    if min_total < 1:
        raise ValueError("min_total must be at least 1")
    if min_per_class < 1:
        raise ValueError("min_per_class must be at least 1")

    labeled = [
        sample
        for sample in samples
        if normalize_decision_label(sample.decision) in DECISION_LABELS
    ]
    label_counts = {label: 0 for label in DECISION_LABELS}
    for sample in labeled:
        label_counts[normalize_decision_label(sample.decision)] += 1

    if len(labeled) < min_total:
        raise InsufficientTrainingData(
            _threshold_message(label_counts, len(labeled), min_total, min_per_class)
        )
    if any(label_counts[label] < min_per_class for label in DECISION_LABELS):
        raise InsufficientTrainingData(
            _threshold_message(label_counts, len(labeled), min_total, min_per_class)
        )

    feature_counts: dict[str, dict[str, int]] = {label: {} for label in DECISION_LABELS}
    feature_totals: dict[str, int] = {label: 0 for label in DECISION_LABELS}
    vocabulary: set[str] = set()

    for sample in labeled:
        label = normalize_decision_label(sample.decision)
        for feature in extract_features(sample):
            vocabulary.add(feature)
            feature_counts[label][feature] = feature_counts[label].get(feature, 0) + 1
            feature_totals[label] += 1

    return TriggerClassifierModel(
        profile=profile,
        trained_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        labels=list(DECISION_LABELS),
        label_counts=label_counts,
        feature_counts=feature_counts,
        feature_totals=feature_totals,
        vocabulary=sorted(vocabulary),
        min_total=min_total,
        min_per_class=min_per_class,
    )


def predict(
    model: TriggerClassifierModel,
    sample: TriggerClassifierSample,
) -> TriggerClassifierPrediction:
    """Predict accepted/rejected for a sample and return normalized confidence."""
    features = extract_features(sample)
    total_samples = sum(model.label_counts.values())
    vocab_size = max(len(model.vocabulary), 1)
    raw_scores: dict[str, float] = {}

    for label in model.labels:
        label_count = model.label_counts.get(label, 0)
        prior = (label_count + 1) / (total_samples + len(model.labels))
        score = math.log(prior)
        denominator = model.feature_totals.get(label, 0) + vocab_size
        counts = model.feature_counts.get(label, {})
        for feature in features:
            score += math.log((counts.get(feature, 0) + 1) / denominator)
        raw_scores[label] = score

    best_label = max(raw_scores, key=raw_scores.get)
    max_score = raw_scores[best_label]
    exp_scores = {label: math.exp(score - max_score) for label, score in raw_scores.items()}
    exp_total = sum(exp_scores.values()) or 1.0
    probabilities = {
        label: value / exp_total
        for label, value in exp_scores.items()
    }
    return TriggerClassifierPrediction(
        label=best_label,
        confidence=probabilities[best_label],
        scores=probabilities,
    )


def save_model(model: TriggerClassifierModel, path: str | Path) -> Path:
    """Persist a classifier model as local JSON."""
    out_path = Path(path).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(asdict(model), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return out_path


def load_model(path: str | Path) -> TriggerClassifierModel:
    """Load a classifier model from local JSON."""
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    return TriggerClassifierModel(
        profile=str(data.get("profile") or ""),
        trained_at=str(data.get("trained_at") or ""),
        labels=[str(label) for label in data.get("labels") or DECISION_LABELS],
        label_counts={
            str(label): int(count)
            for label, count in (data.get("label_counts") or {}).items()
        },
        feature_counts={
            str(label): {
                str(feature): int(count)
                for feature, count in counts.items()
            }
            for label, counts in (data.get("feature_counts") or {}).items()
            if isinstance(counts, dict)
        },
        feature_totals={
            str(label): int(total)
            for label, total in (data.get("feature_totals") or {}).items()
        },
        vocabulary=[str(feature) for feature in data.get("vocabulary") or []],
        min_total=int(data.get("min_total") or 1),
        min_per_class=int(data.get("min_per_class") or 1),
        version=int(data.get("version") or 1),
    )


def _threshold_message(
    label_counts: dict[str, int],
    labeled_total: int,
    min_total: int,
    min_per_class: int,
) -> str:
    return (
        f"Need at least {min_total} labeled samples and {min_per_class} per class; "
        f"found {labeled_total} "
        f"(accepted={label_counts.get('accepted', 0)} "
        f"rejected={label_counts.get('rejected', 0)})"
    )


def _safe_profile_name(profile: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", (profile or "default").strip())
    return safe.strip("._-") or "default"


def _clean_feature_value(value: str) -> str:
    cleaned = re.sub(r"\s+", "_", str(value or "unknown").strip().casefold())
    return cleaned or "unknown"
