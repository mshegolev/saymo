"""Protected voice profile manifests for local voice-clone readiness."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import soundfile as sf

from saymo.tts.factory import is_known_engine


@dataclass(frozen=True)
class VoiceReferenceAudio:
    path: str
    exists: bool
    size_bytes: int
    sha256: str
    duration_seconds: float | None = None
    sample_rate: int | None = None
    channels: int | None = None


@dataclass(frozen=True)
class VoiceReferenceText:
    path: str
    exists: bool
    size_bytes: int
    sha256: str
    chars: int
    preview: str | None = None


@dataclass(frozen=True)
class VoiceProfileManifest:
    profile: str
    engine: str
    language: str
    reference_audio: VoiceReferenceAudio
    reference_text: VoiceReferenceText
    approved_for_calls: bool = False
    approved_benchmark_run: str = ""
    fallback_policy: str = "blocked_until_approved"
    created_at: str = field(default_factory=lambda: _now())
    updated_at: str = field(default_factory=lambda: _now())


@dataclass(frozen=True)
class VoiceProfileCheck:
    profile: str
    status: str
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def build_voice_profile_manifest(
    *,
    profile: str,
    voice_sample: str | Path,
    ref_text_file: str | Path | None,
    engine: str,
    language: str,
) -> VoiceProfileManifest:
    """Build a profile manifest that references existing local files."""
    if not profile.strip():
        raise ValueError("profile must not be empty")
    if not is_known_engine(engine):
        raise ValueError(f"unknown TTS engine: {engine}")

    audio = _audio_reference(Path(voice_sample).expanduser())
    text = _text_reference(Path(ref_text_file).expanduser() if ref_text_file else None)
    return VoiceProfileManifest(
        profile=profile.strip(),
        engine=engine,
        language=language,
        reference_audio=audio,
        reference_text=text,
    )


def write_voice_profile_manifest(
    manifest: VoiceProfileManifest,
    *,
    profiles_dir: str | Path | None = None,
) -> Path:
    """Write a profile manifest under ~/.saymo/voice_profiles/<profile>/."""
    root = Path(profiles_dir).expanduser() if profiles_dir else _default_profiles_dir()
    out_dir = root / manifest.profile
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "profile.json"
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(voice_profile_to_json(manifest), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(out)
    return out


def load_voice_profile_manifest(
    profile: str,
    *,
    profiles_dir: str | Path | None = None,
) -> VoiceProfileManifest:
    """Load a voice profile manifest by profile id."""
    root = Path(profiles_dir).expanduser() if profiles_dir else _default_profiles_dir()
    path = root / profile / "profile.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return voice_profile_from_json(data)


def check_voice_profile(manifest: VoiceProfileManifest) -> VoiceProfileCheck:
    """Check whether referenced profile assets still match the manifest."""
    blockers: list[str] = []
    warnings: list[str] = []

    audio_path = Path(manifest.reference_audio.path).expanduser()
    if not audio_path.exists():
        blockers.append(f"reference audio missing: {audio_path}")
    else:
        current_hash = _sha256_file(audio_path)
        if current_hash != manifest.reference_audio.sha256:
            blockers.append(f"reference audio hash changed: {audio_path}")

    text_path = Path(manifest.reference_text.path).expanduser() if manifest.reference_text.path else None
    if text_path:
        if not text_path.exists():
            warnings.append(f"reference transcript missing: {text_path}")
        else:
            current_hash = _sha256_file(text_path)
            if current_hash != manifest.reference_text.sha256:
                warnings.append(f"reference transcript hash changed: {text_path}")

    if not is_known_engine(manifest.engine):
        blockers.append(f"unknown TTS engine: {manifest.engine}")

    return VoiceProfileCheck(
        profile=manifest.profile,
        status="blocked" if blockers else "ready",
        blockers=tuple(blockers),
        warnings=tuple(warnings),
    )


def voice_profile_to_json(manifest: VoiceProfileManifest) -> dict[str, Any]:
    """Serialize a profile manifest without transcript text."""
    return asdict(manifest)


def voice_profile_from_json(data: dict[str, Any]) -> VoiceProfileManifest:
    """Deserialize a profile manifest."""
    return VoiceProfileManifest(
        profile=str(data["profile"]),
        engine=str(data["engine"]),
        language=str(data.get("language") or "ru"),
        reference_audio=VoiceReferenceAudio(**data["reference_audio"]),
        reference_text=VoiceReferenceText(**data["reference_text"]),
        approved_for_calls=bool(data.get("approved_for_calls", False)),
        approved_benchmark_run=str(data.get("approved_benchmark_run") or ""),
        fallback_policy=str(data.get("fallback_policy") or "blocked_until_approved"),
        created_at=str(data.get("created_at") or _now()),
        updated_at=str(data.get("updated_at") or _now()),
    )


def _audio_reference(path: Path) -> VoiceReferenceAudio:
    size = path.stat().st_size if path.exists() else 0
    sha = _sha256_file(path) if path.exists() else ""
    duration = None
    sample_rate = None
    channels = None
    if path.exists():
        try:
            info = sf.info(str(path))
            sample_rate = int(info.samplerate)
            channels = int(info.channels)
            duration = float(info.frames / info.samplerate) if info.samplerate else None
        except Exception:
            duration = None
    return VoiceReferenceAudio(
        path=str(path),
        exists=path.exists(),
        size_bytes=size,
        sha256=sha,
        duration_seconds=duration,
        sample_rate=sample_rate,
        channels=channels,
    )


def _text_reference(path: Path | None) -> VoiceReferenceText:
    if path is None:
        return VoiceReferenceText(path="", exists=False, size_bytes=0, sha256="", chars=0)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    return VoiceReferenceText(
        path=str(path),
        exists=path.exists(),
        size_bytes=path.stat().st_size if path.exists() else 0,
        sha256=_sha256_file(path) if path.exists() else "",
        chars=len(text),
        preview=None,
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _default_profiles_dir() -> Path:
    return Path.home() / ".saymo" / "voice_profiles"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
