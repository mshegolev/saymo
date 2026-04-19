"""Build training dataset from raw voice recordings.

Segments audio, transcribes via Whisper, validates quality,
generates metadata.csv in LJSpeech format for XTTS v2 fine-tuning.
"""

import csv
import json
import logging
import random
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

logger = logging.getLogger("saymo.tts.dataset")

TRAINING_DATASET_DIR = Path.home() / ".saymo" / "training_dataset"
DEFAULT_SAMPLE_RATE = 22050


@dataclass
class DatasetReport:
    """Summary of dataset preparation results."""

    total_segments: int = 0
    total_duration_sec: float = 0.0
    good_segments: int = 0
    noisy_segments: int = 0
    too_short_segments: int = 0
    too_long_segments: int = 0
    clipped_segments: int = 0
    train_segments: int = 0
    eval_segments: int = 0
    problems: list[str] = field(default_factory=list)

    @property
    def ready_for_training(self) -> bool:
        return self.good_segments >= 50 and self.total_duration_sec >= 600  # 10+ min

    def summary(self) -> str:
        lines = [
            f"Total segments: {self.total_segments}",
            f"Good segments:  {self.good_segments}",
            f"Total duration: {self.total_duration_sec / 60:.1f} min",
            f"Train/Eval:     {self.train_segments}/{self.eval_segments}",
        ]
        if self.noisy_segments:
            lines.append(f"Noisy:          {self.noisy_segments}")
        if self.too_short_segments:
            lines.append(f"Too short:      {self.too_short_segments}")
        if self.too_long_segments:
            lines.append(f"Too long:       {self.too_long_segments}")
        if self.clipped_segments:
            lines.append(f"Clipped:        {self.clipped_segments}")
        lines.append(f"Ready:          {'Yes' if self.ready_for_training else 'No (need 50+ good segments, 10+ min)'}")
        if self.problems:
            lines.append("Problems:")
            for p in self.problems[:10]:
                lines.append(f"  - {p}")
        return "\n".join(lines)


def _read_wav(path: Path) -> tuple[np.ndarray, int]:
    """Read WAV file, return (samples_int16, sample_rate)."""
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)
        audio = np.frombuffer(raw, dtype=np.int16)
    return audio, sr


def _compute_snr(audio: np.ndarray) -> float:
    """Estimate SNR in dB using signal vs noise floor."""
    float_audio = audio.astype(np.float32) / 32768.0
    if len(float_audio) == 0:
        return 0.0

    # Split into frames, estimate noise from quietest 10%
    frame_size = 1024
    n_frames = max(1, len(float_audio) // frame_size)
    energies = []
    for i in range(n_frames):
        frame = float_audio[i * frame_size:(i + 1) * frame_size]
        energies.append(float(np.mean(frame ** 2)))

    energies.sort()
    n_noise = max(1, len(energies) // 10)
    noise_power = np.mean(energies[:n_noise])
    signal_power = np.mean(energies)

    if noise_power <= 0:
        return 60.0  # Very clean
    return float(10 * np.log10(signal_power / noise_power))


def _detect_clipping(audio: np.ndarray, threshold: float = 0.99) -> bool:
    """Check if audio has clipping (samples near max amplitude)."""
    max_val = 32767 * threshold
    clipped = np.sum(np.abs(audio.astype(np.float32)) >= max_val)
    return bool(clipped > len(audio) * 0.001)  # >0.1% clipped samples


def _segment_audio(
    audio: np.ndarray,
    sample_rate: int,
    min_duration: float = 3.0,
    max_duration: float = 15.0,
    silence_threshold: float = 0.01,
    min_silence_duration: float = 0.3,
) -> list[np.ndarray]:
    """Split audio into segments by silence.

    Args:
        audio: Audio samples (int16).
        sample_rate: Sample rate.
        min_duration: Minimum segment duration in seconds.
        max_duration: Maximum segment duration in seconds.
        silence_threshold: Energy threshold for silence detection.
        min_silence_duration: Minimum silence length to split on.

    Returns:
        List of audio segments.
    """
    float_audio = np.abs(audio.astype(np.float32) / 32768.0)
    min_samples = int(min_duration * sample_rate)
    max_samples = int(max_duration * sample_rate)
    silence_samples = int(min_silence_duration * sample_rate)

    # Find silence regions
    is_silence = float_audio < silence_threshold

    segments = []
    start = 0

    while start < len(audio):
        end = min(start + max_samples, len(audio))

        if end - start <= min_samples:
            # Remaining audio too short — append to last segment or keep as-is
            if segments and len(audio[start:]) < min_samples:
                # Too short to be its own segment
                break
            segments.append(audio[start:end])
            break

        # Look for silence near max_duration to split naturally
        search_start = start + min_samples
        best_split = end

        for pos in range(search_start, end):
            if pos + silence_samples > len(is_silence):
                break
            if np.all(is_silence[pos:pos + silence_samples]):
                best_split = pos + silence_samples // 2
                break

        segments.append(audio[start:best_split])
        start = best_split

    return [s for s in segments if len(s) >= min_samples]


class DatasetBuilder:
    """Build training dataset from raw voice recordings.

    Workflow:
    1. Read raw WAV files from raw_dir
    2. Segment into 3-15s clips
    3. Transcribe via faster-whisper
    4. Validate quality (SNR, clipping, duration)
    5. Generate metadata.csv
    6. Split into train/eval (90/10)
    """

    def __init__(
        self,
        raw_dir: Path | None = None,
        output_dir: Path | None = None,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        language: str = "ru",
    ):
        self.raw_dir = raw_dir or TRAINING_DATASET_DIR / "raw"
        self.output_dir = output_dir or TRAINING_DATASET_DIR
        self.sample_rate = sample_rate
        self.language = language

        self.wavs_dir = self.output_dir / "wavs"
        self.eval_dir = self.output_dir / "eval"
        self.eval_wavs_dir = self.eval_dir / "wavs"

    def _get_raw_files(self) -> list[Path]:
        """Find all WAV files in raw directory."""
        if not self.raw_dir.exists():
            return []
        files = sorted(self.raw_dir.glob("*.wav"))
        return [f for f in files if f.name != "session_progress.json"]

    def _copy_raw_files(self, raw_files: list[Path]) -> list[Path]:
        """Copy raw files to wavs_dir without segmentation.

        Used for guided recordings where each file maps 1:1 to a prompt.
        """
        import shutil

        self.wavs_dir.mkdir(parents=True, exist_ok=True)

        # Clear old segments to avoid stale data
        for old in self.wavs_dir.glob("*.wav"):
            old.unlink()

        copied = []
        for idx, raw_path in enumerate(raw_files):
            dst = self.wavs_dir / f"{idx:04d}.wav"
            shutil.copy2(raw_path, dst)
            copied.append(dst)

        return copied

    def segment_audio(
        self,
        min_duration: float = 3.0,
        max_duration: float = 15.0,
    ) -> list[Path]:
        """Segment all raw recordings into clips.

        Returns:
            List of paths to segmented WAV files.
        """
        self.wavs_dir.mkdir(parents=True, exist_ok=True)

        raw_files = self._get_raw_files()
        if not raw_files:
            raise FileNotFoundError(f"No WAV files in {self.raw_dir}")

        logger.info(f"Segmenting {len(raw_files)} raw files...")
        all_segments: list[Path] = []
        seg_idx = 0

        for raw_path in raw_files:
            audio, sr = _read_wav(raw_path)

            # Resample if needed
            if sr != self.sample_rate:
                logger.warning(f"{raw_path.name}: sample rate {sr} != {self.sample_rate}, skipping")
                continue

            # If file is already short enough, use as-is
            duration = len(audio) / sr
            if duration <= max_duration:
                segments = [audio]
            else:
                segments = _segment_audio(audio, sr, min_duration, max_duration)

            for seg in segments:
                seg_path = self.wavs_dir / f"{seg_idx:04d}.wav"
                with wave.open(str(seg_path), "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(self.sample_rate)
                    wf.writeframes(seg.tobytes())
                all_segments.append(seg_path)
                seg_idx += 1

        logger.info(f"Created {len(all_segments)} segments")
        return all_segments

    def transcribe_segments(self, whisper_model: str = "small") -> dict[str, str]:
        """Transcribe all segmented WAV files.

        Args:
            whisper_model: Whisper model size.

        Returns:
            Dict mapping filename to transcription.
        """
        from saymo.stt.whisper_local import LocalWhisper

        whisper = LocalWhisper(model_size=whisper_model, language=self.language)
        wav_files = sorted(self.wavs_dir.glob("*.wav"))

        if not wav_files:
            raise FileNotFoundError(f"No segments in {self.wavs_dir}")

        logger.info(f"Transcribing {len(wav_files)} segments with whisper-{whisper_model}...")
        transcriptions: dict[str, str] = {}

        for wav_path in wav_files:
            audio, sr = _read_wav(wav_path)
            # Convert to float32 for whisper
            float_audio = audio.astype(np.float32) / 32768.0
            text = whisper.transcribe(float_audio)
            text = text.strip()

            if text:
                transcriptions[wav_path.name] = text
                logger.debug(f"{wav_path.name}: {text[:80]}")
            else:
                logger.warning(f"{wav_path.name}: empty transcription, skipping")

        logger.info(f"Transcribed {len(transcriptions)}/{len(wav_files)} segments")
        return transcriptions

    def validate_dataset(self) -> DatasetReport:
        """Validate quality of segmented audio files.

        Returns:
            DatasetReport with quality metrics.
        """
        report = DatasetReport()
        wav_files = sorted(self.wavs_dir.glob("*.wav")) if self.wavs_dir.exists() else []

        for wav_path in wav_files:
            audio, sr = _read_wav(wav_path)
            duration = len(audio) / sr
            report.total_segments += 1
            report.total_duration_sec += duration

            problems = []

            if duration < 3.0:
                report.too_short_segments += 1
                problems.append(f"too short ({duration:.1f}s)")

            if duration > 25.0:
                report.too_long_segments += 1
                problems.append(f"too long ({duration:.1f}s)")

            snr = _compute_snr(audio)
            if snr < 20.0:
                report.noisy_segments += 1
                problems.append(f"low SNR ({snr:.1f}dB)")

            if _detect_clipping(audio):
                report.clipped_segments += 1
                problems.append("clipping detected")

            if problems:
                report.problems.append(f"{wav_path.name}: {', '.join(problems)}")
            else:
                report.good_segments += 1

        return report

    def build(
        self,
        min_duration: float = 3.0,
        max_duration: float = 15.0,
        whisper_model: str = "small",
        eval_ratio: float = 0.1,
        prompts: list[str] | None = None,
    ) -> DatasetReport:
        """Full pipeline: segment -> transcribe -> validate -> save.

        Args:
            min_duration: Min segment duration.
            max_duration: Max segment duration.
            whisper_model: Whisper model for transcription.
            eval_ratio: Fraction of data for evaluation set.
            prompts: If provided, use as ground-truth transcriptions instead
                     of Whisper. When prompts are given, raw files are copied
                     as-is (no segmentation) so that each prompt maps 1:1
                     to its recording.

        Returns:
            DatasetReport with results.
        """
        raw_files = self._get_raw_files()

        # Step 1: Segment (or copy as-is for guided recordings)
        if prompts:
            # Guided recording mode: copy raw files directly, no segmentation.
            # Raw files are ~15-20s each — XTTS v2 handles up to 30s fine.
            # Segmenting would break the 1:1 prompt-to-audio mapping.
            #
            # If we have fewer prompts than raw files (e.g., extra recordings
            # beyond the prompt set), only use raw files that have prompts.
            usable_raw = raw_files[:len(prompts)]
            if len(usable_raw) < len(raw_files):
                logger.info(
                    f"Using {len(usable_raw)}/{len(raw_files)} raw files "
                    f"(matched to {len(prompts)} prompts)"
                )
            segments = self._copy_raw_files(usable_raw)
            logger.info(f"Guided mode: copied {len(segments)} raw files as-is (no segmentation)")

            # Use provided prompts as ground-truth transcriptions
            transcriptions = {}
            for seg_path, prompt_text in zip(segments, prompts):
                transcriptions[seg_path.name] = prompt_text
            logger.info(f"Using {len(prompts)} ground-truth transcriptions")
        else:
            segments = self.segment_audio(min_duration, max_duration)
            transcriptions = self.transcribe_segments(whisper_model)

        # Step 3: Validate
        report = self.validate_dataset()

        # Step 4: Split train/eval
        items = list(transcriptions.items())
        random.shuffle(items)
        n_eval = max(1, int(len(items) * eval_ratio))
        eval_items = items[:n_eval]
        train_items = items[n_eval:]

        # Step 5: Write metadata.csv for train
        metadata_path = self.output_dir / "metadata.csv"
        with open(metadata_path, "w", newline="") as f:
            writer = csv.writer(f, delimiter="|")
            for filename, text in sorted(train_items):
                writer.writerow([filename.replace(".wav", ""), text])

        report.train_segments = len(train_items)

        # Step 6: Write eval set
        self.eval_dir.mkdir(parents=True, exist_ok=True)
        self.eval_wavs_dir.mkdir(parents=True, exist_ok=True)

        eval_metadata_path = self.eval_dir / "metadata.csv"
        with open(eval_metadata_path, "w", newline="") as f:
            writer = csv.writer(f, delimiter="|")
            for filename, text in sorted(eval_items):
                # Copy WAV to eval dir
                src = self.wavs_dir / filename
                dst = self.eval_wavs_dir / filename
                if src.exists():
                    dst.write_bytes(src.read_bytes())
                writer.writerow([filename.replace(".wav", ""), text])

        report.eval_segments = len(eval_items)

        # Save report
        report_path = self.output_dir / "dataset_report.json"
        report_path.write_text(json.dumps({
            "total_segments": report.total_segments,
            "good_segments": report.good_segments,
            "total_duration_sec": report.total_duration_sec,
            "train_segments": report.train_segments,
            "eval_segments": report.eval_segments,
            "ready": report.ready_for_training,
        }, indent=2))

        logger.info(f"Dataset built: {report.train_segments} train, {report.eval_segments} eval")
        return report

    def get_status(self) -> dict:
        """Get current dataset status without building."""
        status = {
            "raw_files": len(self._get_raw_files()),
            "segments": 0,
            "duration_sec": 0.0,
            "has_metadata": False,
            "has_model": False,
        }

        if self.wavs_dir.exists():
            wav_files = list(self.wavs_dir.glob("*.wav"))
            status["segments"] = len(wav_files)
            for wav_path in wav_files:
                audio, sr = _read_wav(wav_path)
                status["duration_sec"] += len(audio) / sr

        status["has_metadata"] = (self.output_dir / "metadata.csv").exists()

        model_dir = Path.home() / ".saymo" / "models" / "xtts_finetuned"
        status["has_model"] = (model_dir / "model.pth").exists() or (model_dir / "best_model.pth").exists()

        report_path = self.output_dir / "dataset_report.json"
        if report_path.exists():
            status["last_report"] = json.loads(report_path.read_text())

        return status
