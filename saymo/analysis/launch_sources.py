"""Source and prepared-audio launch-readiness checks."""

from __future__ import annotations

from saymo.analysis.launch_readiness import LaunchReadinessCheck
from saymo.obsidian.daily_notes import (
    daily_note_path,
    ensure_daily_note,
    inspect_standup_source,
)

SOURCE_PLACEHOLDER_ONLY = "placeholder_only"


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
    action = f"Run saymo call-ready -p {profile} --provider {provider_name} --prepare"
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
        action="" if readiness.exists else action,
        rerun=rerun,
        metadata=metadata,
    )
    source_ready = LaunchReadinessCheck(
        key="daily_note_source_ready",
        label="daily note source ready",
        severity="block",
        ok=readiness.exists and readiness.usable_line_count > 0,
        detail=readiness.reason,
        action="" if readiness.usable_line_count > 0 else action,
        rerun=rerun,
        metadata=metadata,
    )
    return (present, source_ready)
