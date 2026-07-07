"""Read-only inventory of local Saymo voice-clone assets."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import soundfile as sf

from saymo.config import SaymoConfig
from saymo.tts.factory import KNOWN_ENGINES


@dataclass(frozen=True)
class VoiceAssetRecord:
    role: str
    path: str
    status: str
    classification: str
    size_bytes: int = 0
    engine: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VoiceInventoryReport:
    active_engine: str
    realtime_engine: str
    known_engines: tuple[str, ...]
    assets: tuple[VoiceAssetRecord, ...]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))


def build_voice_inventory(
    config: SaymoConfig,
    *,
    saymo_home: str | Path | None = None,
    f5_root: str | Path | None = None,
) -> VoiceInventoryReport:
    """Inspect known local voice paths without mutating them."""
    home = Path(saymo_home).expanduser() if saymo_home else Path.home() / ".saymo"
    f5 = Path(f5_root).expanduser() if f5_root else Path.home() / "F5TTS"
    active = config.tts.engine
    realtime = config.tts.realtime_engine or ""

    voice_sample = home / "voice_samples" / "voice_sample.wav"
    transcript = voice_sample.with_suffix(".txt")
    training_root = home / "training_dataset"
    models_root = home / "models"
    cache_root = home / "audio_cache"
    benchmark_root = home / "voice_benchmarks"
    f5_venv = (
        Path(config.tts.f5tts.venv_python).expanduser()
        if config.tts.f5tts.venv_python
        else f5 / ".venv" / "bin" / "python"
    )
    ckpt = Path(config.tts.f5tts.ckpt_file).expanduser() if config.tts.f5tts.ckpt_file else None
    vocab = Path(config.tts.f5tts.vocab_file).expanduser() if config.tts.f5tts.vocab_file else None

    assets = [
        _file_asset("voice_sample", voice_sample, classification="protected", metadata=_audio_metadata(voice_sample)),
        _transcript_asset(transcript),
        _dir_asset("training_dataset", training_root, classification="protected"),
        _dir_asset("models_root", models_root, classification="protected"),
        _dir_asset("audio_cache", cache_root, classification="generated"),
        _dir_asset("benchmark_root", benchmark_root, classification="generated"),
        _file_asset("f5_venv_python", f5_venv, classification="runtime", engine="f5tts_clone"),
        _file_asset(
            "f5_checkpoint",
            ckpt,
            classification="runtime",
            engine="f5tts_clone",
            missing_classification="requires_user_action",
        ),
        _file_asset(
            "f5_vocab",
            vocab,
            classification="runtime",
            engine="f5tts_clone",
            missing_classification="requires_user_action",
        ),
        VoiceAssetRecord(
            role="engine_config",
            path="config.tts.engine",
            status="usable" if active in KNOWN_ENGINES else "missing",
            classification="config" if active in KNOWN_ENGINES else "requires_user_action",
            metadata={"active_engine": active, "realtime_engine": realtime},
        ),
    ]

    return VoiceInventoryReport(
        active_engine=active,
        realtime_engine=realtime,
        known_engines=tuple(sorted(KNOWN_ENGINES)),
        assets=tuple(assets),
    )


def voice_inventory_to_json(report: VoiceInventoryReport) -> dict[str, Any]:
    """Serialize inventory to JSON-compatible primitives."""
    return asdict(report)


def render_voice_inventory_markdown(report: VoiceInventoryReport) -> str:
    """Render a concise sanitized inventory report."""
    lines = [
        "# Saymo Voice Inventory",
        "",
        f"active engine: {report.active_engine}",
        f"realtime engine: {report.realtime_engine or '(same as active)'}",
        "",
        "| Role | Status | Classification | Path |",
        "|------|--------|----------------|------|",
    ]
    for asset in report.assets:
        lines.append(
            f"| {asset.role} | {asset.status} | {asset.classification} | {asset.path} |"
        )
    return "\n".join(lines) + "\n"


def write_voice_inventory_json(path: str | Path, report: VoiceInventoryReport) -> Path:
    """Write sanitized inventory JSON."""
    out = Path(path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(voice_inventory_to_json(report), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return out


def _file_asset(
    role: str,
    path: Path | None,
    *,
    classification: str,
    engine: str = "",
    metadata: dict[str, Any] | None = None,
    missing_classification: str | None = None,
) -> VoiceAssetRecord:
    if path is None:
        return VoiceAssetRecord(
            role=role,
            path="",
            status="missing",
            classification=missing_classification or "requires_user_action",
            engine=engine,
            metadata=metadata or {},
        )
    exists = path.exists()
    return VoiceAssetRecord(
        role=role,
        path=str(path),
        status="usable" if exists else "missing",
        classification=classification if exists else (missing_classification or "requires_user_action"),
        size_bytes=path.stat().st_size if exists and path.is_file() else 0,
        engine=engine,
        metadata=metadata or {},
    )


def _dir_asset(role: str, path: Path, *, classification: str) -> VoiceAssetRecord:
    exists = path.exists()
    return VoiceAssetRecord(
        role=role,
        path=str(path),
        status="usable" if exists else "missing",
        classification=classification if exists else "requires_user_action",
        size_bytes=_direct_size(path) if exists else 0,
    )


def _transcript_asset(path: Path) -> VoiceAssetRecord:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    return _file_asset(
        "voice_transcript",
        path,
        classification="protected",
        metadata={"chars": len(text)},
    )


def _audio_metadata(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        info = sf.info(str(path))
    except Exception:
        return {}
    return {
        "sample_rate": int(info.samplerate),
        "channels": int(info.channels),
        "duration_seconds": float(info.frames / info.samplerate) if info.samplerate else None,
    }


def _direct_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    if not path.is_dir():
        return 0
    return sum(child.stat().st_size for child in path.iterdir() if child.is_file())
