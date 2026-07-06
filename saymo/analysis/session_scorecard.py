"""Sanitized session reliability scorecards."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from saymo.analysis.live_control import normalize_action
from saymo.analysis.regression_replay import RegressionMetrics
from saymo.analysis.rehearsal import RehearsalArtifact, rehearsal_artifact_from_json


@dataclass(frozen=True)
class TriggerScorecardMetrics:
    """Trigger, addressing, review, and classifier-readiness evidence."""

    total_decisions: int = 0
    triggered_decisions: int = 0
    addressed_to_me_decisions: int = 0
    mention_only_skips: int = 0
    question_decisions: int = 0
    question_noise: int | None = None
    false_handoffs: int | None = None
    missed_handoffs: int | None = None
    speaker_coverage: dict[str, int | None] = field(default_factory=dict)
    review_coverage: dict[str, int | None] = field(default_factory=dict)
    classifier_readiness: str = "unavailable"
    classifier_readiness_missing: tuple[str, ...] = ()
    category_counts: dict[str, int] = field(default_factory=dict)
    decision_counts: dict[str, int] = field(default_factory=dict)
    sample_names: tuple[str, ...] = ()
    addressing: str = "unavailable"
    auto_action: str = "unavailable"
    would_speak: bool | None = None
    blocked_reason: str = ""


@dataclass(frozen=True)
class PlaybackScorecardMetrics:
    """Playback-gate, approval, blocking, latency, and duration evidence."""

    playback_gate_status: str = "unknown"
    playback_gate_detail: str = ""
    approved_speak_attempts: int = 0
    blocked_automatic_playback: int = 0
    latency_ms: dict[str, float] = field(default_factory=dict)
    max_duration_interruptions: int = 0


@dataclass(frozen=True)
class SafetyScorecardMetrics:
    """Handbrake and cancellation evidence."""

    auto_answer_enabled: bool | None = None
    manual_takeover: bool | None = None
    hard_disabled: bool | None = None
    stop_events: int = 0
    takeover_events: int = 0
    hard_disable_events: int = 0
    cancellation_events: int = 0


@dataclass(frozen=True)
class SessionScorecard:
    """One sanitized reliability scorecard."""

    profile: str
    source_type: str
    source_id: str
    status: str
    trigger_metrics: TriggerScorecardMetrics
    playback_metrics: PlaybackScorecardMetrics
    safety_metrics: SafetyScorecardMetrics
    warnings: tuple[str, ...] = ()
    created_at: str = ""


@dataclass(frozen=True)
class _AuditMetrics:
    approved_speak_attempts: int = 0
    blocked_automatic_playback: int = 0
    stop_events: int = 0
    takeover_events: int = 0
    hard_disable_events: int = 0
    cancellation_events: int = 0
    malformed_rows: int = 0
    missing: bool = False


def build_scorecard_from_rehearsal(
    path: str | Path,
    *,
    audit_root: str | Path | None = None,
) -> SessionScorecard:
    """Build a sanitized scorecard from one saved rehearsal artifact."""
    artifact_path = Path(path).expanduser()
    artifact = rehearsal_artifact_from_json(
        json.loads(artifact_path.read_text(encoding="utf-8"))
    )
    audit = _load_live_control_audit(artifact.profile, audit_root=audit_root)
    warnings = _warnings_from_audit(audit)

    return SessionScorecard(
        profile=artifact.profile,
        source_type="rehearsal",
        source_id=artifact_path.name,
        status=_normalize_status(artifact.status),
        trigger_metrics=_trigger_metrics_from_rehearsal(artifact),
        playback_metrics=_playback_metrics_from_rehearsal(artifact, audit),
        safety_metrics=_safety_metrics_from_rehearsal(artifact, audit),
        warnings=tuple(warnings),
        created_at=artifact.created_at,
    )


def build_scorecard_from_regression(
    metrics: RegressionMetrics,
    *,
    audit_root: str | Path | None = None,
) -> SessionScorecard:
    """Build a sanitized scorecard from replayed trigger-session metrics."""
    audit = _load_live_control_audit(metrics.profile, audit_root=audit_root)
    warnings = _warnings_from_audit(audit)
    if metrics.readiness_missing:
        warnings.append(
            "classifier readiness missing: "
            + ", ".join(_sanitize_detail(item) for item in metrics.readiness_missing)
        )

    return SessionScorecard(
        profile=metrics.profile,
        source_type="session",
        source_id=_safe_label(metrics.session_id),
        status=_status_from_regression(metrics),
        trigger_metrics=_trigger_metrics_from_regression(metrics),
        playback_metrics=PlaybackScorecardMetrics(
            approved_speak_attempts=audit.approved_speak_attempts,
            blocked_automatic_playback=audit.blocked_automatic_playback,
        ),
        safety_metrics=SafetyScorecardMetrics(
            stop_events=audit.stop_events,
            takeover_events=audit.takeover_events,
            hard_disable_events=audit.hard_disable_events,
            cancellation_events=audit.cancellation_events,
        ),
        warnings=tuple(warnings),
    )


def scorecard_to_json(scorecard: SessionScorecard) -> dict[str, Any]:
    """Serialize a scorecard to sanitized JSON-compatible primitives."""
    data = asdict(scorecard)
    data["warnings"] = list(scorecard.warnings)
    data["trigger_metrics"]["classifier_readiness_missing"] = list(
        scorecard.trigger_metrics.classifier_readiness_missing
    )
    data["trigger_metrics"]["sample_names"] = list(
        scorecard.trigger_metrics.sample_names
    )
    return data


def write_scorecard_json(path: str | Path, scorecard: SessionScorecard) -> Path:
    """Write sanitized scorecard JSON."""
    out = Path(path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(scorecard_to_json(scorecard), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return out


def render_scorecard_markdown(scorecard: SessionScorecard) -> str:
    """Render a concise sanitized Markdown scorecard."""
    trigger = scorecard.trigger_metrics
    playback = scorecard.playback_metrics
    safety = scorecard.safety_metrics
    lines = [
        "# Saymo Session Reliability Scorecard",
        "",
        f"profile: {_safe_label(scorecard.profile)}",
        f"source: {scorecard.source_type}",
        f"source id: {_safe_label(scorecard.source_id)}",
        f"status: {scorecard.status}",
        "",
        "## Summary",
        "",
        f"triggered decisions: {trigger.triggered_decisions}/{trigger.total_decisions}",
        f"would speak: {_format_bool(trigger.would_speak)}",
        f"classifier readiness: {trigger.classifier_readiness}",
        f"blocked automatic playback: {playback.blocked_automatic_playback}",
        f"cancellations: {safety.cancellation_events}",
        "",
        "## Trigger and Addressing",
        "",
        f"addressed to me: {trigger.addressed_to_me_decisions}",
        f"mention-only skips: {trigger.mention_only_skips}",
        f"question decisions: {trigger.question_decisions}",
        f"question noise: {_format_unknown_int(trigger.question_noise)}",
        f"false handoffs: {_format_unknown_int(trigger.false_handoffs)}",
        f"missed handoffs: {_format_unknown_int(trigger.missed_handoffs)}",
        f"speaker coverage: {_format_counts(trigger.speaker_coverage)}",
        f"review coverage: {_format_counts(trigger.review_coverage)}",
        f"categories: {_format_counts(trigger.category_counts)}",
        f"decisions: {_format_counts(trigger.decision_counts)}",
        f"addressing: {_safe_label(trigger.addressing)}",
        f"auto action: {_safe_label(trigger.auto_action)}",
    ]
    if trigger.blocked_reason:
        lines.append(f"blocked reason: {_sanitize_detail(trigger.blocked_reason)}")
    if trigger.classifier_readiness_missing:
        lines.append("classifier readiness missing:")
        lines.extend(f"- {_sanitize_detail(item)}" for item in trigger.classifier_readiness_missing)

    lines.extend(
        [
            "",
            "## Playback and Handbrake",
            "",
            f"playback gate: {playback.playback_gate_status}",
            f"playback gate detail: {_sanitize_detail(playback.playback_gate_detail) or '-'}",
            f"approved speak attempts: {playback.approved_speak_attempts}",
            f"blocked automatic playback: {playback.blocked_automatic_playback}",
            f"latency: {_format_latency(playback.latency_ms)}",
            f"max-duration interruptions: {playback.max_duration_interruptions}",
            f"auto answer enabled: {_format_bool(safety.auto_answer_enabled)}",
            f"manual takeover: {_format_bool(safety.manual_takeover)}",
            f"hard disabled: {_format_bool(safety.hard_disabled)}",
            f"stop events: {safety.stop_events}",
            f"takeover events: {safety.takeover_events}",
            f"hard-disable events: {safety.hard_disable_events}",
            f"cancellation events: {safety.cancellation_events}",
            "",
            "## Warnings",
            "",
        ]
    )
    if scorecard.warnings:
        lines.extend(f"- {_sanitize_detail(warning)}" for warning in scorecard.warnings)
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _trigger_metrics_from_rehearsal(artifact: RehearsalArtifact) -> TriggerScorecardMetrics:
    decision = artifact.decision
    addressed = decision.addressing in {"addressed_to_me", "handoff", "asked_to_speak"}
    mention_only = decision.addressing in {"mention_only", "mentioned_me"}
    return TriggerScorecardMetrics(
        total_decisions=1,
        triggered_decisions=1 if decision.triggered else 0,
        addressed_to_me_decisions=1 if addressed else 0,
        mention_only_skips=1 if mention_only and not decision.would_speak else 0,
        question_decisions=1 if decision.question else 0,
        question_noise=None,
        false_handoffs=None,
        missed_handoffs=None,
        speaker_coverage={"known": None, "unknown": None, "total": None},
        review_coverage={"labeled": None, "unlabeled": None, "total": None},
        classifier_readiness="unavailable",
        addressing=_safe_label(decision.addressing),
        auto_action=_safe_label(decision.auto_action),
        would_speak=decision.would_speak,
        blocked_reason=_sanitize_detail(decision.blocked_reason),
    )


def _trigger_metrics_from_regression(metrics: RegressionMetrics) -> TriggerScorecardMetrics:
    return TriggerScorecardMetrics(
        total_decisions=metrics.total,
        triggered_decisions=int(metrics.decision_counts.get("accepted", 0)),
        addressed_to_me_decisions=int(metrics.category_counts.get("asked_to_speak", 0)),
        mention_only_skips=int(metrics.category_counts.get("mentioned_me", 0)),
        question_decisions=int(metrics.category_counts.get("question", 0)),
        question_noise=metrics.question_noise,
        false_handoffs=metrics.false_handoffs,
        missed_handoffs=metrics.missed_handoffs,
        speaker_coverage={
            "known": metrics.known_speakers,
            "unknown": metrics.unknown_speakers,
            "total": metrics.total,
        },
        review_coverage={
            "labeled": metrics.labeled_decisions,
            "unlabeled": metrics.unlabeled_decisions,
            "total": metrics.total,
        },
        classifier_readiness=metrics.readiness,
        classifier_readiness_missing=tuple(
            _sanitize_detail(item) for item in metrics.readiness_missing
        ),
        category_counts=dict(metrics.category_counts),
        decision_counts=dict(metrics.decision_counts),
        sample_names=tuple(_safe_label(sample.sample) for sample in metrics.samples),
        addressing="aggregate",
        auto_action="aggregate",
        would_speak=None,
    )


def _playback_metrics_from_rehearsal(
    artifact: RehearsalArtifact,
    audit: _AuditMetrics,
) -> PlaybackScorecardMetrics:
    gate = _find_check(artifact, "playback gate")
    return PlaybackScorecardMetrics(
        playback_gate_status=gate.status if gate else "unknown",
        playback_gate_detail=_sanitize_detail(gate.detail if gate else ""),
        approved_speak_attempts=audit.approved_speak_attempts,
        blocked_automatic_playback=audit.blocked_automatic_playback,
        latency_ms=_latency_from_checks(artifact),
        max_duration_interruptions=_max_duration_interruptions(artifact),
    )


def _safety_metrics_from_rehearsal(
    artifact: RehearsalArtifact,
    audit: _AuditMetrics,
) -> SafetyScorecardMetrics:
    state = artifact.live_control_state
    return SafetyScorecardMetrics(
        auto_answer_enabled=_bool_or_none(state.get("auto_answer_enabled")),
        manual_takeover=_bool_or_none(state.get("manual_takeover")),
        hard_disabled=_bool_or_none(state.get("hard_disabled")),
        stop_events=audit.stop_events,
        takeover_events=audit.takeover_events,
        hard_disable_events=audit.hard_disable_events,
        cancellation_events=audit.cancellation_events,
    )


def _find_check(artifact: RehearsalArtifact, name: str):
    needle = name.casefold()
    for check in artifact.checks:
        if needle in check.name.casefold():
            return check
    return None


def _latency_from_checks(artifact: RehearsalArtifact) -> dict[str, float]:
    values: dict[str, float] = {}
    for check in artifact.checks:
        if "latency" not in check.name.casefold() and "ms" not in check.detail.casefold():
            continue
        for label, value in re.findall(
            r"([A-Za-z][A-Za-z0-9_ -]*)\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*ms",
            check.detail,
        ):
            key = label.strip().lower().replace(" ", "_").replace("-", "_")
            values[key] = float(value)
    return values


def _max_duration_interruptions(artifact: RehearsalArtifact) -> int:
    count = 0
    for check in artifact.checks:
        text = f"{check.name} {check.detail}".casefold()
        if ("max duration" in text or "max-duration" in text) and check.status in {"fail", "warn"}:
            count += 1
    return count


def _load_live_control_audit(
    profile: str,
    *,
    audit_root: str | Path | None,
) -> _AuditMetrics:
    path = _audit_path(profile, audit_root)
    if not path.exists():
        return _AuditMetrics(missing=True)

    counts = {
        "approved_speak_attempts": 0,
        "blocked_automatic_playback": 0,
        "stop_events": 0,
        "takeover_events": 0,
        "hard_disable_events": 0,
        "cancellation_events": 0,
        "malformed_rows": 0,
    }
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            counts["malformed_rows"] += 1
            continue
        if not isinstance(row, Mapping):
            counts["malformed_rows"] += 1
            continue
        action_text = str(row.get("action") or "")
        result_text = str(row.get("result") or "")
        reason_text = str(row.get("reason") or "")
        combined_result = f"{result_text} {reason_text}".casefold()

        if _is_cancellation_result(combined_result):
            counts["cancellation_events"] += 1
        if _is_blocked_playback_result(action_text, combined_result):
            counts["blocked_automatic_playback"] += 1

        try:
            action = normalize_action(action_text)
        except ValueError:
            counts["malformed_rows"] += 1
            continue

        if action == "approved_speak":
            counts["approved_speak_attempts"] += 1
        elif action == "stop":
            counts["stop_events"] += 1
        elif action == "takeover":
            counts["takeover_events"] += 1
        elif action == "hard_disable":
            counts["hard_disable_events"] += 1

    return _AuditMetrics(**counts)


def _audit_path(profile: str, audit_root: str | Path | None) -> Path:
    root = Path(audit_root).expanduser() if audit_root else Path.home() / ".saymo" / "live_control"
    return root / _safe_profile(profile) / "audit.jsonl"


def _warnings_from_audit(audit: _AuditMetrics) -> list[str]:
    warnings: list[str] = []
    if audit.missing:
        warnings.append("live-control audit log not found")
    if audit.malformed_rows:
        warnings.append(f"skipped {audit.malformed_rows} malformed audit rows")
    return warnings


def _status_from_regression(metrics: RegressionMetrics) -> str:
    if metrics.false_handoffs or metrics.missed_handoffs:
        return "fail"
    if (
        metrics.question_noise
        or metrics.readiness != "ready"
        or metrics.unknown_speakers
        or metrics.unlabeled_decisions
    ):
        return "warn"
    return "pass"


def _normalize_status(status: str) -> str:
    value = str(status or "").strip().lower()
    return value if value in {"pass", "warn", "fail"} else "fail"


def _safe_label(value: Any) -> str:
    text = " ".join(str(value or "").split())
    text = re.sub(r"(?:[A-Za-z]:)?/(?:[^\s/]+/)*[^\s/]+", lambda m: Path(m.group()).name, text)
    return text or "unknown"


def _safe_profile(profile: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in profile)
    return safe or "default"


def _sanitize_detail(value: Any) -> str:
    text = _safe_label(value)
    text = re.sub(r"\b[A-Z0-9_]*SECRET[A-Z0-9_=-]*\b", "[redacted]", text, flags=re.IGNORECASE)
    text = re.sub(r"\b[A-Z0-9_]*TOKEN[A-Z0-9_=-]*\b", "[redacted]", text, flags=re.IGNORECASE)
    return text


def _format_bool(value: bool | None) -> str:
    if value is None:
        return "unknown"
    return "yes" if value else "no"


def _format_unknown_int(value: int | None) -> str:
    return "unknown" if value is None else str(value)


def _format_counts(counts: Mapping[str, Any]) -> str:
    if not counts:
        return "unknown"
    return ", ".join(f"{key}={_format_count_value(value)}" for key, value in sorted(counts.items()))


def _format_count_value(value: Any) -> str:
    return "unknown" if value is None else str(value)


def _format_latency(values: Mapping[str, float]) -> str:
    if not values:
        return "unknown"
    return ", ".join(f"{key}={value:g}ms" for key, value in sorted(values.items()))


def _bool_or_none(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _is_cancellation_result(value: str) -> bool:
    return any(word in value for word in ("cancel", "timeout", "interrupt", "stopped"))


def _is_blocked_playback_result(action: str, value: str) -> bool:
    action_value = str(action or "").casefold()
    return (
        "automatic_playback_blocked" in value
        or "automatic playback blocked" in value
        or action_value == "automatic_playback_blocked"
    )
