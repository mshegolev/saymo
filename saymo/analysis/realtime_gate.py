"""Fail-closed realtime startup gate over shared launch readiness."""

from __future__ import annotations

from dataclasses import dataclass

from saymo.analysis.launch_readiness import (
    LaunchReadinessReport,
    collect_launch_readiness,
    render_launch_readiness,
)


@dataclass(frozen=True)
class RealtimeLaunchGate:
    """Realtime startup decision derived from LaunchReadinessReport."""

    profile: str
    provider: str
    allowed: bool
    reason: str
    report: LaunchReadinessReport


def evaluate_realtime_launch_gate(
    config,
    *,
    profile: str,
    provider_name: str | None = None,
) -> RealtimeLaunchGate:
    """Evaluate whether realtime mode may start for one profile/provider."""
    meeting = config.get_meeting(profile)
    provider = provider_name or (meeting.provider if meeting else "glip")
    report = collect_launch_readiness(
        config,
        profile=profile,
        provider_name=provider,
        prepare=False,
    )
    allowed = report.ready
    return RealtimeLaunchGate(
        profile=profile,
        provider=report.provider or provider,
        allowed=allowed,
        reason="launch-readiness-ready" if allowed else "launch-readiness-blocked",
        report=report,
    )


def render_realtime_launch_block(gate: RealtimeLaunchGate) -> str:
    """Render blocked realtime startup with call-ready remediation."""
    rendered = render_launch_readiness(gate.report)
    return f"{rendered}\nrealtime: blocked ({gate.reason})"
