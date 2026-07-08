"""Sanitized realtime decision events for the live meeting loop."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from saymo.analysis import live_control


EVENT_LOG_NAME = "realtime-decisions.jsonl"
MAX_TEXT_LENGTH = 240

_OUTCOMES = {"spoke", "skipped", "blocked"}
_SENSITIVE_MARKERS = (
    "raw" + "_" + "transcript",
    "raw" + " " + "transcript",
    "generated" + "_" + "answer",
    "answer" + "_" + "text",
    "daily" + "_" + "note",
    "audio" + "_" + "bytes",
    "transcript" + "_" + "window",
)
_SENTINEL_TOKEN_RE = re.compile(r"\b" + "PRIVATE" + r"_[A-Za-z0-9_]+\b")
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b([A-Za-z0-9_.-]*(?:token|secret|password|passwd|api[_-]?key)"
    r"[A-Za-z0-9_.-]*)\s*[:=]\s*[^\s,;]+"
)
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}")
_LONG_TOKEN_RE = re.compile(r"\b[A-Za-z0-9_=-]{32,}\b")


@dataclass(frozen=True)
class RealtimeDecisionEvent:
    """Allowlisted local evidence for one realtime decision."""

    created_at: str = ""
    profile: str = ""
    provider: str = ""
    outcome: Literal["spoke", "skipped", "blocked"] = "blocked"
    label: str = ""
    source: str = ""
    automatic: bool = True
    intent_key: str = ""
    confidence: float | None = None
    audio_path: str = ""
    detail: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            object.__setattr__(self, "created_at", _now())

    def to_dict(self) -> dict[str, Any]:
        """Return the stable sanitized event payload."""
        return {
            "created_at": _sanitize_text(self.created_at, max_length=64),
            "profile": _sanitize_text(self.profile, max_length=80),
            "provider": _sanitize_text(self.provider, max_length=80),
            "outcome": self.outcome if self.outcome in _OUTCOMES else "blocked",
            "label": _sanitize_text(self.label, max_length=96),
            "source": _sanitize_text(self.source, max_length=96),
            "automatic": bool(self.automatic),
            "intent_key": _sanitize_text(self.intent_key, max_length=120),
            "confidence": _sanitize_confidence(self.confidence),
            "audio_path": _sanitize_text(self.audio_path, max_length=240),
            "detail": _sanitize_text(self.detail, max_length=MAX_TEXT_LENGTH),
        }


@dataclass(frozen=True)
class RealtimeEventSummary:
    """Sanitized aggregate evidence from realtime decision JSONL rows."""

    path: str = ""
    total: int = 0
    malformed_rows: int = 0
    outcome_counts: dict[str, int] = field(default_factory=dict)
    label_counts: dict[str, int] = field(default_factory=dict)
    source_counts: dict[str, int] = field(default_factory=dict)
    launch_starts: int = 0
    launch_ends: int = 0
    launch_blocks: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    fallback_blocks: int = 0
    provider_blocks: int = 0
    handbrake_blocks: int = 0
    playback_attempts: int = 0
    stop_reasons: dict[str, int] = field(default_factory=dict)


def realtime_event_log_path(profile: str, *, base_dir: Path | str | None = None) -> Path:
    """Return the JSONL decision-event path for a profile."""
    return live_control.live_control_dir(profile, base_dir=base_dir) / EVENT_LOG_NAME


def append_realtime_decision_event(
    profile: str,
    event: RealtimeDecisionEvent,
    *,
    base_dir: Path | str | None = None,
) -> Path:
    """Append one sanitized realtime decision event as JSONL."""
    path = realtime_event_log_path(profile, base_dir=base_dir)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
    return path


def load_realtime_decision_events(path: str | Path) -> tuple[RealtimeDecisionEvent, ...]:
    """Load sanitized realtime decision events from JSONL, skipping bad rows."""
    events, _malformed = _read_realtime_decision_events(path)
    return events


def summarize_realtime_decision_events(path: str | Path) -> RealtimeEventSummary:
    """Summarize sanitized realtime decision evidence from JSONL."""
    event_path = Path(path).expanduser()
    events, malformed_rows = _read_realtime_decision_events(event_path)
    outcomes: Counter[str] = Counter()
    labels: Counter[str] = Counter()
    sources: Counter[str] = Counter()

    for event in events:
        payload = event.to_dict()
        outcomes[str(payload.get("outcome") or "blocked")] += 1
        labels[str(payload.get("label") or "unknown")] += 1
        sources[str(payload.get("source") or "unknown")] += 1

    return RealtimeEventSummary(
        path=str(event_path),
        total=len(events),
        malformed_rows=malformed_rows,
        outcome_counts=_sorted_counts(outcomes),
        label_counts=_sorted_counts(labels),
        source_counts=_sorted_counts(sources),
        launch_starts=labels.get("launch-start", 0),
        launch_ends=labels.get("launch-end", 0),
        launch_blocks=labels.get("launch-readiness-blocked", 0),
        cache_hits=labels.get("response-cache-hit", 0),
        cache_misses=labels.get("cache-miss-blocked", 0),
        fallback_blocks=labels.get("fallback-blocked", 0),
        provider_blocks=labels.get("provider-blocked", 0),
        handbrake_blocks=labels.get("handbrake-blocked", 0),
        playback_attempts=sum(
            count
            for label, count in labels.items()
            if label in {"playback-attempt", "playback-attempted", "playback-started"}
        ),
        stop_reasons=_stop_reason_counts(labels),
    )


def _read_realtime_decision_events(
    path: str | Path,
) -> tuple[tuple[RealtimeDecisionEvent, ...], int]:
    event_path = Path(path).expanduser()
    events: list[RealtimeDecisionEvent] = []
    malformed = 0
    for raw in event_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if not isinstance(row, Mapping):
            malformed += 1
            continue
        events.append(_event_from_mapping(row))
    return tuple(events), malformed


def _event_from_mapping(row: Mapping[str, Any]) -> RealtimeDecisionEvent:
    event = RealtimeDecisionEvent(
        created_at=str(row.get("created_at") or ""),
        profile=str(row.get("profile") or ""),
        provider=str(row.get("provider") or ""),
        outcome=_outcome(row.get("outcome")),
        label=str(row.get("label") or ""),
        source=str(row.get("source") or ""),
        automatic=bool(row.get("automatic", True)),
        intent_key=str(row.get("intent_key") or ""),
        confidence=_sanitize_confidence(row.get("confidence")),
        audio_path=str(row.get("audio_path") or ""),
        detail=str(row.get("detail") or ""),
    )
    return RealtimeDecisionEvent(**event.to_dict())


def _outcome(value: object) -> Literal["spoke", "skipped", "blocked"]:
    text = str(value or "")
    return text if text in _OUTCOMES else "blocked"  # type: ignore[return-value]


def _sorted_counts(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def _stop_reason_counts(labels: Counter[str]) -> dict[str, int]:
    return {
        label: labels[label]
        for label in sorted(labels)
        if "stop" in label.casefold() or "cancel" in label.casefold()
    }


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00",
        "Z",
    )


def _sanitize_text(value: object, *, max_length: int) -> str:
    text = str(value or "")
    text = " ".join(text.replace("\r", " ").replace("\n", " ").split())
    lower = text.lower()
    if any(marker in lower for marker in _SENSITIVE_MARKERS):
        return "[redacted]"
    text = _SENTINEL_TOKEN_RE.sub("[redacted]", text)
    text = _SECRET_ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}=[redacted]", text)
    text = _BEARER_RE.sub("Bearer [redacted]", text)
    text = _LONG_TOKEN_RE.sub("[redacted]", text)
    if len(text) > max_length:
        return text[: max(0, max_length - 3)].rstrip() + "..."
    return text


def _sanitize_confidence(value: float | None) -> float | None:
    if value is None:
        return None
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(confidence):
        return None
    return confidence
