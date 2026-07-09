"""Call-ready TTS selector and fallback policy."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from saymo.analysis.voice_profile import (
    VoiceProfileManifest,
    check_voice_profile,
    load_voice_profile_manifest,
)
from saymo.config import SaymoConfig, VoiceSelectorPurposeConfig
from saymo.tts.factory import is_known_engine

CLONED_ENGINES = frozenset({
    "coqui_clone",
    "xtts_rvc_clone",
    "f5tts_clone",
    "qwen3_clone",
})
NON_CLONED_ENGINES = frozenset({"piper", "macos_say"})
REALTIME_PURPOSES = frozenset({"realtime", "live_call"})


@dataclass(frozen=True)
class VoiceSelectorDecision:
    purpose: str
    requested_engine: str
    selected_engine: str
    attempted_engines: tuple[str, ...]
    fallback_engine: str = ""
    allowed: bool = True
    blocked_reason: str = ""
    is_voice_clone: bool = False
    non_cloned_allowed: bool = False
    profile: str = ""
    profile_approved: bool = False
    approved_benchmark_run: str = ""
    reference_audio_sha256: str = ""
    reference_text_sha256: str = ""
    reference_fingerprint: str = ""

    def to_metadata(self) -> dict[str, Any]:
        return asdict(self)


class VoiceSelectorBlocked(RuntimeError):
    """Raised when selector policy refuses synthesis for a purpose."""

    def __init__(self, decision: VoiceSelectorDecision):
        self.decision = decision
        super().__init__(decision.blocked_reason or "voice selector blocked")


@dataclass(frozen=True)
class SelectedVoiceEngine:
    engine: Any
    decision: VoiceSelectorDecision

    async def synthesize(self, text: str) -> bytes:
        return await self.engine.synthesize(text)


def resolve_voice_selector(
    config: SaymoConfig,
    *,
    purpose: str,
) -> VoiceSelectorDecision:
    """Resolve the engine and readiness state for one synthesis purpose."""
    purpose_cfg = _purpose_config(config, purpose)
    requested = _requested_engine(config, purpose, purpose_cfg)
    candidates = _candidate_engines(requested, purpose_cfg.fallbacks)
    selected = next((engine for engine in candidates if is_known_engine(engine)), requested)
    fallback_engine = selected if selected != requested else ""
    is_voice_clone = selected in CLONED_ENGINES
    non_cloned_allowed = bool(purpose_cfg.allow_non_cloned)

    allowed = True
    blocked_reason = ""

    if not is_known_engine(selected):
        allowed = False
        blocked_reason = "engine_unknown"
    elif selected in NON_CLONED_ENGINES and _requires_cloned_engine(purpose, purpose_cfg):
        allowed = False
        blocked_reason = "engine_not_voice_clone"

    manifest: VoiceProfileManifest | None = None
    profile_name = _profile_name(config, purpose_cfg)
    if not blocked_reason and _requires_approved_profile(purpose, purpose_cfg):
        if not profile_name:
            allowed = False
            blocked_reason = "voice_profile_missing"
        else:
            try:
                manifest = load_voice_profile_manifest(
                    profile_name,
                    profiles_dir=config.voice_selector.profiles_dir or None,
                )
            except FileNotFoundError:
                allowed = False
                blocked_reason = "voice_profile_missing"
            else:
                profile_check = check_voice_profile(manifest)
                if profile_check.blockers:
                    allowed = False
                    blocked_reason = "voice_profile_blocked"
                elif not manifest.approved_for_calls:
                    allowed = False
                    blocked_reason = "voice_profile_unapproved"

    if manifest is None and profile_name:
        try:
            manifest = load_voice_profile_manifest(
                profile_name,
                profiles_dir=config.voice_selector.profiles_dir or None,
            )
        except FileNotFoundError:
            manifest = None

    return VoiceSelectorDecision(
        purpose=purpose,
        requested_engine=requested,
        selected_engine=selected,
        attempted_engines=tuple(candidates),
        fallback_engine=fallback_engine,
        allowed=allowed,
        blocked_reason=blocked_reason,
        is_voice_clone=is_voice_clone,
        non_cloned_allowed=non_cloned_allowed,
        profile=manifest.profile if manifest else profile_name,
        profile_approved=bool(manifest and manifest.approved_for_calls),
        approved_benchmark_run=manifest.approved_benchmark_run if manifest else "",
        reference_audio_sha256=manifest.reference_audio.sha256 if manifest else "",
        reference_text_sha256=manifest.reference_text.sha256 if manifest else "",
        reference_fingerprint=_reference_fingerprint(manifest),
    )


def get_selected_tts_engine(
    config: SaymoConfig,
    *,
    purpose: str,
) -> SelectedVoiceEngine:
    """Return a factory-instantiated engine plus selector decision."""
    decision = resolve_voice_selector(config, purpose=purpose)
    if not decision.allowed:
        raise VoiceSelectorBlocked(decision)
    from saymo.tts.factory import get_tts_engine_by_name

    return SelectedVoiceEngine(
        engine=get_tts_engine_by_name(config, decision.selected_engine),
        decision=decision,
    )


def selector_fingerprint_payload(config: SaymoConfig, *, purpose: str) -> dict[str, Any]:
    """Return privacy-safe data that should invalidate voice audio caches."""
    decision = resolve_voice_selector(config, purpose=purpose)
    engine = decision.selected_engine
    return {
        "selector": decision.to_metadata(),
        "tts": {
            "engine": config.tts.engine,
            "realtime_engine": config.tts.realtime_engine,
            "selected_engine": engine,
        },
        "engine_config": _engine_config_payload(config, engine),
    }


def _purpose_config(config: SaymoConfig, purpose: str) -> VoiceSelectorPurposeConfig:
    selector = getattr(config, "voice_selector", None)
    if selector is None:
        return VoiceSelectorPurposeConfig()
    return getattr(selector, purpose, VoiceSelectorPurposeConfig())


def _requested_engine(
    config: SaymoConfig,
    purpose: str,
    purpose_cfg: VoiceSelectorPurposeConfig,
) -> str:
    if purpose_cfg.engine:
        return purpose_cfg.engine
    if purpose in REALTIME_PURPOSES and config.tts.realtime_engine:
        return config.tts.realtime_engine
    return config.tts.engine


def _candidate_engines(requested: str, fallbacks: list[str]) -> list[str]:
    candidates: list[str] = []
    for engine in [requested, *fallbacks]:
        if engine and engine not in candidates:
            candidates.append(engine)
    return candidates or [""]


def _profile_name(config: SaymoConfig, purpose_cfg: VoiceSelectorPurposeConfig) -> str:
    return purpose_cfg.voice_profile or config.voice_selector.default_profile


def _requires_approved_profile(
    purpose: str,
    purpose_cfg: VoiceSelectorPurposeConfig,
) -> bool:
    return bool(purpose_cfg.require_approved_profile or purpose == "live_call")


def _requires_cloned_engine(
    purpose: str,
    purpose_cfg: VoiceSelectorPurposeConfig,
) -> bool:
    return purpose == "live_call" and not purpose_cfg.allow_non_cloned


def _reference_fingerprint(manifest: VoiceProfileManifest | None) -> str:
    if manifest is None:
        return ""
    parts = {
        "audio": manifest.reference_audio.sha256,
        "text": manifest.reference_text.sha256,
        "text_chars": manifest.reference_text.chars,
    }
    return json.dumps(parts, sort_keys=True, ensure_ascii=False)


def _engine_config_payload(config: SaymoConfig, engine: str) -> dict[str, Any]:
    if engine == "f5tts_clone":
        f5 = config.tts.f5tts
        return {
            "model_name": f5.model_name,
            "ckpt_file": f5.ckpt_file,
            "vocab_file": f5.vocab_file,
            "nfe_step": f5.nfe_step,
            "speed": f5.speed,
            "device": f5.device,
            "natural_pacing": f5.natural_pacing,
            "sentence_pause_seconds": f5.sentence_pause_seconds,
            "clause_pause_seconds": f5.clause_pause_seconds,
            "silent_breath_pause_seconds": f5.silent_breath_pause_seconds,
            "breath_interval_sentences": f5.breath_interval_sentences,
        }
    if engine == "qwen3_clone":
        qwen = config.tts.qwen3
        return {
            "model": qwen.model,
            "lora_adapter": qwen.lora_adapter,
        }
    if engine == "xtts_rvc_clone":
        rvc = config.tts.rvc
        return {
            "model_path": rvc.model_path,
            "index_path": rvc.index_path,
            "pitch_shift": rvc.pitch_shift,
            "index_rate": rvc.index_rate,
            "f0_method": rvc.f0_method,
        }
    if engine == "piper":
        return {"model_path": config.tts.piper.model_path}
    if engine == "macos_say":
        return {"voice": config.tts.macos_say.voice}
    if engine == "coqui_clone":
        return {"language": config.speech.language}
    return {}
