#!/usr/bin/env python3
"""Live meeting subtitles: STT of a Zoom call + immediate EN→RU translation.

Captures two audio streams — remote participants (via BlackHole, fed by a
Multi-Output Device) and your own microphone — segments each on silence,
transcribes with faster-whisper, and translates non-Russian utterances.
Prints a colored live feed and appends a bilingual Markdown transcript.

Three translators are available, all selected with --translator:
  ollama     (default) a local LLM via Ollama. Takes instructions, so most
             --vocab terms survive untranslated and it sees the previous
             turns as context. ~1.1s per phrase. Adherence is good, not
             guaranteed: on an 8B model roughly one phrase in three still
             translates a listed term.
  argos      Fully local Argos Translate. ~0.2s per phrase, but it cannot be
             instructed: "pipeline" becomes "трубопровод", "staging" becomes
             "постановка". Use it when latency matters more than wording.
  anthropic  Claude via the API. Needs ANTHROPIC_API_KEY.

Whichever you pick, the English source line is printed above each
translation — that is the safety net, not decoration.

Setup (once, per translator you intend to use):
    uv pip install --python .venv/bin/python -e ".[stt,translate]"
    ollama pull aya-expanse:8b                       # for --translator ollama
    # for --translator argos, the EN→RU pair (~187MB). Python's urllib may
    # fail certificate verification here, hence curl:
    curl -sSL -o /tmp/en_ru.argosmodel \
        https://argos-net.com/v1/translate-en_ru-1_9.argosmodel
    .venv/bin/python -c "import argostranslate.package as p; \
        p.install_from_path('/tmp/en_ru.argosmodel')"

Usage:
    .venv/bin/python scripts/live_translate.py --vocab "Oozie,Impala,staging"
    .venv/bin/python scripts/live_translate.py --translator argos

Audio routing (do this before the call):
    Audio MIDI Setup → create a Multi-Output Device containing your headset
    AND "BlackHole 16ch" → select it as the speaker inside Zoom. Without it
    the remote stream stays silent.
"""

from __future__ import annotations

import argparse
import logging
import os
import queue
import re
import sys
import threading
import time
import warnings
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd

from saymo.audio.devices import find_device

logger = logging.getLogger("saymo.live_translate")

SAMPLE_RATE = 16000
BLOCK_SECONDS = 0.1
BLOCK_SAMPLES = int(SAMPLE_RATE * BLOCK_SECONDS)

# Segmentation
SILENCE_BLOCKS = 7           # 0.7s of silence closes an utterance
SPEECH_BLOCKS = 2            # 0.2s above threshold opens one
PREROLL_BLOCKS = 5           # keep 0.5s before the trigger so we don't clip
MAX_UTTERANCE_SECONDS = 12.0
MIN_UTTERANCE_SECONDS = 0.4
CALIBRATION_SECONDS = 1.5
NOISE_MULTIPLIER = 4.0
ABSOLUTE_FLOOR = 0.004

TRANSLATE_MODEL = "claude-haiku-4-5"
OLLAMA_MODEL = "aya-expanse:8b"
OLLAMA_HOST = "http://127.0.0.1:11434"
TRANSLATE_CONTEXT_TURNS = 3

# Whisper reliably invents these over silence or noise.
HALLUCINATIONS = {
    "thank you.", "thank you", "thanks for watching!", "you", ".", "bye.",
    "subtitles by the amara.org community", "продолжение следует...",
    "субтитры сделал dimatorzok", "редактор субтитров а.синецкая",
    "субтитры создавал dimatorzok", "спасибо за просмотр!",
}

RESET = "\033[0m"
DIM = "\033[2m"
COLORS = {"THEM": "\033[36m", "YOU": "\033[33m"}   # cyan / yellow
RU_COLOR = "\033[1;97m"                            # bright white
ERR_COLOR = "\033[31m"

SYSTEM_PROMPT = (
    "You translate live meeting speech from English into Russian.\n"
    "Rules:\n"
    "- Output ONLY the Russian translation. No preamble, no quotes, no notes.\n"
    "- The input is raw speech-to-text: it may be a fragment, lack punctuation, "
    "or contain recognition errors. Translate what was most likely said.\n"
    "- Keep technical terms, product names, tickers and acronyms in their "
    "original form (deploy, pipeline, staging, PR, DATA-1234).\n"
    "- Preserve the speaker's register — this is spoken conversation, not prose.\n"
    "- If the input is already Russian, return it unchanged."
)


@dataclass
class Utterance:
    speaker: str          # "THEM" | "YOU"
    audio: np.ndarray
    started_at: float


@dataclass
class Line:
    speaker: str
    started_at: float
    source: str
    needs_translation: bool


class Segmenter:
    """Turns a raw audio stream into utterances, cutting on silence."""

    def __init__(self, speaker: str, out_queue: "queue.Queue[Utterance]",
                 threshold: float | None, stop: threading.Event):
        self.speaker = speaker
        self.out_queue = out_queue
        self.threshold: float = threshold if threshold is not None else 0.0
        self.stop = stop
        self.blocks: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=200)
        self._noise_samples: list[float] = []
        self._calibrated = threshold is not None

    def callback(self, indata, _frames, _time_info, status):
        if status:
            logger.debug(f"[{self.speaker}] audio status: {status}")
        mono = indata[:, 0].copy() if indata.ndim > 1 else indata.copy().flatten()
        try:
            self.blocks.put_nowait(mono.astype(np.float32, copy=False))
        except queue.Full:
            pass  # drop rather than stall the audio callback

    def _calibrate(self, rms: float) -> None:
        self._noise_samples.append(rms)
        if len(self._noise_samples) * BLOCK_SECONDS >= CALIBRATION_SECONDS:
            floor = float(np.median(self._noise_samples))
            self.threshold = max(floor * NOISE_MULTIPLIER, ABSOLUTE_FLOOR)
            self._calibrated = True
            print(f"{DIM}[{self.speaker}] noise floor {floor:.5f} → "
                  f"threshold {self.threshold:.5f}{RESET}", flush=True)

    def run(self) -> None:
        preroll: deque[np.ndarray] = deque(maxlen=PREROLL_BLOCKS)
        buffer: list[np.ndarray] = []
        speaking = False
        loud_run = 0
        quiet_run = 0
        started_at = 0.0
        max_blocks = int(MAX_UTTERANCE_SECONDS / BLOCK_SECONDS)

        while not self.stop.is_set():
            try:
                block = self.blocks.get(timeout=0.5)
            except queue.Empty:
                continue

            rms = float(np.sqrt(np.mean(np.square(block))))
            if not self._calibrated:
                self._calibrate(rms)
                preroll.append(block)
                continue

            loud = rms > self.threshold

            if not speaking:
                preroll.append(block)
                loud_run = loud_run + 1 if loud else 0
                if loud_run >= SPEECH_BLOCKS:
                    speaking = True
                    quiet_run = 0
                    buffer = list(preroll)
                    started_at = time.time() - len(buffer) * BLOCK_SECONDS
                    preroll.clear()
                continue

            buffer.append(block)
            quiet_run = 0 if loud else quiet_run + 1

            if quiet_run >= SILENCE_BLOCKS or len(buffer) >= max_blocks:
                self._emit(buffer, started_at)
                speaking = False
                loud_run = 0
                quiet_run = 0
                buffer = []
                preroll.clear()

        if speaking and buffer:
            self._emit(buffer, started_at)

    def _emit(self, buffer: list[np.ndarray], started_at: float) -> None:
        audio = np.concatenate(buffer)
        if len(audio) / SAMPLE_RATE < MIN_UTTERANCE_SECONDS:
            return
        try:
            self.out_queue.put_nowait(Utterance(self.speaker, audio, started_at))
        except queue.Full:
            print(f"{ERR_COLOR}[{self.speaker}] ASR queue full — utterance "
                  f"dropped{RESET}", file=sys.stderr, flush=True)


def is_russian(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    cyrillic = sum(1 for c in letters if "Ѐ" <= c <= "ӿ")
    return cyrillic / len(letters) > 0.3


def is_junk(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 2:
        return True
    if stripped.lower() in HALLUCINATIONS:
        return True
    # "..." / "!!!" / "- - -" and similar noise
    return not re.search(r"[A-Za-zЀ-ӿ0-9]", stripped)


class ArgosTranslator:
    """EN→RU via a local Argos Translate model — no network, no key.

    Translates each utterance in isolation: there is no conversation context
    to carry, so technical vocabulary drifts. The printed English source is
    what makes that survivable.
    """

    def __init__(self, from_code: str = "en", to_code: str = "ru"):
        import argostranslate.package as package
        import argostranslate.translate as translate

        installed = {
            (pkg.from_code, pkg.to_code)
            for pkg in package.get_installed_packages()
        }
        if (from_code, to_code) not in installed:
            raise RuntimeError(
                f"Argos model {from_code}→{to_code} is not installed. Install it:\n"
                f"    curl -sSL -o /tmp/{from_code}_{to_code}.argosmodel \\\n"
                f"        https://argos-net.com/v1/translate-"
                f"{from_code}_{to_code}-1_9.argosmodel\n"
                f"    .venv/bin/python -c \"import argostranslate.package as p; "
                f"p.install_from_path('/tmp/{from_code}_{to_code}.argosmodel')\""
            )
        self._translate = translate.translate
        self.from_code = from_code
        self.to_code = to_code

    def translate(self, text: str) -> str:
        return self._translate(text, self.from_code, self.to_code).strip()


class OllamaTranslator:
    """EN→RU via a local Ollama model — no network, no key.

    Unlike Argos, this one takes instructions: the --vocab terms are handed
    over as a do-not-translate list, which is what stops "staging" from
    becoming "постановка". Costs roughly a second more per phrase.
    """

    def __init__(self, model: str, host: str, keep_terms: list[str]):
        self.model = model
        self.url = host.rstrip("/") + "/api/generate"
        self.history: deque[tuple[str, str]] = deque(maxlen=TRANSLATE_CONTEXT_TURNS)

        installed = self._installed_models(host)
        if model not in installed:
            raise RuntimeError(
                f"Ollama model {model!r} is not pulled. Run:\n"
                f"    ollama pull {model}\n"
                f"Installed: {', '.join(sorted(installed)) or '(none)'}"
            )

        keep = ", ".join(keep_terms) if keep_terms else None
        self.system = (
            "You translate live meeting speech from English into Russian.\n"
            "Output ONLY the Russian translation. No preamble, no quotes, no notes.\n"
            "The input is raw speech-to-text: it may be a fragment, lack "
            "punctuation, or contain recognition errors. Translate what was "
            "most likely said.\n"
            "Preserve the speaker's register — this is spoken conversation.\n"
            "If the input is already Russian, return it unchanged."
        )
        if keep:
            # A bare "do not translate these" instruction is followed only
            # about half the time; worked examples roughly double adherence.
            # Even so it is not guaranteed — see the module docstring.
            self.system += (
                f"\nThese are technical terms. Copy them into the Russian "
                f"output verbatim in Latin script, never translate or "
                f"transliterate them: {keep}.\n"
                "Examples:\n"
                "  EN: The pipeline is green, we can merge.\n"
                "  RU: pipeline зелёный, можно делать merge.\n"
                "  EN: The staging deploy failed, the batch size was too large.\n"
                "  RU: deploy на staging упал, batch size был слишком большой.\n"
            )

    @staticmethod
    def _installed_models(host: str) -> set[str]:
        import json
        import urllib.error
        import urllib.request

        try:
            with urllib.request.urlopen(
                host.rstrip("/") + "/api/tags", timeout=5
            ) as response:
                payload = json.load(response)
        except (urllib.error.URLError, OSError) as exc:
            raise RuntimeError(
                f"Cannot reach Ollama at {host}: {exc}. Is `ollama serve` running?"
            ) from exc
        return {entry["name"] for entry in payload.get("models", [])}

    def translate(self, text: str) -> str:
        import json
        import urllib.request

        prompt = text
        if self.history:
            recent = "\n".join(f"EN: {en}\nRU: {ru}" for en, ru in self.history)
            prompt = (
                f"Previous lines of this meeting, for context:\n{recent}\n\n"
                f"Translate this line:\n{text}"
            )

        body = json.dumps({
            "model": self.model,
            "system": self.system,
            "prompt": prompt,
            "stream": False,
            # Zero temperature: the same phrase should not translate two
            # different ways across a meeting.
            "options": {"temperature": 0.0, "num_predict": 300},
        }).encode()
        request = urllib.request.Request(
            self.url, data=body, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            translated = json.load(response).get("response", "").strip()
        if translated:
            self.history.append((text, translated))
        return translated


class AnthropicTranslator:
    """EN→RU via the Anthropic API, with a few previous turns as context."""

    def __init__(self, model: str):
        import anthropic

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Run:\n"
                "    export ANTHROPIC_API_KEY=sk-ant-..."
            )
        self.client = anthropic.Anthropic(api_key=api_key, timeout=20.0, max_retries=1)
        self.model = model
        self.history: deque[tuple[str, str]] = deque(maxlen=TRANSLATE_CONTEXT_TURNS)

    def translate(self, text: str) -> str:
        parts = []
        if self.history:
            recent = "\n".join(f"EN: {en}\nRU: {ru}" for en, ru in self.history)
            parts.append(f"Previous lines of this meeting, for context:\n{recent}\n")
        parts.append(f"Translate this line:\n{text}")

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": "\n".join(parts)}],
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("translation refused by the model")
        translated = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()
        if translated:
            self.history.append((text, translated))
        return translated


class MaskedTranslator:
    """Wraps a translator so --vocab terms survive verbatim, deterministically.

    Asking a model to leave terms alone works most of the time and fails the
    rest; substituting them for placeholders before translation and putting
    them back afterwards always works. The placeholder format was chosen by
    measurement — of `[[n]]`, `«n»`, `Xn X` and `§n§`, only the bare
    alphanumeric form survived every substitution on both Argos and an 8B
    LLM (`§n§` was stripped every single time).
    """

    PLACEHOLDER = "X{}X"

    def __init__(self, inner: AnyTranslator, terms: list[str]):
        self.inner = inner
        # Longest first, so "batch size" wins over a bare "batch". Word
        # boundaries matter: without them "deploy" matches inside
        # "deployment", the tail is left behind, and the model declines the
        # placeholder into "deployмента".
        ordered = sorted(terms, key=len, reverse=True)
        alternatives = "|".join(re.escape(term) for term in ordered)
        self.pattern = re.compile(rf"\b(?:{alternatives})\b", re.IGNORECASE)

    def translate(self, text: str) -> str:
        found: list[str] = []

        def swap(match: re.Match[str]) -> str:
            found.append(match.group(0))
            return self.PLACEHOLDER.format(len(found) - 1)

        masked = self.pattern.sub(swap, text)
        translated = self.inner.translate(masked)
        for index, original in enumerate(found):
            placeholder = self.PLACEHOLDER.format(index)
            if placeholder in translated:
                translated = translated.replace(placeholder, original)
            else:
                # The model dropped it; the term is simply absent from the
                # Russian line. Better than leaving "X3X" on screen.
                logger.debug(f"placeholder for {original!r} lost in translation")
        return translated


AnyTranslator = (OllamaTranslator | ArgosTranslator | AnthropicTranslator
                 | MaskedTranslator)


class InFlight:
    """Counts utterances that entered the pipeline but aren't printed yet.

    An empty queue does not mean the work is done — a worker holds the item
    while it transcribes or translates it. Shutting down on empty queues
    alone loses the last line, so ownership is tracked explicitly: the ASR
    worker enters on pickup and hands the count over to the translator.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._count = 0

    def enter(self) -> None:
        with self._lock:
            self._count += 1

    def leave(self) -> None:
        with self._lock:
            self._count -= 1

    def busy(self) -> bool:
        with self._lock:
            return self._count > 0


class Printer:
    """Serializes console output and the transcript file across threads."""

    def __init__(self, transcript: Path):
        self.lock = threading.Lock()
        self.file = transcript.open("a", encoding="utf-8")
        header = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.file.write(f"\n# Meeting {header}\n\n")
        self.file.flush()

    def source(self, line: Line) -> None:
        stamp = datetime.fromtimestamp(line.started_at).strftime("%H:%M:%S")
        color = COLORS.get(line.speaker, "")
        with self.lock:
            print(f"{DIM}{stamp}{RESET} {color}{line.speaker}{RESET} {line.source}",
                  flush=True)
            self.file.write(f"**{stamp} {line.speaker}:** {line.source}\n\n")
            self.file.flush()

    def translation(self, line: Line, russian: str) -> None:
        stamp = datetime.fromtimestamp(line.started_at).strftime("%H:%M:%S")
        with self.lock:
            print(f"{DIM}{stamp}{RESET}      {RU_COLOR}→ {russian}{RESET}", flush=True)
            self.file.write(f"> → {russian}\n\n")
            self.file.flush()

    def error(self, line: Line, message: str) -> None:
        stamp = datetime.fromtimestamp(line.started_at).strftime("%H:%M:%S")
        with self.lock:
            print(f"{DIM}{stamp}{RESET}      {ERR_COLOR}→ [перевод не удался: "
                  f"{message}]{RESET}", flush=True)
            self.file.write(f"> → _[перевод не удался: {message}]_\n\n")
            self.file.flush()

    def close(self) -> None:
        with self.lock:
            self.file.close()


def asr_worker(utterances: "queue.Queue[Utterance]",
               to_translate: "queue.Queue[tuple[Line, str]]",
               model_size: str, languages: dict[str, str],
               printer: Printer, stop: threading.Event, inflight: InFlight,
               vocab: str | None = None) -> None:
    from faster_whisper import WhisperModel

    print(f"{DIM}Loading whisper '{model_size}'...{RESET}", flush=True)
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    print(f"{DIM}Whisper ready. Listening — Ctrl+C to stop.{RESET}\n", flush=True)

    while not stop.is_set():
        try:
            utt = utterances.get(timeout=0.5)
        except queue.Empty:
            continue

        inflight.enter()
        language = languages[utt.speaker]
        try:
            segments, _info = model.transcribe(
                utt.audio,
                language=None if language == "auto" else language,
                beam_size=5,
                vad_filter=True,
                condition_on_previous_text=False,
                initial_prompt=vocab,
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
        except Exception as exc:  # noqa: BLE001 — never kill the loop
            logger.warning(f"transcription failed: {exc}")
            inflight.leave()
            continue

        if is_junk(text):
            inflight.leave()
            continue

        line = Line(utt.speaker, utt.started_at, text, not is_russian(text))
        printer.source(line)
        if line.needs_translation:
            # Ownership of the count passes to the translate worker.
            to_translate.put((line, text))
        else:
            inflight.leave()


def translate_worker(to_translate: "queue.Queue[tuple[Line, str]]",
                     translator: AnyTranslator, printer: Printer,
                     stop: threading.Event, inflight: InFlight) -> None:
    while not stop.is_set():
        try:
            line, text = to_translate.get(timeout=0.5)
        except queue.Empty:
            continue
        try:
            russian = translator.translate(text)
            if russian:
                printer.translation(line, russian)
        except Exception as exc:  # noqa: BLE001 — a bad call must not stop subtitles
            printer.error(line, type(exc).__name__)
        finally:
            inflight.leave()


def parse_vocab_terms(spec: str | None) -> list[str]:
    """Read the jargon list from an inline string or a file, one term per line."""
    if not spec:
        return []
    candidate = Path(spec)
    raw = (candidate.read_text().splitlines() if candidate.is_file()
           else spec.split(","))
    return [term.strip() for term in raw if term.strip()]


def build_vocab_prompt(terms: list[str]) -> str | None:
    """Turn the jargon list into a Whisper `initial_prompt`.

    Whisper conditions on this text, so it is phrased as a sentence rather
    than a bare list — that biases recognition toward the spelling of names
    it would otherwise mangle ("Oozie" heard as "Uzi").
    """
    if not terms:
        return None
    return "This meeting mentions: " + ", ".join(terms) + "."


def open_stream(name: str, segmenter: Segmenter) -> sd.InputStream:
    device = find_device(name, kind="input")
    if not device:
        raise RuntimeError(f"Input device not found: {name!r}")
    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        device=device.index,
        blocksize=BLOCK_SAMPLES,
        callback=segmenter.callback,
    )
    stream.start()
    print(f"{DIM}[{segmenter.speaker}] capturing from '{device.name}'{RESET}",
          flush=True)
    return stream


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Live STT + EN→RU translation for a call.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--them-device", default="BlackHole 16ch",
                        help="input device carrying the remote participants")
    parser.add_argument("--you-device", default="Plantronics",
                        help="your microphone (use --no-mic to skip it)")
    parser.add_argument("--no-mic", action="store_true",
                        help="transcribe only the remote side")
    parser.add_argument("--model", default="small",
                        help="faster-whisper model size (tiny/base/small/medium)")
    parser.add_argument("--them-lang", default="en",
                        help="language of the remote side, or 'auto'")
    parser.add_argument("--you-lang", default="auto",
                        help="your language, or 'auto'")
    parser.add_argument("--translator", choices=("ollama", "argos", "anthropic"),
                        default="ollama",
                        help="local LLM, local Argos, or Claude via the API")
    parser.add_argument("--ollama-model", default=OLLAMA_MODEL,
                        help="Ollama model, when --translator ollama")
    parser.add_argument("--ollama-host", default=OLLAMA_HOST,
                        help="Ollama server address")
    parser.add_argument("--translate-model", default=TRANSLATE_MODEL,
                        help="Anthropic model, when --translator anthropic")
    parser.add_argument("--no-mask", action="store_true",
                        help="translate --vocab terms instead of protecting "
                             "them with placeholders")
    parser.add_argument("--vocab", default=None,
                        help="comma-separated jargon to bias recognition "
                             "(e.g. 'Oozie,Impala,HDFS'), or a path to a file "
                             "with one term per line")
    parser.add_argument("--threshold", type=float, default=None,
                        help="fixed VAD threshold; omit to auto-calibrate")
    parser.add_argument("--out", type=Path, default=None,
                        help="transcript path (default: logs/meeting-<ts>.md)")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    if not args.verbose:
        # Argos pulls in stanza, which is chatty on import and at first use.
        warnings.filterwarnings("ignore", category=SyntaxWarning)
        logging.getLogger("stanza").setLevel(logging.ERROR)

    transcript = args.out or (
        Path("logs") / f"meeting-{datetime.now():%Y%m%d-%H%M}.md"
    )
    transcript.parent.mkdir(parents=True, exist_ok=True)

    vocab_terms = parse_vocab_terms(args.vocab)
    vocab = build_vocab_prompt(vocab_terms)

    masking = bool(vocab_terms) and not args.no_mask
    translator: AnyTranslator
    try:
        if args.translator == "ollama":
            # With masking on, the prompt-level keep list is redundant.
            translator = OllamaTranslator(
                args.ollama_model, args.ollama_host,
                [] if masking else vocab_terms)
        elif args.translator == "argos":
            translator = ArgosTranslator()
        else:
            translator = AnthropicTranslator(args.translate_model)
        if masking:
            translator = MaskedTranslator(translator, vocab_terms)
    except RuntimeError as exc:
        print(f"{ERR_COLOR}{exc}{RESET}", file=sys.stderr)
        return 1

    stop = threading.Event()
    inflight = InFlight()
    utterances: "queue.Queue[Utterance]" = queue.Queue(maxsize=50)
    to_translate: "queue.Queue[tuple[Line, str]]" = queue.Queue(maxsize=50)
    printer = Printer(transcript)

    sources: list[tuple[str, str, str]] = [
        ("THEM", args.them_device, args.them_lang)
    ]
    if not args.no_mic:
        sources.append(("YOU", args.you_device, args.you_lang))
    languages = {speaker: lang for speaker, _, lang in sources}

    segmenters: list[Segmenter] = []
    streams: list[sd.InputStream] = []
    threads: list[threading.Thread] = []

    try:
        for speaker, device_name, _ in sources:
            segmenter = Segmenter(speaker, utterances, args.threshold, stop)
            streams.append(open_stream(device_name, segmenter))
            segmenters.append(segmenter)
    except RuntimeError as exc:
        print(f"{ERR_COLOR}{exc}{RESET}", file=sys.stderr)
        for stream in streams:
            stream.stop()
            stream.close()
        printer.close()
        return 1

    print(f"{DIM}Transcript: {transcript}{RESET}", flush=True)

    for segmenter in segmenters:
        threads.append(threading.Thread(
            target=segmenter.run, name=f"seg-{segmenter.speaker}", daemon=True))
    threads.append(threading.Thread(
        target=asr_worker,
        args=(utterances, to_translate, args.model, languages, printer, stop,
              inflight, vocab),
        name="asr", daemon=True))
    threads.append(threading.Thread(
        target=translate_worker,
        args=(to_translate, translator, printer, stop, inflight),
        name="translate", daemon=True))
    for thread in threads:
        thread.start()

    try:
        while not stop.is_set():
            time.sleep(0.3)
    except KeyboardInterrupt:
        print(f"\n{DIM}Stopping — draining queues...{RESET}", flush=True)
    finally:
        for stream in streams:
            stream.stop()
            stream.close()
        # Let the pipeline finish what it already captured. Empty queues are
        # not enough — a worker holds the item it is currently working on.
        deadline = time.time() + 60.0
        while time.time() < deadline and (
            not utterances.empty() or not to_translate.empty() or inflight.busy()
        ):
            time.sleep(0.3)
        if inflight.busy():
            print(f"{ERR_COLOR}Не дождались перевода последних реплик — "
                  f"обрываю.{RESET}", file=sys.stderr, flush=True)
        stop.set()
        for thread in threads:
            thread.join(timeout=10.0)
        printer.close()
        print(f"{DIM}Transcript saved: {transcript}{RESET}", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
