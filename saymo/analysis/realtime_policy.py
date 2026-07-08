"""Fail-closed automatic response policy for realtime mode."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from saymo.analysis.cache_metadata import build_voice_cache_metadata
from saymo.analysis.realtime_events import RealtimeDecisionEvent
from saymo.analysis.realtime_gate import RealtimePlaybackBlock
from saymo.analysis.response_cache import (
    CachedResponse,
    ResponseCache,
    build_library,
    response_cache_coverage,
)


@dataclass(frozen=True)
class RealtimeResponseDecision:
    outcome: Literal["speak", "block", "skip"]
    label: str
    source: str
    reason: str
    audio_path: Path | None = None
    intent_key: str = ""
    confidence: float | None = None
    automatic: bool = True
    cleanup_path: bool = False

    def to_event(self, *, profile: str, provider: str) -> RealtimeDecisionEvent:
        """Convert a response decision to a sanitized local event payload."""
        outcome = {
            "speak": "spoke",
            "block": "blocked",
            "skip": "skipped",
        }[self.outcome]
        return RealtimeDecisionEvent(
            profile=profile,
            provider=provider,
            outcome=outcome,
            label=self.label,
            source=self.source,
            automatic=self.automatic,
            intent_key=self.intent_key,
            confidence=self.confidence,
            audio_path=str(self.audio_path or ""),
            detail=self.reason,
        )


def build_realtime_response_cache(config) -> ResponseCache | None:
    """Build the metadata-aware response cache used by automatic realtime answers."""
    if not getattr(config.responses, "enabled", True):
        return None

    cache_dir = Path(config.responses.cache_dir) if config.responses.cache_dir else None
    return ResponseCache(
        library=build_library(config.responses.library),
        cache_dir=cache_dir,
        confidence_threshold=config.responses.confidence_threshold,
        voice_metadata=build_voice_cache_metadata(config, purpose="response_cache"),
    )


def resolve_manual_standup_decision(
    *,
    prepared_standup_path: Path,
    handbrake_block: RealtimePlaybackBlock | None = None,
) -> RealtimeResponseDecision:
    """Resolve an explicit operator-requested prepared standup playback."""
    if handbrake_block is not None:
        return RealtimeResponseDecision(
            outcome="block",
            label="manual-standup-blocked",
            source="manual_standup",
            reason=handbrake_block.reason,
            automatic=False,
        )

    path = Path(prepared_standup_path)
    if not path.exists():
        return RealtimeResponseDecision(
            outcome="block",
            label="manual-standup-blocked",
            source="manual_standup",
            reason="prepared-standup-missing",
            automatic=False,
        )

    return RealtimeResponseDecision(
        outcome="speak",
        label="manual-standup-requested",
        source="manual_standup",
        reason="manual prepared playback requested",
        audio_path=path,
        automatic=False,
    )


async def resolve_realtime_response_decision(
    config,
    *,
    transcript_window: str,
    response_cache: ResponseCache | None,
    deterministic_should_answer: bool = True,
) -> RealtimeResponseDecision:
    """Resolve automatic realtime output using prepared response-cache audio only."""
    if not deterministic_should_answer:
        return RealtimeResponseDecision(
            outcome="skip",
            label="deterministic-skip",
            source="deterministic",
            reason="deterministic addressing skipped",
        )

    if not getattr(config.responses, "enabled", True) or response_cache is None:
        return RealtimeResponseDecision(
            outcome="block",
            label="cache-disabled-blocked",
            source="response_cache",
            reason="response cache unavailable",
        )

    cached = await _classifier_cache_hit(config, transcript_window, response_cache)
    if cached is not None:
        return _cache_hit_decision(cached)

    cached = response_cache.lookup(transcript_window)
    if cached is not None:
        return _cache_hit_decision(cached)

    stale_key = _stale_cache_key(response_cache)
    if stale_key:
        return RealtimeResponseDecision(
            outcome="block",
            label="voice-metadata-blocked",
            source="response_cache",
            reason="cached response voice metadata is stale",
            intent_key=stale_key,
        )

    if getattr(config.responses, "live_fallback", False):
        return RealtimeResponseDecision(
            outcome="block",
            label="fallback-blocked",
            source="response_cache",
            reason="live fallback is disabled for automatic realtime answers",
        )

    return RealtimeResponseDecision(
        outcome="block",
        label="cache-miss-blocked",
        source="response_cache",
        reason="no prepared response-cache hit",
    )


async def _classifier_cache_hit(
    config,
    transcript_window: str,
    response_cache: ResponseCache,
) -> CachedResponse | None:
    if not getattr(config.responses, "intent_classifier", False):
        return None

    try:
        from saymo.speech.ollama_composer import classify_intent

        intent_key = await classify_intent(
            transcript_window,
            available_keys=response_cache.library_keys(),
            model=config.ollama.model,
            ollama_url=config.ollama.url,
            config=config,
        )
    except Exception:
        return None

    if not intent_key:
        return None
    return response_cache.get_variant_by_key(intent_key)


def _cache_hit_decision(cached: CachedResponse) -> RealtimeResponseDecision:
    return RealtimeResponseDecision(
        outcome="speak",
        label="response-cache-hit",
        source="response_cache",
        reason="prepared cached response selected",
        audio_path=Path(cached.audio_path),
        intent_key=cached.key,
        confidence=cached.confidence,
    )


def _stale_cache_key(response_cache: ResponseCache) -> str:
    if getattr(response_cache, "voice_metadata", None) is None:
        return ""
    try:
        coverage = response_cache_coverage(response_cache, max_examples=1)
    except Exception:
        return ""
    if not coverage.stale:
        return ""
    variant = coverage.stale[0].split(":", 1)[0]
    return variant.split("[", 1)[0]
