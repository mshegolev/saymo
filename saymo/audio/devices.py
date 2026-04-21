"""Audio device discovery and validation."""

from dataclasses import dataclass

import sounddevice as sd


@dataclass
class AudioDevice:
    index: int
    name: str
    max_input_channels: int
    max_output_channels: int
    default_samplerate: float


def list_devices() -> list[AudioDevice]:
    """List all available audio devices."""
    devices = sd.query_devices()
    result = []
    for i, d in enumerate(devices):
        result.append(AudioDevice(
            index=i,
            name=d['name'],  # type: ignore[index]
            max_input_channels=d['max_input_channels'],  # type: ignore[index,arg-type]
            max_output_channels=d['max_output_channels'],  # type: ignore[index,arg-type]
            default_samplerate=d['default_samplerate'],  # type: ignore[index,arg-type]
        ))
    return result


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
