"""macOS system audio helpers.

Thin wrappers over ``osascript`` so Saymo can read / adjust the system
microphone input volume from code. Used by the autocalibration loop
when software gain hits its cap and hardware input level needs to be
raised between recordings.

Everything here is best-effort:

- ``get_input_volume`` / ``set_input_volume`` return / accept a value in
  ``[0.0, 1.0]`` and silently fall back to ``None`` / ``False`` on
  non-macOS systems or when ``osascript`` is unavailable.
- No CoreAudio dependencies — the ``osascript`` path works without
  special permissions on the signed CLI user.
"""

from __future__ import annotations

import logging
import platform
import shutil
import subprocess

logger = logging.getLogger("saymo.audio.macos")


def is_macos() -> bool:
    return platform.system() == "Darwin"


def _osascript_available() -> bool:
    return shutil.which("osascript") is not None


def get_input_volume() -> float | None:
    """Return the current system input volume in ``[0.0, 1.0]``.

    Returns ``None`` on non-macOS systems, when ``osascript`` is missing,
    or when the command fails for any reason.
    """
    if not is_macos() or not _osascript_available():
        return None
    try:
        result = subprocess.run(
            ["osascript", "-e", "input volume of (get volume settings)"],
            capture_output=True,
            text=True,
            timeout=3.0,
            check=True,
        )
        value = int(result.stdout.strip())
        return max(0.0, min(1.0, value / 100.0))
    except (subprocess.SubprocessError, ValueError) as e:
        logger.warning(f"failed to read input volume: {e}")
        return None


def set_input_volume(fraction: float) -> bool:
    """Set system input volume. ``fraction`` is ``[0.0, 1.0]``.

    Returns ``True`` on success.
    """
    if not is_macos() or not _osascript_available():
        return False
    fraction = max(0.0, min(1.0, float(fraction)))
    percent = int(round(fraction * 100))
    try:
        subprocess.run(
            ["osascript", "-e", f"set volume input volume {percent}"],
            capture_output=True,
            text=True,
            timeout=3.0,
            check=True,
        )
        logger.info(f"system input volume set to {percent}%")
        return True
    except subprocess.SubprocessError as e:
        logger.warning(f"failed to set input volume: {e}")
        return False


def bump_input_volume(delta_fraction: float) -> tuple[float | None, float | None]:
    """Raise (or lower) system input volume by ``delta_fraction``.

    Returns ``(before, after)``, both in ``[0.0, 1.0]`` or ``None`` if
    the read/write failed. Values clamp to ``[0.0, 1.0]``.
    """
    before = get_input_volume()
    if before is None:
        return None, None
    target = max(0.0, min(1.0, before + float(delta_fraction)))
    ok = set_input_volume(target)
    if not ok:
        return before, None
    after = get_input_volume()
    return before, after
