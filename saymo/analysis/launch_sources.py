"""Source and prepared-audio launch-readiness checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from saymo.analysis.launch_readiness import LaunchReadinessCheck
from saymo.obsidian.daily_notes import (
    daily_note_path,
    ensure_daily_note,
    inspect_standup_source,
)

SOURCE_PLACEHOLDER_ONLY = "placeholder_only"


@dataclass(frozen=True)
class PreparedAudioStatus:
    """Privacy-safe readiness summary for prepared standup audio."""

    path: Path
    ok: bool
    reason: str
    metadata: dict[str, str | int | bool]


def collect_daily_note_checks(
    config,
    profile: str,
    *,
    provider_name: str,
    prepare: bool,
) -> tuple[LaunchReadinessCheck, ...]:
    """Collect daily-note presence and usable-source readiness checks."""
    note_path = daily_note_path(config.obsidian)
    if prepare and not note_path.exists():
        note_path = ensure_daily_note(config.obsidian)

    readiness = inspect_standup_source(note_path)
    create_note_action = (
        f"Run saymo call-ready -p {profile} --provider {provider_name} --prepare"
    )
    source_action = (
        f"Add usable standup content to {readiness.path}, "
        f"then run saymo prepare -p {profile}"
    )
    rerun = f"saymo call-ready -p {profile} --provider {provider_name}"
    metadata = {
        "note_path": str(readiness.path),
        "exists": readiness.exists,
        "line_count": readiness.line_count,
        "usable_line_count": readiness.usable_line_count,
        "source_sha256": readiness.source_sha256,
    }

    present = LaunchReadinessCheck(
        key="daily_note_present",
        label="daily note present",
        severity="block",
        ok=readiness.exists,
        detail="ready" if readiness.exists else "missing",
        action="" if readiness.exists else create_note_action,
        rerun=rerun,
        metadata=metadata,
    )
    source_ready = LaunchReadinessCheck(
        key="daily_note_source_ready",
        label="daily note source ready",
        severity="block",
        ok=readiness.exists and readiness.usable_line_count > 0,
        detail=readiness.reason,
        action="" if readiness.usable_line_count > 0 else source_action,
        rerun=rerun,
        metadata=metadata,
    )
    return (present, source_ready)


def prepared_audio_status(
    config,
    *,
    profile: str,
    team_mode: bool,
    source_sha256: str,
) -> PreparedAudioStatus:
    """Check prepared standup WAV freshness without synthesizing audio."""
    from saymo.analysis.cache_metadata import (
        build_voice_cache_metadata,
        check_voice_cache_metadata,
    )
    from saymo.commands import _get_cached_audio_path
    from saymo.tts.selector import resolve_voice_selector

    audio_path = _get_cached_audio_path(team=team_mode)
    live_decision = resolve_voice_selector(config, purpose="live_call")
    expected = build_voice_cache_metadata(
        config,
        purpose="prepare",
        source_kind=config.speech.source,
        source_profile=profile,
        source_sha256=source_sha256,
    )
    metadata_check = check_voice_cache_metadata(audio_path, expected)

    reason = ""
    ok = metadata_check.valid and live_decision.allowed
    if not metadata_check.valid:
        reason = metadata_check.blocked_reason
    elif not live_decision.allowed:
        reason = live_decision.blocked_reason

    return PreparedAudioStatus(
        path=audio_path,
        ok=ok,
        reason=reason,
        metadata={
            "audio_path": str(audio_path),
            "team_mode": team_mode,
            "source_kind": config.speech.source,
            "source_profile": profile,
            "source_sha256": source_sha256,
            "stale_reason": reason,
            "selected_engine": expected.selected_engine,
            "voice_profile": expected.profile,
            "profile_approved": expected.profile_approved,
        },
    )


def collect_prepared_audio_check(
    config,
    profile: str,
    *,
    provider_name: str,
    team_mode: bool,
    source_sha256: str,
) -> LaunchReadinessCheck:
    """Collect the blocking prepared standup audio readiness check."""
    status = prepared_audio_status(
        config,
        profile=profile,
        team_mode=team_mode,
        source_sha256=source_sha256,
    )
    action = f"Run saymo prepare -p {profile}"
    return LaunchReadinessCheck(
        key="prepared_standup_audio",
        label="prepared standup audio",
        severity="block",
        ok=status.ok,
        detail="ready" if status.ok else status.reason,
        action="" if status.ok else action,
        rerun=f"saymo call-ready -p {profile} --provider {provider_name}",
        metadata=status.metadata,
    )
