"""Play a pre-rendered WAV straight into a Glip call.

Bypasses standup prep / TTS entirely. Reuses saymo's existing provider
machinery: stash current Glip mic → switch to BlackHole 2ch → Unmute →
play WAV (pausable) → Mute → restore the original mic. No JIRA, no
Ollama, no audio_cache filename gymnastics.

Usage:
    .venv/bin/python scripts/play_to_glip.py [WAV_PATH] \\
        [--provider glip] [--mic-back "MacBook Pro Microphone"]

Defaults: WAV ~/Desktop/qa_presentation.wav, provider `glip`. If
``--mic-back`` is omitted, the script reads Glip's currently-selected
microphone before swapping to BlackHole and restores that exact label
afterwards.

Hotkeys (while the script is running, configurable in config.yaml):
  * ``Cmd+Shift+M`` (``safety.hotkey_toggle``) — pause / resume playback.
    The output stream stays open and Glip stays unmuted, but only
    silence is emitted; tap it again to resume from the same position.
  * ``Cmd+Shift+X`` (``safety.hotkey_stop``)   — stop playback fully,
    mute Glip, restore the user's real mic.
  * ``Ctrl+C`` in the terminal — same as ``hotkey_stop``.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import signal
import sys
import threading
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

from saymo.audio.devices import find_device  # noqa: F401  (kept for future pausable-stream work)
from saymo.commands import _play_cached_audio
from saymo.config import load_config


def _install_stop_hotkey(config, on_stop) -> object | None:
    """Bind a global hotkey that calls ``on_stop()`` immediately.

    Returns the listener (caller is responsible for ``.stop()``), or
    ``None`` if pynput / accessibility permissions are unavailable.
    """
    hotkey = config.safety.hotkey_stop
    if not hotkey:
        return None
    try:
        from pynput import keyboard as _kb
    except Exception as e:
        print(f"[stop hotkey unavailable: {e}]", file=sys.stderr)
        return None

    def _trigger():
        sd.stop()
        print(f"\n[STOP] {hotkey} pressed — cancelling playback.", flush=True)
        try:
            on_stop()
        except Exception as e:
            print(f"[panic recovery failed: {e}]", file=sys.stderr)

    try:
        listener = _kb.GlobalHotKeys({hotkey: _trigger})
        listener.start()
        print(f"[panic button] {hotkey} = stop, Ctrl+C also works", flush=True)
        return listener
    except Exception as e:
        print(f"[stop hotkey disabled: {e}]", file=sys.stderr)
        return None


def _panic_recover(provider_name: str, original_mic: str | None) -> None:
    """Mute Glip and restore the user's real microphone."""
    try:
        from saymo.providers.factory import get_provider

        provider = get_provider(provider_name)
        # Re-focus the call tab, then mute. Mute via toggle is idempotent
        # only when we're currently unmuted — the provider tracks this
        # implicitly through unmute_speak_mute, so on a panic stop we just
        # press the mute hotkey once.
        try:
            provider.activate_meeting()
            provider.toggle_mute()
        except Exception as e:
            print(f"[mute on stop failed: {e}]", file=sys.stderr)
    except Exception as e:
        print(f"[provider lookup failed: {e}]", file=sys.stderr)

    if original_mic:
        try:
            from saymo.glip_control import switch_rc_mic_to

            ok = switch_rc_mic_to(original_mic)
            print(
                f"[mic restored to '{original_mic}']" if ok
                else f"[could not auto-restore '{original_mic}' — switch manually]",
                flush=True,
            )
        except Exception as e:
            print(f"[mic restore failed: {e}]", file=sys.stderr)


async def run(audio_path: Path, provider_name: str, mic_back: str | None) -> int:
    if not audio_path.exists():
        print(f"WAV not found: {audio_path}", file=sys.stderr)
        return 1

    config = load_config()
    # Force playback into BlackHole 2ch so Glip picks it up as the mic.
    config.audio.playback_device = "BlackHole 2ch"

    # Stash the user's real mic so we can put it back afterwards.
    original_mic: str | None = mic_back
    if original_mic is None and provider_name == "glip":
        try:
            from saymo.glip_control import get_current_rc_mic

            original_mic = get_current_rc_mic()
            if original_mic and "blackhole" in original_mic.lower():
                # Already switched from a previous run — don't restore to BH.
                original_mic = None
            if original_mic:
                print(f"[remembered mic: '{original_mic}']", flush=True)
        except Exception as e:
            print(f"[could not read current mic: {e}]", file=sys.stderr)

    listener = _install_stop_hotkey(
        config, lambda: _panic_recover(provider_name, original_mic)
    )

    # Ctrl+C → SIGINT: stop sd immediately, then let asyncio raise.
    loop = asyncio.get_running_loop()

    def _sigint(*_):
        sd.stop()
        print("\n[STOP] Ctrl+C — cancelling playback.", flush=True)
        raise KeyboardInterrupt

    try:
        loop.add_signal_handler(signal.SIGINT, _sigint)
    except NotImplementedError:
        pass  # Windows / non-asyncio loops

    print(
        f"Playing {audio_path} ({audio_path.stat().st_size // 1024} KB) "
        f"into {provider_name} via BlackHole 2ch...",
        flush=True,
    )
    try:
        await _play_cached_audio(config, audio_path, provider_name)
        # Normal completion: provider already muted us. Just put the mic back.
        if original_mic and provider_name == "glip":
            try:
                from saymo.glip_control import switch_rc_mic_to

                if switch_rc_mic_to(original_mic):
                    print(f"[mic restored to '{original_mic}']", flush=True)
            except Exception as e:
                print(f"[mic restore failed: {e}]", file=sys.stderr)
        print("Done.", flush=True)
        return 0
    except KeyboardInterrupt:
        sd.stop()
        _panic_recover(provider_name, original_mic)
        return 130
    finally:
        if listener is not None:
            try:
                listener.stop()
            except Exception:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Play a WAV to a Chrome call provider.")
    parser.add_argument(
        "wav",
        nargs="?",
        default=str(Path.home() / "Desktop" / "qa_presentation.wav"),
        help="Path to the WAV file to play (default: ~/Desktop/qa_presentation.wav).",
    )
    parser.add_argument(
        "--provider",
        default="glip",
        help="Call provider: glip, mts-link, zoom, teams, ... (default: glip).",
    )
    parser.add_argument(
        "--mic-back",
        default=None,
        help=(
            "Microphone label to restore after playback (substring match in "
            "the Glip audio dropdown, e.g. 'MacBook Pro Microphone' or "
            "'AirPods'). If omitted, the script reads the currently selected "
            "Glip mic before switching and restores that exact label."
        ),
    )
    args = parser.parse_args()
    return asyncio.run(
        run(Path(args.wav).expanduser(), args.provider, args.mic_back)
    )


if __name__ == "__main__":
    sys.exit(main())
