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


def load_launch_evidence(path: str | Path) -> LaunchEvidence:
    """Load one saved launch-readiness artifact without running checks."""
    artifact_path = Path(path).expanduser()
    data = json.loads(artifact_path.read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        data = {}
    return summarize_launch_evidence(data, path=artifact_path)


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
