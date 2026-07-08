"""Foreground call-control daemon heartbeat and hotkey queue helpers."""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from saymo.analysis.live_control import (
    ACTION_CATALOG,
    append_control_command,
    audit_log_path,
    command_log_path,
    command_log_offset,
    hotkey_listener_bindings,
    live_control_dir,
    read_control_commands,
    sanitized_control_payload,
)


DAEMON_VERSION = "1"


@dataclass(frozen=True)
class ControlDaemonHeartbeat:
    """Profile-scoped liveness and hotkey-registration evidence."""

    profile: str
    pid: int
    label: str
    started_at: str
    heartbeat_at: str
    hotkeys_active: bool
    hotkey_registration_status: str
    hotkey_registration_detail: str
    bindings_count: int
    command_log_offset: int
    daemon_version: str


@dataclass(frozen=True)
class HandbrakeReachabilityProbe:
    """Evidence that the profile handbrake control plane is reachable."""

    profile: str
    probe_id: str
    ok: bool
    heartbeat_fresh: bool
    hotkeys_active: bool
    command_written: bool
    command_consumed: bool
    audit_applied: bool
    detail: str
    command_log_path: str
    audit_log_path: str
    stdout_log_path: str
    stderr_log_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def daemon_heartbeat_path(profile: str, *, base_dir: Path | str | None = None) -> Path:
    """Return the heartbeat file path beside existing live-control files."""
    return live_control_dir(profile, base_dir=base_dir) / "daemon-heartbeat.json"


def write_daemon_heartbeat(
    heartbeat: ControlDaemonHeartbeat,
    *,
    base_dir: Path | str | None = None,
) -> Path:
    """Persist one daemon heartbeat as sanitized JSON."""
    path = daemon_heartbeat_path(heartbeat.profile, base_dir=base_dir)
    path.write_text(
        json.dumps(asdict(heartbeat), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def load_daemon_heartbeat(
    profile: str,
    *,
    base_dir: Path | str | None = None,
) -> ControlDaemonHeartbeat | None:
    """Load the latest daemon heartbeat, returning None on corrupt evidence."""
    path = daemon_heartbeat_path(profile, base_dir=base_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    try:
        return ControlDaemonHeartbeat(
            profile=str(data.get("profile") or profile),
            pid=int(data.get("pid") or 0),
            label=str(data.get("label") or ""),
            started_at=str(data.get("started_at") or ""),
            heartbeat_at=str(data.get("heartbeat_at") or ""),
            hotkeys_active=bool(data.get("hotkeys_active", False)),
            hotkey_registration_status=str(
                data.get("hotkey_registration_status") or ""
            ),
            hotkey_registration_detail=str(
                data.get("hotkey_registration_detail") or ""
            ),
            bindings_count=int(data.get("bindings_count") or 0),
            command_log_offset=int(data.get("command_log_offset") or 0),
            daemon_version=str(data.get("daemon_version") or ""),
        )
    except (TypeError, ValueError):
        return None


def heartbeat_is_fresh(
    heartbeat: ControlDaemonHeartbeat | None,
    *,
    now: datetime | None = None,
    max_age_seconds: float = 5.0,
) -> bool:
    """Return whether heartbeat evidence is parseable, recent, and not future."""
    if heartbeat is None:
        return False
    try:
        heartbeat_at = _parse_timestamp(heartbeat.heartbeat_at)
    except ValueError:
        return False
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    age_seconds = (current - heartbeat_at).total_seconds()
    return 0 <= age_seconds <= max_age_seconds


def run_handbrake_reachability_probe(
    profile: str,
    *,
    base_dir: Path | str | None = None,
    timeout_seconds: float = 2.0,
    poll_interval_seconds: float = 0.1,
    now: datetime | None = None,
) -> HandbrakeReachabilityProbe:
    """Queue a benign status command and prove daemon/audit reachability."""
    probe_id = _new_probe_id()
    stdout_log_path, stderr_log_path = _daemon_log_paths(profile, base_dir=base_dir)
    command_path = command_log_path(profile, base_dir=base_dir)
    audit_path = audit_log_path(profile, base_dir=base_dir)

    start_offset = command_log_offset(profile, base_dir=base_dir)
    append_control_command(
        profile,
        "status",
        source="probe",
        payload=sanitized_control_payload({"probe_id": probe_id}),
        base_dir=base_dir,
    )
    new_commands, command_end_offset = read_control_commands(
        profile,
        offset=start_offset,
        base_dir=base_dir,
    )
    command = next(
        (
            item
            for item in reversed(new_commands)
            if item.action == "status"
            and item.source == "probe"
            and item.payload.get("probe_id") == probe_id
        ),
        None,
    )
    command_written = command is not None
    command_id = command.command_id if command else ""

    deadline = time.monotonic() + max(0.0, float(timeout_seconds))
    heartbeat_fresh = False
    hotkeys_active = False
    command_consumed = False
    audit_applied = False

    while True:
        heartbeat = load_daemon_heartbeat(profile, base_dir=base_dir)
        heartbeat_fresh = heartbeat_is_fresh(heartbeat, now=_probe_now(now))
        hotkeys_active = bool(heartbeat and heartbeat.hotkeys_active)
        command_consumed = bool(
            heartbeat
            and command_written
            and heartbeat.command_log_offset >= command_end_offset
        )
        audit_applied = bool(
            command_written
            and _matching_probe_audit_exists(
                profile,
                probe_id=probe_id,
                command_id=command_id,
                base_dir=base_dir,
            )
        )
        if (
            heartbeat_fresh
            and hotkeys_active
            and command_written
            and command_consumed
            and audit_applied
        ):
            break
        if time.monotonic() >= deadline:
            break
        time.sleep(max(0.0, float(poll_interval_seconds)))

    detail = _probe_detail(
        heartbeat_fresh=heartbeat_fresh,
        hotkeys_active=hotkeys_active,
        command_written=command_written,
        command_consumed=command_consumed,
        audit_applied=audit_applied,
    )
    return HandbrakeReachabilityProbe(
        profile=profile,
        probe_id=probe_id,
        ok=detail == "reachable",
        heartbeat_fresh=heartbeat_fresh,
        hotkeys_active=hotkeys_active,
        command_written=command_written,
        command_consumed=command_consumed,
        audit_applied=audit_applied,
        detail=detail,
        command_log_path=str(command_path),
        audit_log_path=str(audit_path),
        stdout_log_path=str(stdout_log_path),
        stderr_log_path=str(stderr_log_path),
    )


def run_control_daemon(
    config,
    *,
    profile: str,
    label: str = "",
    heartbeat_interval_seconds: float = 2.0,
    base_dir: Path | str | None = None,
    listener_factory=None,
    stop_after_heartbeats: int | None = None,
) -> int:
    """Run a foreground daemon that writes heartbeats and queues hotkeys."""
    started_at = _now()
    resolved_label = label or f"com.saymo.call-control.{_safe_label_fragment(profile)}"
    handlers = {
        action: _command_handler(profile, action, base_dir=base_dir)
        for action in ACTION_CATALOG
    }
    bindings = hotkey_listener_bindings(config, handlers)
    listener = None
    listener_started = False
    hotkeys_active = False
    if bindings:
        try:
            factory = listener_factory or _default_listener_factory()
            listener = factory(bindings)
            listener.start()
            listener_started = True
            hotkeys_active = True
            registration_status = "ok"
            registration_detail = "registered global hotkeys"
        except Exception as exc:
            registration_status = "blocked"
            registration_detail = _bounded_exception_detail(exc)
    else:
        registration_status = "no_bindings"
        registration_detail = "no hotkeys configured"

    heartbeat_count = 0
    try:
        while True:
            heartbeat_count += 1
            write_daemon_heartbeat(
                ControlDaemonHeartbeat(
                    profile=profile,
                    pid=os.getpid(),
                    label=resolved_label,
                    started_at=started_at,
                    heartbeat_at=_now(),
                    hotkeys_active=hotkeys_active,
                    hotkey_registration_status=registration_status,
                    hotkey_registration_detail=registration_detail,
                    bindings_count=len(bindings),
                    command_log_offset=command_log_offset(profile, base_dir=base_dir),
                    daemon_version=DAEMON_VERSION,
                ),
                base_dir=base_dir,
            )
            if (
                stop_after_heartbeats is not None
                and heartbeat_count >= stop_after_heartbeats
            ):
                break
            time.sleep(max(0.0, float(heartbeat_interval_seconds)))
    except KeyboardInterrupt:
        return 130
    finally:
        if listener is not None and listener_started:
            try:
                listener.stop()
            except Exception:
                pass
    return 0


def _command_handler(profile: str, action: str, *, base_dir: Path | str | None):
    def _handler() -> None:
        queue_daemon_hotkey_command(profile, action, base_dir=base_dir)

    return _handler


def queue_daemon_hotkey_command(
    profile: str,
    action: str,
    *,
    payload: dict[str, Any] | None = None,
    base_dir: Path | str | None = None,
) -> Path:
    """Queue one daemon-owned hotkey action with bounded metadata only."""
    return append_control_command(
        profile,
        action,
        source="daemon_hotkey",
        payload=sanitized_control_payload(payload),
        base_dir=base_dir,
    )


def _default_listener_factory():
    from pynput import keyboard

    return keyboard.GlobalHotKeys


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_probe_id() -> str:
    return f"probe-{uuid.uuid4().hex[:16]}"


def _probe_now(now: datetime | None) -> datetime:
    return (now or datetime.now(timezone.utc)).astimezone(timezone.utc)


def _daemon_log_paths(
    profile: str,
    *,
    base_dir: Path | str | None = None,
) -> tuple[Path, Path]:
    label = f"com.saymo.call-control.{_safe_label_fragment(profile)}"
    log_dir = live_control_dir(profile, base_dir=base_dir) / "logs"
    return log_dir / f"{label}.out.log", log_dir / f"{label}.err.log"


def _matching_probe_audit_exists(
    profile: str,
    *,
    probe_id: str,
    command_id: str,
    base_dir: Path | str | None = None,
) -> bool:
    path = audit_log_path(profile, base_dir=base_dir)
    if not path.exists():
        return False
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("action") != "status":
            continue
        if event.get("source") != "probe":
            continue
        if command_id and event.get("command_id") != command_id:
            continue
        if event.get("probe_id") != probe_id:
            continue
        return bool(event.get("result"))
    return False


def _probe_detail(
    *,
    heartbeat_fresh: bool,
    hotkeys_active: bool,
    command_written: bool,
    command_consumed: bool,
    audit_applied: bool,
) -> str:
    if not heartbeat_fresh:
        return "stale heartbeat"
    if not hotkeys_active:
        return "hotkeys blocked"
    if not command_written:
        return "command not written"
    if not command_consumed:
        return "command not consumed"
    if not audit_applied:
        return "missing audit"
    return "reachable"


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _safe_label_fragment(profile: str) -> str:
    safe = "".join(
        ch.lower() if ch.isalnum() or ch in {"-", "_", "."} else "-"
        for ch in str(profile or "")
    ).strip(".-")
    return safe or "default"


def _bounded_exception_detail(exc: BaseException, *, limit: int = 200) -> str:
    detail = f"{type(exc).__name__}: {exc}"
    detail = " ".join(detail.split())
    if len(detail) <= limit:
        return detail
    return detail[: limit - 3] + "..."
