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


@dataclass(frozen=True)
class RealtimePlaybackBlock:
    """Runtime reason that automatic realtime playback must not start."""

    label: str
    reason: str
    detail: str = ""


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


def automatic_handbrake_block(
    auto_answer_enabled,
    manual_takeover,
    hard_disabled,
) -> RealtimePlaybackBlock | None:
    """Return a stable runtime handbrake block for automatic answers."""
    if manual_takeover.is_set():
        return RealtimePlaybackBlock(
            label="handbrake-blocked",
            reason="manual-takeover",
            detail="manual takeover active",
        )
    if hard_disabled.is_set():
        return RealtimePlaybackBlock(
            label="handbrake-blocked",
            reason="hard-disabled",
            detail="automatic answers hard disabled",
        )
    if not auto_answer_enabled.is_set():
        return RealtimePlaybackBlock(
            label="handbrake-blocked",
            reason="auto-answer-off",
            detail="auto-answer disabled",
        )
    return None


def provider_playback_block(provider) -> RealtimePlaybackBlock | None:
    """Return a stable provider readiness block immediately before playback."""
    try:
        status = provider.check_ready()
    except Exception as e:
        return RealtimePlaybackBlock(
            label="provider-blocked",
            reason="provider-check-error",
            detail=type(e).__name__,
        )
    if not getattr(status, "meeting_found", False):
        return RealtimePlaybackBlock(
            label="provider-blocked",
            reason="meeting-not-found",
            detail=str(getattr(provider, "name", "") or "provider"),
        )
    return None
