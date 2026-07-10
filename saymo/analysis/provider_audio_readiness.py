"""Provider and audio launch-readiness helpers."""

from __future__ import annotations

from typing import Any

import sounddevice as sd

from saymo.analysis.launch_readiness import LaunchReadinessCheck
from saymo.analysis import live_control
from saymo.audio import devices as audio_devices
from saymo.providers import factory as provider_factory
from saymo.providers._chrome_base import ChromeCallProvider
from saymo.providers.base import MeetingStatus


_PROVIDER_OUTPUT_DEVICE = "BlackHole 2ch"
_CAPTURE_ROUTE_DEVICE = "BlackHole 16ch"
_MIC_SWITCH_PROVIDER_CLASSES = {"GlipProvider", "MTSLinkProvider"}
_CHROME_PERMISSION_MARKERS = (
    "applescript",
    "automation",
    "chrome",
    "google chrome",
    "not authorized",
    "not authorised",
    "osascript",
    "permission",
    "accessibility",
    "denied",
)


def collect_provider_audio_checks(
    config,
    *,
    profile: str,
    provider_name: str,
    rerun_command: str | None = None,
    mode: str = "call-ready",
) -> tuple[LaunchReadinessCheck, ...]:
    """Collect provider/audio checks for the shared launch gate."""
    rerun = rerun_command or _rerun(profile, provider_name)
    provider_tab, provider, provider_error = _provider_tab_check_with_context(
        config,
        profile=profile,
        provider_name=provider_name,
        rerun_command=rerun,
        mode=mode,
    )
    audio_route_checks = collect_audio_route_checks(
        config,
        profile=profile,
        provider_name=provider_name,
        rerun_command=rerun,
        mode=mode,
    )
    return (
        provider_tab,
        *audio_route_checks,
        *collect_provider_capability_checks(
            config,
            profile=profile,
            provider_name=provider_name,
            provider=provider,
            rerun_command=rerun,
            mode=mode,
        ),
        *collect_permission_checks(
            config,
            profile=profile,
            provider_name=provider_name,
            provider_error=provider_error,
            audio_route_checks=audio_route_checks,
            rerun_command=rerun,
            mode=mode,
        ),
    )


def collect_audio_route_checks(
    config,
    *,
    profile: str,
    provider_name: str,
    rerun_command: str | None = None,
    mode: str = "call-ready",
) -> tuple[LaunchReadinessCheck, ...]:
    """Check configured audio routes without changing system audio state."""
    del mode
    rerun = rerun_command or _rerun(profile, provider_name)
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
            rerun=rerun,
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
            rerun=rerun,
        ),
        _audio_route_check(
            key="provider_output_blackhole",
            label="provider output BlackHole",
            device_name=_PROVIDER_OUTPUT_DEVICE,
            kind="output",
            device=provider_output,
            action="Run saymo test-devices and install BlackHole 2ch/16ch if missing",
            rerun=rerun,
        ),
        _audio_route_check(
            key="capture_route_blackhole",
            label="capture route BlackHole",
            device_name=_CAPTURE_ROUTE_DEVICE,
            kind="input",
            device=capture_route,
            action="Run saymo test-devices and install BlackHole 2ch/16ch if missing",
            rerun=rerun,
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
            rerun=rerun,
        ),
    )


def collect_provider_tab_check(
    config,
    *,
    profile: str,
    provider_name: str,
    rerun_command: str | None = None,
    mode: str = "call-ready",
) -> LaunchReadinessCheck:
    """Check whether the configured provider has a meeting tab ready."""
    check, _, _ = _provider_tab_check_with_context(
        config,
        profile=profile,
        provider_name=provider_name,
        rerun_command=rerun_command,
        mode=mode,
    )
    return check


def collect_provider_capability_checks(
    config,
    *,
    profile: str,
    provider_name: str,
    provider: object | None = None,
    rerun_command: str | None = None,
    mode: str = "call-ready",
) -> tuple[LaunchReadinessCheck, ...]:
    """Report provider capabilities without invoking provider actions."""
    del config
    rerun = rerun_command or _rerun(profile, provider_name)
    if provider is None:
        try:
            provider = provider_factory.get_provider(provider_name)
        except Exception as exc:
            return (
                LaunchReadinessCheck(
                    key="provider_capabilities",
                    label="provider capabilities",
                    severity="warn",
                    ok=False,
                    detail="provider_capabilities_unavailable",
                    action=(
                        "Fix provider configuration, "
                        f"{_then_rerun(mode, rerun)}."
                    ),
                    rerun=rerun,
                    metadata={
                        "category": "provider",
                        "provider_name": provider_name,
                        "configured_provider": provider_name,
                        "tab_activation_supported": False,
                        "mute_recovery_supported": False,
                        "mic_switch_supported": False,
                        "mic_switch_status": "mic_switch_unknown",
                        "capability_limitations": ["provider_capabilities_unavailable"],
                        "error_type": type(exc).__name__,
                    },
                ),
            )

    resolved_provider = _provider_name(provider, provider_name)
    tab_activation_supported = callable(getattr(provider, "activate_meeting", None))
    mute_recovery_supported = callable(getattr(provider, "toggle_mute", None))
    mic_switch_supported = _provider_supports_mic_switch(provider, provider_name)
    limitations = [] if mic_switch_supported else ["mic_switch_unsupported"]
    mic_switch_status = (
        "mic_switch_supported" if mic_switch_supported else "mic_switch_unsupported"
    )
    return (
        LaunchReadinessCheck(
            key="provider_capabilities",
            label="provider capabilities",
            severity="info" if mic_switch_supported else "warn",
            ok=mic_switch_supported,
            detail=(
                "provider_capabilities_supported"
                if mic_switch_supported
                else "mic_switch_unsupported"
            ),
            action=(
                ""
                if mic_switch_supported
                else (
                    "Use saymo takeover-check before relying on automated "
                    "microphone switching for this provider."
                )
            ),
            rerun="" if mic_switch_supported else rerun,
            metadata={
                "category": "provider",
                "provider_name": resolved_provider,
                "configured_provider": provider_name,
                "tab_activation_supported": tab_activation_supported,
                "mute_recovery_supported": mute_recovery_supported,
                "mic_switch_supported": mic_switch_supported,
                "mic_switch_status": mic_switch_status,
                "capability_limitations": limitations,
            },
        ),
    )


def collect_permission_checks(
    config,
    *,
    profile: str,
    provider_name: str,
    provider_error: str = "",
    microphone_permission_blocked: bool = False,
    audio_routing_permission_blocked: bool = False,
    audio_route_checks: tuple[LaunchReadinessCheck, ...] | None = None,
    rerun_command: str | None = None,
    mode: str = "call-ready",
) -> tuple[LaunchReadinessCheck, ...]:
    """Collect non-destructive macOS permission remediation rows."""
    checks: list[LaunchReadinessCheck] = []
    rerun = rerun_command or _rerun(profile, provider_name)
    if _looks_like_chrome_permission_error(provider_error):
        checks.append(
            _permission_check(
                key="chrome_automation_permission",
                label="Chrome automation permission",
                detail="chrome_automation_blocked",
                action=(
                    "Allow Google Chrome automation and terminal Accessibility "
                    f"permissions, {_then_rerun(mode, rerun)}."
                ),
                rerun=rerun,
                provider_name=provider_name,
            )
        )

    hotkey_status, hotkey_detail = _hotkey_permission_status(config, profile)
    if hotkey_status not in {"ok", "skipped", "no_bindings"}:
        checks.append(
            _permission_check(
                key="hotkey_accessibility_permission",
                label="hotkey Accessibility permission",
                detail="hotkey_accessibility_blocked",
                action=(
                    "Allow the terminal app running Saymo in macOS Accessibility "
                    "settings."
                ),
                rerun=rerun,
                provider_name=provider_name,
                extra_metadata={
                    "registration_status": hotkey_status,
                    "registration_detail": hotkey_detail,
                },
            )
        )

    audio_blocked = audio_routing_permission_blocked or _audio_routing_permission_blocked(
        config,
        audio_route_checks=audio_route_checks,
    )
    microphone_blocked = microphone_permission_blocked or _microphone_permission_blocked(
        config,
        audio_route_checks=audio_route_checks,
    )

    if microphone_blocked:
        checks.append(
            _permission_check(
                key="microphone_capture_permission",
                label="microphone capture permission",
                detail="microphone_capture_permission_blocked",
                action=(
                    "Allow microphone access for the terminal app running Saymo, "
                    f"{_then_rerun(mode, rerun)}."
                ),
                rerun=rerun,
                provider_name=provider_name,
            )
        )

    if audio_blocked:
        checks.append(
            _permission_check(
                key="audio_routing_permission",
                label="audio routing permission",
                detail="audio_routing_permission_blocked",
                action=(
                    "Verify BlackHole permissions/routes in macOS Audio MIDI Setup "
                    f"and allow required audio access, {_then_rerun(mode, rerun)}."
                ),
                rerun=rerun,
                provider_name=provider_name,
            )
        )

    return tuple(checks)


def _provider_tab_check_with_context(
    config,
    *,
    profile: str,
    provider_name: str,
    rerun_command: str | None = None,
    mode: str = "call-ready",
) -> tuple[LaunchReadinessCheck, object | None, str]:
    """Return provider tab check plus context for follow-on read-only checks."""
    del config
    rerun = rerun_command or _rerun(profile, provider_name)
    try:
        provider = provider_factory.get_provider(provider_name)
    except Exception as exc:
        if _is_unknown_provider(exc):
            return (
                _blocked_check(
                    configured_provider=provider_name,
                    provider_name=provider_name,
                    detail="unknown_provider",
                    action=(
                        "Use a supported provider name, "
                        f"{_then_rerun(mode, rerun, call_ready_text='then rerun saymo call-ready')}"
                    ),
                    rerun=rerun,
                    error_type=type(exc).__name__,
                ),
                None,
                str(exc),
            )
        return (
            _blocked_check(
                configured_provider=provider_name,
                provider_name=provider_name,
                detail="provider_check_error",
                action=(
                    "Open Chrome, allow provider automation permissions, "
                    f"{_then_rerun(mode, rerun, call_ready_text='then rerun saymo call-ready')}"
                ),
                rerun=rerun,
                error_type=type(exc).__name__,
            ),
            None,
            str(exc),
        )

    resolved_provider = _provider_name(provider, provider_name)
    url_pattern = _provider_url_pattern(provider)
    try:
        status = provider.check_ready()
    except Exception as exc:
        return (
            _blocked_check(
                configured_provider=provider_name,
                provider_name=resolved_provider,
                detail="provider_check_error",
                action=(
                    "Open Chrome, allow provider automation permissions, "
                    f"{_then_rerun(mode, rerun, call_ready_text='then rerun saymo call-ready')}"
                ),
                rerun=rerun,
                error_type=type(exc).__name__,
                url_pattern=url_pattern,
            ),
            provider,
            str(exc),
        )

    return (
        _check_from_status(
            configured_provider=provider_name,
            provider_name=resolved_provider,
            url_pattern=url_pattern,
            status=status,
            rerun=rerun,
        ),
        provider,
        "",
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


def _provider_supports_mic_switch(provider: Any, provider_name: str) -> bool:
    del provider_name
    class_name = provider.__class__.__name__
    provider_method = getattr(provider.__class__, "switch_mic", None)
    base_method = getattr(ChromeCallProvider, "switch_mic", None)
    return class_name in _MIC_SWITCH_PROVIDER_CLASSES or (
        callable(provider_method) and provider_method is not base_method
    )


def _permission_check(
    *,
    key: str,
    label: str,
    detail: str,
    action: str,
    rerun: str,
    provider_name: str,
    extra_metadata: dict[str, Any] | None = None,
) -> LaunchReadinessCheck:
    metadata: dict[str, Any] = {
        "category": "macos-permission",
        "provider_name": provider_name,
        "configured_provider": provider_name,
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    return LaunchReadinessCheck(
        key=key,
        label=label,
        severity="block",
        ok=False,
        detail=detail,
        action=action,
        rerun=rerun,
        metadata=metadata,
    )


def _hotkey_permission_status(config: Any, profile: str) -> tuple[str, str]:
    try:
        report = live_control.build_hotkey_doctor_report(config, profile, probe=True)
    except Exception as exc:
        return "blocked", type(exc).__name__
    return (
        str(getattr(report, "registration_status", "") or ""),
        str(getattr(report, "registration_detail", "") or ""),
    )


def _looks_like_chrome_permission_error(provider_error: str) -> bool:
    lower = str(provider_error or "").lower()
    return bool(lower) and any(marker in lower for marker in _CHROME_PERMISSION_MARKERS)


def _microphone_permission_blocked(
    config: Any,
    *,
    audio_route_checks: tuple[LaunchReadinessCheck, ...] | None = None,
) -> bool:
    check = _route_check(audio_route_checks, "recording_microphone_input")
    if check is not None:
        return _check_device_settings_blocked(check)

    audio_config = getattr(config, "audio", None)
    device_name = _config_text(audio_config, "recording_device")
    if not device_name:
        return False
    device = audio_devices.find_device(device_name, kind="input")
    if device is None:
        return False
    return _check_device_settings_blocked(
        _audio_route_check(
            key="recording_microphone_input",
            label="recording microphone input",
            device_name=device_name,
            kind="input",
            device=device,
            action="",
            rerun="",
        )
    )


def _audio_routing_permission_blocked(
    config: Any,
    *,
    audio_route_checks: tuple[LaunchReadinessCheck, ...] | None = None,
) -> bool:
    checks = audio_route_checks
    if checks is None:
        checks = _fallback_audio_route_checks(config)
    route_keys = (
        "capture_input_device",
        "playback_output_device",
        "provider_output_blackhole",
        "capture_route_blackhole",
    )
    blocked = False
    for key in route_keys:
        check = _route_check(checks, key)
        if check is not None:
            blocked = _check_device_settings_blocked(check) or blocked
    return blocked


def _fallback_audio_route_checks(config: Any) -> tuple[LaunchReadinessCheck, ...]:
    audio_config = getattr(config, "audio", None)
    capture_name = _config_text(audio_config, "capture_device")
    playback_name = _config_text(audio_config, "playback_device")
    return (
        _audio_route_check(
            key="capture_input_device",
            label="capture input device",
            device_name=capture_name,
            kind="input",
            device=(
                audio_devices.find_device(capture_name, kind="input")
                if capture_name
                else None
            ),
            action="",
            rerun="",
        ),
        _audio_route_check(
            key="playback_output_device",
            label="playback output device",
            device_name=playback_name,
            kind="output",
            device=(
                audio_devices.find_device(playback_name, kind="output")
                if playback_name
                else None
            ),
            action="",
            rerun="",
        ),
        _audio_route_check(
            key="provider_output_blackhole",
            label="provider output BlackHole",
            device_name=_PROVIDER_OUTPUT_DEVICE,
            kind="output",
            device=audio_devices.find_device(_PROVIDER_OUTPUT_DEVICE, kind="output"),
            action="",
            rerun="",
        ),
        _audio_route_check(
            key="capture_route_blackhole",
            label="capture route BlackHole",
            device_name=_CAPTURE_ROUTE_DEVICE,
            kind="input",
            device=audio_devices.find_device(_CAPTURE_ROUTE_DEVICE, kind="input"),
            action="",
            rerun="",
        ),
    )


def _route_check(
    checks: tuple[LaunchReadinessCheck, ...] | None,
    key: str,
) -> LaunchReadinessCheck | None:
    for check in checks or ():
        if check.key == key:
            return check
    return None


def _check_device_settings_blocked(check: LaunchReadinessCheck) -> bool:
    if not check.ok:
        return False
    metadata = dict(check.metadata or {})
    device = metadata.get("device")
    if not isinstance(device, dict):
        return False
    index = device.get("index")
    if index is None:
        return False
    samplerate = device.get("default_samplerate")
    kwargs = {"device": index}
    if samplerate:
        kwargs["samplerate"] = samplerate
    try:
        if metadata.get("kind") == "output":
            sd.check_output_settings(**kwargs)
        else:
            sd.check_input_settings(**kwargs)
    except Exception:
        return True
    return False


def _rerun(profile: str, provider_name: str) -> str:
    return f"saymo call-ready -p {profile} --provider {provider_name}"


def _then_rerun(
    mode: str,
    rerun: str,
    *,
    call_ready_text: str = "then rerun call-ready",
) -> str:
    if mode == "dry-run":
        return f"then rerun {rerun}"
    return call_ready_text


def _config_text(config: Any, field: str) -> str:
    value = getattr(config, field, "")
    return str(value or "").strip()


def _is_unknown_provider(exc: Exception) -> bool:
    return isinstance(exc, ValueError) and "Unknown provider" in str(exc)
