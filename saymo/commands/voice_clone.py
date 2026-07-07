"""Voice clone inventory and profile commands."""

from __future__ import annotations

from pathlib import Path

import click
from rich.table import Table

from saymo.commands import console, main


@main.command("voice-inventory")
@click.option("--saymo-home", type=click.Path(), default=None, help="Override ~/.saymo root for inventory.")
@click.option("--f5-root", type=click.Path(), default=None, help="Override ~/F5TTS root for inventory.")
@click.option("--json-output", type=click.Path(), default=None, help="Write sanitized inventory JSON.")
@click.pass_context
def voice_inventory(ctx, saymo_home, f5_root, json_output):
    """Inspect local voice assets without mutating them."""
    from saymo.analysis.voice_inventory import (
        build_voice_inventory,
        render_voice_inventory_markdown,
        write_voice_inventory_json,
    )

    report = build_voice_inventory(
        ctx.obj["config"],
        saymo_home=Path(saymo_home) if saymo_home else None,
        f5_root=Path(f5_root) if f5_root else None,
    )

    console.print("[bold blue]Voice inventory[/]")
    console.print(render_voice_inventory_markdown(report), markup=False)
    if json_output:
        out = write_voice_inventory_json(json_output, report)
        console.print(f"[green]Wrote JSON:[/] {out}")


@main.group("voice-profile")
def voice_profile():
    """Manage local voice profile manifests."""


@voice_profile.command("init")
@click.option("--profile", "-p", required=True, help="Voice profile id.")
@click.option("--voice-sample", type=click.Path(), required=True, help="Existing reference WAV.")
@click.option("--ref-text-file", type=click.Path(), required=True, help="Existing transcript sidecar.")
@click.option("--engine", required=True, help="Known TTS engine key.")
@click.option("--profiles-dir", type=click.Path(), default=None, help="Override voice profiles root.")
@click.option("--dry-run", "dry_run", is_flag=True, help="Show proposed manifest without writing.")
@click.option("--apply", "apply_changes", is_flag=True, help="Write the manifest.")
@click.pass_context
def voice_profile_init(
    ctx,
    profile,
    voice_sample,
    ref_text_file,
    engine,
    profiles_dir,
    dry_run,
    apply_changes,
):
    """Create or update a voice profile manifest."""
    from saymo.analysis.voice_profile import (
        build_voice_profile_manifest,
        voice_profile_to_json,
        write_voice_profile_manifest,
    )

    if dry_run and apply_changes:
        raise click.ClickException("Use either --dry-run or --apply, not both.")
    if not dry_run and not apply_changes:
        dry_run = True

    config = ctx.obj["config"]
    manifest = build_voice_profile_manifest(
        profile=profile,
        voice_sample=voice_sample,
        ref_text_file=ref_text_file,
        engine=engine,
        language=config.speech.language,
    )

    if dry_run:
        console.print("[bold yellow]Dry-run voice profile manifest[/]")
        _print_profile_summary(manifest)
        console.print("[dim]No files written. Re-run with --apply to save.[/]")
        return

    out = write_voice_profile_manifest(
        manifest,
        profiles_dir=Path(profiles_dir) if profiles_dir else None,
    )
    console.print(f"[bold green]Wrote voice profile:[/] {out}")
    _print_profile_summary(manifest)


@voice_profile.command("show")
@click.option("--profile", "-p", required=True, help="Voice profile id.")
@click.option("--profiles-dir", type=click.Path(), default=None, help="Override voice profiles root.")
def voice_profile_show(profile, profiles_dir):
    """Show a saved voice profile manifest."""
    from saymo.analysis.voice_profile import load_voice_profile_manifest

    manifest = load_voice_profile_manifest(
        profile,
        profiles_dir=Path(profiles_dir) if profiles_dir else None,
    )
    console.print(f"approved for calls: {'yes' if manifest.approved_for_calls else 'no'}")
    _print_profile_summary(manifest)


@voice_profile.command("check")
@click.option("--profile", "-p", required=True, help="Voice profile id.")
@click.option("--profiles-dir", type=click.Path(), default=None, help="Override voice profiles root.")
def voice_profile_check(profile, profiles_dir):
    """Check saved voice profile references."""
    from saymo.analysis.voice_profile import check_voice_profile, load_voice_profile_manifest

    manifest = load_voice_profile_manifest(
        profile,
        profiles_dir=Path(profiles_dir) if profiles_dir else None,
    )
    check = check_voice_profile(manifest)
    console.print(f"voice profile: {check.profile}")
    console.print(f"status: {check.status}")
    for blocker in check.blockers:
        console.print(f"[red]blocker:[/] {blocker}")
    for warning in check.warnings:
        console.print(f"[yellow]warning:[/] {warning}")


@voice_profile.command("approve")
@click.option("--profile", "-p", required=True, help="Voice profile id.")
@click.option("--profiles-dir", type=click.Path(), default=None, help="Override voice profiles root.")
@click.option("--score-report", type=click.Path(exists=True), required=True, help="Completed scored score-report.md.")
@click.option("--similarity", type=float, required=True, help="Manual similarity score, 0-10.")
@click.option("--artifacts", type=float, required=True, help="Manual artifact score, 0-10; higher is cleaner.")
@click.option("--call-readiness", type=float, required=True, help="Manual call-readiness score, 0-10.")
@click.option("--override-reason", default="", help="Required when approving below the 7/10 gate.")
@click.option("--dry-run", "dry_run", is_flag=True, help="Validate without writing.")
@click.option("--apply", "apply_changes", is_flag=True, help="Write approval to the profile manifest.")
def voice_profile_approve(
    profile,
    profiles_dir,
    score_report,
    similarity,
    artifacts,
    call_readiness,
    override_reason,
    dry_run,
    apply_changes,
):
    """Approve a voice profile for live calls using benchmark evidence."""
    from saymo.analysis.voice_approval import approve_voice_profile

    if dry_run and apply_changes:
        raise click.ClickException("Use either --dry-run or --apply, not both.")
    if not dry_run and not apply_changes:
        dry_run = True
    if dry_run:
        console.print("[bold yellow]Dry-run voice profile approval[/]")
        console.print("[dim]No files written. Re-run with --apply to save.[/]")
        return
    try:
        manifest = approve_voice_profile(
            profile=profile,
            profiles_dir=Path(profiles_dir) if profiles_dir else None,
            score_report=score_report,
            similarity=similarity,
            artifacts=artifacts,
            call_readiness=call_readiness,
            override_reason=override_reason,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    console.print("[bold green]Voice profile approved[/]")
    console.print(f"approved for calls: {'yes' if manifest.approved_for_calls else 'no'}")
    console.print(f"score report: {manifest.approved_benchmark_run}")


@voice_profile.command("reject")
@click.option("--profile", "-p", required=True, help="Voice profile id.")
@click.option("--profiles-dir", type=click.Path(), default=None, help="Override voice profiles root.")
@click.option("--score-report", type=click.Path(exists=True), required=True, help="Completed scored score-report.md.")
@click.option("--reason", required=True, help="Why this profile/engine was rejected.")
@click.option("--dry-run", "dry_run", is_flag=True, help="Validate without writing.")
@click.option("--apply", "apply_changes", is_flag=True, help="Write rejection to the profile manifest.")
def voice_profile_reject(profile, profiles_dir, score_report, reason, dry_run, apply_changes):
    """Reject a voice profile and clear live-call approval."""
    from saymo.analysis.voice_approval import reject_voice_profile

    if dry_run and apply_changes:
        raise click.ClickException("Use either --dry-run or --apply, not both.")
    if not dry_run and not apply_changes:
        dry_run = True
    if dry_run:
        console.print("[bold yellow]Dry-run voice profile rejection[/]")
        console.print("[dim]No files written. Re-run with --apply to save.[/]")
        return
    try:
        manifest = reject_voice_profile(
            profile=profile,
            profiles_dir=Path(profiles_dir) if profiles_dir else None,
            score_report=score_report,
            reason=reason,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    console.print("[bold yellow]Voice profile rejected[/]")
    console.print(f"approved for calls: {'yes' if manifest.approved_for_calls else 'no'}")
    console.print(f"score report: {manifest.approved_benchmark_run}")


@main.command("voice-preview")
@click.option("--profile", "-p", required=True, help="Voice profile id.")
@click.option("--profiles-dir", type=click.Path(), default=None, help="Override voice profiles root.")
@click.option("--text", required=True, help="Preview text. Stored only as a hash in audit metadata.")
@click.option("--dry-run", is_flag=True, help="Write preview audit without synthesizing audio.")
@click.pass_context
def voice_preview(ctx, profile, profiles_dir, text, dry_run):
    """Preview cloned voice locally and write preview-only audit metadata."""
    from saymo.analysis.voice_approval import write_voice_preview_audit

    config = ctx.obj["config"]
    out = write_voice_preview_audit(
        config,
        profile=profile,
        text=text,
        profiles_dir=Path(profiles_dir) if profiles_dir else None,
    )
    console.print(f"[bold green]Preview-only audit:[/] {out}")
    if dry_run:
        return
    from saymo.commands.core import _speak_text, run_async

    run_async(_speak_text(config, text, purpose="preview"))


def _print_profile_summary(manifest) -> None:
    table = Table("Field", "Value")
    table.add_row("profile", manifest.profile)
    table.add_row("engine", manifest.engine)
    table.add_row("language", manifest.language)
    table.add_row("voice sample", manifest.reference_audio.path)
    table.add_row("voice sample sha", manifest.reference_audio.sha256[:12])
    table.add_row("sample rate", str(manifest.reference_audio.sample_rate or "unknown"))
    table.add_row("transcript", manifest.reference_text.path)
    table.add_row("transcript chars", str(manifest.reference_text.chars))
    table.add_row("approved for calls", "yes" if manifest.approved_for_calls else "no")
    table.add_row("approved benchmark", manifest.approved_benchmark_run or "(none)")
    table.add_row("fallback policy", manifest.fallback_policy)
    console.print(table)
