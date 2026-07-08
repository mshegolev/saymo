"""Sanitized realtime decision events for the live meeting loop."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
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
