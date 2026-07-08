"""Call-control daemon commands."""

from __future__ import annotations

import json
from pathlib import Path
from subprocess import CalledProcessError

import click

from saymo.analysis.control_daemon import (
    daemon_heartbeat_path,
    run_control_daemon,
    run_handbrake_reachability_probe,
)
from saymo.analysis.launch_agent import (
    LaunchAgentError,
    build_launch_agent_spec,
    collect_call_control_agent_status,
    install_launch_agent,
    restart_launch_agent,
    start_launch_agent,
    stop_launch_agent,
    uninstall_launch_agent,
)
from saymo.analysis.live_control import (
    append_control_command,
    normalize_action,
    sanitized_control_payload,
)
from saymo.commands import console, main


@main.command("call-control-daemon")
@click.option("--profile", "-p", default="standup", show_default=True)
@click.option(
    "--heartbeat-interval",
    type=float,
    default=2.0,
    show_default=True,
    help="Seconds between heartbeat writes.",
)
@click.option(
    "--base-dir",
    default=None,
    type=click.Path(path_type=Path),
    help="Override live-control directory; defaults to ~/.saymo/live_control.",
)
@click.option("--label", default="", help="Override daemon label in heartbeat.")
@click.option(
    "--once",
    is_flag=True,
    help="Write one heartbeat and exit; intended for tests and diagnostics.",
)
@click.pass_context
def call_control_daemon(ctx, profile, heartbeat_interval, base_dir, label, once):
    """Run the foreground call-control daemon for one profile."""
    if heartbeat_interval < 0:
        raise click.ClickException("--heartbeat-interval must be >= 0")
    exit_code = run_control_daemon(
        ctx.obj["config"],
        profile=profile,
        label=label,
        heartbeat_interval_seconds=heartbeat_interval,
        base_dir=base_dir,
        stop_after_heartbeats=1 if once else None,
    )
    console.print(
        f"daemon heartbeat: {daemon_heartbeat_path(profile, base_dir=base_dir)}",
        markup=False,
        soft_wrap=True,
    )
    raise click.exceptions.Exit(exit_code)


@main.group("call-control")
def call_control():
    """Queue call-control actions through the existing live-control queue."""


@call_control.command("action")
@click.option("--profile", "-p", default="standup", show_default=True)
@click.option(
    "--action",
    "action_name",
    required=True,
    help="Existing live-control action or alias.",
)
@click.option(
    "--probe-id",
    default="",
    help="Optional sanitized probe id to include in command metadata.",
)
@click.option(
    "--base-dir",
    default=None,
    type=click.Path(path_type=Path),
    help="Override live-control directory; defaults to ~/.saymo/live_control.",
)
def call_control_action(profile, action_name, probe_id, base_dir):
    """Queue one existing live-control action for a running `saymo auto`."""
    try:
        action = normalize_action(action_name)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    payload = sanitized_control_payload({"probe_id": probe_id})
    path = append_control_command(
        profile,
        action,
        source="daemon_cli",
        payload=payload,
        base_dir=base_dir,
    )
    console.print(f"queued: {action}")
    console.print(f"commands: {path}")


@call_control.command("probe")
@click.option("--profile", "-p", default="standup", show_default=True)
@click.option(
    "--base-dir",
    default=None,
    type=click.Path(path_type=Path),
    help="Override live-control directory; defaults to ~/.saymo/live_control.",
)
@click.option(
    "--timeout",
    type=float,
    default=2.0,
    show_default=True,
    help="Seconds to wait for daemon/audit evidence.",
)
@click.option("--json", "json_output", is_flag=True, help="Print machine-readable output.")
def call_control_probe(profile, base_dir, timeout, json_output):
    """Probe whether the call-control handbrake is reachable end-to-end."""
    if timeout < 0:
        raise click.ClickException("--timeout must be >= 0")
    probe = run_handbrake_reachability_probe(
        profile,
        base_dir=base_dir,
        timeout_seconds=timeout,
    )
    if json_output:
        click.echo(json.dumps(probe.to_dict(), indent=2, sort_keys=True))
    else:
        _print_probe_summary(probe)
    raise click.exceptions.Exit(0 if probe.ok else 1)


@main.group("call-control-agent")
def call_control_agent():
    """Manage the per-profile call-control LaunchAgent."""


@call_control_agent.command("install")
@click.option("--profile", "-p", default="standup", show_default=True)
def call_control_agent_install(profile):
    """Install or update the profile LaunchAgent plist."""
    spec = _agent_spec(profile)
    _run_agent_action(lambda: install_launch_agent(spec))
    _print_agent_summary("installed", spec)


@call_control_agent.command("uninstall")
@click.option("--profile", "-p", default="standup", show_default=True)
def call_control_agent_uninstall(profile):
    """Boot out the LaunchAgent and remove its plist."""
    spec = _agent_spec(profile)
    _run_agent_action(lambda: uninstall_launch_agent(spec))
    _print_agent_summary("uninstall", spec)


@call_control_agent.command("start")
@click.option("--profile", "-p", default="standup", show_default=True)
def call_control_agent_start(profile):
    """Bootstrap the installed LaunchAgent."""
    spec = _agent_spec(profile)
    _run_agent_action(lambda: start_launch_agent(spec))
    _print_agent_summary("start", spec)


@call_control_agent.command("stop")
@click.option("--profile", "-p", default="standup", show_default=True)
def call_control_agent_stop(profile):
    """Boot out the loaded LaunchAgent."""
    spec = _agent_spec(profile)
    _run_agent_action(lambda: stop_launch_agent(spec))
    _print_agent_summary("stop", spec)


@call_control_agent.command("restart")
@click.option("--profile", "-p", default="standup", show_default=True)
def call_control_agent_restart(profile):
    """Kickstart the loaded LaunchAgent."""
    spec = _agent_spec(profile)
    _run_agent_action(lambda: restart_launch_agent(spec))
    _print_agent_summary("restart", spec)


@call_control_agent.command("status")
@click.option("--profile", "-p", default="standup", show_default=True)
@click.option("--json", "json_output", is_flag=True, help="Print machine-readable status.")
def call_control_agent_status(profile, json_output):
    """Inspect LaunchAgent plist and launchd state without mutation."""
    spec = _agent_spec(profile)
    status = _run_agent_action(lambda: collect_call_control_agent_status(spec))
    if json_output:
        click.echo(json.dumps(status.to_dict(), indent=2, sort_keys=True))
        return
    _print_agent_summary(
        "status",
        spec,
        extra=[
            f"classification: {status.classification}",
            f"installed: {'yes' if status.installed else 'no'}",
            f"plist current: {'yes' if status.plist_current else 'no'}",
            f"loaded: {'yes' if status.loaded else 'no'}",
            f"heartbeat fresh: {'yes' if status.heartbeat_fresh else 'no'}",
            f"running: {'yes' if status.running else 'no'}",
            f"hotkeys active: {'yes' if status.hotkeys_active else 'no'}",
            f"hotkey registration: {status.hotkey_registration_status}",
            f"detail: {status.detail}",
            f"action: {status.action}",
            f"rerun: {status.rerun}",
        ],
    )


def _agent_spec(profile: str):
    try:
        return build_launch_agent_spec(profile)
    except LaunchAgentError as exc:
        raise click.ClickException(str(exc)) from exc


def _run_agent_action(action):
    try:
        return action()
    except CalledProcessError as exc:
        detail = (exc.stderr or exc.output or str(exc)).strip()
        if detail:
            raise click.ClickException(detail) from exc
        raise click.ClickException(f"command failed with exit {exc.returncode}") from exc


def _print_agent_summary(action: str, spec, *, extra: list[str] | None = None) -> None:
    lines = [
        f"{action}: {spec.label}",
        f"plist: {spec.plist_path}",
        f"stdout: {spec.stdout_log_path}",
        f"stderr: {spec.stderr_log_path}",
    ]
    lines.extend(extra or [])
    console.print("\n".join(lines), markup=False, soft_wrap=True)


def _print_probe_summary(probe) -> None:
    lines = [
        f"probe: {'reachable' if probe.ok else 'not reachable'}",
        f"detail: {probe.detail}",
        f"probe id: {probe.probe_id}",
        f"heartbeat fresh: {'yes' if probe.heartbeat_fresh else 'no'}",
        f"hotkeys active: {'yes' if probe.hotkeys_active else 'no'}",
        f"command written: {'yes' if probe.command_written else 'no'}",
        f"command consumed: {'yes' if probe.command_consumed else 'no'}",
        f"audit applied: {'yes' if probe.audit_applied else 'no'}",
        f"commands: {probe.command_log_path}",
        f"audit: {probe.audit_log_path}",
        f"stdout: {probe.stdout_log_path}",
        f"stderr: {probe.stderr_log_path}",
    ]
    console.print("\n".join(lines), markup=False, soft_wrap=True)
