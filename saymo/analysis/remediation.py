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
    scorecard_rerun = _scorecard_rerun(scorecard, profile=profile, source_ref=source_ref)
    trigger = scorecard.trigger_metrics
    playback = scorecard.playback_metrics
    safety = scorecard.safety_metrics
    hints: list[RemediationHint] = []
    hints.extend(_v19_scorecard_hints(scorecard, scorecard_rerun=scorecard_rerun))

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
    hints: list[RemediationHint] = []
    for violation in getattr(report, "violations", ()) or ():
        rule = str(getattr(violation, "rule", "unknown") or "unknown")
        if _is_v19_soak_rule(rule):
            hints.append(_v19_safety_soak_hint(profile, violation, report))
            continue
        rerun = f"saymo safety-soak -p {profile}"
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
                rerun=f"saymo safety-soak -p {profile}",
            )
        )
    for warning in getattr(report, "warnings", ()) or ():
        hints.append(_hint_for_warning(str(warning), rerun=f"saymo safety-soak -p {profile}"))
    return _dedupe(hints)


def _v19_scorecard_hints(
    scorecard: SessionScorecard,
    *,
    scorecard_rerun: str,
) -> list[RemediationHint]:
    hints: list[RemediationHint] = []
    launch = scorecard.launch_metrics
    realtime = scorecard.realtime_metrics

    if launch.status != "unavailable":
        if launch.status == "loaded":
            failed_labels = ", ".join(launch.failed_labels) or "none"
            categories = _format_counts(launch.blocker_categories)
            log_paths = ", ".join(launch.log_paths) or "none"
            detail = (
                f"failed_labels={failed_labels} categories={categories} "
                f"artifact_path={launch.artifact_path or 'unknown'} "
                f"log_paths={log_paths} blocks={launch.block_count} "
                f"warnings={launch.warn_count}"
            )
            action = "Fix launch blockers, then rerun call-ready, call-control, and scorecard checks."
            rerun_commands = _launch_rerun_chain(launch.rerun_commands, scorecard_rerun)
            for category in launch.blocker_categories or {"retest": launch.block_count}:
                hints.append(
                    RemediationHint(
                        category=str(category),
                        title=f"Fix {category} launch evidence",
                        detail=detail,
                        action=action,
                        rerun=rerun_commands,
                    )
                )
        else:
            hints.append(
                RemediationHint(
                    category="source-data",
                    title="Load launch evidence artifact",
                    detail=(
                        f"status={launch.status} "
                        f"artifact_path={launch.artifact_path or 'unknown'}"
                    ),
                    action="Regenerate the call-ready JSON artifact before scoring the session.",
                    rerun=scorecard_rerun,
                )
            )

    if realtime.status != "unavailable":
        if realtime.status == "loaded":
            detail = (
                f"artifact_path={realtime.artifact_path or 'unknown'} "
                f"cache_hits={realtime.cache_hits} cache_misses={realtime.cache_misses} "
                f"provider_blocks={realtime.provider_blocks} "
                f"fallback_blocks={realtime.fallback_blocks} "
                f"handbrake_blocks={realtime.handbrake_blocks} "
                f"playback_attempts={realtime.playback_attempts} "
                f"malformed_rows={realtime.malformed_rows}"
            )
            if (
                realtime.cache_misses
                or realtime.provider_blocks
                or realtime.fallback_blocks
                or realtime.handbrake_blocks
                or realtime.malformed_rows
            ):
                hints.append(
                    RemediationHint(
                        category="retest",
                        title="Review realtime evidence blockers",
                        detail=detail,
                        action="Inspect sanitized realtime labels and rerun the scorecard after fixing blockers.",
                        rerun=scorecard_rerun,
                    )
                )
        else:
            hints.append(
                RemediationHint(
                    category="retest",
                    title="Load realtime evidence artifact",
                    detail=(
                        f"status={realtime.status} "
                        f"artifact_path={realtime.artifact_path or 'unknown'}"
                    ),
                    action="Regenerate realtime decision JSONL evidence before scoring the session.",
                    rerun=scorecard_rerun,
                )
            )
    return hints


def _v19_safety_soak_hint(profile: str, violation: Any, report: Any) -> RemediationHint:
    rule = str(getattr(violation, "rule", "unknown") or "unknown")
    detail_text = str(getattr(violation, "detail", "") or "")
    source_id = str(getattr(violation, "source_id", "") or "unknown")
    scorecard_json = _scorecard_json_ref(source_id)
    launch_json = _field_from_detail(detail_text, "launch_json") or "<launch.json>"
    realtime_jsonl = _field_from_detail(detail_text, "realtime_jsonl") or "<realtime.jsonl>"
    count = _v19_violation_count(rule, report)
    source_label = _source_label(source_id)
    detail = f"source={source_label} rule={rule}"
    if count:
        detail += f" count={count}"
    action = (
        "Rerun scorecard first: "
        f"saymo session-scorecard -p {profile} --rehearsal <artifact> "
        f"--launch-json {launch_json} --realtime-jsonl {realtime_jsonl} "
        f"--json-output {scorecard_json}"
    )
    return RemediationHint(
        category=_v19_rule_category(rule),
        title=f"Resolve {rule}",
        detail=detail,
        action=action,
        rerun=f"saymo safety-soak -p {profile} --scorecard-json {scorecard_json}",
    )


def _is_v19_soak_rule(rule: str) -> bool:
    return rule in {
        "launch_not_ready",
        "stale_or_missing_response_cache",
        "call_control_daemon_not_ready",
        "provider_blocked",
        "fallback_blocked",
        "handbrake_blocked",
    }


def _v19_rule_category(rule: str) -> str:
    if rule in {"launch_not_ready", "stale_or_missing_response_cache"}:
        return "source-data"
    if rule == "call_control_daemon_not_ready":
        return "call-control"
    if rule == "provider_blocked":
        return "provider"
    return "retest"


def _v19_violation_count(rule: str, report: Any) -> int:
    totals = dict(getattr(report, "totals", {}) or {})
    key_by_rule = {
        "launch_not_ready": "launch_not_ready",
        "stale_or_missing_response_cache": "cache_missing",
        "call_control_daemon_not_ready": "daemon_not_ready",
        "provider_blocked": "provider_blocks",
        "fallback_blocked": "fallback_blocks",
        "handbrake_blocked": "handbrake_blocks",
    }
    key = key_by_rule.get(rule)
    if not key:
        return 0
    return _int_value(totals.get(key))


def _field_from_detail(detail: str, field: str) -> str:
    match = re.search(rf"(?:^|\s){re.escape(field)}=([^\s]+)", detail)
    return match.group(1) if match else ""


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
    if key in {"call_control_agent", "call_control_daemon"}:
        return "call-control"
    if key == "call_control_hotkeys":
        return "macos-permission"
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


def _scorecard_rerun(
    scorecard: SessionScorecard,
    *,
    profile: str,
    source_ref: str,
) -> str:
    parts = [f"saymo session-scorecard -p {profile}", source_ref]
    if scorecard.launch_metrics.artifact_path:
        parts.append(f"--launch-json {shlex.quote(scorecard.launch_metrics.artifact_path)}")
    if scorecard.realtime_metrics.artifact_path:
        parts.append(f"--realtime-jsonl {shlex.quote(scorecard.realtime_metrics.artifact_path)}")
    return " ".join(part for part in parts if part).strip()


def _launch_rerun_chain(
    commands: tuple[str, ...],
    scorecard_rerun: str,
) -> str:
    items = [command for command in commands if command]
    items.append(scorecard_rerun)
    return " && ".join(_dedupe_text(items))


def _format_counts(counts: Mapping[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{key}={counts[key]}" for key in sorted(counts))


def _scorecard_json_ref(source_id: str) -> str:
    text = str(source_id or "").strip()
    if text.endswith(".json") or "/" in text:
        return text
    return "<scorecard.json>"


def _source_label(source_id: str) -> str:
    text = str(source_id or "").strip()
    if not text:
        return "unknown"
    return Path(text).name if "/" in text else text


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


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


def _dedupe_text(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "")
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
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
