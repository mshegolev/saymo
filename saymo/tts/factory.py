"""TTS engine factory — single dispatch point for all TTS backends.

Usage:
    engine = get_tts_engine(config)
    audio_bytes = await engine.synthesize(text)
    await engine.synthesize_to_device(text, device_name)

All engines expose ``synthesize(text) -> bytes`` and
``synthesize_to_device(text, device_name) -> None`` (most of them). Callers
should not import concrete TTS classes directly — use this factory instead.
"""

import logging

from saymo.config import SaymoConfig

logger = logging.getLogger("saymo.tts.factory")


class UnsupportedTTSEngine(RuntimeError):
    """Raised when a configured engine name is unknown or not implemented."""


def get_tts_engine(config: SaymoConfig, *, realtime: bool = False):
    """Instantiate the TTS engine configured in ``config.tts.engine``.

    Pass ``realtime=True`` to prefer ``config.tts.realtime_engine`` when set
    — used by the auto-mode Q&A path so users can split slow, high-quality
    engines from fast real-time ones without editing source.

    Deferred imports keep optional deps (coqui-tts, piper-tts, mlx) from
    being required at import time — callers only pay for what they use.
    """
    engine = config.tts.engine
    if realtime:
        override = getattr(config.tts, "realtime_engine", "") or ""
        if override:
            engine = override

    if engine == "coqui_clone":
        from saymo.tts.coqui_clone import CoquiCloneTTS
        return CoquiCloneTTS(language=config.speech.language)

    if engine == "piper":
        from saymo.tts.piper_tts import PiperTTS
        return PiperTTS(model_path=config.tts.piper.model_path or None)

    if engine == "macos_say":
        from saymo.tts.macos_say import MacOSSay
        return MacOSSay(config.tts.macos_say)

    if engine == "qwen3_clone":
        from saymo.tts.qwen3_tts import Qwen3CloneTTS
        return Qwen3CloneTTS(
            language=config.speech.language,
            model=config.tts.qwen3.model,
            lora_adapter=config.tts.qwen3.lora_adapter or None,
        )

    if engine == "xtts_rvc_clone":
        from saymo.tts.xtts_rvc import XttsRvcCloneTTS
        return XttsRvcCloneTTS(
            language=config.speech.language,
            rvc=config.tts.rvc,
        )

    if engine == "f5tts_clone":
        from saymo.tts.f5tts import F5TTSCloneTTS
        return F5TTSCloneTTS(
            language=config.speech.language,
            f5tts=config.tts.f5tts,
        )

    raise UnsupportedTTSEngine(
        f"Unknown TTS engine: {engine!r}. "
        f"Supported: coqui_clone, xtts_rvc_clone, f5tts_clone, qwen3_clone (voice-cloning) "
        f"or piper, macos_say (fallback)."
    )


KNOWN_ENGINES = frozenset({
    "coqui_clone", "xtts_rvc_clone", "f5tts_clone", "qwen3_clone", "piper", "macos_say",
})


def is_known_engine(name: str) -> bool:
    """Return True if ``name`` is a recognized engine key (even if not implemented)."""
    return name in KNOWN_ENGINES
