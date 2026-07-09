"""Privacy-safe metadata sidecars for generated voice audio caches."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from saymo.config import SaymoConfig
from saymo.tts.selector import selector_fingerprint_payload


@dataclass(frozen=True)
class VoiceCacheMetadata:
    purpose: str
    selected_engine: str
    attempted_engines: tuple[str, ...] = ()
    fingerprint: str = ""
    fallback_engine: str = ""
    is_voice_clone: bool = False
    blocked_reason: str = ""
    profile: str = ""
    profile_approved: bool = False
    source_kind: str = ""
    source_profile: str = ""
    source_sha256: str = ""
    source_type: str = ""
    source_preset_id: str = ""
    profile_preset_id: str = ""
    source_override_preset_id: str = ""
    reference_audio_sha256: str = ""
    reference_text_sha256: str = ""
    non_cloned_allowed: bool = False
    schema_version: int = 1
    created_at: str = field(default_factory=lambda: _now())


@dataclass(frozen=True)
class VoiceCacheMetadataCheck:
    valid: bool
    blocked_reason: str = ""
    metadata: VoiceCacheMetadata | None = None


def build_voice_cache_metadata(
    config: SaymoConfig,
    *,
    purpose: str,
    text: str = "",
    source_kind: str = "",
    source_profile: str = "",
    source_sha256: str = "",
    profile: str = "",
    source_type: str | None = None,
) -> VoiceCacheMetadata:
    payload = selector_fingerprint_payload(
        config,
        purpose=purpose,
        profile=profile,
        source_type=source_type,
    )
    selector = payload["selector"]
    source_preset = payload.get("source_preset") or {}
    fingerprint = _sha256_json(payload)
    resolved_source_sha256 = source_sha256
    if not resolved_source_sha256 and text:
        resolved_source_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return VoiceCacheMetadata(
        purpose=purpose,
        selected_engine=selector["selected_engine"],
        attempted_engines=tuple(selector["attempted_engines"]),
        fingerprint=fingerprint,
        fallback_engine=selector["fallback_engine"],
        is_voice_clone=selector["is_voice_clone"],
        blocked_reason=selector["blocked_reason"],
        profile=selector["profile"],
        profile_approved=selector["profile_approved"],
        source_kind=source_kind,
        source_profile=source_profile,
        source_sha256=resolved_source_sha256,
        source_type=str(source_preset.get("source_type") or source_type or ""),
        source_preset_id=str(source_preset.get("resolved_preset_id") or ""),
        profile_preset_id=str(source_preset.get("profile_preset_id") or ""),
        source_override_preset_id=str(source_preset.get("override_preset_id") or ""),
        reference_audio_sha256=selector["reference_audio_sha256"],
        reference_text_sha256=selector["reference_text_sha256"],
        non_cloned_allowed=selector["non_cloned_allowed"],
    )


def voice_cache_metadata_path(audio_path: str | Path) -> Path:
    path = Path(audio_path)
    return path.with_name(path.name + ".meta.json")


def write_voice_cache_metadata(
    audio_path: str | Path,
    metadata: VoiceCacheMetadata,
) -> Path:
    out = voice_cache_metadata_path(audio_path)
    out.write_text(
        json.dumps(_metadata_to_json(metadata), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return out


def read_voice_cache_metadata(audio_path: str | Path) -> VoiceCacheMetadata:
    data = json.loads(voice_cache_metadata_path(audio_path).read_text(encoding="utf-8"))
    return _metadata_from_json(data)


def check_voice_cache_metadata(
    audio_path: str | Path,
    expected: VoiceCacheMetadata,
) -> VoiceCacheMetadataCheck:
    if not Path(audio_path).exists():
        return VoiceCacheMetadataCheck(False, "audio_missing")
    sidecar = voice_cache_metadata_path(audio_path)
    if not sidecar.exists():
        return VoiceCacheMetadataCheck(False, "voice_metadata_missing")
    current = read_voice_cache_metadata(audio_path)
    if current.fingerprint != expected.fingerprint:
        return VoiceCacheMetadataCheck(False, "voice_metadata_stale", current)
    if expected.source_sha256 and current.source_sha256 != expected.source_sha256:
        return VoiceCacheMetadataCheck(False, "source_metadata_stale", current)
    return VoiceCacheMetadataCheck(True, metadata=current)


def _metadata_to_json(metadata: VoiceCacheMetadata) -> dict[str, Any]:
    payload = asdict(metadata)
    payload["attempted_engines"] = list(metadata.attempted_engines)
    return payload


def _metadata_from_json(data: dict[str, Any]) -> VoiceCacheMetadata:
    return VoiceCacheMetadata(
        purpose=str(data.get("purpose") or ""),
        selected_engine=str(data.get("selected_engine") or ""),
        attempted_engines=tuple(data.get("attempted_engines") or ()),
        fingerprint=str(data.get("fingerprint") or ""),
        fallback_engine=str(data.get("fallback_engine") or ""),
        is_voice_clone=bool(data.get("is_voice_clone", False)),
        blocked_reason=str(data.get("blocked_reason") or ""),
        profile=str(data.get("profile") or ""),
        profile_approved=bool(data.get("profile_approved", False)),
        source_kind=str(data.get("source_kind") or ""),
        source_profile=str(data.get("source_profile") or ""),
        source_sha256=str(data.get("source_sha256") or ""),
        source_type=str(data.get("source_type") or ""),
        source_preset_id=str(data.get("source_preset_id") or ""),
        profile_preset_id=str(data.get("profile_preset_id") or ""),
        source_override_preset_id=str(data.get("source_override_preset_id") or ""),
        reference_audio_sha256=str(data.get("reference_audio_sha256") or ""),
        reference_text_sha256=str(data.get("reference_text_sha256") or ""),
        non_cloned_allowed=bool(data.get("non_cloned_allowed", False)),
        schema_version=int(data.get("schema_version") or 1),
        created_at=str(data.get("created_at") or _now()),
    )


def _sha256_json(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
