"""Sanitized regression replay metrics for saved trigger sessions."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from saymo.analysis.trigger_readiness import readiness_metrics


@dataclass(frozen=True)
class RegressionSample:
    """Sanitized per-sample replay result."""

    sample: str
    sequence: int
    stored_category: str
    current_category: str
    speaker: str
    decision: str
    current_will_answer: bool
    false_handoff: bool
    missed_handoff: bool


@dataclass(frozen=True)
class RegressionMetrics:
    """Session-level replay metrics."""

    profile: str
    session_id: str
    total: int
    false_handoffs: int
    missed_handoffs: int
    question_noise: int
    known_speakers: int
    unknown_speakers: int
    labeled_decisions: int
    unlabeled_decisions: int
    readiness: str
    readiness_missing: tuple[str, ...]
    speaker_counts: dict[str, int]
    category_counts: dict[str, int]
    decision_counts: dict[str, int]
    samples: tuple[RegressionSample, ...]


def build_regression_metrics(
    rows: Sequence[Any],
    *,
    profile: str,
    session_id: str,
) -> RegressionMetrics:
    """Build sanitized reliability metrics from evaluated trigger rows."""
    samples: list[RegressionSample] = []
    speakers: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    decisions: Counter[str] = Counter()
    false_handoffs = 0
    missed_handoffs = 0
    question_noise = 0

    records = [_record_from_row(row) for row in rows]
    readiness = readiness_metrics(records)

    for row in rows:
        record = _record_from_row(row)
        decision = str(_get(record, "answer_decision", "unlabeled"))
        speaker = str(_get(record, "speaker", "unknown"))
        stored_category = str(_get(record, "category", "unknown"))
        current_category = str(_get(row, "current_category", stored_category))
        current_will_answer = bool(_get(row, "current_will_answer", False))
        current_question = bool(_get(row, "current_question", False))

        speakers[speaker] += 1
        categories[stored_category] += 1
        decisions[decision] += 1

        false_handoff = decision == "rejected" and current_will_answer
        missed_handoff = decision == "accepted" and not current_will_answer
        if false_handoff:
            false_handoffs += 1
        if missed_handoff:
            missed_handoffs += 1
        if current_question and not current_will_answer:
            question_noise += 1

        samples.append(
            RegressionSample(
                sample=Path(str(_get(record, "path", ""))).name,
                sequence=int(_get(record, "session_sequence", 0) or 0),
                stored_category=stored_category,
                current_category=current_category,
                speaker=speaker,
                decision=decision,
                current_will_answer=current_will_answer,
                false_handoff=false_handoff,
                missed_handoff=missed_handoff,
            )
        )

    known_speakers = sum(count for speaker, count in speakers.items() if speaker != "unknown")
    unknown_speakers = speakers.get("unknown", 0)
    labeled_decisions = decisions.get("accepted", 0) + decisions.get("rejected", 0)
    unlabeled_decisions = decisions.get("unlabeled", 0)
    return RegressionMetrics(
        profile=profile,
        session_id=session_id,
        total=len(rows),
        false_handoffs=false_handoffs,
        missed_handoffs=missed_handoffs,
        question_noise=question_noise,
        known_speakers=known_speakers,
        unknown_speakers=unknown_speakers,
        labeled_decisions=labeled_decisions,
        unlabeled_decisions=unlabeled_decisions,
        readiness="ready" if readiness.passed else "not_ready",
        readiness_missing=tuple(readiness.missing_items),
        speaker_counts=dict(sorted(speakers.items())),
        category_counts=dict(sorted(categories.items())),
        decision_counts=dict(sorted(decisions.items())),
        samples=tuple(sorted(samples, key=lambda item: (item.sequence, item.sample))),
    )


def regression_metrics_to_json(metrics: RegressionMetrics) -> dict[str, Any]:
    """Serialize metrics to sanitized JSON-compatible primitives."""
    data = asdict(metrics)
    data["readiness_missing"] = list(metrics.readiness_missing)
    data["samples"] = [asdict(sample) for sample in metrics.samples]
    return data


def regression_metrics_from_json(data: Mapping[str, Any]) -> RegressionMetrics:
    """Load sanitized regression metrics from JSON-compatible primitives."""
    return RegressionMetrics(
        profile=str(data.get("profile") or ""),
        session_id=str(data.get("session_id") or ""),
        total=int(data.get("total") or 0),
        false_handoffs=int(data.get("false_handoffs") or 0),
        missed_handoffs=int(data.get("missed_handoffs") or 0),
        question_noise=int(data.get("question_noise") or 0),
        known_speakers=int(data.get("known_speakers") or 0),
        unknown_speakers=int(data.get("unknown_speakers") or 0),
        labeled_decisions=int(data.get("labeled_decisions") or 0),
        unlabeled_decisions=int(data.get("unlabeled_decisions") or 0),
        readiness=str(data.get("readiness") or "not_ready"),
        readiness_missing=tuple(str(item) for item in data.get("readiness_missing", ())),
        speaker_counts=dict(data.get("speaker_counts") or {}),
        category_counts=dict(data.get("category_counts") or {}),
        decision_counts=dict(data.get("decision_counts") or {}),
        samples=tuple(
            RegressionSample(
                sample=str(item.get("sample") or ""),
                sequence=int(item.get("sequence") or 0),
                stored_category=str(item.get("stored_category") or ""),
                current_category=str(item.get("current_category") or ""),
                speaker=str(item.get("speaker") or "unknown"),
                decision=str(item.get("decision") or "unlabeled"),
                current_will_answer=bool(item.get("current_will_answer")),
                false_handoff=bool(item.get("false_handoff")),
                missed_handoff=bool(item.get("missed_handoff")),
            )
            for item in data.get("samples", ())
            if isinstance(item, dict)
        ),
    )


def write_regression_json(path: str | Path, metrics: RegressionMetrics) -> Path:
    """Write sanitized metrics JSON."""
    out = Path(path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(regression_metrics_to_json(metrics), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return out


def load_regression_json(path: str | Path) -> RegressionMetrics:
    """Load sanitized metrics JSON."""
    return regression_metrics_from_json(
        json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    )


def render_regression_report(
    metrics: RegressionMetrics,
    *,
    baseline: RegressionMetrics | None = None,
) -> str:
    """Render a sanitized markdown regression report."""
    lines = [
        "# Saymo Regression Replay",
        "",
        f"profile: {metrics.profile}",
        f"session: {metrics.session_id}",
        f"samples: {metrics.total}",
        f"false handoffs: {metrics.false_handoffs}",
        f"missed handoffs: {metrics.missed_handoffs}",
        f"question noise: {metrics.question_noise}",
        f"speaker coverage: known={metrics.known_speakers}/{metrics.total} unknown={metrics.unknown_speakers}",
        f"review coverage: labeled={metrics.labeled_decisions}/{metrics.total} unlabeled={metrics.unlabeled_decisions}",
        f"readiness: {metrics.readiness}",
        f"speakers: {_format_counts(metrics.speaker_counts)}",
        f"categories: {_format_counts(metrics.category_counts)}",
        f"decisions: {_format_counts(metrics.decision_counts)}",
    ]
    if metrics.readiness_missing:
        lines.append("missing:")
        lines.extend(f"- {item}" for item in metrics.readiness_missing)
    if baseline is not None:
        lines.extend(
            [
                "",
                "## Compared With Baseline",
                "",
                f"false handoffs delta: {metrics.false_handoffs - baseline.false_handoffs:+d}",
                f"missed handoffs delta: {metrics.missed_handoffs - baseline.missed_handoffs:+d}",
                f"question noise delta: {metrics.question_noise - baseline.question_noise:+d}",
                f"unknown speakers delta: {metrics.unknown_speakers - baseline.unknown_speakers:+d}",
            ]
        )
    lines.extend(["", "## Samples", ""])
    for sample in metrics.samples:
        lines.append(
            "- "
            f"{sample.sample}: seq={sample.sequence} "
            f"stored={sample.stored_category} current={sample.current_category} "
            f"speaker={sample.speaker} decision={sample.decision} "
            f"will_answer={'yes' if sample.current_will_answer else 'no'} "
            f"false_handoff={'yes' if sample.false_handoff else 'no'} "
            f"missed_handoff={'yes' if sample.missed_handoff else 'no'}"
        )
    return "\n".join(lines) + "\n"


def _record_from_row(row: Any) -> Any:
    return _get(row, "record", row)


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _format_counts(counts: Mapping[str, int]) -> str:
    if not counts:
        return "(none)"
    return ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))

