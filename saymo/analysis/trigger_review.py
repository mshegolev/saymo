"""Reusable trigger-sample review and relabel helpers."""

from __future__ import annotations

import json
import shutil
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any


TRIGGER_SAMPLE_CATEGORIES = (
    "asked_to_speak",
    "mentioned_me",
    "question",
    "speech",
    "silence",
)
SPEAKER_LABELS = ("me", "other", "unknown")
ANSWER_DECISION_LABELS = ("accepted", "rejected", "unlabeled")


@dataclass(frozen=True)
class TriggerReviewFilters:
    """Filter options shared by list, review, and report flows."""

    session: str | None = None
    category: str | None = None
    speaker: str | None = None
    answer_decision: str | None = None
    date_from: str | datetime | date | None = None
    date_to: str | datetime | date | None = None
    classifier_disagreement: bool | None = None


@dataclass(frozen=True)
class CategoryRelabelPlan:
    """Filesystem paths needed for moving a sample to another category."""

    path: Path
    category: str
    previous_category: str
    target_path: Path
    wav_path: Path
    target_wav_path: Path
    wav_exists: bool


@dataclass(frozen=True)
class CategoryRelabelResult:
    """Result of applying a category relabel."""

    previous_category: str
    category: str
    previous_path: Path
    path: Path
    previous_wav_path: Path
    wav_path: Path
    wav_moved: bool


@dataclass(frozen=True)
class SanitizedReviewSample:
    """One report sample summary with transcript/audio payload omitted."""

    path: str
    profile: str
    created_at: str
    session_sequence: int
    category: str
    current_category: str
    speaker: str
    answer_decision: str
    trigger: bool
    question: bool
    will_answer: bool
    current_trigger: bool
    current_question: bool
    current_will_answer: bool
    miss: bool
    false_positive: bool
    classifier_disagreement: bool
    rms: float
    peak: float


@dataclass(frozen=True)
class SanitizedReviewCategory:
    """Report group for one stored category within a session."""

    category: str
    total: int
    speaker_counts: dict[str, int]
    answer_decision_counts: dict[str, int]
    samples: tuple[SanitizedReviewSample, ...]


@dataclass(frozen=True)
class SanitizedReviewSession:
    """Report group for one trigger-capture session."""

    session_id: str
    session_name: str
    total: int
    categories: tuple[SanitizedReviewCategory, ...]


@dataclass(frozen=True)
class SanitizedReviewReport:
    """Sanitized trigger-review report grouped by session then category."""

    total: int
    sessions: tuple[SanitizedReviewSession, ...]


@dataclass(frozen=True)
class ReviewAction:
    """Parsed review queue action."""

    kind: str
    value: str | None = None


def filter_review_rows(
    rows: Sequence[Any],
    filters: TriggerReviewFilters | None = None,
) -> list[Any]:
    """Return rows matching trigger-review filters.

    Items may be evaluated rows with a ``record`` attribute or raw record-like
    objects. ``classifier_disagreement`` only has meaning for evaluated rows.
    """
    if filters is None:
        return list(rows)
    validate_review_filters(filters)
    return [row for row in rows if review_row_matches(row, filters)]


def validate_review_filters(filters: TriggerReviewFilters) -> None:
    """Validate user-provided review filters before applying them."""
    for name, value, end_of_day in (
        ("date_from", filters.date_from, False),
        ("date_to", filters.date_to, True),
    ):
        if value is not None and _parse_datetime_bound(value, end_of_day=end_of_day) is None:
            raise ValueError(
                f"Invalid {name}: {value!r}; expected ISO date or datetime"
            )


def review_row_matches(row: Any, filters: TriggerReviewFilters) -> bool:
    """Check one row against trigger-review filters."""
    record = _record_from_row(row)
    if filters.session:
        session_id = str(_get(record, "session_id", ""))
        if not session_id.startswith(filters.session):
            return False
    if filters.category and str(_get(record, "category", "")) != filters.category:
        return False
    if filters.speaker and str(_get(record, "speaker", "")) != filters.speaker:
        return False
    if (
        filters.answer_decision
        and str(_get(record, "answer_decision", "")) != filters.answer_decision
    ):
        return False
    if not _created_at_in_range(
        _get(record, "created_at", ""),
        date_from=filters.date_from,
        date_to=filters.date_to,
    ):
        return False
    if filters.classifier_disagreement is not None:
        if has_classifier_disagreement(row) is not filters.classifier_disagreement:
            return False
    return True


def has_classifier_disagreement(row: Any) -> bool:
    """Return whether stored sample metadata differs from current evaluation."""
    explicit = _get(row, "classifier_disagreement", None)
    if explicit is not None:
        return bool(explicit)

    record = _record_from_row(row)
    if bool(_get(row, "miss", False)) or bool(_get(row, "false_positive", False)):
        return True

    comparisons = (
        ("category", "current_category"),
        ("trigger", "current_trigger"),
        ("question", "current_question"),
        ("will_answer", "current_will_answer"),
        ("addressing", "current_addressing"),
    )
    for stored_name, current_name in comparisons:
        current = _get(row, current_name, None)
        if current is None:
            continue
        if _get(record, stored_name, None) != current:
            return True
    return False


def plan_category_relabel(
    sample_json: str | Path,
    category: str,
) -> CategoryRelabelPlan:
    """Plan a metadata category update plus adjacent JSON/WAV move."""
    target_category = _normalize_category(category)
    path = Path(sample_json).expanduser()
    data = _read_sample_metadata(path)
    previous_category = str(data.get("category") or path.parent.name)
    wav_name = Path(str(data.get("wav") or path.with_suffix(".wav").name)).name
    target_dir = path.parent.parent / target_category
    wav_path = path.with_name(wav_name)
    return CategoryRelabelPlan(
        path=path,
        category=target_category,
        previous_category=previous_category,
        target_path=target_dir / path.name,
        wav_path=wav_path,
        target_wav_path=target_dir / wav_name,
        wav_exists=wav_path.exists(),
    )


def apply_category_relabel(
    sample_json: str | Path,
    category: str,
) -> CategoryRelabelResult:
    """Update sample metadata category and move JSON plus adjacent WAV."""
    plan = plan_category_relabel(sample_json, category)
    data = _read_sample_metadata(plan.path)
    _check_relabel_collisions(plan)

    data["category"] = plan.category
    plan.target_path.parent.mkdir(parents=True, exist_ok=True)
    plan.path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if plan.path != plan.target_path:
        shutil.move(str(plan.path), str(plan.target_path))

    wav_moved = False
    if plan.wav_exists and plan.wav_path != plan.target_wav_path:
        shutil.move(str(plan.wav_path), str(plan.target_wav_path))
        wav_moved = True

    return CategoryRelabelResult(
        previous_category=plan.previous_category,
        category=plan.category,
        previous_path=plan.path,
        path=plan.target_path,
        previous_wav_path=plan.wav_path,
        wav_path=plan.target_wav_path,
        wav_moved=wav_moved,
    )


def build_sanitized_review_report(rows: Sequence[Any]) -> SanitizedReviewReport:
    """Build sanitized report data grouped by session, then stored category."""
    session_groups: dict[tuple[str, str], dict[str, list[Any]]] = {}
    for row in rows:
        record = _record_from_row(row)
        session_id = str(_get(record, "session_id", "")) or "unsessioned"
        session_name = str(_get(record, "session_name", "")) or session_id
        category = str(_get(record, "category", "")) or "unknown"
        session = session_groups.setdefault((session_id, session_name), {})
        session.setdefault(category, []).append(row)

    sessions: list[SanitizedReviewSession] = []
    for (session_id, session_name), categories_by_name in session_groups.items():
        categories: list[SanitizedReviewCategory] = []
        for category, category_rows in categories_by_name.items():
            samples = tuple(_sanitize_row(row) for row in category_rows)
            speaker_counts = _count_values(
                _get(sample, "speaker", "") for sample in samples
            )
            decision_counts = _count_values(
                _get(sample, "answer_decision", "") for sample in samples
            )
            categories.append(
                SanitizedReviewCategory(
                    category=category,
                    total=len(samples),
                    speaker_counts=speaker_counts,
                    answer_decision_counts=decision_counts,
                    samples=samples,
                )
            )
        sessions.append(
            SanitizedReviewSession(
                session_id=session_id,
                session_name=session_name,
                total=sum(category.total for category in categories),
                categories=tuple(categories),
            )
        )
    return SanitizedReviewReport(
        total=sum(session.total for session in sessions),
        sessions=tuple(sessions),
    )


def render_grouped_trigger_report(profile: str, rows: Sequence[Any]) -> str:
    """Render a sanitized markdown report grouped by session and category."""
    report = build_sanitized_review_report(rows)
    lines = [
        "# Saymo Trigger Sample Report",
        "",
        f"profile: {profile}",
        f"records: {report.total}",
    ]
    for session in report.sessions:
        lines.extend(
            [
                "",
                f"## Session: {session.session_id}",
                "",
                f"name: {session.session_name}",
                f"records: {session.total}",
            ]
        )
        for category in session.categories:
            lines.extend(
                [
                    "",
                    f"### {category.category}",
                    "",
                    f"records: {category.total}",
                    "speakers: "
                    + _format_counts(category.speaker_counts),
                    "decisions: "
                    + _format_counts(category.answer_decision_counts),
                ]
            )
            for sample in category.samples:
                lines.append(
                    "- "
                    f"{sample.path}: current={sample.current_category}, "
                    f"speaker={sample.speaker}, "
                    f"decision={sample.answer_decision}, "
                    f"trigger={'yes' if sample.current_trigger else 'no'}, "
                    f"question={'yes' if sample.current_question else 'no'}, "
                    f"will_answer={'yes' if sample.current_will_answer else 'no'}, "
                    f"disagreement={'yes' if sample.classifier_disagreement else 'no'}"
                )
    return "\n".join(lines) + "\n"


def parse_review_action(raw: str | None) -> ReviewAction | None:
    """Parse a category, speaker, decision, skip, or quit review action."""
    text = _clean_action_text(raw)
    if not text:
        return ReviewAction("skip")
    if text in {"q", "quit", "exit"}:
        return ReviewAction("quit")
    if text in {"k", "keep", "next", "n", "skip"}:
        return ReviewAction("skip")

    prefixed = _parse_prefixed_action(text)
    if prefixed is not None:
        return prefixed

    for parser in (parse_category_action, parse_speaker_action, parse_decision_action):
        action = parser(text)
        if action is not None:
            return action
    return None


def parse_category_action(raw: str | None) -> ReviewAction | None:
    """Parse a category relabel value."""
    category = _category_alias(_clean_action_text(raw))
    if category is None:
        return None
    return ReviewAction("category", category)


def parse_speaker_action(raw: str | None) -> ReviewAction | None:
    """Parse a speaker relabel value."""
    speaker = _speaker_alias(_clean_action_text(raw))
    if speaker is None:
        return None
    return ReviewAction("speaker", speaker)


def parse_decision_action(raw: str | None) -> ReviewAction | None:
    """Parse an answer-decision relabel value."""
    decision = _decision_alias(_clean_action_text(raw))
    if decision is None:
        return None
    return ReviewAction("decision", decision)


def _sanitize_row(row: Any) -> SanitizedReviewSample:
    record = _record_from_row(row)
    path = Path(str(_get(record, "path", "")))
    return SanitizedReviewSample(
        path=path.name,
        profile=str(_get(record, "profile", "")),
        created_at=str(_get(record, "created_at", "")),
        session_sequence=int(_get(record, "session_sequence", 0) or 0),
        category=str(_get(record, "category", "")),
        current_category=str(_get(row, "current_category", _get(record, "category", ""))),
        speaker=str(_get(record, "speaker", "unknown")),
        answer_decision=str(_get(record, "answer_decision", "unlabeled")),
        trigger=bool(_get(record, "trigger", False)),
        question=bool(_get(record, "question", False)),
        will_answer=bool(_get(record, "will_answer", False)),
        current_trigger=bool(_get(row, "current_trigger", _get(record, "trigger", False))),
        current_question=bool(
            _get(row, "current_question", _get(record, "question", False))
        ),
        current_will_answer=bool(
            _get(row, "current_will_answer", _get(record, "will_answer", False))
        ),
        miss=bool(_get(row, "miss", False)),
        false_positive=bool(_get(row, "false_positive", False)),
        classifier_disagreement=has_classifier_disagreement(row),
        rms=float(_get(record, "rms", 0.0) or 0.0),
        peak=float(_get(record, "peak", 0.0) or 0.0),
    )


def _read_sample_metadata(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Sample metadata is not an object: {path}")
    return data


def _check_relabel_collisions(plan: CategoryRelabelPlan) -> None:
    if plan.target_path != plan.path and plan.target_path.exists():
        raise FileExistsError(f"Target sample already exists: {plan.target_path}")
    if (
        plan.wav_exists
        and plan.target_wav_path != plan.wav_path
        and plan.target_wav_path.exists()
    ):
        raise FileExistsError(f"Target WAV already exists: {plan.target_wav_path}")


def _created_at_in_range(
    created_at: Any,
    *,
    date_from: str | datetime | date | None,
    date_to: str | datetime | date | None,
) -> bool:
    start = _parse_datetime_bound(date_from, end_of_day=False)
    end = _parse_datetime_bound(date_to, end_of_day=True)
    if start is None and end is None:
        return True

    value = _parse_datetime_bound(created_at, end_of_day=False)
    if value is None:
        return False
    if start is not None and value < start:
        return False
    if end is not None and value > end:
        return False
    return True


def _parse_datetime_bound(
    value: str | datetime | date | Any,
    *,
    end_of_day: bool,
) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _normalize_datetime(value)
    if isinstance(value, date):
        return datetime.combine(value, time.max if end_of_day else time.min)

    text = str(value).strip()
    if not text:
        return None
    try:
        if len(text) == 10:
            return datetime.combine(
                date.fromisoformat(text),
                time.max if end_of_day else time.min,
            )
        return _normalize_datetime(datetime.fromisoformat(text.replace("Z", "+00:00")))
    except ValueError:
        return None


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _parse_prefixed_action(text: str) -> ReviewAction | None:
    parts = text.split(maxsplit=1)
    if len(parts) != 2:
        return None
    prefix, value = parts
    if prefix in {"c", "cat", "category"}:
        return parse_category_action(value)
    if prefix in {"sp", "speaker"}:
        return parse_speaker_action(value)
    if prefix in {"d", "dec", "decision"}:
        return parse_decision_action(value)
    return None


def _normalize_category(category: str) -> str:
    normalized = _category_alias(category)
    if normalized is None:
        allowed = ", ".join(TRIGGER_SAMPLE_CATEGORIES)
        raise ValueError(f"Unknown trigger sample category {category!r}; expected {allowed}")
    return normalized


def _category_alias(text: str) -> str | None:
    aliases = {
        "ask": "asked_to_speak",
        "asked": "asked_to_speak",
        "answer": "asked_to_speak",
        "asked_to_speak": "asked_to_speak",
        "mention": "mentioned_me",
        "mentioned": "mentioned_me",
        "mentioned_me": "mentioned_me",
        "q": "question",
        "question": "question",
        "speech": "speech",
        "talk": "speech",
        "silence": "silence",
        "silent": "silence",
    }
    return aliases.get(text)


def _speaker_alias(text: str) -> str | None:
    aliases = {
        "me": "me",
        "mine": "me",
        "self": "me",
        "other": "other",
        "them": "other",
        "unknown": "unknown",
        "unk": "unknown",
    }
    return aliases.get(text)


def _decision_alias(text: str) -> str | None:
    aliases = {
        "accept": "accepted",
        "accepted": "accepted",
        "answer": "accepted",
        "yes": "accepted",
        "reject": "rejected",
        "rejected": "rejected",
        "no": "rejected",
        "skip_answer": "rejected",
        "unlabel": "unlabeled",
        "unlabeled": "unlabeled",
        "unknown": "unlabeled",
        "clear": "unlabeled",
    }
    return aliases.get(text)


def _clean_action_text(raw: str | None) -> str:
    return " ".join(str(raw or "").strip().lower().split())


def _record_from_row(row: Any) -> Any:
    return _get(row, "record", row)


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _count_values(values: Any) -> dict[str, int]:
    counter = Counter(str(value) for value in values if str(value))
    return dict(sorted(counter.items()))


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "(none)"
    return ", ".join(f"{key}={value}" for key, value in counts.items())
