"""Floating always-on-top prep window shown by `saymo daily-prep`.

Displays the text prepared for the meeting with a Play/Stop control:
Play starts the cached-audio playback (same path as `saymo speak`) and, in
parallel, records the user's own mic for the meeting; Stop ends the
recording and automatically kicks off a speech-coaching pass (offline
re-transcription + an LLM delivery review) so recommendations land as soon
as the call ends.

Standalone module — the overlay in scripts/live_translate.py is inline in
that script, display-only, and not importable.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("saymo.ui.prep_window")


def _timestamp() -> str:
    return datetime.now().strftime("%H%M%S")


def run_prep_window(
    *,
    profile_name: str,
    meeting_description: str,
    prepared_text: str,
    config,
    audio_path: Path,
    provider_name: str | None,
    recording_device: str,
) -> None:
    """Open the prep window and block on its event loop until it's closed."""
    try:
        import tkinter as tk
        from tkinter import scrolledtext
    except ImportError:
        logger.warning("tkinter unavailable — printing prepared text instead")
        print(prepared_text)
        return

    from saymo.analysis.speech_review import run_speech_review
    from saymo.audio.meeting_recorder import MeetingRecorder
    from saymo.commands import _play_cached_audio

    root = tk.Tk()
    root.title(f"Saymo — {meeting_description or profile_name}")
    root.attributes("-topmost", True)
    root.geometry("520x360")

    text_widget = scrolledtext.ScrolledText(root, wrap=tk.WORD, font=("Helvetica", 13))
    text_widget.insert(tk.END, prepared_text)
    text_widget.configure(state=tk.DISABLED)
    text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    status_var = tk.StringVar(value="Готово к встрече.")
    tk.Label(root, textvariable=status_var, anchor="w").pack(fill=tk.X, padx=10)

    button_row = tk.Frame(root)
    button_row.pack(fill=tk.X, padx=10, pady=10)

    state: dict = {"recorder": None}

    def _set_text(new_text: str) -> None:
        text_widget.configure(state=tk.NORMAL)
        text_widget.delete("1.0", tk.END)
        text_widget.insert(tk.END, new_text)
        text_widget.configure(state=tk.DISABLED)

    def _on_play() -> None:
        play_button.configure(state=tk.DISABLED)
        status_var.set("Играю подготовленную речь и записываю встречу...")

        wav_path = (
            Path.home() / ".saymo" / "meeting_recordings" / f"{profile_name}-{_timestamp()}.wav"
        )
        recorder = MeetingRecorder(recording_device, wav_path)
        try:
            recorder.start()
            state["recorder"] = recorder
        except Exception as exc:
            logger.warning(f"Could not start meeting recording: {exc}")
            status_var.set(f"Запись микрофона не запущена: {exc}")

        def _play_worker() -> None:
            try:
                asyncio.run(_play_cached_audio(config, audio_path, provider_name=provider_name))
            except Exception as exc:
                logger.warning(f"Playback failed: {exc}")

        threading.Thread(target=_play_worker, daemon=True).start()
        stop_button.configure(state=tk.NORMAL)

    def _on_stop() -> None:
        stop_button.configure(state=tk.DISABLED)
        recorder = state.get("recorder")
        if recorder is None:
            status_var.set("Запись не была активна — рекомендаций не будет.")
            return
        wav_path = recorder.stop()
        state["recorder"] = None
        status_var.set("Разбираю запись и готовлю рекомендации...")

        def _review_worker() -> None:
            try:
                recommendations, report_path = asyncio.run(
                    run_speech_review(
                        wav_path,
                        config,
                        profile_name=profile_name,
                        meeting_description=meeting_description,
                    )
                )
            except Exception as exc:
                logger.warning(f"Speech review failed: {exc}")
                root.after(0, lambda: status_var.set(f"Не удалось составить рекомендации: {exc}"))
                return
            root.after(
                0,
                lambda: (
                    _set_text(recommendations),
                    status_var.set(f"Рекомендации сохранены: {report_path}"),
                ),
            )

        threading.Thread(target=_review_worker, daemon=True).start()

    play_button = tk.Button(button_row, text="▶ Play", command=_on_play, width=12)
    play_button.pack(side=tk.LEFT, padx=(0, 8))
    stop_button = tk.Button(
        button_row, text="■ Stop", command=_on_stop, width=12, state=tk.DISABLED
    )
    stop_button.pack(side=tk.LEFT)

    root.mainloop()
