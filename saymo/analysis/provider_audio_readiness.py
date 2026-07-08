"""Provider and audio launch-readiness helpers."""

from __future__ import annotations

from typing import Any

from saymo.analysis.launch_readiness import LaunchReadinessCheck
from saymo.audio import devices as audio_devices
from saymo.providers import factory as provider_factory
from saymo.providers.base import MeetingStatus


_PROVIDER_OUTPUT_DEVICE = "BlackHole 2ch"
_CAPTURE_ROUTE_DEVICE = "BlackHole 16ch"


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
        *collect_audio_route_checks(
            config,
            profile=profile,
            provider_name=provider_name,
        ),
    )


def collect_audio_route_checks(
    config,
    *,
    profile: str,
    provider_name: str,
) -> tuple[LaunchReadinessCheck, ...]:
    """Check configured audio routes without changing system audio state."""
    audio_config = getattr(config, "audio", None)
    capture_name = _config_text(audio_config, "capture_device")
    playback_name = _config_text(audio_config, "playback_device")
    recording_name = _config_text(audio_config, "recording_device")

    capture = (
        audio_devices.find_device(capture_name, kind="input")
        if capture_name
        else None
    )
    playback = (
        audio_devices.find_device(playback_name, kind="output")
        if playback_name
        else None
    )
    provider_output = audio_devices.find_device(
        _PROVIDER_OUTPUT_DEVICE,
        kind="output",
    )
    capture_route = audio_devices.find_device(
        _CAPTURE_ROUTE_DEVICE,
        kind="input",
    )
    recording = (
        audio_devices.find_device(recording_name, kind="input")
        if recording_name
        else None
    )

    return (
        _audio_route_check(
            key="capture_input_device",
            label="capture input device",
            device_name=capture_name,
            kind="input",
            device=capture,
            action=(
                "Run saymo test-devices and set audio.capture_device "
                "to a visible input device"
            ),
            rerun=_rerun(profile, provider_name),
        ),
        _audio_route_check(
            key="playback_output_device",
            label="playback output device",
            device_name=playback_name,
            kind="output",
            device=playback,
            action=(
                "Run saymo test-devices and set audio.playback_device "
                "to a visible output device"
            ),
            rerun=_rerun(profile, provider_name),
        ),
        _audio_route_check(
            key="provider_output_blackhole",
            label="provider output BlackHole",
            device_name=_PROVIDER_OUTPUT_DEVICE,
            kind="output",
            device=provider_output,
            action="Run saymo test-devices and install BlackHole 2ch/16ch if missing",
            rerun=_rerun(profile, provider_name),
        ),
        _audio_route_check(
            key="capture_route_blackhole",
            label="capture route BlackHole",
            device_name=_CAPTURE_ROUTE_DEVICE,
            kind="input",
            device=capture_route,
            action="Run saymo test-devices and install BlackHole 2ch/16ch if missing",
            rerun=_rerun(profile, provider_name),
        ),
        _audio_route_check(
            key="recording_microphone_input",
            label="recording microphone input",
            device_name=recording_name,
            kind="input",
            device=recording,
            action=(
                "Run saymo test-devices and set audio.recording_device "
                "to the real microphone used for takeover"
            ),
            rerun=_rerun(profile, provider_name),
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


def _audio_route_check(
    *,
    key: str,
    label: str,
    device_name: str,
    kind: str,
    device: Any | None,
    action: str,
    rerun: str,
) -> LaunchReadinessCheck:
    found = device is not None
    return LaunchReadinessCheck(
        key=key,
        label=label,
        severity="block",
        ok=found,
        detail="device_found" if found else "device_not_found",
        action="" if found else action,
        rerun="" if found else rerun,
        metadata=_audio_metadata(
            device_name=device_name,
            kind=kind,
            required=True,
            device=device,
        ),
    )


def _audio_metadata(
    *,
    device_name: str,
    kind: str,
    required: bool,
    device: Any | None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "category": "audio-device",
        "device_name": device_name,
        "kind": kind,
        "required": required,
        "found": device is not None,
    }
    if device is not None:
        metadata["device"] = {
            "index": getattr(device, "index", None),
            "name": getattr(device, "name", None),
            "max_input_channels": getattr(device, "max_input_channels", None),
            "max_output_channels": getattr(device, "max_output_channels", None),
            "default_samplerate": getattr(device, "default_samplerate", None),
        }
    return metadata


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


def _config_text(config: Any, field: str) -> str:
    value = getattr(config, field, "")
    return str(value or "").strip()


def _is_unknown_provider(exc: Exception) -> bool:
    return isinstance(exc, ValueError) and "Unknown provider" in str(exc)
