"""Named timing presets for F5-TTS natural pacing."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from saymo.config import F5TTSConfig, SaymoConfig


@dataclass(frozen=True)
class F5PausePreset:
    """Concrete F5 timing values that can be applied to config."""

    id: str
    label: str
    description: str
    sentence_pause_seconds: float
    clause_pause_seconds: float
    silent_breath_pause_seconds: float
    breath_interval_sentences: int

    @property
    def paragraph_pause_seconds(self) -> float:
        """F5 uses the silent-breath pause for paragraph breaks."""
        return self.silent_breath_pause_seconds

    def to_config_update(self) -> dict[str, float | int | str]:
        return {
            "pause_preset": self.id,
            "sentence_pause_seconds": self.sentence_pause_seconds,
            "clause_pause_seconds": self.clause_pause_seconds,
            "silent_breath_pause_seconds": self.silent_breath_pause_seconds,
            "breath_interval_sentences": self.breath_interval_sentences,
        }

    def to_timing_dict(self) -> dict[str, float | int | str]:
        return {
            **self.to_config_update(),
            "paragraph_pause_seconds": self.paragraph_pause_seconds,
        }


F5_SOURCE_TYPES = ("prepared", "response_cache", "spontaneous")
F5_SOURCE_TYPE_PURPOSES = {
    "prepared": "prepare",
    "response_cache": "response_cache",
    "spontaneous": "preview",
}


@dataclass(frozen=True)
class F5PresetResolution:
    """Resolved F5 pause preset choice for a profile/source-type pair."""

    profile: str
    source_type: str
    purpose: str
    profile_preset_id: str
    override_preset_id: str
    resolved_preset_id: str
    preset: F5PausePreset


F5_PAUSE_PRESETS: tuple[F5PausePreset, ...] = (
    F5PausePreset(
        id="approved",
        label="Approved benchmark",
        description="Matches the currently approved local F5 benchmark timing.",
        sentence_pause_seconds=0.38,
        clause_pause_seconds=0.18,
        silent_breath_pause_seconds=0.60,
        breath_interval_sentences=2,
    ),
    F5PausePreset(
        id="crisp",
        label="Crisp",
        description="Shorter gaps for quick status answers without robot-fast delivery.",
        sentence_pause_seconds=0.26,
        clause_pause_seconds=0.12,
        silent_breath_pause_seconds=0.42,
        breath_interval_sentences=2,
    ),
    F5PausePreset(
        id="calm",
        label="Calm",
        description="A little more room between thoughts for natural live-call pacing.",
        sentence_pause_seconds=0.44,
        clause_pause_seconds=0.22,
        silent_breath_pause_seconds=0.68,
        breath_interval_sentences=2,
    ),
    F5PausePreset(
        id="deliberate",
        label="Deliberate",
        description="Longer pauses for careful explanations and less rushed delivery.",
        sentence_pause_seconds=0.55,
        clause_pause_seconds=0.28,
        silent_breath_pause_seconds=0.85,
        breath_interval_sentences=2,
    ),
)

_PRESETS_BY_ID = {preset.id: preset for preset in F5_PAUSE_PRESETS}


def normalize_f5_source_type(source_type: str | None) -> str:
    """Return a canonical F5 source type or raise with the valid choices."""
    if source_type is None:
        return "spontaneous"
    key = str(source_type).strip().lower()
    if key in F5_SOURCE_TYPES:
        return key
    available = ", ".join(F5_SOURCE_TYPES)
    raise ValueError(f"Unknown F5 source type: {source_type}. Available: {available}")


def f5_source_type_for_purpose(purpose: str) -> str | None:
    """Map an existing selector/cache purpose to the matching source type."""
    key = str(purpose or "").strip().lower()
    for source_type, mapped_purpose in F5_SOURCE_TYPE_PURPOSES.items():
        if mapped_purpose == key:
            return source_type
    return None


def list_f5_pause_presets() -> tuple[F5PausePreset, ...]:
    """Return presets in stable display order."""
    return F5_PAUSE_PRESETS


def get_f5_pause_preset(preset_id: str) -> F5PausePreset:
    """Resolve a preset id case-insensitively."""
    key = str(preset_id or "").strip().lower()
    try:
        return _PRESETS_BY_ID[key]
    except KeyError as exc:
        available = ", ".join(_PRESETS_BY_ID)
        raise ValueError(
            f"Unknown F5 pause preset: {preset_id}. Available: {available}"
        ) from exc


def apply_f5_pause_preset(
    target: SaymoConfig | F5TTSConfig,
    preset_id: str,
) -> F5PausePreset:
    """Apply a preset to a SaymoConfig or direct F5TTSConfig object."""
    preset = get_f5_pause_preset(preset_id)
    f5 = _resolve_f5_config(target)
    for key, value in preset.to_config_update().items():
        setattr(f5, key, value)
    return preset


def f5_timing_snapshot(
    target: SaymoConfig | F5TTSConfig,
    *,
    preset_id: str | None = None,
) -> dict[str, Any]:
    """Return the privacy-safe F5 timing fields used for review metadata."""
    f5 = _resolve_f5_config(target)
    silent_breath = float(getattr(f5, "silent_breath_pause_seconds", 0.6))
    return {
        "preset_id": preset_id or getattr(f5, "pause_preset", "custom") or "custom",
        "sentence_pause_seconds": float(getattr(f5, "sentence_pause_seconds", 0.38)),
        "clause_pause_seconds": float(getattr(f5, "clause_pause_seconds", 0.18)),
        "paragraph_pause_seconds": silent_breath,
        "silent_breath_pause_seconds": silent_breath,
        "breath_interval_sentences": int(
            getattr(f5, "breath_interval_sentences", 2) or 0
        ),
    }


def resolve_f5_pause_preset_for_source(
    config: SaymoConfig,
    *,
    profile: str,
    source_type: str | None = None,
) -> F5PresetResolution:
    """Resolve the F5 pause preset for a meeting profile source type."""
    resolved_source_type = normalize_f5_source_type(source_type)
    voice = _meeting_voice_config(config, profile)
    overrides = voice.get("f5_pause_presets", {})
    if not isinstance(overrides, dict):
        overrides = {}

    override_preset_id = _clean_preset_id(overrides.get(resolved_source_type))
    profile_preset_id = _clean_preset_id(voice.get("f5_pause_preset"))
    global_preset_id = _clean_preset_id(getattr(config.tts.f5tts, "pause_preset", ""))
    resolved_preset_id = (
        override_preset_id
        or profile_preset_id
        or global_preset_id
        or "approved"
    )
    preset = get_f5_pause_preset(resolved_preset_id)
    return F5PresetResolution(
        profile=profile,
        source_type=resolved_source_type,
        purpose=F5_SOURCE_TYPE_PURPOSES[resolved_source_type],
        profile_preset_id=profile_preset_id,
        override_preset_id=override_preset_id,
        resolved_preset_id=preset.id,
        preset=preset,
    )


def config_with_f5_pause_preset_for_source(
    config: SaymoConfig,
    *,
    profile: str,
    source_type: str | None = None,
) -> tuple[SaymoConfig, F5PresetResolution]:
    """Return a copied config with concrete F5 timing for a source type."""
    resolution = resolve_f5_pause_preset_for_source(
        config,
        profile=profile,
        source_type=source_type,
    )
    copied = deepcopy(config)
    apply_f5_pause_preset(copied, resolution.resolved_preset_id)
    return copied, resolution


def _resolve_f5_config(target: SaymoConfig | F5TTSConfig) -> F5TTSConfig:
    if isinstance(target, F5TTSConfig):
        return target
    return target.tts.f5tts


def _meeting_voice_config(config: SaymoConfig, profile: str) -> dict[str, Any]:
    meeting = config.get_meeting(profile) if profile else None
    if meeting and isinstance(meeting.voice, dict):
        return meeting.voice
    return {}


def _clean_preset_id(value: Any) -> str:
    return str(value or "").strip().lower()
