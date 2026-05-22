"""Local live-call control state, commands, hotkeys, and audit helpers."""

from __future__ import annotations

import json
import subprocess
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PRIMARY_ACTIONS = (
    "toggle_auto_answer",
    "speak",
    "stop",
    "takeover",
)

OPTIONAL_ACTIONS = (
    "approved_speak",
    "skip_current",
    "capture_marker",
    "status",
    "hard_disable",
)

ACTION_ORDER = PRIMARY_ACTIONS + OPTIONAL_ACTIONS


@dataclass(frozen=True)
class LiveControlAction:
    """User-facing live-control action definition."""

    action: str
    label: str
    hotkey_field: str
    description: str
    primary: bool = False


ACTION_CATALOG: dict[str, LiveControlAction] = {
    "toggle_auto_answer": LiveControlAction(
        action="toggle_auto_answer",
        label="Auto Answer",
        hotkey_field="hotkey_toggle",
        description="Toggle automatic answering on or off.",
        primary=True,
    ),
    "speak": LiveControlAction(
        action="speak",
        label="Speak",
        hotkey_field="hotkey_speak",
        description="Explicitly play the prepared cached response.",
        primary=True,
    ),
    "stop": LiveControlAction(
        action="stop",
        label="Stop",
        hotkey_field="hotkey_stop",
        description="Cancel current Saymo playback.",
        primary=True,
    ),
    "takeover": LiveControlAction(
        action="takeover",
        label="Takeover",
        hotkey_field="hotkey_takeover",
        description="Pause Saymo and switch the call mic back to the user when possible.",
        primary=True,
    ),
    "approved_speak": LiveControlAction(
        action="approved_speak",
        label="Approved Draft",
        hotkey_field="hotkey_approved_speak",
        description="Request playback for an already approved answer draft.",
    ),
    "skip_current": LiveControlAction(
        action="skip_current",
        label="Skip",
        hotkey_field="hotkey_skip",
        description="Skip the current handoff candidate and continue listening.",
    ),
    "capture_marker": LiveControlAction(
        action="capture_marker",
        label="Mark Capture",
        hotkey_field="hotkey_capture_marker",
        description="Drop a local audit marker for later review/training.",
    ),
    "status": LiveControlAction(
        action="status",
        label="Status",
        hotkey_field="hotkey_status",
        description="Print the current live-control state and local control paths.",
    ),
    "hard_disable": LiveControlAction(
        action="hard_disable",
        label="Hard Disable",
        hotkey_field="hotkey_hard_disable",
        description="Stop playback and keep auto-answer disabled until explicitly re-enabled.",
    ),
}


@dataclass(frozen=True)
class LiveControlCommand:
    """One locally queued command from a button, hotkey, or script."""

    action: str
    source: str = "panel"
    created_at: str = ""
    command_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "action", normalize_action(self.action))
        if not self.created_at:
            object.__setattr__(self, "created_at", _now())
        if not self.command_id:
            object.__setattr__(self, "command_id", uuid.uuid4().hex)


@dataclass(frozen=True)
class LiveControlSnapshot:
    """Persisted state shown by local control surfaces."""

    profile: str
    auto_answer_enabled: bool = True
    paused: bool = False
    speaking: bool = False
    manual_takeover: bool = False
    hard_disabled: bool = False
    hotkeys_active: bool = False
    last_trigger: str = ""
    last_action: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        if not self.updated_at:
            object.__setattr__(self, "updated_at", _now())


@dataclass(frozen=True)
class HotkeyDoctorReport:
    """Pre-call hotkey diagnostics rendered by ``saymo hotkey-doctor``."""

    profile: str
    bindings: dict[str, str]
    process_running: bool
    registration_status: str
    registration_detail: str
    needs_accessibility: bool = True


def normalize_action(action: str) -> str:
    """Normalize aliases used by docs, CLI, and hotkey config."""
    normalized = str(action or "").strip().lower().replace("-", "_")
    aliases = {
        "toggle": "toggle_auto_answer",
        "toggle_auto": "toggle_auto_answer",
        "auto": "toggle_auto_answer",
        "auto_answer": "toggle_auto_answer",
        "approved": "approved_speak",
        "approved_draft": "approved_speak",
        "skip": "skip_current",
        "capture": "capture_marker",
        "marker": "capture_marker",
        "cockpit": "status",
        "show_cockpit": "status",
        "panic": "hard_disable",
        "disable": "hard_disable",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in ACTION_CATALOG:
        raise ValueError(f"unknown live-control action: {action}")
    return normalized


def live_control_dir(profile: str, *, base_dir: Path | str | None = None) -> Path:
    """Return the local control directory for one profile."""
    root = Path(base_dir).expanduser() if base_dir else Path.home() / ".saymo" / "live_control"
    path = root / _safe_profile(profile)
    path.mkdir(parents=True, exist_ok=True)
    return path


def command_log_path(profile: str, *, base_dir: Path | str | None = None) -> Path:
    return live_control_dir(profile, base_dir=base_dir) / "commands.jsonl"


def state_path(profile: str, *, base_dir: Path | str | None = None) -> Path:
    return live_control_dir(profile, base_dir=base_dir) / "state.json"


def audit_log_path(profile: str, *, base_dir: Path | str | None = None) -> Path:
    return live_control_dir(profile, base_dir=base_dir) / "audit.jsonl"


def command_log_offset(profile: str, *, base_dir: Path | str | None = None) -> int:
    """Return current command log size so old commands are not replayed."""
    path = command_log_path(profile, base_dir=base_dir)
    return path.stat().st_size if path.exists() else 0


def append_control_command(
    profile: str,
    action: str,
    *,
    source: str = "panel",
    payload: dict[str, Any] | None = None,
    base_dir: Path | str | None = None,
) -> Path:
    """Append a local command for a running ``saymo auto`` process."""
    command = LiveControlCommand(
        action=action,
        source=source,
        payload=payload or {},
    )
    path = command_log_path(profile, base_dir=base_dir)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(command), ensure_ascii=False, sort_keys=True) + "\n")
    return path


def read_control_commands(
    profile: str,
    *,
    offset: int = 0,
    base_dir: Path | str | None = None,
) -> tuple[list[LiveControlCommand], int]:
    """Read commands written after ``offset`` and return the new offset."""
    path = command_log_path(profile, base_dir=base_dir)
    if not path.exists():
        return [], 0
    commands: list[LiveControlCommand] = []
    with path.open("r", encoding="utf-8") as fh:
        fh.seek(offset)
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                commands.append(
                    LiveControlCommand(
                        action=str(data.get("action") or ""),
                        source=str(data.get("source") or "panel"),
                        created_at=str(data.get("created_at") or ""),
                        command_id=str(data.get("command_id") or ""),
                        payload=dict(data.get("payload") or {}),
                    )
                )
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        new_offset = fh.tell()
    return commands, new_offset


def write_live_state(
    profile: str,
    snapshot: LiveControlSnapshot,
    *,
    base_dir: Path | str | None = None,
) -> Path:
    """Persist current live-control state for panels and diagnostics."""
    path = state_path(profile, base_dir=base_dir)
    path.write_text(
        json.dumps(asdict(snapshot), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def load_live_state(
    profile: str,
    *,
    base_dir: Path | str | None = None,
) -> LiveControlSnapshot | None:
    """Load the latest live-control state if a running process wrote one."""
    path = state_path(profile, base_dir=base_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return LiveControlSnapshot(
        profile=str(data.get("profile") or profile),
        auto_answer_enabled=bool(data.get("auto_answer_enabled", True)),
        paused=bool(data.get("paused", False)),
        speaking=bool(data.get("speaking", False)),
        manual_takeover=bool(data.get("manual_takeover", False)),
        hard_disabled=bool(data.get("hard_disabled", False)),
        hotkeys_active=bool(data.get("hotkeys_active", False)),
        last_trigger=str(data.get("last_trigger") or ""),
        last_action=str(data.get("last_action") or ""),
        updated_at=str(data.get("updated_at") or ""),
    )


def append_control_audit(
    profile: str,
    *,
    action: str,
    source: str,
    previous_state: dict[str, Any] | LiveControlSnapshot | None,
    next_state: dict[str, Any] | LiveControlSnapshot | None,
    result: str,
    reason: str = "",
    mic_result: str = "",
    base_dir: Path | str | None = None,
) -> Path:
    """Append a local audit event for live-control actions."""
    event = {
        "created_at": _now(),
        "action": normalize_action(action),
        "source": source,
        "previous_state": _state_payload(previous_state),
        "next_state": _state_payload(next_state),
        "result": result,
        "reason": reason,
        "mic_result": mic_result,
    }
    path = audit_log_path(profile, base_dir=base_dir)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def effective_hotkey_bindings(config) -> dict[str, str]:
    """Return configured action -> hotkey bindings for known actions."""
    bindings: dict[str, str] = {}
    safety = getattr(config, "safety", None)
    for action in ACTION_ORDER:
        field_name = ACTION_CATALOG[action].hotkey_field
        value = str(getattr(safety, field_name, "") or "").strip()
        if value:
            bindings[action] = value
    return bindings


def hotkey_listener_bindings(config, handlers: dict[str, Any]) -> dict[str, Any]:
    """Return pynput binding map for configured actions with registered handlers."""
    bindings: dict[str, Any] = {}
    for action, hotkey in effective_hotkey_bindings(config).items():
        handler = handlers.get(action)
        if handler is not None:
            bindings[hotkey] = handler
    return bindings


def render_hotkey_table(config) -> str:
    """Render action/hotkey descriptions for docs and CLI output."""
    bindings = effective_hotkey_bindings(config)
    lines = ["| Action | Hotkey | What it does |", "|---|---|---|"]
    for action in ACTION_ORDER:
        entry = ACTION_CATALOG[action]
        lines.append(
            f"| {entry.label} | `{bindings.get(action, 'disabled')}` | {entry.description} |"
        )
    return "\n".join(lines)


def build_hotkey_doctor_report(config, profile: str, *, probe: bool = True) -> HotkeyDoctorReport:
    """Collect pre-call diagnostics for global hotkeys."""
    bindings = effective_hotkey_bindings(config)
    process_running = _saymo_auto_process_running(profile)
    status, detail = _probe_hotkey_registration(bindings) if probe else (
        "skipped",
        "registration probe skipped",
    )
    return HotkeyDoctorReport(
        profile=profile,
        bindings=bindings,
        process_running=process_running,
        registration_status=status,
        registration_detail=detail,
    )


def render_hotkey_doctor_report(report: HotkeyDoctorReport) -> str:
    """Render a concise human-readable hotkey diagnostic report."""
    lines = [
        f"profile: {report.profile}",
        f"saymo auto listener: {'running' if report.process_running else 'not detected'}",
        f"hotkey registration: {report.registration_status}",
        f"registration detail: {report.registration_detail}",
        "terminal focus: not required after `saymo auto` registers global hotkeys",
        "macOS permission: Accessibility must allow the terminal app running Saymo",
        "bindings:",
    ]
    if not report.bindings:
        lines.append("  (none configured)")
    else:
        for action in ACTION_ORDER:
            if action in report.bindings:
                lines.append(f"  {action}: {report.bindings[action]}")
    return "\n".join(lines)


def _probe_hotkey_registration(bindings: dict[str, str]) -> tuple[str, str]:
    if not bindings:
        return "no_bindings", "no hotkeys configured"
    try:
        from pynput import keyboard as _keyboard

        hotkey = next(iter(bindings.values()))
        listener = _keyboard.GlobalHotKeys({hotkey: lambda: None})
        listener.start()
        listener.stop()
        return "ok", "global hotkey listener can be created"
    except ImportError as e:
        return "missing_dependency", str(e)
    except Exception as e:
        return "blocked", str(e)


def _saymo_auto_process_running(profile: str) -> bool:
    try:
        out = subprocess.check_output(
            ["ps", "-axo", "command"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return False
    profile_markers = {f"-p {profile}", f"--profile {profile}", f" {profile}"}
    for line in out.splitlines():
        if "saymo" not in line or " auto" not in line:
            continue
        if any(marker in line for marker in profile_markers) or profile in {"", "standup"}:
            return True
    return False


def _safe_profile(profile: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in profile)
    return safe or "default"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _state_payload(value: dict[str, Any] | LiveControlSnapshot | None) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, LiveControlSnapshot):
        return asdict(value)
    return dict(value)
