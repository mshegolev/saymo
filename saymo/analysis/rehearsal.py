"""Pre-call rehearsal artifacts and summary helpers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class RehearsalCheck:
    """One pass/warn/fail rehearsal check."""

    name: str
    status: str
    detail: str = ""
    blocking: bool = False


@dataclass(frozen=True)
class RehearsalDecision:
    """Dry-run decision for the rehearsal transcript."""

    triggered: bool
    addressing: str
    reason: str
    auto_action: str
    would_speak: bool
    blocked_reason: str = ""
    matched_phrase: str = ""
    question: bool = False


@dataclass(frozen=True)
class RehearsalArtifact:
    """Sanitized pre-call rehearsal result."""

    profile: str
    provider: str
    transcript: str
    dry_run: bool
    status: str
    checks: tuple[RehearsalCheck, ...]
    decision: RehearsalDecision
    live_control_state: dict[str, Any]
    hotkey_status: str
    launch_evidence: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            object.__setattr__(self, "created_at", _now())


def default_rehearsal_dir(profile: str, *, base_dir: str | Path | None = None) -> Path:
    """Return the local rehearsal artifact directory for one profile."""
    root = Path(base_dir).expanduser() if base_dir else Path.home() / ".saymo" / "rehearsals"
    return root / _safe_profile(profile)


def rehearsal_artifact_to_json(artifact: RehearsalArtifact) -> dict[str, Any]:
    """Serialize a rehearsal artifact to sanitized JSON-compatible data."""
    data = asdict(artifact)
    data["transcript"] = ""
    data["checks"] = [asdict(check) for check in artifact.checks]
    data["decision"] = asdict(artifact.decision)
    data["live_control_state"] = _sanitized_live_control_state(artifact.live_control_state)
    data["launch_evidence"] = _sanitized_launch_evidence_reference(artifact.launch_evidence)
    return data


def rehearsal_artifact_from_json(data: Mapping[str, Any]) -> RehearsalArtifact:
    """Load a rehearsal artifact from JSON-compatible data."""
    return RehearsalArtifact(
        profile=str(data.get("profile") or ""),
        provider=str(data.get("provider") or ""),
        transcript=str(data.get("transcript") or ""),
        dry_run=bool(data.get("dry_run", True)),
        status=str(data.get("status") or "fail"),
        checks=tuple(
            RehearsalCheck(
                name=str(item.get("name") or ""),
                status=str(item.get("status") or "fail"),
                detail=str(item.get("detail") or ""),
                blocking=bool(item.get("blocking", False)),
            )
            for item in data.get("checks", ())
            if isinstance(item, Mapping)
        ),
        decision=RehearsalDecision(
            triggered=bool((data.get("decision") or {}).get("triggered", False)),
            addressing=str((data.get("decision") or {}).get("addressing") or ""),
            reason=str((data.get("decision") or {}).get("reason") or ""),
            auto_action=str((data.get("decision") or {}).get("auto_action") or "skip"),
            would_speak=bool((data.get("decision") or {}).get("would_speak", False)),
            blocked_reason=str((data.get("decision") or {}).get("blocked_reason") or ""),
            matched_phrase=str((data.get("decision") or {}).get("matched_phrase") or ""),
            question=bool((data.get("decision") or {}).get("question", False)),
        ),
        live_control_state=dict(data.get("live_control_state") or {}),
        hotkey_status=str(data.get("hotkey_status") or ""),
        launch_evidence=_sanitized_launch_evidence_reference(
            data.get("launch_evidence") or {}
        ),
        created_at=str(data.get("created_at") or ""),
    )


def write_rehearsal_artifact(
    artifact: RehearsalArtifact,
    *,
    base_dir: str | Path | None = None,
) -> Path:
    """Write a rehearsal artifact under the profile-local directory."""
    directory = default_rehearsal_dir(artifact.profile, base_dir=base_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{_safe_timestamp(artifact.created_at)}.json"
    path.write_text(
        json.dumps(rehearsal_artifact_to_json(artifact), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return path


def overall_status(checks: tuple[RehearsalCheck, ...]) -> str:
    """Return fail/warn/pass for a set of rehearsal checks."""
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "warn" for check in checks):
        return "warn"
    return "pass"


def _safe_profile(profile: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in profile)
    return safe or "default"


def _safe_timestamp(value: str) -> str:
    text = value or _now()
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "-" for ch in text)


def _sanitized_live_control_state(state: Mapping[str, Any]) -> dict[str, bool]:
    allowed = (
        "auto_answer_enabled",
        "manual_takeover",
        "hard_disabled",
        "paused",
        "speaking",
        "hotkeys_active",
    )
    return {
        key: bool(state[key])
        for key in allowed
        if key in state and isinstance(state[key], bool)
    }


def _sanitized_launch_evidence_reference(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    allowed = (
        "path",
        "mode",
        "status",
        "ready",
        "block_count",
        "warn_count",
        "failed_labels",
        "rerun_commands",
    )
    data: dict[str, Any] = {}
    for key in allowed:
        if key not in value:
            continue
        item = value[key]
        if key in {"path", "mode", "status"}:
            text = _clean_reference_text(item)
            if text:
                data[key] = text
        elif key == "ready":
            data[key] = item if isinstance(item, bool) else None
        elif key in {"block_count", "warn_count"}:
            data[key] = _safe_int(item)
        elif key in {"failed_labels", "rerun_commands"}:
            rows = item if isinstance(item, (list, tuple)) else ()
            data[key] = [
                text
                for text in (_clean_reference_text(row) for row in rows)
                if text
            ]
    return data


def _clean_reference_text(value: Any) -> str:
    text = " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())
    for sentinel in (
        "PRIVATE_TRANSCRIPT",
        "PRIVATE_PROMPT_TEXT",
        "PRIVATE_GENERATED_RESPONSE",
        "PRIVATE_VOICE_SAMPLE",
        "PRIVATE_TRAINING_DATA",
        "SECRET_TOKEN",
    ):
        text = text.replace(sentinel, "[redacted]")
    return text


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
