"""Launch-readiness checks for response cache and cloned voice metadata."""

from __future__ import annotations

from pathlib import Path

from saymo.analysis.cache_advice import response_cache_advice
from saymo.analysis.cache_metadata import build_voice_cache_metadata
from saymo.analysis.launch_readiness import LaunchReadinessCheck
from saymo.analysis.response_cache import (
    ResponseCache,
    build_library,
    response_cache_coverage,
)
from saymo.tts.selector import resolve_voice_selector


def collect_response_cache_check(
    config,
    *,
    profile: str,
    provider_name: str,
) -> LaunchReadinessCheck:
    """Build a strict, privacy-safe response-cache coverage check."""
    rerun = _rerun_command(profile, provider_name)
    cache_dir = Path(config.responses.cache_dir) if config.responses.cache_dir else None

    if not config.responses.enabled:
        return LaunchReadinessCheck(
            key="response_cache_coverage",
            label="response cache coverage",
            severity="block",
            ok=False,
            detail="response_cache_disabled",
            action="Set responses.enabled=true, then run saymo prepare-responses",
            rerun=rerun,
            metadata={
                "ready": 0,
                "total": 0,
                "missing_examples": [],
                "stale_examples": [],
                "cache_dir": str(cache_dir) if cache_dir else "",
            },
        )

    library = build_library(config.responses.library)
    cache = ResponseCache(
        library=library,
        cache_dir=cache_dir,
        confidence_threshold=config.responses.confidence_threshold,
        voice_metadata=build_voice_cache_metadata(config, purpose="response_cache"),
    )
    coverage = response_cache_coverage(cache)
    ok = coverage.ready == coverage.total
    advice = response_cache_advice(config, profile=profile)
    return LaunchReadinessCheck(
        key="response_cache_coverage",
        label="response cache coverage",
        severity="block",
        ok=ok,
        detail=f"{coverage.ready}/{coverage.total} variants ready",
        action="" if ok else _response_cache_action(advice),
        rerun="" if ok else rerun,
        metadata={
            "ready": coverage.ready,
            "total": coverage.total,
            "missing_examples": list(coverage.missing),
            "stale_examples": list(coverage.stale),
            "missing_count": len(coverage.missing),
            "stale_count": len(coverage.stale),
            "cost_warning": advice.warning,
            "cache_dir": str(coverage.cache_dir) if coverage.cache_dir else "",
        },
    )


def collect_voice_metadata_check(
    config,
    *,
    profile: str,
    provider_name: str,
) -> LaunchReadinessCheck:
    """Build a strict, privacy-safe cloned-voice metadata check."""
    decision = resolve_voice_selector(config, purpose="live_call")
    ok = decision.allowed and decision.is_voice_clone and decision.profile_approved
    blocked_reason = _voice_blocked_reason(decision)
    return LaunchReadinessCheck(
        key="cloned_voice_metadata",
        label="cloned voice metadata",
        severity="block",
        ok=ok,
        detail="ready" if ok else blocked_reason,
        action="" if ok else "Approve a cloned voice profile for live calls",
        rerun="" if ok else _rerun_command(profile, provider_name),
        metadata={
            "selected_engine": decision.selected_engine,
            "voice_profile": decision.profile,
            "profile_approved": decision.profile_approved,
            "reference_audio_sha256": decision.reference_audio_sha256,
            "reference_text_sha256": decision.reference_text_sha256,
            "reference_fingerprint": decision.reference_fingerprint,
            "blocked_reason": "" if ok else blocked_reason,
        },
    )


def _voice_blocked_reason(decision) -> str:
    if decision.allowed and decision.is_voice_clone and decision.profile_approved:
        return ""
    if decision.blocked_reason:
        return decision.blocked_reason
    if not decision.is_voice_clone:
        return "engine_not_voice_clone"
    if not decision.profile_approved:
        return "voice_profile_unapproved"
    return "voice_selector_blocked"


def _rerun_command(profile: str, provider_name: str) -> str:
    return f"saymo call-ready -p {profile} --provider {provider_name}"


def _response_cache_action(advice) -> str:
    if advice.warning:
        return f"{advice.action} {advice.warning}"
    return advice.action
