"""Per-profile macOS LaunchAgent for scheduled `saymo daily-prep` runs.

Sibling to ``saymo.analysis.launch_agent`` (the call-control daemon agent):
that one is a KeepAlive background process, this one is a one-shot job fired
by launchd's ``StartCalendarInterval`` at the meeting's configured time, so it
gets its own spec/plist renderer rather than a flag bolted onto the existing
one. The subprocess/plutil/launchctl plumbing is generic enough to reuse.
"""

from __future__ import annotations

import hashlib
import plistlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from saymo.analysis.launch_agent import (
    DEFAULT_PATH,
    CommandResult,
    LaunchAgentError,
    _print_output_has_pid,
    _resolve_saymo_executable,
    _safe_profile_fragment,
    bootout_argv,
    bootstrap_argv,
    kickstart_argv,
    plutil_lint_argv,
    print_argv,
    run_command,
)

LABEL_PREFIX = "com.saymo.daily-prep"

_WEEKDAY_NUMBERS = {
    "sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6,
}
DEFAULT_DAYS = ["mon", "tue", "wed", "thu", "fri"]


@dataclass(frozen=True)
class PrepAgentSpec:
    """Resolved LaunchAgent paths and launchd identity for one profile's prep job."""

    profile: str
    label: str
    plist_path: Path
    stdout_log_path: Path
    stderr_log_path: Path
    saymo_executable: str
    working_directory: str
    home: str
    path: str
    uid: int
    calendar_intervals: list[dict[str, int]]
    secret_env: dict[str, str]


_ENV_VAR_PATTERN = re.compile(r"\$\{(\w+)\}")


def _config_env_var_names() -> list[str]:
    """Env var names referenced via ``${VAR}`` in the active config.yaml.

    launchd's GUI session does not read ~/.zshrc, so secrets exported there
    (JIRA_TOKEN, etc.) never reach a scheduled job unless baked into the
    plist's EnvironmentVariables at install time. Mirrors the candidate
    order in ``saymo.config.load_config``.
    """
    candidates = [
        Path.home() / ".saymo" / "config.yaml",
        Path.cwd() / "config.yaml",
        Path(__file__).resolve().parents[2] / "config.yaml",
    ]
    for candidate in candidates:
        if candidate.exists():
            text = candidate.read_text(encoding="utf-8")
            return sorted(set(_ENV_VAR_PATTERN.findall(text)))
    return []


def _parse_schedule(schedule: dict) -> list[dict[str, int]]:
    time_str = str((schedule or {}).get("time") or "").strip()
    if ":" not in time_str:
        raise LaunchAgentError(
            f"meeting has no usable schedule.time (got {time_str!r}); "
            "expected 'HH:MM' in config.yaml"
        )
    hour_str, minute_str = time_str.split(":", 1)
    try:
        hour, minute = int(hour_str), int(minute_str)
    except ValueError as exc:
        raise LaunchAgentError(f"invalid schedule.time {time_str!r}: expected 'HH:MM'") from exc
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise LaunchAgentError(f"invalid schedule.time {time_str!r}: out of range")

    days = schedule.get("days") or DEFAULT_DAYS
    intervals = []
    for day in days:
        key = str(day).strip().lower()[:3]
        if key not in _WEEKDAY_NUMBERS:
            raise LaunchAgentError(f"invalid schedule.days entry {day!r}")
        intervals.append({"Weekday": _WEEKDAY_NUMBERS[key], "Hour": hour, "Minute": minute})
    return intervals


def build_prep_agent_spec(
    profile: str,
    config,
    *,
    saymo_executable: str | None = None,
    home: Path | None = None,
    uid: int | None = None,
) -> PrepAgentSpec:
    """Build a deterministic per-profile prep-agent spec from `meeting.schedule`."""
    import os

    meeting = config.get_meeting(profile)
    if meeting is None:
        raise LaunchAgentError(f"unknown meeting profile: {profile!r}")
    calendar_intervals = _parse_schedule(meeting.schedule)

    resolved_home = (home or Path.home()).expanduser()
    executable = _resolve_saymo_executable(saymo_executable)
    safe_profile = _safe_profile_fragment(profile)
    label = f"{LABEL_PREFIX}.{safe_profile}"
    plist_path = resolved_home / "Library" / "LaunchAgents" / f"{label}.plist"
    log_dir = resolved_home / ".saymo" / "daily_prep" / safe_profile / "logs"
    return PrepAgentSpec(
        profile=str(profile),
        label=label,
        plist_path=plist_path,
        stdout_log_path=log_dir / f"{label}.out.log",
        stderr_log_path=log_dir / f"{label}.err.log",
        saymo_executable=executable,
        working_directory=str(Path.cwd()),
        home=str(resolved_home),
        path=os.environ.get("PATH") or DEFAULT_PATH,
        uid=os.getuid() if uid is None else int(uid),
        calendar_intervals=calendar_intervals,
        secret_env={
            name: os.environ[name] for name in _config_env_var_names() if name in os.environ
        },
    )


def render_prep_agent_plist(spec: PrepAgentSpec) -> dict[str, object]:
    """Render the LaunchAgent plist payload as plistlib-compatible data."""
    return {
        "Label": spec.label,
        "ProgramArguments": [
            spec.saymo_executable,
            "daily-prep",
            "--profile",
            spec.profile,
        ],
        "StartCalendarInterval": spec.calendar_intervals,
        "WorkingDirectory": spec.working_directory,
        "EnvironmentVariables": {
            **spec.secret_env,
            "HOME": spec.home,
            "PATH": spec.path,
            "PYTHONUNBUFFERED": "1",
            "NO_PROXY": "localhost,127.0.0.1",
        },
        "StandardOutPath": str(spec.stdout_log_path),
        "StandardErrorPath": str(spec.stderr_log_path),
    }


def expected_plist_bytes(spec: PrepAgentSpec) -> bytes:
    return plistlib.dumps(
        render_prep_agent_plist(spec),
        fmt=plistlib.FMT_XML,
        sort_keys=True,
    )


def expected_plist_hash(spec: PrepAgentSpec) -> str:
    return hashlib.sha256(expected_plist_bytes(spec)).hexdigest()


def installed_plist_hash(spec: PrepAgentSpec) -> str:
    if not spec.plist_path.exists():
        return ""
    return hashlib.sha256(spec.plist_path.read_bytes()).hexdigest()


def install_prep_agent(spec: PrepAgentSpec, *, lint: bool = True) -> CommandResult | None:
    """Write the plist and log directory, then optionally lint the plist."""
    spec.plist_path.parent.mkdir(parents=True, exist_ok=True)
    spec.stdout_log_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = spec.plist_path.with_suffix(spec.plist_path.suffix + ".tmp")
    tmp_path.write_bytes(expected_plist_bytes(spec))
    tmp_path.replace(spec.plist_path)
    if lint:
        return run_command(plutil_lint_argv(spec), check=True)
    return None


def uninstall_prep_agent(spec: PrepAgentSpec) -> CommandResult:
    result = run_command(bootout_argv(spec), check=False)
    if spec.plist_path.exists():
        spec.plist_path.unlink()
    return result


def start_prep_agent(spec: PrepAgentSpec) -> CommandResult:
    return run_command(bootstrap_argv(spec), check=True)


def stop_prep_agent(spec: PrepAgentSpec) -> CommandResult:
    return run_command(bootout_argv(spec), check=True)


def restart_prep_agent(spec: PrepAgentSpec) -> CommandResult:
    return run_command(kickstart_argv(spec, restart=True), check=True)


@dataclass(frozen=True)
class PrepAgentStatus:
    """Read-only plist/launchd status evidence for the prep agent."""

    spec: PrepAgentSpec
    installed: bool
    plist_current: bool
    loaded: bool
    running: bool
    next_fire: list[dict[str, int]]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("plist_path", "stdout_log_path", "stderr_log_path"):
            data["spec"][key] = str(getattr(self.spec, key))
        # Report which secrets are baked in, never their values.
        data["spec"]["secret_env"] = sorted(self.spec.secret_env.keys())
        return data


def collect_prep_agent_status(spec: PrepAgentSpec) -> PrepAgentStatus:
    """Collect read-only plist, plutil, and launchctl status evidence."""
    installed = spec.plist_path.exists()
    plist_current = installed and installed_plist_hash(spec) == expected_plist_hash(spec)
    launchctl_result = run_command(print_argv(spec), check=False)
    loaded = launchctl_result.returncode == 0
    return PrepAgentStatus(
        spec=spec,
        installed=installed,
        plist_current=plist_current,
        loaded=loaded,
        running=loaded and _print_output_has_pid(launchctl_result.stdout),
        next_fire=spec.calendar_intervals,
    )


__all__ = [
    "LaunchAgentError",
    "PrepAgentSpec",
    "PrepAgentStatus",
    "build_prep_agent_spec",
    "collect_prep_agent_status",
    "install_prep_agent",
    "restart_prep_agent",
    "start_prep_agent",
    "stop_prep_agent",
    "uninstall_prep_agent",
]
