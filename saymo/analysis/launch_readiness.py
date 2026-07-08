"""Shared contracts for call launch readiness checks."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal


Severity = Literal["block", "warn", "info"]

_PRIVATE_SENTINELS = (
    "PRIVATE_DAILY_NOTE",
    "PRIVATE_TRANSCRIPT",
    "PRIVATE_GENERATED_ANSWER",
    "SECRET_TOKEN",
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
    """Collect the Phase 36.01 contract-only launch-readiness checks."""
    meeting = config.get_meeting(profile)
    provider = provider_name or (meeting.provider if meeting else "glip")
    checks: list[LaunchReadinessCheck] = [
        LaunchReadinessCheck(
            key="profile",
            label="profile",
            severity="info",
            ok=True,
            detail=f"profile={profile}",
            metadata={
                "profile": profile,
                "meeting_configured": meeting is not None,
                "prepare": bool(prepare),
            },
        ),
        LaunchReadinessCheck(
            key="provider_basic_scope",
            label="provider basic scope",
            severity="info",
            ok=True,
            detail=f"provider={provider}; deferred_to_phase=37",
            metadata={
                "provider": provider,
                "deferred_to_phase": "37",
            },
        ),
    ]
    checks.extend(
        _collect_injected_checks(
            config,
            profile=profile,
            provider_name=provider,
            prepare=prepare,
        )
    )
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
    return "\n".join(lines)


def _collect_injected_checks(
    config,
    *,
    profile: str,
    provider_name: str,
    prepare: bool,
) -> tuple[LaunchReadinessCheck, ...]:
    """Collect launch-source checks without changing the command wrapper."""
    from saymo.analysis.launch_sources import collect_daily_note_checks

    return collect_daily_note_checks(
        config,
        profile,
        provider_name=provider_name,
        prepare=prepare,
    )


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
