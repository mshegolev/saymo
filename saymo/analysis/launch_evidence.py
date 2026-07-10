"""Read-only launch-readiness evidence loading and summarization."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


_SENSITIVE_MARKERS = (
    "raw" + "_" + "transcript",
    "raw" + " " + "transcript",
    "generated" + "_" + "answer",
    "answer" + "_" + "text",
    "daily" + "_" + "note" + "_" + "body",
    "daily" + "_" + "note",
    "audio" + "_" + "bytes",
    "transcript" + "_" + "window",
)
_SENTINEL_TOKEN_RE = re.compile(r"\b" + "PRIVATE" + r"_[A-Za-z0-9_]+\b")
_SECRET_WORD_RE = re.compile(
    r"\b[A-Z0-9_]*(?:SECRET|TOKEN|PASSWORD|PASSWD|API[_-]?KEY)[A-Z0-9_=-]*\b",
    flags=re.IGNORECASE,
)
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b([A-Za-z0-9_.-]*(?:token|secret|password|passwd|api[_-]?key)"
    r"[A-Za-z0-9_.-]*)\s*[:=]\s*[^\s,;]+"
)
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}")
_LONG_TOKEN_RE = re.compile(r"\b[A-Za-z0-9_=-]{32,}\b")


@dataclass(frozen=True)
class LaunchEvidence:
    """Normalized local evidence from one launch-readiness artifact."""

    schema_version: str = "1.0"
    evidence_kind: str = "launch-readiness"
    mode: str = "call-ready"
    path: str = ""
    profile: str = ""
    provider: str = ""
    ready: bool = False
    check_count: int = 0
    ready_count: int = 0
    block_count: int = 0
    warn_count: int = 0
    failed_labels: tuple[str, ...] = ()
    blocker_categories: dict[str, int] = field(default_factory=dict)
    cache_counts: dict[str, int] = field(default_factory=dict)
    voice_metadata: dict[str, Any] = field(default_factory=dict)
    provider_status: dict[str, Any] = field(default_factory=dict)
    daemon_status: dict[str, Any] = field(default_factory=dict)
    artifact_paths: tuple[str, ...] = ()
    rerun_commands: tuple[str, ...] = ()
    checks: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class LaunchEvidenceComparison:
    """Normalized difference between two saved launch-readiness artifacts."""

    current_path: str
    previous_path: str
    status: str
    ready_change: str
    block_delta: int
    warn_delta: int
    resolved_failures: tuple[str, ...] = ()
    new_failures: tuple[str, ...] = ()
    blocker_category_deltas: dict[str, int] = field(default_factory=dict)
    cache_deltas: dict[str, int] = field(default_factory=dict)
    provider_change: str = "unchanged"
    daemon_change: str = "unchanged"
    rerun_commands_added: tuple[str, ...] = ()
    rerun_commands_removed: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def load_launch_evidence(path: str | Path) -> LaunchEvidence:
    """Load one saved launch-readiness artifact without running checks."""
    artifact_path = Path(path).expanduser()
    data = json.loads(artifact_path.read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        data = {}
    return summarize_launch_evidence(data, path=artifact_path)


def compare_launch_evidence_paths(
    *,
    current: str | Path,
    previous: str | Path,
) -> LaunchEvidenceComparison:
    """Compare two saved launch-readiness artifacts without running checks."""
    current_path = Path(current).expanduser()
    previous_path = Path(previous).expanduser()
    if not current_path.exists():
        raise ValueError(f"launch evidence not found: {current_path}")
    if not previous_path.exists():
        raise ValueError(f"launch evidence not found: {previous_path}")
    try:
        current_evidence = load_launch_evidence(current_path)
    except json.JSONDecodeError as exc:
        raise ValueError(f"launch evidence invalid: {current_path}") from exc
    try:
        previous_evidence = load_launch_evidence(previous_path)
    except json.JSONDecodeError as exc:
        raise ValueError(f"launch evidence invalid: {previous_path}") from exc
    return compare_launch_evidence(current_evidence, previous_evidence)


def compare_launch_evidence(
    current: LaunchEvidence,
    previous: LaunchEvidence,
) -> LaunchEvidenceComparison:
    """Return normalized readiness deltas for two loaded evidence artifacts."""
    ready_change = _ready_change(current.ready, previous.ready)
    block_delta = current.block_count - previous.block_count
    warn_delta = current.warn_count - previous.warn_count
    previous_failed = set(previous.failed_labels)
    current_failed = set(current.failed_labels)
    resolved_failures = tuple(
        label for label in previous.failed_labels if label not in current_failed
    )
    new_failures = tuple(
        label for label in current.failed_labels if label not in previous_failed
    )
    blocker_category_deltas = _dict_delta(
        current.blocker_categories,
        previous.blocker_categories,
    )
    cache_deltas = _dict_delta(current.cache_counts, previous.cache_counts)
    provider_change = _status_change(
        _bool_state(_provider_ready_from_status(current.provider_status)),
        _bool_state(_provider_ready_from_status(previous.provider_status)),
    )
    daemon_change = _status_change(
        _bool_state(_daemon_ready_from_status(current.daemon_status)),
        _bool_state(_daemon_ready_from_status(previous.daemon_status)),
    )
    previous_reruns = set(previous.rerun_commands)
    current_reruns = set(current.rerun_commands)
    rerun_commands_added = tuple(
        command for command in current.rerun_commands if command not in previous_reruns
    )
    rerun_commands_removed = tuple(
        command for command in previous.rerun_commands if command not in current_reruns
    )

    improved = False
    regressed = False

    if ready_change == "not_ready_to_ready":
        improved = True
    elif ready_change == "ready_to_not_ready":
        regressed = True
    if block_delta < 0:
        improved = True
    elif block_delta > 0:
        regressed = True
    if warn_delta < 0:
        improved = True
    elif warn_delta > 0:
        regressed = True
    if resolved_failures:
        improved = True
    if new_failures:
        regressed = True
    for delta in blocker_category_deltas.values():
        if delta < 0:
            improved = True
        elif delta > 0:
            regressed = True
    for key, delta in cache_deltas.items():
        if key == "ready":
            if delta > 0:
                improved = True
            elif delta < 0:
                regressed = True
        elif key == "missing":
            if delta < 0:
                improved = True
            elif delta > 0:
                regressed = True
    for change in (provider_change, daemon_change):
        if change in {"not_ready_to_ready", "unknown_to_ready", "not_ready_to_unknown"}:
            improved = True
        elif change in {"ready_to_not_ready", "unknown_to_not_ready", "ready_to_unknown"}:
            regressed = True
    if rerun_commands_removed:
        improved = True
    if rerun_commands_added:
        regressed = True

    return LaunchEvidenceComparison(
        current_path=current.path,
        previous_path=previous.path,
        status=_comparison_status(improved, regressed),
        ready_change=ready_change,
        block_delta=block_delta,
        warn_delta=warn_delta,
        resolved_failures=resolved_failures,
        new_failures=new_failures,
        blocker_category_deltas=blocker_category_deltas,
        cache_deltas=cache_deltas,
        provider_change=provider_change,
        daemon_change=daemon_change,
        rerun_commands_added=rerun_commands_added,
        rerun_commands_removed=rerun_commands_removed,
    )


def launch_evidence_comparison_to_json(
    comparison: LaunchEvidenceComparison,
) -> dict[str, Any]:
    """Serialize a comparison without exposing raw check rows."""
    return {
        "current_path": comparison.current_path,
        "previous_path": comparison.previous_path,
        "status": comparison.status,
        "ready_change": comparison.ready_change,
        "block_delta": comparison.block_delta,
        "warn_delta": comparison.warn_delta,
        "resolved_failures": list(comparison.resolved_failures),
        "new_failures": list(comparison.new_failures),
        "blocker_category_deltas": dict(comparison.blocker_category_deltas),
        "cache_deltas": dict(comparison.cache_deltas),
        "provider_change": comparison.provider_change,
        "daemon_change": comparison.daemon_change,
        "rerun_commands_added": list(comparison.rerun_commands_added),
        "rerun_commands_removed": list(comparison.rerun_commands_removed),
        "warnings": list(comparison.warnings),
    }


def render_launch_evidence_comparison(comparison: LaunchEvidenceComparison) -> str:
    """Render a compact human-readable readiness comparison."""
    previous_ready, current_ready = _render_ready_change(comparison.ready_change)
    return "\n".join(
        [
            f"dry-run comparison: {comparison.status}",
            f"current: {comparison.current_path}",
            f"previous: {comparison.previous_path}",
            f"ready: {previous_ready} -> {current_ready}",
            f"blocks: {comparison.block_delta}",
            f"warnings: {comparison.warn_delta}",
            f"resolved: {_render_list(comparison.resolved_failures)}",
            f"new: {_render_list(comparison.new_failures)}",
            "blocker category deltas: "
            + _render_mapping(comparison.blocker_category_deltas),
            f"cache deltas: {_render_mapping(comparison.cache_deltas)}",
            f"provider: {comparison.provider_change}",
            f"daemon: {comparison.daemon_change}",
            f"rerun commands added: {_render_list(comparison.rerun_commands_added)}",
            f"rerun commands removed: {_render_list(comparison.rerun_commands_removed)}",
            f"warnings: {_render_list(comparison.warnings)}",
        ]
    )


def summarize_launch_evidence(
    data: Mapping[str, Any],
    *,
    path: str | Path = "",
) -> LaunchEvidence:
    """Normalize a launch-readiness artifact dictionary."""
    checks = _checks_from_data(data)
    path_text = _sanitize_text(str(path)) if path else ""
    root_artifact_path = _sanitize_text(data.get("artifact_path") or "")
    artifact_paths = _artifact_paths(
        checks,
        root_path=root_artifact_path or path_text,
        fallback_path=path_text,
    )

    return LaunchEvidence(
        schema_version=_sanitize_text(data.get("schema_version") or "legacy"),
        evidence_kind=_sanitize_text(data.get("evidence_kind") or "launch-readiness"),
        mode=_sanitize_text(data.get("mode") or "call-ready"),
        path=path_text,
        profile=_sanitize_text(data.get("profile") or ""),
        provider=_sanitize_text(data.get("provider") or ""),
        ready=_ready_from_data(data, checks),
        check_count=_count_from_root(data, "check_count", len(checks)),
        ready_count=_count_from_root(data, "ready_count", _ready_count(checks)),
        block_count=_count_from_root(data, "block_count", _block_count(checks)),
        warn_count=_count_from_root(data, "warn_count", _warn_count(checks)),
        failed_labels=_failed_labels(checks),
        blocker_categories=_blocker_categories(checks),
        cache_counts=_cache_counts(checks),
        voice_metadata=_voice_metadata(checks),
        provider_status=_provider_status(checks),
        daemon_status=_daemon_status(checks),
        artifact_paths=artifact_paths,
        rerun_commands=_rerun_commands(checks),
        checks=checks,
    )


def _checks_from_data(data: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    rows = data.get("checks") or ()
    if not isinstance(rows, (list, tuple)):
        return ()
    checks: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        sanitized = _sanitize_value(dict(row))
        if isinstance(sanitized, dict):
            checks.append(sanitized)
    return tuple(checks)


def _ready_from_data(data: Mapping[str, Any], checks: tuple[dict[str, Any], ...]) -> bool:
    value = data.get("ready")
    if isinstance(value, bool):
        return value
    return _block_count(checks) == 0


def _count_from_root(data: Mapping[str, Any], key: str, default: int) -> int:
    if key in data:
        return _int_value(data.get(key))
    return default


def _ready_count(checks: tuple[dict[str, Any], ...]) -> int:
    return sum(1 for check in checks if bool(check.get("ok")))


def _block_count(checks: tuple[dict[str, Any], ...]) -> int:
    return sum(
        1
        for check in checks
        if not bool(check.get("ok")) and str(check.get("severity") or "") == "block"
    )


def _warn_count(checks: tuple[dict[str, Any], ...]) -> int:
    return sum(
        1
        for check in checks
        if not bool(check.get("ok")) and str(check.get("severity") or "") == "warn"
    )


def _failed_labels(checks: tuple[dict[str, Any], ...]) -> tuple[str, ...]:
    return tuple(
        _sanitize_text(check.get("label") or check.get("key") or "unknown")
        for check in checks
        if not bool(check.get("ok"))
    )


def _blocker_categories(checks: tuple[dict[str, Any], ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for check in checks:
        if bool(check.get("ok")) or str(check.get("severity") or "") != "block":
            continue
        metadata = _mapping(check.get("metadata"))
        category = _sanitize_text(
            metadata.get("category") or _category_for_key(str(check.get("key") or ""))
        )
        counts[category] = counts.get(category, 0) + 1
    return dict(sorted(counts.items()))


def _cache_counts(checks: tuple[dict[str, Any], ...]) -> dict[str, int]:
    check = _check_by_key(checks, "response_cache_coverage")
    if not check:
        return {}
    metadata = _mapping(check.get("metadata"))
    missing = metadata.get("missing")
    if missing is None:
        missing_examples = metadata.get("missing_examples")
        missing = len(missing_examples) if isinstance(missing_examples, (list, tuple)) else 0
    return {
        "ready": _int_value(metadata.get("ready")),
        "total": _int_value(metadata.get("total")),
        "missing": _int_value(missing),
    }


def _voice_metadata(checks: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    check = _check_by_key(checks, "cloned_voice_metadata")
    if not check:
        return {}
    metadata = _mapping(check.get("metadata"))
    keys = (
        "selected_engine",
        "voice_profile",
        "profile_approved",
        "reference_fingerprint",
        "reference_audio_sha256",
        "reference_text_sha256",
        "blocked_reason",
    )
    return {
        key: metadata[key]
        for key in keys
        if key in metadata
    }


def _provider_status(checks: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    status: dict[str, Any] = {}
    tab = _check_by_key(checks, "provider_meeting_tab")
    if tab:
        metadata = _mapping(tab.get("metadata"))
        status.update(
            {
                "meeting_tab_ok": bool(tab.get("ok")),
                "meeting_tab_detail": _sanitize_text(tab.get("detail") or ""),
            }
        )
        for key in ("meeting_found", "app_running"):
            if key in metadata:
                status[key] = metadata[key]
    capabilities = _check_by_key(checks, "provider_capabilities")
    if capabilities:
        metadata = _mapping(capabilities.get("metadata"))
        status.update(
            {
                "capabilities_ok": bool(capabilities.get("ok")),
                "capabilities_detail": _sanitize_text(capabilities.get("detail") or ""),
            }
        )
        for key in ("activation", "mic_switch", "mute_recovery"):
            if key in metadata:
                status[key] = metadata[key]
    return status


def _daemon_status(checks: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    status: dict[str, Any] = {}
    rows = {
        "agent_ok": _check_by_key(checks, "call_control_agent"),
        "daemon_ok": _check_by_key(checks, "call_control_daemon"),
        "hotkeys_ok": _check_by_key(checks, "call_control_hotkeys"),
    }
    for key, check in rows.items():
        if check:
            status[key] = bool(check.get("ok"))
    for check_key in ("call_control_agent", "call_control_daemon", "call_control_hotkeys"):
        check = _check_by_key(checks, check_key)
        if not check:
            continue
        metadata = _mapping(check.get("metadata"))
        for key in (
            "heartbeat_fresh",
            "running",
            "hotkeys_active",
            "stdout_log_path",
            "stderr_log_path",
        ):
            if key in metadata and key not in status:
                status[key] = metadata[key]
        if check_key == "call_control_daemon" and "classification" in metadata:
            status["classification"] = metadata["classification"]
    return status


def _artifact_paths(
    checks: tuple[dict[str, Any], ...],
    *,
    root_path: str,
    fallback_path: str,
) -> tuple[str, ...]:
    values: list[str] = []
    if root_path:
        values.append(root_path)
    elif fallback_path:
        values.append(fallback_path)
    for check in checks:
        metadata = _mapping(check.get("metadata"))
        used_keys: set[str] = set()
        for key in (
            "stdout_log_path",
            "stderr_log_path",
            "artifact_path",
            "plist_path",
            "note_path",
        ):
            if key in metadata:
                values.append(_sanitize_text(metadata[key]))
                used_keys.add(key)
        for key, value in metadata.items():
            key_text = str(key)
            if key_text in used_keys:
                continue
            if key_text.endswith("_path"):
                values.append(_sanitize_text(value))
    return _dedupe(values)


def _rerun_commands(checks: tuple[dict[str, Any], ...]) -> tuple[str, ...]:
    return _dedupe(
        _sanitize_text(check.get("rerun") or "")
        for check in checks
        if check.get("rerun")
    )


def _ready_change(current_ready: bool | None, previous_ready: bool | None) -> str:
    if previous_ready is True and current_ready is True:
        return "unchanged_ready"
    if previous_ready is False and current_ready is False:
        return "unchanged_not_ready"
    if previous_ready is False and current_ready is True:
        return "not_ready_to_ready"
    if previous_ready is True and current_ready is False:
        return "ready_to_not_ready"
    return _status_change(_bool_state(current_ready), _bool_state(previous_ready))


def _bool_state(value: bool | None) -> str:
    if value is True:
        return "ready"
    if value is False:
        return "not_ready"
    return "unknown"


def _status_change(current_state: str, previous_state: str) -> str:
    if current_state == previous_state:
        return "unchanged"
    return f"{previous_state}_to_{current_state}"


def _dict_delta(current: Mapping[str, Any], previous: Mapping[str, Any]) -> dict[str, int]:
    keys = sorted(set(current) | set(previous))
    return {
        _sanitize_text(key): _int_value(current.get(key)) - _int_value(previous.get(key))
        for key in keys
    }


def _comparison_status(improved: bool, regressed: bool) -> str:
    if improved and regressed:
        return "mixed"
    if improved:
        return "improved"
    if regressed:
        return "regressed"
    return "unchanged"


def _provider_ready_from_status(status: Mapping[str, Any]) -> bool | None:
    values = [
        status[key]
        for key in ("meeting_tab_ok", "capabilities_ok", "meeting_found")
        if isinstance(status.get(key), bool)
    ]
    if not values:
        return None
    return all(values)


def _daemon_ready_from_status(status: Mapping[str, Any]) -> bool | None:
    ok_values = [
        value
        for key, value in status.items()
        if str(key).endswith("_ok") and isinstance(value, bool)
    ]
    if ok_values:
        return all(ok_values)
    values = [
        status[key]
        for key in ("daemon_ok", "running", "heartbeat_fresh")
        if isinstance(status.get(key), bool)
    ]
    if not values:
        return None
    return all(values)


def _render_ready_change(value: str) -> tuple[str, str]:
    if value == "unchanged_ready":
        return "yes", "yes"
    if value == "unchanged_not_ready":
        return "no", "no"
    if value == "not_ready_to_ready":
        return "no", "yes"
    if value == "ready_to_not_ready":
        return "yes", "no"
    if value == "unknown_to_ready":
        return "unknown", "yes"
    if value == "unknown_to_not_ready":
        return "unknown", "no"
    if value == "ready_to_unknown":
        return "yes", "unknown"
    if value == "not_ready_to_unknown":
        return "no", "unknown"
    return "unknown", "unknown"


def _render_list(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "none"


def _render_mapping(values: Mapping[str, int]) -> str:
    if not values:
        return "none"
    return ", ".join(f"{key}={value}" for key, value in sorted(values.items()))


def _check_by_key(
    checks: tuple[dict[str, Any], ...],
    key: str,
) -> dict[str, Any] | None:
    for check in checks:
        if check.get("key") == key:
            return check
    return None


def _category_for_key(key: str) -> str:
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
    if key.startswith("daily_note_") or key in {
        "prepared_standup_audio",
        "response_cache_coverage",
    }:
        return "source-data"
    if key == "cloned_voice_metadata":
        return "voice-cache"
    return "retest"


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return _sanitize_text(value)
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int | float):
        if isinstance(value, float) and not math.isfinite(value):
            return 0
        return value
    if isinstance(value, Mapping):
        return {
            _sanitize_text(str(key)): _sanitize_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize_value(item) for item in value]
    return _sanitize_text(str(value))


def _sanitize_text(value: Any) -> str:
    text = " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())
    lower = text.lower()
    if any(marker in lower for marker in _SENSITIVE_MARKERS):
        return "[redacted]"
    text = _SENTINEL_TOKEN_RE.sub("[redacted]", text)
    text = _SECRET_ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}=[redacted]", text)
    text = _BEARER_RE.sub("Bearer [redacted]", text)
    text = _SECRET_WORD_RE.sub("[redacted]", text)
    text = _LONG_TOKEN_RE.sub("[redacted]", text)
    return text


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _dedupe(values: Any) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = _sanitize_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return tuple(result)
