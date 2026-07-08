"""Actionable remediation hints for local diagnostics."""

from __future__ import annotations

import re
import shlex
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from saymo.analysis.rehearsal import RehearsalArtifact
from saymo.analysis.session_scorecard import SessionScorecard


@dataclass(frozen=True)
class RemediationHint:
    """One concrete next action for a failed or warning diagnostic."""

    category: str
    title: str
    detail: str
    action: str
    rerun: str


def render_remediation_hints(hints: Iterable[RemediationHint]) -> str:
    """Render compact sanitized remediation output."""
    items = tuple(hints)
    lines = ["remediation:"]
    if not items:
        lines.append("- none")
        return "\n".join(lines)
    for hint in items:
        lines.append(f"- [{_safe_label(hint.category)}] {_safe_label(hint.title)}")
        if hint.detail:
            lines.append(f"  why: {_sanitize(hint.detail)}")
        if hint.action:
            lines.append(f"  action: {_sanitize(hint.action)}")
        if hint.rerun:
            lines.append(f"  rerun: {_sanitize_rerun(hint.rerun)}")
    return "\n".join(lines)


def hints_from_preflight_checks(profile: str, checks: Iterable[Any]) -> list[RemediationHint]:
    """Return remediation hints for failed/warning auto-preflight checks."""
    hints: list[RemediationHint] = []
    rerun = f"saymo auto-preflight -p {_safe_profile(profile)}"
    for check in checks:
        ok = bool(getattr(check, "ok", False))
        if ok:
            continue
        name = str(getattr(check, "name", "") or "")
        detail = str(getattr(check, "detail", "") or "")
        hints.append(_hint_for_check(name, detail, rerun=rerun))
    return _dedupe(hints)


def hints_from_launch_readiness(report: Any) -> list[RemediationHint]:
    """Return remediation hints for failed/warning call-ready checks."""
    hints: list[RemediationHint] = []
    for check in getattr(report, "checks", ()) or ():
        severity = str(getattr(check, "severity", "") or "")
        ok = bool(getattr(check, "ok", False))
        if ok and severity != "warn":
            continue
        metadata = dict(getattr(check, "metadata", {}) or {})
        key = str(getattr(check, "key", "") or "")
        category = str(metadata.get("category") or _launch_category_for_check(key))
        hints.append(
            RemediationHint(
                category=category,
                title=str(getattr(check, "label", "") or key),
                detail=str(getattr(check, "detail", "") or ""),
                action=str(getattr(check, "action", "") or ""),
                rerun=str(getattr(check, "rerun", "") or ""),
            )
        )
    return _dedupe(hints)


def hints_from_rehearsal(artifact: RehearsalArtifact) -> list[RemediationHint]:
    """Return remediation hints for a rehearsal artifact."""
    rerun = f"saymo rehearsal -p {_safe_profile(artifact.profile)}"
    hints: list[RemediationHint] = []
    for check in artifact.checks:
        if check.status == "pass":
            continue
        name = check.name.removeprefix("preflight: ").strip()
        hints.append(_hint_for_check(name, check.detail, rerun=rerun))
    blocked = str(artifact.decision.blocked_reason or "")
    if blocked and "confirmation required" in blocked.lower():
        hints.append(
            RemediationHint(
                category="config",
                title="Review confirmation gate",
                detail=blocked,
                action="Keep confirmation on for safety or update safety.require_confirmation intentionally.",
                rerun=rerun,
            )
        )
    if blocked and "handbrake" in blocked.lower():
        hints.append(
            RemediationHint(
                category="retest",
                title="Reset handbrake state",
                detail=blocked,
                action="Turn auto-answer back on only if you are ready for Saymo to speak.",
                rerun=rerun,
            )
        )
    return _dedupe(hints)


def hints_from_scorecard(scorecard: SessionScorecard) -> list[RemediationHint]:
    """Return remediation hints for a session scorecard."""
    profile = _safe_profile(scorecard.profile)
    source_ref = _scorecard_source_ref(scorecard)
    scorecard_rerun = f"saymo session-scorecard -p {profile} {source_ref}".strip()
    trigger = scorecard.trigger_metrics
    playback = scorecard.playback_metrics
    safety = scorecard.safety_metrics
    hints: list[RemediationHint] = []

    if (trigger.false_handoffs or 0) or (trigger.missed_handoffs or 0):
        hints.append(
            RemediationHint(
                category="review-labeling",
                title="Review handoff labels",
                detail=(
                    f"false_handoffs={trigger.false_handoffs or 0} "
                    f"missed_handoffs={trigger.missed_handoffs or 0}"
                ),
                action=(
                    f"Run saymo trigger-samples queue -p {profile} --session "
                    f"{_safe_label(scorecard.source_id)} and correct accepted/rejected labels."
                ),
                rerun=scorecard_rerun,
            )
        )
    unknown = (trigger.speaker_coverage or {}).get("unknown")
    unlabeled = (trigger.review_coverage or {}).get("unlabeled")
    if unknown or unlabeled or trigger.classifier_readiness == "not_ready":
        hints.append(
            RemediationHint(
                category="review-labeling",
                title="Improve speaker labels",
                detail=(
                    f"unknown_speakers={unknown or 0} unlabeled_decisions={unlabeled or 0} "
                    f"readiness={trigger.classifier_readiness}"
                ),
                action=(
                    f"Run saymo trigger-samples queue -p {profile} --session "
                    f"{_safe_label(scorecard.source_id)} and label speaker/decision rows."
                ),
                rerun=scorecard_rerun,
            )
        )
    if playback.blocked_automatic_playback:
        hints.append(
            RemediationHint(
                category="retest",
                title="Inspect blocked automatic playback",
                detail=f"blocked_automatic_playback={playback.blocked_automatic_playback}",
                action="Confirm the block was expected from the handbrake or approval gate.",
                rerun=scorecard_rerun,
            )
        )
    if safety.hard_disabled or safety.manual_takeover:
        hints.append(
            RemediationHint(
                category="retest",
                title="Recheck live-control state",
                detail="manual takeover or hard-disable was active",
                action=f"Run saymo rehearsal -p {profile} after resetting live-control state.",
                rerun=scorecard_rerun,
            )
        )
    for warning in scorecard.warnings:
        hints.append(_hint_for_warning(warning, rerun=scorecard_rerun))
    return _dedupe(hints)


def hints_from_safety_soak(report: Any) -> list[RemediationHint]:
    """Return remediation hints for a safety soak gate report."""
    profile = _safe_profile(getattr(report, "profile", "personal"))
    rerun = f"saymo safety-soak -p {profile}"
    hints: list[RemediationHint] = []
    for violation in getattr(report, "violations", ()) or ():
        hints.append(
            RemediationHint(
                category="retest",
                title="Resolve safety soak violation",
                detail=f"{getattr(violation, 'source_id', 'unknown')}: {getattr(violation, 'rule', 'unknown')}",
                action=(
                    "Inspect the listed rehearsal or scorecard remediation output, "
                    "then rerun safety-soak with the same inputs."
                ),
                rerun=rerun,
            )
        )
    for metric in getattr(report, "drift", ()) or ():
        if not bool(getattr(metric, "worsened", False)):
            continue
        hints.append(
            RemediationHint(
                category="review-labeling",
                title="Fix worsened soak drift",
                detail=(
                    f"{getattr(metric, 'name', 'unknown')} delta="
                    f"{getattr(metric, 'delta', 'unknown')}"
                ),
                action="Review the source scorecards before accepting a new baseline.",
                rerun=rerun,
            )
        )
    for warning in getattr(report, "warnings", ()) or ():
        hints.append(_hint_for_warning(str(warning), rerun=rerun))
    return _dedupe(hints)


def hints_from_hotkey_doctor(report: Any, *, probe: bool) -> list[RemediationHint]:
    """Return remediation hints for a hotkey doctor report."""
    profile = _safe_profile(getattr(report, "profile", "personal"))
    suffix = "" if probe else " --no-probe"
    rerun = f"saymo hotkey-doctor -p {profile}{suffix}"
    bindings = dict(getattr(report, "bindings", {}) or {})
    missing_primary = [
        action
        for action in ("toggle_auto_answer", "speak", "stop", "takeover")
        if action not in bindings
    ]
    hints: list[RemediationHint] = []
    if missing_primary:
        hints.append(
            RemediationHint(
                category="config",
                title="Configure global hotkeys",
                detail="missing primary actions: " + ", ".join(missing_primary),
                action="Set safety.hotkey_toggle, hotkey_speak, hotkey_stop, and hotkey_takeover.",
                rerun=rerun,
            )
        )
    if not bool(getattr(report, "process_running", False)):
        hints.append(
            RemediationHint(
                category="retest",
                title="Start Saymo auto listener",
                detail="global hotkeys work only after the listener is running",
                action=f"Start saymo auto -p {profile} before relying on call hotkeys.",
                rerun=rerun,
            )
        )
    status = str(getattr(report, "registration_status", "") or "")
    if status not in {"ok", "skipped"}:
        hints.append(
            RemediationHint(
                category="macos-permission",
                title="Allow Accessibility permission",
                detail=str(getattr(report, "registration_detail", "") or status),
                action="Allow the terminal app running Saymo in macOS Accessibility settings.",
                rerun=rerun,
            )
        )
    return _dedupe(hints)


def hint_for_takeover_failure(
    profile: str,
    reason: str,
    *,
    provider: str = "",
) -> RemediationHint:
    """Return one remediation hint for a takeover-check failure."""
    lower = reason.lower()
    rerun = f"saymo takeover-check -p {_safe_profile(profile)}"
    if "recording_device" in lower or "recording mic" in lower:
        return RemediationHint(
            category="config",
            title="Configure recording microphone",
            detail=reason,
            action="Set audio.recording_device to the real microphone you will use during takeover.",
            rerun=rerun,
        )
    if "tab not found" in lower or "meeting" in lower:
        return RemediationHint(
            category="retest",
            title="Open provider meeting tab",
            detail=reason,
            action=f"Open the {provider or 'provider'} meeting in Chrome, then rerun takeover-check.",
            rerun=rerun,
        )
    return RemediationHint(
        category="audio-device",
        title="Fix microphone switching",
        detail=reason,
        action="Verify both the real microphone and BlackHole are visible to the call provider.",
        rerun=rerun,
    )


def _hint_for_check(name: str, detail: str, *, rerun: str) -> RemediationHint:
    lower = name.lower()
    if "capture" in lower:
        return RemediationHint("audio-device", "Fix capture input", detail, "Select a valid capture input device.", rerun)
    if "playback" in lower or "provider output" in lower:
        return RemediationHint("audio-device", "Fix playback routing", detail, "Select BlackHole/output devices visible to macOS.", rerun)
    if "prepared standup" in lower or "response cache" in lower:
        return RemediationHint("source-data", "Prepare response cache", detail, "Run saymo prepare for this profile or accept prepared-standup fallback.", rerun)
    if "provider tab" in lower:
        return RemediationHint("retest", "Open provider meeting tab", detail, "Open the meeting in Chrome and rerun the check.", rerun)
    if "profile trigger" in lower:
        return RemediationHint("config", "Configure trigger phrases", detail, "Add trigger_phrases for this meeting profile.", rerun)
    if "hotkey" in lower:
        return RemediationHint("config", "Configure global hotkeys", detail, "Set the primary safety hotkeys in config.yaml.", rerun)
    return RemediationHint("retest", f"Recheck {name}", detail, "Fix the reported issue and rerun the check.", rerun)


def _launch_category_for_check(key: str) -> str:
    if key in {"provider_meeting_tab", "provider_capabilities"}:
        return "provider"
    if key in {
        "capture_input_device",
        "playback_output_device",
        "provider_output_blackhole",
        "capture_route_blackhole",
        "recording_microphone_input",
    }:
        return "audio-device"
    if key in {
        "hotkey_accessibility_permission",
        "chrome_automation_permission",
        "microphone_capture_permission",
        "audio_routing_permission",
    }:
        return "macos-permission"
    if key.startswith("daily_note_") or key == "prepared_standup_audio":
        return "source-data"
    if key == "response_cache_coverage":
        return "source-data"
    if key == "cloned_voice_metadata":
        return "voice-cache"
    return "retest"


def _hint_for_warning(warning: str, *, rerun: str) -> RemediationHint:
    lower = warning.lower()
    if "audit" in lower:
        return RemediationHint("retest", "Regenerate live-control audit", warning, "Run a fresh rehearsal or live-control action so audit evidence exists.", rerun)
    if "classifier readiness" in lower:
        return RemediationHint("review-labeling", "Improve classifier readiness", warning, "Add accepted/rejected labels for this session.", rerun)
    return RemediationHint("retest", "Review scorecard warning", warning, "Inspect the warning and rerun the scorecard after fixing it.", rerun)


def _scorecard_source_ref(scorecard: SessionScorecard) -> str:
    if scorecard.source_type == "rehearsal":
        source = scorecard.source_path or f"~/.saymo/rehearsals/{_safe_profile(scorecard.profile)}/{_safe_label(scorecard.source_id)}"
        return f"--rehearsal {shlex.quote(source)}"
    return f"--session {_safe_label(scorecard.source_id)}"


def _dedupe(hints: Iterable[RemediationHint]) -> list[RemediationHint]:
    seen: set[tuple[str, str, str]] = set()
    result: list[RemediationHint] = []
    for hint in hints:
        key = (hint.category, hint.title, hint.rerun)
        if key in seen:
            continue
        seen.add(key)
        result.append(hint)
    return result


def _sanitize(value: Any) -> str:
    text = _safe_label(value)
    text = re.sub(r"\b[A-Z0-9_]*SECRET[A-Z0-9_=-]*\b", "[redacted]", text, flags=re.IGNORECASE)
    text = re.sub(r"\b[A-Z0-9_]*TOKEN[A-Z0-9_=-]*\b", "[redacted]", text, flags=re.IGNORECASE)
    return text


def _sanitize_rerun(value: Any) -> str:
    text = " ".join(str(value or "").split())
    text = re.sub(r"\b[A-Z0-9_]*SECRET[A-Z0-9_=-]*\b", "[redacted]", text, flags=re.IGNORECASE)
    text = re.sub(r"\b[A-Z0-9_]*TOKEN[A-Z0-9_=-]*\b", "[redacted]", text, flags=re.IGNORECASE)
    return text


def _safe_label(value: Any) -> str:
    text = " ".join(str(value or "").split())
    text = re.sub(r"(?:[A-Za-z]:)?/(?:[^\s/]+/)*[^\s/]+", lambda m: Path(m.group()).name, text)
    return text or "unknown"


def _safe_profile(profile: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in profile)
    return safe or "default"
