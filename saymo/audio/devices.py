"""Audio device discovery and validation.

This module is the single entry-point for ``sounddevice`` calls — other
modules should prefer the helpers here (``list_devices``, ``find_device``,
``default_input``, ``default_output``) so all ``# type: ignore[index]``
annotations needed by the untyped ``sounddevice`` API stay local to one
file.
"""

from dataclasses import dataclass
from typing import Any

import sounddevice as sd


@dataclass
class AudioDevice:
    index: int
    name: str
    max_input_channels: int
    max_output_channels: int
    default_samplerate: float


def _as_dict(dev: Any) -> dict[str, Any]:
    """Narrow ``sounddevice`` query result into a plain dict.

    ``sd.query_devices()`` returns ``DeviceList | dict`` without proper
    typing; this helper localizes the ``type: ignore`` so callers get a
    well-typed ``dict[str, Any]``.
    """
    return dict(dev)  # type: ignore[arg-type]


def list_devices() -> list[AudioDevice]:
    """List all available audio devices."""
    devices = sd.query_devices()
    result = []
    for i, d in enumerate(devices):
        dd = _as_dict(d)
        result.append(AudioDevice(
            index=i,
            name=dd['name'],
            max_input_channels=dd['max_input_channels'],
            max_output_channels=dd['max_output_channels'],
            default_samplerate=dd['default_samplerate'],
        ))
    return result


def default_input() -> dict[str, Any] | None:
    """Return the system default input device as a dict, or None."""
    try:
        dev = sd.query_devices(kind="input")
    except Exception:
        return None
    if not dev:
        return None
    return _as_dict(dev)


def default_output() -> dict[str, Any] | None:
    """Return the system default output device as a dict, or None."""
    try:
        dev = sd.query_devices(kind="output")
    except Exception:
        return None
    if not dev:
        return None
    return _as_dict(dev)


def find_device(name: str, kind: str = "input") -> AudioDevice | None:
    """Find a device by name substring. kind: 'input' or 'output'."""
    for dev in list_devices():
        if name.lower() in dev.name.lower():
            if kind == "input" and dev.max_input_channels > 0:
                return dev
            if kind == "output" and dev.max_output_channels > 0:
                return dev
    return None


def find_blackhole_devices() -> dict[str, AudioDevice]:
    """Find all BlackHole virtual audio devices."""
    result = {}
    for dev in list_devices():
        if "blackhole" in dev.name.lower():
            result[dev.name] = dev
    return result


def validate_devices(capture_name: str, playback_name: str) -> tuple[AudioDevice | None, AudioDevice | None]:
    """Validate that configured capture and playback devices exist."""
    capture = find_device(capture_name, kind="input")
    playback = find_device(playback_name, kind="output")
    return capture, playback
