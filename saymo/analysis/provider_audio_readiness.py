"""Provider and audio launch-readiness helpers."""

from __future__ import annotations

from typing import Any

from saymo.analysis.launch_readiness import LaunchReadinessCheck
from saymo.providers import factory as provider_factory
from saymo.providers.base import MeetingStatus


def collect_provider_audio_checks(
    config,
    *,
    profile: str,
    provider_name: str,
) -> tuple[LaunchReadinessCheck, ...]:
    """Collect provider/audio checks for the shared launch gate."""
    return (
        collect_provider_tab_check(
            config,
            profile=profile,
            provider_name=provider_name,
        ),
    )


def collect_provider_tab_check(
    config,
    *,
    profile: str,
    provider_name: str,
) -> LaunchReadinessCheck:
    """Check whether the configured provider has a meeting tab ready."""
    del config
    rerun = _rerun(profile, provider_name)
    try:
        provider = provider_factory.get_provider(provider_name)
    except Exception as exc:
        if _is_unknown_provider(exc):
            return _blocked_check(
                configured_provider=provider_name,
                provider_name=provider_name,
                detail="unknown_provider",
                action="Use a supported provider name, then rerun saymo call-ready",
                rerun=rerun,
                error_type=type(exc).__name__,
            )
        return _blocked_check(
            configured_provider=provider_name,
            provider_name=provider_name,
            detail="provider_check_error",
            action=(
                "Open Chrome, allow provider automation permissions, "
                "then rerun saymo call-ready"
            ),
            rerun=rerun,
            error_type=type(exc).__name__,
        )

    resolved_provider = _provider_name(provider, provider_name)
    url_pattern = _provider_url_pattern(provider)
    try:
        status = provider.check_ready()
    except Exception as exc:
        return _blocked_check(
            configured_provider=provider_name,
            provider_name=resolved_provider,
            detail="provider_check_error",
            action=(
                "Open Chrome, allow provider automation permissions, "
                "then rerun saymo call-ready"
            ),
            rerun=rerun,
            error_type=type(exc).__name__,
            url_pattern=url_pattern,
        )

    return _check_from_status(
        configured_provider=provider_name,
        provider_name=resolved_provider,
        url_pattern=url_pattern,
        status=status,
        rerun=rerun,
    )


def _check_from_status(
    *,
    configured_provider: str,
    provider_name: str,
    url_pattern: str | None,
    status: MeetingStatus,
    rerun: str,
) -> LaunchReadinessCheck:
    meeting_found = bool(status.meeting_found)
    return LaunchReadinessCheck(
        key="provider_meeting_tab",
        label="provider meeting tab",
        severity="block",
        ok=meeting_found,
        detail="meeting_found" if meeting_found else "meeting_tab_not_found",
        action="" if meeting_found else f"Open the {provider_name} meeting in Chrome",
        rerun="" if meeting_found else rerun,
        metadata=_metadata(
            configured_provider=configured_provider,
            provider_name=provider_name,
            url_pattern=url_pattern,
            status=status,
        ),
    )


def _blocked_check(
    *,
    configured_provider: str,
    provider_name: str,
    detail: str,
    action: str,
    rerun: str,
    error_type: str,
    url_pattern: str | None = None,
) -> LaunchReadinessCheck:
    return LaunchReadinessCheck(
        key="provider_meeting_tab",
        label="provider meeting tab",
        severity="block",
        ok=False,
        detail=detail,
        action=action,
        rerun=rerun,
        metadata=_metadata(
            configured_provider=configured_provider,
            provider_name=provider_name,
            url_pattern=url_pattern,
            status=MeetingStatus(),
            error_type=error_type,
        ),
    )


def _metadata(
    *,
    configured_provider: str,
    provider_name: str,
    url_pattern: str | None,
    status: MeetingStatus,
    error_type: str | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "category": "provider",
        "provider_name": provider_name,
        "configured_provider": configured_provider,
        "url_pattern": url_pattern,
        "meeting_found": bool(status.meeting_found),
        "app_running": bool(status.app_running),
        "tab_info": list(status.tab_info) if status.tab_info else None,
    }
    if error_type:
        metadata["error_type"] = error_type
    return metadata


def _provider_name(provider: Any, configured_provider: str) -> str:
    value = getattr(provider, "name", configured_provider)
    return str(value or configured_provider)


def _provider_url_pattern(provider: Any) -> str | None:
    value = getattr(provider, "url_pattern", None)
    if value is None:
        return None
    text = str(value)
    return text or None


def _rerun(profile: str, provider_name: str) -> str:
    return f"saymo call-ready -p {profile} --provider {provider_name}"


def _is_unknown_provider(exc: Exception) -> bool:
    return isinstance(exc, ValueError) and "Unknown provider" in str(exc)
