"""Foreground call-control daemon heartbeat and hotkey queue helpers."""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from saymo.analysis.live_control import (
    ACTION_CATALOG,
    append_control_command,
    command_log_offset,
    hotkey_listener_bindings,
    live_control_dir,
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
