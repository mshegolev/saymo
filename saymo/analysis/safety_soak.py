"""Safety soak gates over sanitized Saymo reliability scorecards."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from saymo.analysis.session_scorecard import SessionScorecard


DRIFT_METRICS = (
    "false_handoffs",
    "missed_handoffs",
    "question_noise",
    "unknown_speakers",
    "max_latency_ms",
)

V19_TOTAL_LINES = (
    ("launch_not_ready", "launch not ready"),
    ("launch_blocks", "launch blocks"),
    ("launch_warnings", "launch warnings"),
    ("cache_hits", "cache hits"),
    ("cache_misses", "cache misses"),
    ("cache_missing", "cache missing"),
    ("provider_blocks", "provider blocks"),
    ("fallback_blocks", "fallback blocks"),
    ("handbrake_blocks", "handbrake blocks"),
    ("realtime_malformed_rows", "realtime malformed rows"),
    ("daemon_not_ready", "daemon not ready"),
)

REALTIME_CACHE_BLOCK_LABELS = (
    "cache-miss-blocked",
    "cache-disabled-blocked",
    "voice-metadata-blocked",
)

DAEMON_READY_FIELDS = (
    "daemon_ready",
    "daemon_running",
    "daemon_heartbeat_fresh",
    "daemon_hotkeys_ready",
    "hotkeys_ready",
)


@dataclass(frozen=True)
class SafetySoakViolation:
    """One safety invariant breach."""

    source_id: str
    rule: str
    detail: str


@dataclass(frozen=True)
class SafetySoakDriftMetric:
    """One aggregate metric compared against a prior soak baseline."""

    name: str
    baseline: float
    current: float
    delta: float
    worsened: bool


@dataclass(frozen=True)
class SafetySoakSource:
    """Sanitized per-input summary."""

    source_type: str
    source_id: str
    status: str
    would_speak: bool | None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class SafetySoakReport:
    """Aggregated safety soak gate result."""

    profile: str
    status: str
    totals: dict[str, float | int]
    sources: tuple[SafetySoakSource, ...]
    violations: tuple[SafetySoakViolation, ...] = ()
    drift: tuple[SafetySoakDriftMetric, ...] = ()
    warnings: tuple[str, ...] = ()
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))


def build_safety_soak_report(
    *,
    profile: str,
    scorecards: Iterable[SessionScorecard],
    baseline: SafetySoakReport | None = None,
) -> SafetySoakReport:
    """Build an aggregate safety soak gate report from sanitized scorecards."""
    scorecard_items = tuple(scorecards)
    totals = _aggregate_totals(scorecard_items)
    violations = tuple(
        violation
        for scorecard in scorecard_items
        for violation in _violations_for_scorecard(scorecard)
    )
    drift = _compare_drift(totals, baseline.totals if baseline else None)
    warnings = tuple(_warnings_for_scorecards(scorecard_items))
    sources = tuple(
        SafetySoakSource(
            source_type=scorecard.source_type,
            source_id=scorecard.source_id,
            status=scorecard.status,
            would_speak=scorecard.trigger_metrics.would_speak,
            warnings=scorecard.warnings,
        )
        for scorecard in scorecard_items
    )
    status = "fail" if violations or any(metric.worsened for metric in drift) else "pass"
    return SafetySoakReport(
        profile=profile,
        status=status,
        totals=totals,
        sources=sources,
        violations=violations,
        drift=drift,
        warnings=warnings,
    )


def safety_soak_to_json(report: SafetySoakReport) -> dict[str, Any]:
    """Serialize a safety soak report to JSON-compatible primitives."""
    data = asdict(report)
    data["sources"] = [
        {
            **source,
            "warnings": list(source.get("warnings") or []),
        }
        for source in data["sources"]
    ]
    data["violations"] = list(data["violations"])
    data["drift"] = list(data["drift"])
    data["warnings"] = list(report.warnings)
    return data


def safety_soak_from_json(data: dict[str, Any]) -> SafetySoakReport:
    """Load a safety soak report from a prior JSON export."""
    return SafetySoakReport(
        profile=str(data.get("profile") or "unknown"),
        status=str(data.get("status") or "fail"),
        totals={
            str(key): _number_value(value)
            for key, value in (data.get("totals") or {}).items()
        },
        sources=tuple(
            SafetySoakSource(
                source_type=str(source.get("source_type") or "unknown"),
                source_id=_safe_text(source.get("source_id") or "unknown"),
                status=str(source.get("status") or "unknown"),
                would_speak=source.get("would_speak") if isinstance(source.get("would_speak"), bool) else None,
                warnings=tuple(_safe_text(item) for item in source.get("warnings") or ()),
            )
            for source in data.get("sources") or ()
            if isinstance(source, dict)
        ),
        violations=tuple(
            SafetySoakViolation(
                source_id=_safe_text(item.get("source_id") or "unknown"),
                rule=_safe_text(item.get("rule") or "unknown"),
                detail=_safe_text(item.get("detail") or ""),
            )
            for item in data.get("violations") or ()
            if isinstance(item, dict)
        ),
        drift=tuple(
            SafetySoakDriftMetric(
                name=_safe_text(item.get("name") or "unknown"),
                baseline=float(_number_value(item.get("baseline"))),
                current=float(_number_value(item.get("current"))),
                delta=float(_number_value(item.get("delta"))),
                worsened=bool(item.get("worsened")),
            )
            for item in data.get("drift") or ()
            if isinstance(item, dict)
        ),
        warnings=tuple(_safe_text(item) for item in data.get("warnings") or ()),
        created_at=_safe_text(data.get("created_at") or ""),
    )


def load_safety_soak_json(path: str | Path) -> SafetySoakReport:
    """Load a prior safety soak report JSON file."""
    return safety_soak_from_json(json.loads(Path(path).expanduser().read_text(encoding="utf-8")))


def write_safety_soak_json(path: str | Path, report: SafetySoakReport) -> Path:
    """Write safety soak JSON."""
    out = Path(path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(safety_soak_to_json(report), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return out


def render_safety_soak_markdown(report: SafetySoakReport) -> str:
    """Render a concise sanitized Markdown safety soak report."""
    lines = [
        "# Saymo Safety Soak Gate",
        "",
        f"profile: {_safe_text(report.profile)}",
        f"status: {report.status}",
        f"items: {int(report.totals.get('items', 0))}",
        f"would speak: {int(report.totals.get('would_speak', 0))}",
        f"blocked automatic playback: {int(report.totals.get('blocked_automatic_playback', 0))}",
        f"unsafe automatic playback: {int(report.totals.get('unsafe_automatic_playback', 0))}",
        f"false handoffs: {int(report.totals.get('false_handoffs', 0))}",
        f"missed handoffs: {int(report.totals.get('missed_handoffs', 0))}",
        f"question noise: {int(report.totals.get('question_noise', 0))}",
        f"unknown speakers: {int(report.totals.get('unknown_speakers', 0))}",
        f"max latency: {_format_number(report.totals.get('max_latency_ms', 0))}ms",
        "",
        "## Safety Violations",
        "",
    ]
    if report.violations:
        lines.extend(
            f"- {violation.source_id}: {violation.rule}: {violation.detail}"
            for violation in report.violations
        )
    else:
        lines.append("- none")

    v19_lines = _render_v19_totals(report.totals)
    if v19_lines:
        lines.extend(["", "## v1.9 Evidence Totals", "", *v19_lines])

    lines.extend(["", "## Baseline Drift", ""])
    if report.drift:
        lines.extend(
            (
                f"- {metric.name}: current={_format_number(metric.current)} "
                f"baseline={_format_number(metric.baseline)} "
                f"delta={_format_number(metric.delta)} "
                f"status={'worse' if metric.worsened else 'ok'}"
            )
            for metric in report.drift
        )
    else:
        lines.append("- no baseline")

    lines.extend(["", "## Sources", ""])
    if report.sources:
        lines.extend(
            (
                f"- {source.source_type}/{source.source_id}: "
                f"status={source.status} would_speak={_format_bool(source.would_speak)}"
            )
            for source in report.sources
        )
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Next Actions",
            "",
            "- inspect the listed source scorecard or rehearsal artifact and its remediation output",
            "- fix safety violations or accepted drift before rerunning this soak",
            "- refresh the baseline only after the current soak is acceptable",
        ]
    )

    lines.extend(["", "## Warnings", ""])
    if report.warnings:
        lines.extend(f"- {warning}" for warning in report.warnings)
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _aggregate_totals(scorecards: tuple[SessionScorecard, ...]) -> dict[str, float | int]:
    max_latency = 0.0
    for scorecard in scorecards:
        if scorecard.playback_metrics.latency_ms:
            max_latency = max(max_latency, max(scorecard.playback_metrics.latency_ms.values()))
    v19_evidence_items = sum(
        1
        for item in scorecards
        if _has_launch_metrics(item) or _has_realtime_metrics(item)
    )
    return {
        "items": len(scorecards),
        "would_speak": sum(1 for item in scorecards if item.trigger_metrics.would_speak is True),
        "blocked_automatic_playback": sum(
            item.playback_metrics.blocked_automatic_playback for item in scorecards
        ),
        "unsafe_automatic_playback": sum(
            item.playback_metrics.unsafe_automatic_playback for item in scorecards
        ),
        "approved_speak_attempts": sum(
            item.playback_metrics.approved_speak_attempts for item in scorecards
        ),
        "false_handoffs": sum(_metric_value(item.trigger_metrics.false_handoffs) for item in scorecards),
        "missed_handoffs": sum(_metric_value(item.trigger_metrics.missed_handoffs) for item in scorecards),
        "question_noise": sum(_metric_value(item.trigger_metrics.question_noise) for item in scorecards),
        "unknown_speakers": sum(
            _metric_value(item.trigger_metrics.speaker_coverage.get("unknown"))
            for item in scorecards
        ),
        "max_latency_ms": max_latency,
        "v19_evidence_items": v19_evidence_items,
        "launch_not_ready": sum(
            1
            for item in scorecards
            if _has_launch_metrics(item) and item.launch_metrics.ready is False
        ),
        "launch_blocks": sum(
            item.launch_metrics.block_count
            for item in scorecards
            if _has_launch_metrics(item)
        ),
        "launch_warnings": sum(
            item.launch_metrics.warn_count
            for item in scorecards
            if _has_launch_metrics(item)
        ),
        "cache_hits": sum(
            item.realtime_metrics.cache_hits
            for item in scorecards
            if _has_realtime_metrics(item)
        ),
        "cache_misses": sum(
            item.realtime_metrics.cache_misses
            for item in scorecards
            if _has_realtime_metrics(item)
        ),
        "cache_missing": sum(
            item.launch_metrics.cache_missing
            for item in scorecards
            if _has_launch_metrics(item)
        ),
        "provider_blocks": sum(_provider_block_total(item) for item in scorecards),
        "fallback_blocks": sum(
            item.realtime_metrics.fallback_blocks
            for item in scorecards
            if _has_realtime_metrics(item)
        ),
        "handbrake_blocks": sum(
            item.realtime_metrics.handbrake_blocks
            for item in scorecards
            if _has_realtime_metrics(item)
        ),
        "realtime_malformed_rows": sum(
            item.realtime_metrics.malformed_rows
            for item in scorecards
            if _has_realtime_metrics(item)
        ),
        "daemon_not_ready": sum(
            1
            for item in scorecards
            if _has_launch_metrics(item) and _daemon_not_ready(item)
        ),
    }


def _violations_for_scorecard(scorecard: SessionScorecard) -> tuple[SafetySoakViolation, ...]:
    violations: list[SafetySoakViolation] = []
    source_id = scorecard.source_id
    if scorecard.playback_metrics.unsafe_automatic_playback:
        violations.append(
            SafetySoakViolation(
                source_id=source_id,
                rule="unsafe_automatic_playback",
                detail=(
                    "automatic playback occurred while a handbrake boundary "
                    f"was active ({scorecard.playback_metrics.unsafe_automatic_playback})"
                ),
            )
        )

    violations.extend(_v19_violations_for_scorecard(scorecard))

    if scorecard.trigger_metrics.would_speak is not True:
        return tuple(violations)

    safety = scorecard.safety_metrics
    if safety.auto_answer_enabled is False:
        violations.append(
            SafetySoakViolation(
                source_id=source_id,
                rule="auto_answer_off",
                detail="would speak while auto-answer is off",
            )
        )
    if safety.manual_takeover is True:
        violations.append(
            SafetySoakViolation(
                source_id=source_id,
                rule="manual_takeover_active",
                detail="would speak while manual takeover is active",
            )
        )
    if safety.hard_disabled is True:
        violations.append(
            SafetySoakViolation(
                source_id=source_id,
                rule="hard_disabled",
                detail="would speak while hard-disable is active",
            )
        )

    gate_text = (
        f"{scorecard.playback_metrics.playback_gate_status} "
        f"{scorecard.playback_metrics.playback_gate_detail}"
    ).casefold()
    if "unapproved" in gate_text or "not approved" in gate_text:
        violations.append(
            SafetySoakViolation(
                source_id=source_id,
                rule="unapproved_draft",
                detail="would speak from an unapproved draft",
            )
        )
    voice_rules = (
        "voice_profile_missing",
        "voice_profile_unapproved",
        "voice_profile_blocked",
        "voice_metadata_missing",
        "voice_metadata_stale",
        "engine_not_voice_clone",
    )
    for rule in voice_rules:
        if rule in gate_text:
            violations.append(
                SafetySoakViolation(
                    source_id=source_id,
                    rule=rule,
                    detail=f"would speak with voice readiness blocker: {rule}",
                )
            )
    return tuple(violations)


def _v19_violations_for_scorecard(scorecard: SessionScorecard) -> list[SafetySoakViolation]:
    violations: list[SafetySoakViolation] = []
    source_id = scorecard.source_id
    launch = scorecard.launch_metrics
    realtime = scorecard.realtime_metrics

    if _has_launch_metrics(scorecard) and launch.ready is False:
        violations.append(
            SafetySoakViolation(
                source_id=source_id,
                rule="launch_not_ready",
                detail=(
                    "launch readiness is not ready "
                    f"(blocks={launch.block_count} warnings={launch.warn_count}"
                    f"{_failed_launch_labels(launch.failed_labels)})"
                ),
            )
        )

    if _has_launch_cache_blocker(scorecard) or _has_realtime_cache_blocker(scorecard):
        violations.append(
            SafetySoakViolation(
                source_id=source_id,
                rule="stale_or_missing_response_cache",
                detail=(
                    "response cache is stale or missing "
                    f"(launch_ready={launch.cache_ready}/{launch.cache_total} "
                    f"launch_missing={launch.cache_missing} "
                    f"realtime_cache_misses={realtime.cache_misses} "
                    f"realtime_cache_blockers={_realtime_cache_blocker_count(realtime)})"
                ),
            )
        )

    if _has_launch_metrics(scorecard) and _daemon_not_ready(scorecard):
        violations.append(
            SafetySoakViolation(
                source_id=source_id,
                rule="call_control_daemon_not_ready",
                detail=(
                    "call-control daemon readiness is explicitly false "
                    f"(ready={_format_bool(launch.daemon_ready)} "
                    f"running={_format_bool(launch.daemon_running)} "
                    f"heartbeat_fresh={_format_bool(launch.daemon_heartbeat_fresh)})"
                ),
            )
        )

    if _provider_block_total(scorecard):
        violations.append(
            SafetySoakViolation(
                source_id=source_id,
                rule="provider_blocked",
                detail=(
                    "provider readiness or realtime provider block failed "
                    f"(launch_ready={_format_bool(launch.provider_ready)} "
                    f"realtime_provider_blocks={realtime.provider_blocks})"
                ),
            )
        )

    if _has_realtime_metrics(scorecard) and realtime.fallback_blocks > 0:
        violations.append(
            SafetySoakViolation(
                source_id=source_id,
                rule="fallback_blocked",
                detail=f"realtime fallback blocks={realtime.fallback_blocks}",
            )
        )

    if _has_realtime_metrics(scorecard) and realtime.handbrake_blocks > 0:
        violations.append(
            SafetySoakViolation(
                source_id=source_id,
                rule="handbrake_blocked",
                detail=f"realtime handbrake blocks={realtime.handbrake_blocks}",
            )
        )
    return violations


def _render_v19_totals(totals: dict[str, float | int]) -> list[str]:
    has_v19_evidence = _metric_value(totals.get("v19_evidence_items")) > 0
    has_nonzero_total = any(
        _metric_value(totals.get(key)) > 0 for key, _label in V19_TOTAL_LINES
    )
    if not has_v19_evidence and not has_nonzero_total:
        return []
    return [
        f"{label}: {_format_number(totals.get(key, 0))}"
        for key, label in V19_TOTAL_LINES
    ]


def _has_launch_metrics(scorecard: SessionScorecard) -> bool:
    return scorecard.launch_metrics.status != "unavailable"


def _has_realtime_metrics(scorecard: SessionScorecard) -> bool:
    return scorecard.realtime_metrics.status != "unavailable"


def _has_launch_cache_blocker(scorecard: SessionScorecard) -> bool:
    if not _has_launch_metrics(scorecard):
        return False
    launch = scorecard.launch_metrics
    return launch.cache_total > 0 and (
        launch.cache_ready < launch.cache_total or launch.cache_missing > 0
    )


def _has_realtime_cache_blocker(scorecard: SessionScorecard) -> bool:
    if not _has_realtime_metrics(scorecard):
        return False
    realtime = scorecard.realtime_metrics
    return realtime.cache_misses > 0 or _realtime_cache_blocker_count(realtime) > 0


def _realtime_cache_blocker_count(realtime: Any) -> int:
    return sum(
        _metric_value(realtime.label_counts.get(label))
        for label in REALTIME_CACHE_BLOCK_LABELS
    )


def _daemon_not_ready(scorecard: SessionScorecard) -> bool:
    launch = scorecard.launch_metrics
    return any(getattr(launch, field, None) is False for field in DAEMON_READY_FIELDS)


def _provider_block_total(scorecard: SessionScorecard) -> int:
    total = 0
    if _has_launch_metrics(scorecard) and scorecard.launch_metrics.provider_ready is False:
        total += 1
    if _has_realtime_metrics(scorecard):
        total += scorecard.realtime_metrics.provider_blocks
    return total


def _failed_launch_labels(labels: tuple[str, ...]) -> str:
    if not labels:
        return ""
    return " failed=" + ", ".join(_safe_text(label) for label in labels)


def _compare_drift(
    totals: dict[str, float | int],
    baseline_totals: dict[str, float | int] | None,
) -> tuple[SafetySoakDriftMetric, ...]:
    if not baseline_totals:
        return ()
    drift = []
    for name in DRIFT_METRICS:
        current = float(totals.get(name, 0) or 0)
        baseline = float(baseline_totals.get(name, 0) or 0)
        delta = current - baseline
        drift.append(
            SafetySoakDriftMetric(
                name=name,
                baseline=baseline,
                current=current,
                delta=delta,
                worsened=delta > 0,
            )
        )
    return tuple(drift)


def _warnings_for_scorecards(scorecards: tuple[SessionScorecard, ...]) -> list[str]:
    warnings: list[str] = []
    for scorecard in scorecards:
        if scorecard.status != "pass":
            warnings.append(f"{scorecard.source_id}: source scorecard status is {scorecard.status}")
        warnings.extend(f"{scorecard.source_id}: {warning}" for warning in scorecard.warnings)
    return warnings


def _metric_value(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _number_value(value: Any) -> float | int:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0
    return int(number) if number.is_integer() else number


def _safe_text(value: Any) -> str:
    return " ".join(str(value or "").split()) or "unknown"


def _format_bool(value: bool | None) -> str:
    if value is None:
        return "unknown"
    return "yes" if value else "no"


def _format_number(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "0"
    return f"{number:g}"
