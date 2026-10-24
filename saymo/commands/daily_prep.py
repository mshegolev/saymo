"""Scheduled meeting prep: `saymo daily-prep` and its LaunchAgent.

`daily-prep` runs `prepare`, best-effort opens the call app, and shows the
floating prep window (text + Play/Stop). `daily-prep-agent` installs a
per-profile macOS LaunchAgent that fires `daily-prep` unattended at the
meeting's configured `schedule.time`/`schedule.days`.
"""

from __future__ import annotations

import json
import subprocess
from subprocess import CalledProcessError

import click

from saymo.analysis.prep_launch_agent import (
    LaunchAgentError,
    build_prep_agent_spec,
    collect_prep_agent_status,
    install_prep_agent,
    restart_prep_agent,
    start_prep_agent,
    stop_prep_agent,
    uninstall_prep_agent,
)
from saymo.commands import _get_cached_audio_path, _get_cached_text_path, console, main, run_async
from saymo.commands.core import _prepare, _prepare_team


@main.command("daily-prep")
@click.option("--profile", "-p", default="standup", show_default=True, help="Meeting profile.")
@click.option("--no-window", is_flag=True, help="Prepare and open the call app, skip the prep window.")
@click.pass_context
def daily_prep(ctx, profile, no_window):
    """Prepare speech, best-effort open the call app, show the prep window.

    Intended to run unattended from `daily-prep-agent`'s LaunchAgent, but can
    also be run by hand any time before a meeting.
    """
    config = ctx.obj["config"]
    meeting = config.get_meeting(profile)
    if not meeting:
        raise click.ClickException(
            f"Unknown profile: {profile}. Available: {', '.join(config.list_meetings())}"
        )
    config.speech.source = meeting.source
    console.print(f"[bold blue]Daily prep: {profile} — {meeting.description}[/]")

    if meeting.team:
        text = run_async(_prepare_team(config, save=False, profile_name=profile))
    else:
        text = run_async(_prepare(config, save=False, profile_name=profile))

    if not text:
        text_path = _get_cached_text_path(team=meeting.team)
        text = text_path.read_text(encoding="utf-8") if text_path.exists() else ""

    if meeting.meeting_url:
        try:
            subprocess.run(["open", meeting.meeting_url], check=False)
            console.print(f"[dim]Opened: {meeting.meeting_url}[/]")
        except OSError as exc:
            console.print(f"[yellow]Could not open meeting URL: {exc}[/]")

    if no_window:
        return

    from saymo.ui.prep_window import run_prep_window

    run_prep_window(
        profile_name=profile,
        meeting_description=meeting.description,
        prepared_text=text or "(текст не подготовлен — проверь источник заметок)",
        config=config,
        audio_path=_get_cached_audio_path(team=meeting.team),
        provider_name=meeting.provider,
        recording_device=config.audio.recording_device,
    )


@main.group("daily-prep-agent")
def daily_prep_agent():
    """Manage the per-profile scheduled daily-prep LaunchAgent."""


@daily_prep_agent.command("install")
@click.option("--profile", "-p", default="standup", show_default=True)
@click.pass_context
def daily_prep_agent_install(ctx, profile):
    """Install or update the profile's scheduled prep LaunchAgent plist."""
    spec = _agent_spec(ctx.obj["config"], profile)
    _run_agent_action(lambda: install_prep_agent(spec))
    _print_agent_summary("installed", spec)


@daily_prep_agent.command("uninstall")
@click.option("--profile", "-p", default="standup", show_default=True)
@click.pass_context
def daily_prep_agent_uninstall(ctx, profile):
    """Boot out the LaunchAgent and remove its plist."""
    spec = _agent_spec(ctx.obj["config"], profile)
    _run_agent_action(lambda: uninstall_prep_agent(spec))
    _print_agent_summary("uninstall", spec)


@daily_prep_agent.command("start")
@click.option("--profile", "-p", default="standup", show_default=True)
@click.pass_context
def daily_prep_agent_start(ctx, profile):
    """Bootstrap the installed LaunchAgent."""
    spec = _agent_spec(ctx.obj["config"], profile)
    _run_agent_action(lambda: start_prep_agent(spec))
    _print_agent_summary("start", spec)


@daily_prep_agent.command("stop")
@click.option("--profile", "-p", default="standup", show_default=True)
@click.pass_context
def daily_prep_agent_stop(ctx, profile):
    """Boot out the loaded LaunchAgent."""
    spec = _agent_spec(ctx.obj["config"], profile)
    _run_agent_action(lambda: stop_prep_agent(spec))
    _print_agent_summary("stop", spec)


@daily_prep_agent.command("restart")
@click.option("--profile", "-p", default="standup", show_default=True)
@click.pass_context
def daily_prep_agent_restart(ctx, profile):
    """Kickstart the loaded LaunchAgent."""
    spec = _agent_spec(ctx.obj["config"], profile)
    _run_agent_action(lambda: restart_prep_agent(spec))
    _print_agent_summary("restart", spec)


@daily_prep_agent.command("status")
@click.option("--profile", "-p", default="standup", show_default=True)
@click.option("--json", "json_output", is_flag=True, help="Print machine-readable status.")
@click.pass_context
def daily_prep_agent_status(ctx, profile, json_output):
    """Inspect LaunchAgent plist and launchd state without mutation."""
    spec = _agent_spec(ctx.obj["config"], profile)
    status = _run_agent_action(lambda: collect_prep_agent_status(spec))
    if json_output:
        click.echo(json.dumps(status.to_dict(), indent=2, sort_keys=True))
        return
    _print_agent_summary(
        "status",
        spec,
        extra=[
            f"installed: {'yes' if status.installed else 'no'}",
            f"plist current: {'yes' if status.plist_current else 'no'}",
            f"loaded: {'yes' if status.loaded else 'no'}",
            f"running: {'yes' if status.running else 'no'}",
            f"next fire: {status.next_fire}",
            f"secrets baked in: {', '.join(sorted(spec.secret_env)) or '(none)'}",
        ],
    )


def _agent_spec(config, profile):
    try:
        return build_prep_agent_spec(profile, config)
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
