"""Voice profile approval and preview audit helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from saymo.analysis.voice_benchmark import require_completed_score_report
from saymo.analysis.voice_profile import (
    VoiceProfileManifest,
    check_voice_profile,
    load_voice_profile_manifest,
    write_voice_profile_manifest,
)
from saymo.config import SaymoConfig
from saymo.tts.selector import resolve_voice_selector

APPROVAL_GATE = 7.0


def approve_voice_profile(
    *,
    profile: str,
    profiles_dir: str | Path | None,
    score_report: str | Path,
    similarity: float,
    artifacts: float,
    call_readiness: float,
    override_reason: str = "",
) -> VoiceProfileManifest:
    """Approve a voice profile for live calls from explicit score evidence."""
    score_path = _validate_score_report(score_report)
    manifest = load_voice_profile_manifest(profile, profiles_dir=profiles_dir)
    profile_check = check_voice_profile(manifest)
    if profile_check.blockers:
        raise ValueError("; ".join(profile_check.blockers))
    failed = _failed_gates(
        similarity=similarity,
        artifacts=artifacts,
        call_readiness=call_readiness,
    )
    if failed and not override_reason.strip():
        raise ValueError("approval gates failed: " + ", ".join(failed))

    policy = (
        f"approved: score_report={score_path}; "
        f"similarity={similarity:g}; artifacts={artifacts:g}; "
        f"call_readiness={call_readiness:g}"
    )
    if override_reason.strip():
        policy += f"; override={override_reason.strip()}"
    updated = replace(
        manifest,
        approved_for_calls=True,
        approved_benchmark_run=str(score_path),
        fallback_policy=policy,
        updated_at=_now(),
    )
    write_voice_profile_manifest(updated, profiles_dir=profiles_dir)
    return updated


def reject_voice_profile(
    *,
    profile: str,
    profiles_dir: str | Path | None,
    score_report: str | Path,
    reason: str,
) -> VoiceProfileManifest:
    """Reject a profile and clear call approval."""
    score_path = _validate_score_report(score_report)
    manifest = load_voice_profile_manifest(profile, profiles_dir=profiles_dir)
    updated = replace(
        manifest,
        approved_for_calls=False,
        approved_benchmark_run=str(score_path),
        fallback_policy=f"rejected: {reason.strip() or 'no reason provided'}",
        updated_at=_now(),
    )
    write_voice_profile_manifest(updated, profiles_dir=profiles_dir)
    return updated


def write_voice_preview_audit(
    config: SaymoConfig,
    *,
    profile: str,
    text: str,
    profiles_dir: str | Path | None = None,
    audit_dir: str | Path | None = None,
) -> Path:
    """Write preview-only audit metadata without storing the preview text."""
    if profiles_dir is not None:
        config.voice_selector.profiles_dir = str(Path(profiles_dir).expanduser())
    config.voice_selector.default_profile = profile
    selector = resolve_voice_selector(config, purpose="preview")
    root = Path(audit_dir).expanduser() if audit_dir else _preview_dir(profile, profiles_dir)
    root.mkdir(parents=True, exist_ok=True)
    out = root / f"{_stamp()}-preview.json"
    payload: dict[str, Any] = {
        "created_at": _now(),
        "profile": profile,
        "preview_only": True,
        "selector": selector.to_metadata(),
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def _validate_score_report(score_report: str | Path) -> Path:
    path = Path(score_report).expanduser()
    require_completed_score_report(path, label="voice approval")
    text = path.read_text(encoding="utf-8")
    if "promotion ready: yes" not in text:
        raise ValueError(f"voice approval score report is not promotion-ready: {path}")
    return path


def _failed_gates(*, similarity: float, artifacts: float, call_readiness: float) -> list[str]:
    failed = []
    if float(similarity) < APPROVAL_GATE:
        failed.append("similarity")
    if float(artifacts) < APPROVAL_GATE:
        failed.append("artifacts")
    if float(call_readiness) < APPROVAL_GATE:
        failed.append("call_readiness")
    return failed


def _preview_dir(profile: str, profiles_dir: str | Path | None) -> Path:
    root = Path(profiles_dir).expanduser() if profiles_dir else Path.home() / ".saymo" / "voice_profiles"
    return root / profile / "previews"


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
