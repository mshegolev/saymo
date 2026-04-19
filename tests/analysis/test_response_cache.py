"""Tests for the Tier-A response cache (CPU-only real-time Q&A)."""

import asyncio
from pathlib import Path

import pytest

from saymo.analysis.response_cache import (
    DEFAULT_RESPONSE_LIBRARY,
    CachedResponse,
    ResponseCache,
    ResponseEntry,
    build_library,
)


@pytest.fixture
def tmp_cache_dir(tmp_path) -> Path:
    d = tmp_path / "responses"
    d.mkdir()
    return d


@pytest.fixture
def tiny_library() -> dict[str, ResponseEntry]:
    """A minimal library so tests are fast and deterministic."""
    return {
        "blockers_none": ResponseEntry(
            key="blockers_none",
            triggers=["есть блокеры", "блокеры"],
            variants=["Блокеров нет.", "Сейчас всё идёт без блокеров."],
        ),
        "eta_today": ResponseEntry(
            key="eta_today",
            triggers=["когда будет", "сегодня успеешь"],
            variants=["Сегодня будет готово."],
        ),
    }


def test_default_library_has_entries():
    """Sanity check that defaults are loaded and reasonably sized."""
    assert len(DEFAULT_RESPONSE_LIBRARY) >= 20
    for key, entry in DEFAULT_RESPONSE_LIBRARY.items():
        assert entry.triggers, f"{key} has no triggers"
        assert entry.variants, f"{key} has no variants"


def test_build_library_applies_overrides(tiny_library):
    """User overrides replace the default entry with the same key."""
    overrides = {
        "blockers_none": {
            "triggers": ["никаких блокеров"],
            "variants": ["Нет, всё спокойно."],
            "description": "Custom wording",
        },
    }
    merged = build_library(overrides)
    assert merged["blockers_none"].triggers == ["никаких блокеров"]
    assert merged["blockers_none"].variants == ["Нет, всё спокойно."]
    # Other defaults remain.
    assert "status_generic" in merged


def test_build_library_skips_malformed_overrides():
    """A broken override does not crash startup; it is logged and skipped."""
    overrides = {
        "not_a_mapping": "oops",
        "empty_triggers": {"triggers": [], "variants": ["a"]},
        "empty_variants": {"triggers": ["t"], "variants": []},
    }
    merged = build_library(overrides)
    assert "not_a_mapping" not in merged
    assert "empty_triggers" not in merged
    assert "empty_variants" not in merged


def test_lookup_miss_returns_none(tiny_library, tmp_cache_dir):
    cache = ResponseCache(library=tiny_library, cache_dir=tmp_cache_dir)
    assert cache.lookup("погода сегодня хорошая") is None


def test_lookup_empty_window_returns_none(tmp_cache_dir):
    cache = ResponseCache(cache_dir=tmp_cache_dir)
    assert cache.lookup("") is None
    assert cache.lookup("   ") is None


def test_lookup_without_cached_files_returns_none(tiny_library, tmp_cache_dir):
    """Lookup matches the intent but refuses to return without cached audio."""
    cache = ResponseCache(library=tiny_library, cache_dir=tmp_cache_dir)
    # Matches the 'blockers_none' trigger tokens.
    assert cache.lookup("а есть блокеры какие-то?") is None


def test_lookup_hit_returns_cached_response(tiny_library, tmp_cache_dir):
    """After build() writes WAVs, lookup returns a CachedResponse."""
    cache = ResponseCache(library=tiny_library, cache_dir=tmp_cache_dir)

    async def fake_synth(text: str) -> bytes:
        return b"RIFF" + text.encode("utf-8")

    written = asyncio.run(cache.build(fake_synth))
    # 2 variants for blockers_none + 1 for eta_today = 3 files.
    assert len(written) == 3

    result = cache.lookup("а есть блокеры какие-то?")
    assert isinstance(result, CachedResponse)
    assert result.key == "blockers_none"
    assert result.audio_path.exists()
    assert result.confidence >= 0.6


def test_lookup_respects_confidence_threshold(tiny_library, tmp_cache_dir):
    """A weak partial match below the threshold returns None."""
    cache = ResponseCache(
        library=tiny_library,
        cache_dir=tmp_cache_dir,
        confidence_threshold=0.99,
    )

    async def fake_synth(text: str) -> bytes:
        return b"wav"

    asyncio.run(cache.build(fake_synth))
    # "есть" alone matches only part of the trigger "есть блокеры".
    assert cache.lookup("есть что-то нового?") is None


def test_build_is_idempotent(tiny_library, tmp_cache_dir):
    """Running build twice should not re-synthesise cached variants."""
    cache = ResponseCache(library=tiny_library, cache_dir=tmp_cache_dir)

    calls: list[str] = []

    async def counting_synth(text: str) -> bytes:
        calls.append(text)
        return b"wav"

    first = asyncio.run(cache.build(counting_synth))
    second = asyncio.run(cache.build(counting_synth))
    assert len(first) == 3
    assert len(second) == 0, "second run should skip all (files exist)"
    assert len(calls) == 3


def test_build_force_regenerates(tiny_library, tmp_cache_dir):
    """`force=True` ignores existing files and calls synth for every variant."""
    cache = ResponseCache(library=tiny_library, cache_dir=tmp_cache_dir)

    calls: list[str] = []

    async def counting_synth(text: str) -> bytes:
        calls.append(text)
        return b"wav"

    asyncio.run(cache.build(counting_synth))
    asyncio.run(cache.build(counting_synth, force=True))
    assert len(calls) == 6  # 3 variants × 2 runs


def test_build_survives_synth_failure(tiny_library, tmp_cache_dir):
    """One failing variant must not stop the rest from being cached."""
    cache = ResponseCache(library=tiny_library, cache_dir=tmp_cache_dir)

    async def flaky_synth(text: str) -> bytes:
        if text.startswith("Сегодня"):
            raise RuntimeError("engine went home")
        return b"wav"

    written = asyncio.run(cache.build(flaky_synth))
    # 2 blockers_none variants succeed; 1 eta_today variant fails.
    assert len(written) == 2


def test_variant_path_stable_and_unique(tiny_library, tmp_cache_dir):
    """Same text → same filename; different text → different filename."""
    cache = ResponseCache(library=tiny_library, cache_dir=tmp_cache_dir)
    a = cache._variant_path("blockers_none", 0, "Блокеров нет.")
    b = cache._variant_path("blockers_none", 0, "Блокеров нет.")
    c = cache._variant_path("blockers_none", 0, "Other text.")
    assert a == b
    assert a != c
