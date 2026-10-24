"""Post-meeting speech coaching.

Re-transcribes the local-mic recording captured by
``saymo.audio.meeting_recorder.MeetingRecorder`` with the offline Whisper
model configured in ``config.stt.whisper`` (large by default — the live path
runs a small model for latency and is too weak on Russian for this), then
asks the local LLM for delivery feedback via
``saymo.speech.ollama_composer.compose_speech_coaching``.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from saymo.speech.ollama_composer import check_ollama_health, compose_speech_coaching
from saymo.stt.whisper_local import LocalWhisper

logger = logging.getLogger("saymo.analysis.speech_review")


def reviews_dir() -> Path:
    return Path.home() / ".saymo" / "speech_reviews"


def transcribe_meeting_recording(wav_path: Path, config) -> str:
    """Re-transcribe a full meeting recording with the configured offline model."""
    whisper = LocalWhisper(
        model_size=config.stt.whisper.model_size,
        language=config.speech.language,
    )
    return whisper.transcribe(str(wav_path))


async def run_speech_review(
    wav_path: Path,
    config,
    *,
    profile_name: str = "",
    meeting_description: str = "",
) -> tuple[str, Path]:
    """Transcribe ``wav_path`` and compose spoken-delivery recommendations.

    Returns the recommendations text and the markdown report path it was
    written to under ``~/.saymo/speech_reviews/``.
    """
    wav_path = Path(wav_path)
    logger.info(f"Re-transcribing {wav_path} for speech review")
    transcript = transcribe_meeting_recording(wav_path, config)

    if not await check_ollama_health(config.ollama.url):
        raise RuntimeError("Ollama not running — start with: ollama serve")

    recommendations = await compose_speech_coaching(
        transcript,
        model=config.ollama.model,
        ollama_url=config.ollama.url,
        meeting_description=meeting_description,
        config=config,
    )

    target_dir = reviews_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"-{profile_name}" if profile_name else ""
    report_path = target_dir / f"{date.today().isoformat()}{suffix}.md"
    report_path.write_text(
        f"# Speech review — {date.today().isoformat()}{suffix}\n\n"
        f"## Recommendations\n\n{recommendations}\n\n"
        f"## Transcript\n\n{transcript}\n",
        encoding="utf-8",
    )
    logger.info(f"Speech review written to {report_path}")
    return recommendations, report_path
