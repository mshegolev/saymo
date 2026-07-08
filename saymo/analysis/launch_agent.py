"""Per-profile macOS LaunchAgent helpers for the call-control daemon."""

from __future__ import annotations

import hashlib
import os
import plistlib
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


LABEL_PREFIX = "com.saymo.call-control"
DEFAULT_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
LAUNCHCTL = "/bin/launchctl"
PLUTIL = "/usr/bin/plutil"


class LaunchAgentError(RuntimeError):
    """Raised when LaunchAgent setup cannot be constructed safely."""


@dataclass(frozen=True)
class LaunchAgentSpec:
    """Resolved LaunchAgent paths and launchd identity for one profile."""

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
    heartbeat_interval_seconds: float


@dataclass(frozen=True)
class CommandResult:
    """Captured subprocess result from the launchctl/plutil boundary."""

    argv: list[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class LaunchAgentStatus:
    """Read-only LaunchAgent status evidence."""

    spec: LaunchAgentSpec
    installed: bool
    plist_current: bool
    expected_hash: str
    installed_hash: str
    plutil_ok: bool
    loaded: bool
    running: bool
    plutil_result: CommandResult | None
    launchctl_result: CommandResult


def build_launch_agent_spec(
    profile: str,
    *,
    saymo_executable: str | None = None,
    home: Path | None = None,
    uid: int | None = None,
    heartbeat_interval_seconds: float = 2.0,
) -> LaunchAgentSpec:
    """Build a deterministic per-profile LaunchAgent spec."""
    resolved_home = (home or Path.home()).expanduser()
    executable = _resolve_saymo_executable(saymo_executable)
    safe_profile = _safe_profile_fragment(profile)
    label = f"{LABEL_PREFIX}.{safe_profile}"
    plist_path = resolved_home / "Library" / "LaunchAgents" / f"{label}.plist"
    log_dir = resolved_home / ".saymo" / "live_control" / safe_profile / "logs"
    return LaunchAgentSpec(
        profile=str(profile or "default"),
        label=label,
        plist_path=plist_path,
        stdout_log_path=log_dir / f"{label}.out.log",
        stderr_log_path=log_dir / f"{label}.err.log",
        saymo_executable=executable,
        working_directory=str(Path.cwd()),
        home=str(resolved_home),
        path=os.environ.get("PATH") or DEFAULT_PATH,
        uid=os.getuid() if uid is None else int(uid),
        heartbeat_interval_seconds=float(heartbeat_interval_seconds),
    )


def render_launch_agent_plist(spec: LaunchAgentSpec) -> dict[str, object]:
    """Render the LaunchAgent plist payload as plistlib-compatible data."""
    return {
        "Label": spec.label,
        "ProgramArguments": [
            spec.saymo_executable,
            "call-control-daemon",
            "--profile",
            spec.profile,
            "--heartbeat-interval",
            str(spec.heartbeat_interval_seconds),
        ],
        "RunAtLoad": True,
        "KeepAlive": {"SuccessfulExit": False},
        "WorkingDirectory": spec.working_directory,
        "EnvironmentVariables": {
            "HOME": spec.home,
            "PATH": spec.path,
            "PYTHONUNBUFFERED": "1",
            "NO_PROXY": "localhost,127.0.0.1",
        },
        "StandardOutPath": str(spec.stdout_log_path),
        "StandardErrorPath": str(spec.stderr_log_path),
        "ThrottleInterval": 10,
    }


def expected_plist_bytes(spec: LaunchAgentSpec) -> bytes:
    """Return deterministic XML plist bytes for install and drift checks."""
    return plistlib.dumps(
        render_launch_agent_plist(spec),
        fmt=plistlib.FMT_XML,
        sort_keys=True,
    )


def expected_plist_hash(spec: LaunchAgentSpec) -> str:
    """Return the expected SHA-256 hash for the rendered plist."""
    return hashlib.sha256(expected_plist_bytes(spec)).hexdigest()


def installed_plist_hash(spec: LaunchAgentSpec) -> str:
    """Return the installed plist hash, or an empty string when missing."""
    if not spec.plist_path.exists():
        return ""
    return hashlib.sha256(spec.plist_path.read_bytes()).hexdigest()


def bootstrap_argv(spec: LaunchAgentSpec) -> list[str]:
    return [LAUNCHCTL, "bootstrap", f"gui/{spec.uid}", str(spec.plist_path)]


def bootout_argv(spec: LaunchAgentSpec) -> list[str]:
    return [LAUNCHCTL, "bootout", _service_domain(spec)]


def kickstart_argv(spec: LaunchAgentSpec, *, restart: bool = False) -> list[str]:
    argv = [LAUNCHCTL, "kickstart"]
    if restart:
        argv.append("-k")
    argv.append(_service_domain(spec))
    return argv


def print_argv(spec: LaunchAgentSpec) -> list[str]:
    return [LAUNCHCTL, "print", _service_domain(spec)]


def plutil_lint_argv(spec: LaunchAgentSpec) -> list[str]:
    return [PLUTIL, "-lint", str(spec.plist_path)]


def run_command(argv: list[str], *, check: bool = False) -> CommandResult:
    """Run one command through the injectable subprocess boundary."""
    completed = subprocess.run(
        argv,
        text=True,
        capture_output=True,
        check=False,
    )
    result = CommandResult(
        argv=list(argv),
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode,
            result.argv,
            output=result.stdout,
            stderr=result.stderr,
        )
    return result


def install_launch_agent(spec: LaunchAgentSpec, *, lint: bool = True) -> CommandResult | None:
    """Write the plist and log directory, then optionally lint the plist."""
    spec.plist_path.parent.mkdir(parents=True, exist_ok=True)
    spec.stdout_log_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = spec.plist_path.with_suffix(spec.plist_path.suffix + ".tmp")
    tmp_path.write_bytes(expected_plist_bytes(spec))
    tmp_path.replace(spec.plist_path)
    if lint:
        return run_command(plutil_lint_argv(spec), check=True)
    return None


def uninstall_launch_agent(spec: LaunchAgentSpec) -> CommandResult:
    """Boot out the LaunchAgent if loaded and remove the installed plist."""
    result = run_command(bootout_argv(spec), check=False)
    if spec.plist_path.exists():
        spec.plist_path.unlink()
    return result


def start_launch_agent(spec: LaunchAgentSpec) -> CommandResult:
    """Bootstrap the installed plist into the user GUI domain."""
    return run_command(bootstrap_argv(spec), check=True)


def stop_launch_agent(spec: LaunchAgentSpec) -> CommandResult:
    """Boot out the LaunchAgent service from the user GUI domain."""
    return run_command(bootout_argv(spec), check=True)


def restart_launch_agent(spec: LaunchAgentSpec) -> CommandResult:
    """Restart a loaded LaunchAgent service."""
    return run_command(kickstart_argv(spec, restart=True), check=True)


def collect_launch_agent_status(spec: LaunchAgentSpec) -> LaunchAgentStatus:
    """Collect read-only plist, plutil, and launchctl status evidence."""
    installed = spec.plist_path.exists()
    expected_hash = expected_plist_hash(spec)
    actual_hash = installed_plist_hash(spec)
    plutil_result = run_command(plutil_lint_argv(spec), check=False) if installed else None
    launchctl_result = run_command(print_argv(spec), check=False)
    loaded = launchctl_result.returncode == 0
    return LaunchAgentStatus(
        spec=spec,
        installed=installed,
        plist_current=installed and actual_hash == expected_hash,
        expected_hash=expected_hash,
        installed_hash=actual_hash,
        plutil_ok=bool(plutil_result and plutil_result.returncode == 0),
        loaded=loaded,
        running=loaded and _print_output_has_pid(launchctl_result.stdout),
        plutil_result=plutil_result,
        launchctl_result=launchctl_result,
    )


def _resolve_saymo_executable(explicit: str | None) -> str:
    if explicit:
        return str(Path(explicit).expanduser())
    resolved = shutil.which("saymo")
    if resolved:
        return resolved
    raise LaunchAgentError(
        "Could not find a saymo executable on PATH. Run from the Saymo "
        "environment or pass an explicit executable path."
    )


def _safe_profile_fragment(profile: str) -> str:
    raw = str(profile or "default").strip().lower()
    safe = re.sub(r"[^a-z0-9_.-]+", "-", raw)
    safe = re.sub(r"[-_.]{2,}", "-", safe).strip("-_.")
    return safe or "default"


def _service_domain(spec: LaunchAgentSpec) -> str:
    return f"gui/{spec.uid}/{spec.label}"


def _print_output_has_pid(output: str) -> bool:
    for line in output.splitlines():
        match = re.search(r"\bpid\s*=\s*(-?\d+)", line)
        if match:
            return int(match.group(1)) > 0
    return False
