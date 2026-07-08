"""Shared contracts for call launch readiness checks."""

from __future__ import annotations

import re
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


Severity = Literal["block", "warn", "info"]

_PRIVATE_SENTINELS = (
    "PRIVATE_DAILY_NOTE",
    "PRIVATE_TRANSCRIPT",
    "PRIVATE_GENERATED_ANSWER",
    "SECRET_TOKEN",
)

_LAUNCH_CHECK_ORDER = (
    "daily_note_present",
    "daily_note_source_ready",
    "prepared_standup_audio",
    "response_cache_coverage",
    "cloned_voice_metadata",
    "provider_meeting_tab",
    "capture_input_device",
    "playback_output_device",
    "provider_output_blackhole",
    "capture_route_blackhole",
    "recording_microphone_input",
    "provider_capabilities",
)


@dataclass(frozen=True)
class LaunchReadinessCheck:
    """One structured launch-readiness check."""

    key: str
    label: str
    severity: Severity
    ok: bool
    detail: str = ""
    action: str = ""
    rerun: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": _sanitize_text(self.key),
            "label": _sanitize_text(self.label),
            "severity": self.severity,
            "ok": bool(self.ok),
            "detail": _sanitize_text(self.detail),
            "action": _sanitize_text(self.action),
            "rerun": _sanitize_text(self.rerun),
            "metadata": _sanitize_value(self.metadata),
        }


@dataclass(frozen=True)
class LaunchReadinessReport:
    """Launch-readiness report for one profile/provider pair."""

    profile: str
    provider: str
    checks: tuple[LaunchReadinessCheck, ...]

    @property
    def ready(self) -> bool:
        return all(check.ok or check.severity != "block" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        checks = tuple(self.checks)
        return {
            "profile": _sanitize_text(self.profile),
            "provider": _sanitize_text(self.provider),
            "ready": self.ready,
            "check_count": len(checks),
            "ready_count": sum(1 for check in checks if check.ok),
            "block_count": sum(
                1 for check in checks if check.severity == "block" and not check.ok
            ),
            "warn_count": sum(
                1 for check in checks if check.severity == "warn" and not check.ok
            ),
            "checks": [check.to_dict() for check in checks],
        }


def collect_launch_readiness(
    config,
    *,
    profile: str,
    provider_name: str | None,
    prepare: bool = False,
) -> LaunchReadinessReport:
    """Collect the full Phase 36 launch-readiness checks."""
    meeting = config.get_meeting(profile)
    provider = provider_name or (meeting.provider if meeting else "glip")
    checks = list(_collect_phase36_checks(
        config,
        profile=profile,
        provider_name=provider,
        prepare=prepare,
    ))
    return LaunchReadinessReport(
        profile=profile,
        provider=provider,
        checks=tuple(checks),
    )


def render_launch_readiness(report: LaunchReadinessReport) -> str:
    """Render concise human-readable launch-readiness output."""
    lines = [f"call-ready: {'ready' if report.ready else 'not ready'}"]
    for severity in ("block", "warn", "info"):
        grouped = [check for check in report.checks if check.severity == severity]
        if not grouped:
            continue
        lines.append(f"{severity}:")
        for check in grouped:
            status = "ok" if check.ok else "not ok"
            detail = _sanitize_text(check.detail)
            suffix = f": {detail}" if detail else ""
            lines.append(f"- {check.key}: {status}{suffix}")
            if check.action:
                lines.append(f"  action: {_sanitize_text(check.action)}")
            if check.rerun:
                lines.append(f"  rerun: {_sanitize_text(check.rerun)}")
    lines.extend(render_grouped_launch_remediation(report).splitlines())
    return "\n".join(lines)


def render_grouped_launch_remediation(report: LaunchReadinessReport) -> str:
    """Render failed and warning launch checks as grouped remediation."""
    from saymo.analysis.remediation import hints_from_launch_readiness

    relevant_checks = [
        check
        for check in report.checks
        if not check.ok or check.severity == "warn"
    ]
    hints = hints_from_launch_readiness(report)
    grouped: dict[Severity, list[Any]] = {
        "block": [],
        "warn": [],
        "info": [],
    }
    for check, hint in zip(relevant_checks, hints, strict=False):
        grouped[check.severity].append(hint)

    lines = ["remediation:"]
    for severity in ("block", "warn", "info"):
        lines.append(f"{severity}:")
        items = grouped[severity]
        if not items:
            lines.append("- none")
            continue
        for hint in items:
            lines.append(
                f"- [{_sanitize_text(hint.category)}] {_sanitize_text(hint.title)}"
            )
            if hint.detail:
                lines.append(f"  why: {_sanitize_text(hint.detail)}")
            if hint.action:
                lines.append(f"  action: {_sanitize_text(hint.action)}")
            if hint.rerun:
                lines.append(f"  rerun: {_sanitize_text(hint.rerun)}")
    return "\n".join(lines)


def write_launch_readiness_artifact(
    report: LaunchReadinessReport,
    output_path: Path,
) -> Path:
    """Write a sanitized launch-readiness artifact as JSON."""
    output_path = Path(output_path)
    output_path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def _collect_phase36_checks(
    config,
    *,
    profile: str,
    provider_name: str,
    prepare: bool,
) -> tuple[LaunchReadinessCheck, ...]:
    """Collect launch checks in the operator-facing order."""
    from saymo.analysis.launch_cache import (
        collect_response_cache_check,
        collect_voice_metadata_check,
    )
    from saymo.analysis.provider_audio_readiness import collect_provider_audio_checks
    from saymo.analysis.launch_sources import (
        collect_daily_note_checks,
        collect_prepared_audio_check,
    )

    checks = list(collect_daily_note_checks(
        config,
        profile,
        provider_name=provider_name,
        prepare=prepare,
    ))
    source_sha256 = ""
    for check in checks:
        if check.key == "daily_note_source_ready":
            source_sha256 = str(check.metadata.get("source_sha256") or "")
            break
    meeting = config.get_meeting(profile)
    team_mode = bool(meeting.team) if meeting else False
    checks.append(
        collect_prepared_audio_check(
            config,
            profile,
            provider_name=provider_name,
            team_mode=team_mode,
            source_sha256=source_sha256,
        )
    )
    checks.append(
        collect_response_cache_check(
            config,
            profile=profile,
            provider_name=provider_name,
        )
    )
    checks.append(
        collect_voice_metadata_check(
            config,
            profile=profile,
            provider_name=provider_name,
        )
    )
    checks.extend(
        collect_provider_audio_checks(
            config,
            profile=profile,
            provider_name=provider_name,
        )
    )
    return tuple(checks)


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return _sanitize_text(value)
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int | float):
        return value
    if isinstance(value, dict):
        return {
            _sanitize_text(str(key)): _sanitize_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize_value(item) for item in value]
    return _sanitize_text(str(value))


def _sanitize_text(value: Any) -> str:
    text = " ".join(str(value or "").split())
    for sentinel in _PRIVATE_SENTINELS:
        text = text.replace(sentinel, "[redacted]")
    text = re.sub(
        r"\b[A-Z0-9_]*SECRET[A-Z0-9_=-]*\b",
        "[redacted]",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b[A-Z0-9_]*TOKEN[A-Z0-9_=-]*\b",
        "[redacted]",
        text,
        flags=re.IGNORECASE,
    )
    return text
