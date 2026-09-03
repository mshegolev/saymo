"""Dictation command: speak → whisper STT → Ollama punctuation → paste.

Records from the mic in silence-segmented utterances (adapted from
``scripts/live_translate.py``), transcribes each with faster-whisper
(auto-detects RU/EN), restores punctuation with a local Ollama LLM, and
inserts the result into the active window (clipboard + Cmd+V via
``osascript``, like macOS dictation in any app).

Stop with Ctrl+C.
"""

import asyncio
import logging
import queue
import subprocess
import sys
import threading
import time
from collections import deque

import click
import numpy as np
import sounddevice as sd

from saymo.commands import console, main
from saymo.audio.devices import find_device

logger = logging.getLogger("saymo.dictation")

SAMPLE_RATE = 16000
BLOCK_SECONDS = 0.1
BLOCK_SAMPLES = int(SAMPLE_RATE * BLOCK_SECONDS)

SILENCE_BLOCKS = 10         # 1.0s of silence closes an utterance
SPEECH_BLOCKS = 2           # 0.2s above threshold opens one
PREROLL_BLOCKS = 5          # keep 0.5s before the trigger
MAX_UTTERANCE_SECONDS = 20.0
MIN_UTTERANCE_SECONDS = 0.3
CALIBRATION_SECONDS = 1.2
NOISE_MULTIPLIER = 4.0
ABSOLUTE_FLOOR = 0.004

HALLUCINATIONS = {
    "thank you.", "thank you", "thanks for watching!", "you", ".", "bye.",
    "спасибо за просмотр!", "субтитры", "продолжение следует...",
}


def _real_device(mic_name: str):
    """Resolve a configured mic name to a device, with default fallback."""
    if mic_name:
        dev = find_device(mic_name, kind="input")
        if dev:
            return dev
    dflt = sd.query_devices(kind="input")
    if isinstance(dflt, dict):
        name = str(dflt["name"])
        dev = find_device(name, kind="input")
        if dev:
            return dev
    return None


def _transcribe(audio: np.ndarray, model_size: str) -> str:
    """Run faster-whisper on one utterance (language auto-detected)."""
    from saymo.stt.whisper_local import LocalWhisper

    whisper = LocalWhisper(model_size=model_size, language=None)
    raw = whisper.transcribe(audio).strip()
    if not raw:
        return ""
    lowered = raw.strip().lower()
    if lowered in HALLUCINATIONS:
        return ""
    return raw


async def _punctuate(raw: str, model: str, url: str, config) -> str:
    """Restore punctuation via Ollama, with a plain-text guarantee."""
    from saymo.speech.punctuator import punctuate_text

    text = await punctuate_text(
        raw,
        language="auto",
        model=model,
        ollama_url=url,
        config=config,
    )
    # A well-behaved punctator returns only text; guard against model verbosity.
    for marker in ("Текст:", "Text:", "```"):
        if marker in text:
            text = text.split(marker, 1)[-1]
    return text.strip()


def _paste(text: str) -> None:
    """Insert ``text`` into the frontmost window via CoreGraphics (native macOS).

    Copies to clipboard then sends Cmd+V with ``CGEventPost`` — no Hammerspoon,
    no cliclick, no Accessibility needed from a Python child process.
    """
    try:
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
    except Exception as e:
        logger.warning("pbcopy failed: %s", e)
        console.print(text)
        return
    _cg_cmd_v()


def _cg_cmd_v() -> None:
    """Send Cmd+V to the frontmost app via CoreGraphics (no deps)."""
    import ctypes
    import ctypes.util

    cf = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreGraphics"))

    kCGHIDEventTap = ctypes.c_uint32(0)
    cmd_flag = ctypes.c_uint64(1 << 9)  # kCGEventFlagMaskCommand
    kVK_ANSI_V = ctypes.c_uint16(0x09)
    nSecs = ctypes.c_double(0.0)

    CGEventPost = cf.CGEventPost
    CGEventCreateKeyboardEvent = cf.CGEventCreateKeyboardEvent
    CFRelease = cf.CFRelease

    CGEventCreateKeyboardEvent.restype = ctypes.c_void_p
    CGEventPost.restype = None
    CFRelease.restype = None

    # Key down
    evt = CGEventCreateKeyboardEvent(None, kVK_ANSI_V, True)
    if evt:
        cf.CGEventSetFlags(evt, cmd_flag)
        CGEventPost(kCGHIDEventTap, evt)
        CFRelease(evt)

    # Small inter-key delay
    import time
    time.sleep(0.001)

    # Key up
    evt = CGEventCreateKeyboardEvent(None, kVK_ANSI_V, False)
    if evt:
        cf.CGEventSetFlags(evt, cmd_flag)
        CGEventPost(kCGHIDEventTap, evt)
        CFRelease(evt)


@main.command("dictation")
@click.option("--model-size", "-w", default=None, help="Whisper model size (default: config.stt.whisper)")
@click.option("--ollama-model", "-m", default=None, help="Ollama model for punctuation")
@click.option("--device", "-d", default=None, help="Input device name (overrides config)")
@click.option("--no-paste", is_flag=True, help="Print text instead of pasting")
@click.option("--once", is_flag=True, help="Dictate exactly one utterance, then exit")
@click.pass_context
def dictation(ctx, model_size, ollama_model, device, no_paste, once):
    """Dictate directly into the active window with punctuation (RU/EN).

    Speak, pause briefly — each utterance is transcribed, punctuated with a
    local Ollama model, and inserted. Ctrl+C to stop.
    """
    import soundfile as sf  # noqa: F401  (ensure dep present)

    config = ctx.obj["config"]

    whisper_model = model_size or getattr(config.stt.whisper, "model_size", "large-v3") or "small"
    punct_model = ollama_model or config.ollama.model
    ollama_url = config.ollama.url

    mic_name = device or config.audio.recording_device or ""
    mic = _real_device(mic_name)
    if not mic:
        console.print("[bold red]No input device available[/]")
        return

    console.print(f"[bold blue]Dictation[/] — mic: {mic.name}")
    console.print(
        f"  whisper={whisper_model} · punctuation={punct_model} @ {ollama_url}"
    )
    console.print("  Speak, pause to insert. [dim]Ctrl+C to stop.[/]\n")

    stop = threading.Event()
    seg = _UtteranceCollector(stop)

    def _stream_callback(indata, _frames, _time_info, status):
        if status:
            logger.debug("audio status: %s", status)
        mono = indata[:, 0].copy() if indata.ndim > 1 else indata.copy().flatten()
        try:
            seg.blocks.put_nowait(mono.astype(np.float32, copy=False))
        except queue.Full:
            pass

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        device=mic.index,
        blocksize=SAMPLE_RATE // 10,
        callback=_stream_callback,
    )

    asyncio.run(_run(stream, seg, whisper_model, punct_model, ollama_url, config, no_paste, once, stop))


class _UtteranceCollector:
    """Silence-segmentation state machine (see live_translate.py)."""

    def __init__(self, stop: threading.Event):
        self.stop = stop
        self.blocks: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=400)
        self._noise_samples: list[float] = []
        self._calibrated = False
        self.threshold = 0.0
        self.preroll: deque[np.ndarray] = deque(maxlen=PREROLL_BLOCKS)
        self.buffer: list[np.ndarray] = []
        self.speaking = False
        self.loud_run = 0
        self.quiet_run = 0
        self.max_blocks = int(MAX_UTTERANCE_SECONDS / BLOCK_SECONDS)

    def _calibrate(self, rms: float) -> None:
        self._noise_samples.append(rms)
        if len(self._noise_samples) * BLOCK_SECONDS >= CALIBRATION_SECONDS:
            floor = float(np.median(self._noise_samples))
            self.threshold = max(floor * NOISE_MULTIPLIER, ABSOLUTE_FLOOR)
            self._calibrated = True

    def take_utterance(self) -> np.ndarray | None:
        """Feed queued blocks; return a full utterance audio or None."""
        while not self.stop.is_set():
            try:
                block = self.blocks.get(timeout=0.3)
            except queue.Empty:
                break

            rms = float(np.sqrt(np.mean(np.square(block))))
            if not self._calibrated:
                self._calibrate(rms)
                self.preroll.append(block)
                continue

            loud = rms > self.threshold

            if not self.speaking:
                self.preroll.append(block)
                self.loud_run = self.loud_run + 1 if loud else 0
                if self.loud_run >= SPEECH_BLOCKS:
                    self.speaking = True
                    self.quiet_run = 0
                    self.buffer = list(self.preroll)
                    self.preroll.clear()
                continue

            self.buffer.append(block)
            self.quiet_run = 0 if loud else self.quiet_run + 1

            if self.quiet_run >= SILENCE_BLOCKS or len(self.buffer) >= self.max_blocks:
                audio = np.concatenate(self.buffer)
                self.speaking = False
                self.loud_run = 0
                self.quiet_run = 0
                self.buffer = []
                self.preroll.clear()
                if len(audio) / SAMPLE_RATE >= MIN_UTTERANCE_SECONDS:
                    return audio

        if self.speaking and not self.stop.is_set():
            # Drain what the callback pushed since the loop broke early.
            try:
                while True:
                    self.buffer.append(self.blocks.get_nowait())
            except queue.Empty:
                pass
            if self.buffer:
                audio = np.concatenate(self.buffer)
                self.speaking = False
                if len(audio) / SAMPLE_RATE >= MIN_UTTERANCE_SECONDS:
                    return audio
        return None


async def _run(stream, seg, whisper_model, punct_model, ollama_url, config, no_paste, once, stop):
    stream.start()
    console.print("[green]Listening…[/]")
    try:
        while not stop.is_set():
            audio = await asyncio.to_thread(seg.take_utterance)
            if audio is None:
                if once:
                    break
                continue

            console.print("[dim]…transcribing[/]")
            raw = await asyncio.to_thread(_transcribe, audio, whisper_model)
            if not raw:
                console.print("[yellow]…no speech detected[/]")
                continue

            console.print(f"[cyan]{raw}[/]")
            try:
                text = await _punctuate(raw, punct_model, ollama_url, config)
            except Exception as e:
                console.print(f"[red]punctuation failed:[/] {e}")
                text = raw
            if not text:
                continue

            if no_paste:
                console.print(text)
            else:
                _paste(text)

            if once:
                break
    finally:
        stream.stop()
        stream.close()