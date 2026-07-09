"""Tests for fail-closed automatic realtime response policy."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from saymo.analysis import realtime_policy
from saymo.analysis.cache_metadata import VoiceCacheMetadata, write_voice_cache_metadata
from saymo.analysis.response_cache import ResponseCache, ResponseEntry
from saymo.analysis.realtime_gate import RealtimePlaybackBlock
from saymo.analysis.realtime_policy import (
    RealtimeResponseDecision,
    build_realtime_response_cache,
    resolve_realtime_response_decision,
)
from saymo.config import SaymoConfig


def _run(coro):
    return asyncio.run(coro)


def _metadata(fingerprint: str = "current") -> VoiceCacheMetadata:
    return VoiceCacheMetadata(
        purpose="response_cache",
        selected_engine="f5tts_clone",
        attempted_engines=("f5tts_clone",),
        fingerprint=fingerprint,
        is_voice_clone=True,
        profile="personal",
        profile_approved=True,
    )


def _tiny_library() -> dict[str, ResponseEntry]:
    return {
        "status_ready": ResponseEntry(
            key="status_ready",
            triggers=["какой статус"],
            variants=["Статус готов."],
        )
    }


def test_build_realtime_response_cache_uses_response_cache_voice_metadata(
    monkeypatch,
    tmp_path,
):
    from saymo.analysis import realtime_policy

    config = SaymoConfig()
    config.responses.cache_dir = str(tmp_path)
    config.responses.confidence_threshold = 0.42
    config.responses.library = {
        "custom": {
            "triggers": ["custom trigger"],
            "variants": ["Custom response."],
        }
    }
    expected = _metadata()

    monkeypatch.setattr(
        realtime_policy,
        "build_voice_cache_metadata",
        lambda cfg, *, purpose, profile, source_type: (
            expected
            if (
                purpose == "response_cache"
                and profile == "standup"
                and source_type == "response_cache"
            )
            else None
        ),
    )

    cache = build_realtime_response_cache(config, profile="standup")

    assert isinstance(cache, ResponseCache)
    assert cache.cache_dir == tmp_path
    assert cache.confidence_threshold == 0.42
    assert cache.voice_metadata is expected
    assert "custom" in cache.library


def test_cache_hit_returns_speak_decision():
    config = SaymoConfig()
    audio_path = Path("/tmp/status_ready.wav")
    cached = SimpleNamespace(
        key="status_ready",
        audio_path=audio_path,
        confidence=0.91,
        text="not serialized",
    )
    cache = MagicMock()
    cache.lookup.return_value = cached

    decision = _run(
        resolve_realtime_response_decision(
            config,
            transcript_window="какой статус?",
            response_cache=cache,
        )
    )

    assert decision.outcome == "speak"
    assert decision.label == "response-cache-hit"
    assert decision.source == "response_cache"
    assert decision.audio_path == audio_path
    assert decision.intent_key == "status_ready"
    assert decision.confidence == 0.91


def test_intent_classifier_cache_hit_uses_cached_variant(monkeypatch):
    config = SaymoConfig()
    config.responses.intent_classifier = True
    cached = SimpleNamespace(
        key="eta_today",
        audio_path=Path("/tmp/eta_today.wav"),
        confidence=1.0,
        text="not serialized",
    )
    cache = MagicMock()
    cache.library_keys.return_value = ["eta_today", "status_ready"]
    cache.get_variant_by_key.return_value = cached
    cache.lookup.return_value = None
    classify = AsyncMock(return_value="eta_today")
    monkeypatch.setattr("saymo.speech.ollama_composer.classify_intent", classify)

    decision = _run(
        resolve_realtime_response_decision(
            config,
            transcript_window="когда будет готово?",
            response_cache=cache,
        )
    )

    assert decision.outcome == "speak"
    assert decision.label == "response-cache-hit"
    assert decision.source == "response_cache"
    assert decision.audio_path == cached.audio_path
    assert decision.intent_key == "eta_today"
    classify.assert_awaited_once()
    cache.get_variant_by_key.assert_called_once_with("eta_today")
    cache.lookup.assert_not_called()


def test_intent_classifier_miss_falls_through_to_keyword_cache(monkeypatch):
    config = SaymoConfig()
    config.responses.intent_classifier = True
    cached = SimpleNamespace(
        key="status_ready",
        audio_path=Path("/tmp/status_ready.wav"),
        confidence=0.73,
        text="not serialized",
    )
    cache = MagicMock()
    cache.library_keys.return_value = ["eta_today", "status_ready"]
    cache.get_variant_by_key.return_value = None
    cache.lookup.return_value = cached
    classify = AsyncMock(return_value=None)
    monkeypatch.setattr("saymo.speech.ollama_composer.classify_intent", classify)

    decision = _run(
        resolve_realtime_response_decision(
            config,
            transcript_window="какой статус?",
            response_cache=cache,
        )
    )

    assert decision.outcome == "speak"
    assert decision.label == "response-cache-hit"
    assert decision.intent_key == "status_ready"
    classify.assert_awaited_once()
    cache.lookup.assert_called_once()


def test_cache_miss_blocks_without_standup_fallback():
    config = SaymoConfig()
    cache = MagicMock()
    cache.voice_metadata = None
    cache.lookup.return_value = None
    prepared_standup = Path("/tmp/prepared-standup.wav")

    decision = _run(
        resolve_realtime_response_decision(
            config,
            transcript_window="какой статус?",
            response_cache=cache,
        )
    )

    assert decision.outcome == "block"
    assert decision.label == "cache-miss-blocked"
    assert decision.audio_path is None
    assert decision.audio_path != prepared_standup
    assert decision.cleanup_path is False


def test_manual_standup_decision_speaks_existing_prepared_path(tmp_path):
    prepared_standup = tmp_path / "standup.wav"
    prepared_standup.write_bytes(b"RIFFfake")

    decision = realtime_policy.resolve_manual_standup_decision(
        prepared_standup_path=prepared_standup,
    )

    assert decision.outcome == "speak"
    assert decision.label == "manual-standup-requested"
    assert decision.source == "manual_standup"
    assert decision.reason == "manual prepared playback requested"
    assert decision.audio_path == prepared_standup
    assert decision.automatic is False
    assert decision.cleanup_path is False


def test_manual_standup_decision_blocks_missing_prepared_path(tmp_path):
    missing_standup = tmp_path / "missing.wav"

    decision = realtime_policy.resolve_manual_standup_decision(
        prepared_standup_path=missing_standup,
    )

    assert decision.outcome == "block"
    assert decision.label == "manual-standup-blocked"
    assert decision.source == "manual_standup"
    assert decision.reason == "prepared-standup-missing"
    assert decision.audio_path is None
    assert decision.automatic is False


def test_manual_standup_decision_blocks_supplied_handbrake_reason(tmp_path):
    prepared_standup = tmp_path / "standup.wav"
    prepared_standup.write_bytes(b"RIFFfake")
    handbrake_block = RealtimePlaybackBlock(
        label="handbrake-blocked",
        reason="manual-takeover",
        detail="raw transcript should not leak",
    )

    decision = realtime_policy.resolve_manual_standup_decision(
        prepared_standup_path=prepared_standup,
        handbrake_block=handbrake_block,
    )

    assert decision.outcome == "block"
    assert decision.label == "manual-standup-blocked"
    assert decision.source == "manual_standup"
    assert decision.reason == "manual-takeover"
    assert decision.audio_path is None
    assert decision.automatic is False
    assert "raw transcript" not in repr(decision)


def test_responses_disabled_or_missing_cache_blocks_before_lookup():
    config = SaymoConfig()
    cache = MagicMock()
    config.responses.enabled = False

    disabled = _run(
        resolve_realtime_response_decision(
            config,
            transcript_window="какой статус?",
            response_cache=cache,
        )
    )
    missing = _run(
        resolve_realtime_response_decision(
            config,
            transcript_window="какой статус?",
            response_cache=None,
        )
    )

    assert build_realtime_response_cache(config) is None
    assert disabled.outcome == "block"
    assert disabled.label == "cache-disabled-blocked"
    assert missing.outcome == "block"
    assert missing.label == "cache-disabled-blocked"
    cache.lookup.assert_not_called()


def test_stale_voice_metadata_blocks_selected_cached_wav(tmp_path):
    expected = _metadata("current")
    stale = _metadata("old")
    cache = ResponseCache(
        library=_tiny_library(),
        cache_dir=tmp_path,
        confidence_threshold=0.1,
        voice_metadata=expected,
    )
    audio_path = cache.variant_path("status_ready", 0, "Статус готов.")
    audio_path.write_bytes(b"RIFFfake")
    write_voice_cache_metadata(audio_path, stale)

    decision = _run(
        resolve_realtime_response_decision(
            SaymoConfig(),
            transcript_window="какой статус?",
            response_cache=cache,
        )
    )

    assert decision.outcome == "block"
    assert decision.label == "voice-metadata-blocked"
    assert decision.audio_path is None
    assert decision.intent_key == "status_ready"


def test_live_fallback_setting_blocks_without_llm_or_tts(monkeypatch):
    config = SaymoConfig()
    config.responses.live_fallback = True
    cache = MagicMock()
    cache.voice_metadata = None
    cache.lookup.return_value = None
    forbidden_answer = AsyncMock(side_effect=AssertionError("LLM must not run"))
    monkeypatch.setattr("saymo.speech.ollama_composer.answer_question", forbidden_answer)
    monkeypatch.setattr(
        "saymo.tts.selector.get_selected_tts_engine",
        MagicMock(side_effect=AssertionError("TTS selector must not run")),
    )

    decision = _run(
        resolve_realtime_response_decision(
            config,
            transcript_window="какой статус?",
            response_cache=cache,
        )
    )

    assert decision.outcome == "block"
    assert decision.label == "fallback-blocked"
    assert decision.audio_path is None
    forbidden_answer.assert_not_called()


def test_deterministic_skip_prevents_cache_classifier_llm_and_tts(monkeypatch):
    config = SaymoConfig()
    config.responses.intent_classifier = True
    config.responses.live_fallback = True
    cache = MagicMock()
    cache.lookup.side_effect = AssertionError("cache lookup must not run")
    cache.get_variant_by_key.side_effect = AssertionError("cache key lookup must not run")
    cache.library_keys.side_effect = AssertionError("cache keys must not be read")
    classify = AsyncMock(side_effect=AssertionError("classifier must not run"))
    answer = AsyncMock(side_effect=AssertionError("LLM must not run"))
    monkeypatch.setattr("saymo.speech.ollama_composer.classify_intent", classify)
    monkeypatch.setattr("saymo.speech.ollama_composer.answer_question", answer)
    monkeypatch.setattr(
        "saymo.tts.selector.get_selected_tts_engine",
        MagicMock(side_effect=AssertionError("TTS selector must not run")),
    )

    decision = _run(
        resolve_realtime_response_decision(
            config,
            transcript_window="какой статус?",
            response_cache=cache,
            deterministic_should_answer=False,
        )
    )

    assert decision.outcome == "skip"
    assert decision.label == "deterministic-skip"
    assert decision.audio_path is None
    classify.assert_not_called()
    answer.assert_not_called()


def test_realtime_response_decision_to_event_maps_outcomes_and_sanitizes():
    cases = [
        (
            RealtimeResponseDecision(
                outcome="speak",
                label="response-cache-hit",
                source="response_cache",
                reason="prepared cached response selected token=secret-value",
                audio_path=Path("/tmp/status-ready.wav"),
                intent_key="status_ready",
                confidence=0.91,
            ),
            "spoke",
        ),
        (
            RealtimeResponseDecision(
                outcome="block",
                label="cache-miss-blocked",
                source="response_cache",
                reason="raw transcript says PRIVATE_SENTINEL",
            ),
            "blocked",
        ),
        (
            RealtimeResponseDecision(
                outcome="skip",
                label="deterministic-skip",
                source="deterministic",
                reason="deterministic addressing skipped",
            ),
            "skipped",
        ),
    ]

    for decision, expected_outcome in cases:
        event = decision.to_event(profile="standup", provider="glip")
        payload = event.to_dict()
        serialized = str(payload)

        assert payload["profile"] == "standup"
        assert payload["provider"] == "glip"
        assert payload["outcome"] == expected_outcome
        assert payload["label"] == decision.label
        assert payload["source"] == decision.source
        assert "transcript_window" not in payload
        assert "secret-value" not in serialized
        assert "PRIVATE_SENTINEL" not in serialized
