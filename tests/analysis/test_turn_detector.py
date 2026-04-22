"""Tests for saymo.analysis.turn_detector.TurnDetector."""

import time

import pytest

from saymo.analysis.turn_detector import TurnDetector


# ---------------------------------------------------------------------------
# 1. check() returns True when a name variant is in the text (case-insensitive)
# ---------------------------------------------------------------------------

def test_check_triggers_on_name_variant():
    td = TurnDetector(name_variants=["Misha"], cooldown_seconds=0)
    assert td.check("Hey Misha, how are you?") is True


def test_check_triggers_case_insensitive():
    td = TurnDetector(name_variants=["Misha"], cooldown_seconds=0)
    assert td.check("MISHA please reply") is True


def test_check_no_match_returns_false():
    td = TurnDetector(name_variants=["Misha"], cooldown_seconds=0)
    assert td.check("hello everyone") is False


# ---------------------------------------------------------------------------
# 2. Multiple name_variants — each variant matches independently
# ---------------------------------------------------------------------------

def test_multiple_variants_first_matches():
    td = TurnDetector(name_variants=["Misha", "Михаил", "Mike"], cooldown_seconds=0)
    assert td.check("Михаил, ты здесь?") is True


def test_multiple_variants_second_matches():
    td = TurnDetector(name_variants=["Misha", "Михаил", "Mike"], cooldown_seconds=0)
    assert td.check("Mike, you there?") is True


def test_multiple_variants_third_matches():
    td = TurnDetector(name_variants=["Misha", "Михаил", "Mike"], cooldown_seconds=0)
    assert td.check("Can Misha respond?") is True


# ---------------------------------------------------------------------------
# 3. Cooldown: after one True return, next calls within cooldown return False
# ---------------------------------------------------------------------------

def test_cooldown_suppresses_subsequent_triggers():
    td = TurnDetector(name_variants=["Misha"], cooldown_seconds=10.0)
    assert td.check("Hi Misha") is True
    # Still within cooldown
    assert td.check("Misha again") is False


def test_cooldown_expires_and_triggers_again(monkeypatch):
    td = TurnDetector(name_variants=["Misha"], cooldown_seconds=0.1)
    assert td.check("Hi Misha") is True

    # Advance time past the cooldown
    original_time = time.time
    monkeypatch.setattr("saymo.analysis.turn_detector.time.time",
                        lambda: original_time() + 1.0)

    assert td.check("Misha again") is True


# ---------------------------------------------------------------------------
# 4. recent_transcript returns last 5 chunks joined with spaces in order
# ---------------------------------------------------------------------------

def test_recent_transcript_returns_last_five():
    td = TurnDetector(name_variants=["X"], cooldown_seconds=0)
    for i in range(7):
        td.check(f"chunk{i}")
    # last 5 are chunk2..chunk6
    assert td.recent_transcript == "chunk2 chunk3 chunk4 chunk5 chunk6"


def test_recent_transcript_fewer_than_five_chunks():
    td = TurnDetector(name_variants=["X"], cooldown_seconds=0)
    td.check("alpha")
    td.check("beta")
    assert td.recent_transcript == "alpha beta"


# ---------------------------------------------------------------------------
# 5. Sliding window: name split between two chunks still triggers
# ---------------------------------------------------------------------------

def test_sliding_window_name_split_across_chunks():
    # Use a multi-word name ("John Smith") whose halves land in separate chunks.
    # "John" ends the first chunk; "Smith" starts the second.
    # Neither chunk matches alone, but the joined string "…John Smith…" does.
    td = TurnDetector(name_variants=["John Smith"], cooldown_seconds=0)
    # First chunk: ends with first word of the name — no full match alone
    assert td.check("please ask John") is False
    # Second chunk: starts with second word — no full match alone either,
    # but prev_chunk + " " + text = "please ask John Smith to reply"
    assert td.check("Smith to reply") is True


# ---------------------------------------------------------------------------
# 6. Fuzzy expansions: misspelling of name triggers detection
# ---------------------------------------------------------------------------

def test_fuzzy_expansion_triggers():
    td = TurnDetector(
        name_variants=["Миша"],
        cooldown_seconds=0,
        fuzzy_expansions={"миша": ["мища", "миса"]},
    )
    assert td.check("мища, ответь") is True


def test_fuzzy_expansion_second_variant_triggers():
    td = TurnDetector(
        name_variants=["Миша"],
        cooldown_seconds=0,
        fuzzy_expansions={"миша": ["мища", "миса"]},
    )
    assert td.check("миса, ты слышишь?") is True


def test_fuzzy_expansion_unrelated_word_no_trigger():
    td = TurnDetector(
        name_variants=["Миша"],
        cooldown_seconds=0,
        fuzzy_expansions={"миша": ["мища", "миса"]},
    )
    assert td.check("мишура на ёлке") is False


# ---------------------------------------------------------------------------
# 7. Empty/whitespace text never triggers
# ---------------------------------------------------------------------------

def test_empty_string_returns_false():
    td = TurnDetector(name_variants=["Misha"], cooldown_seconds=0)
    assert td.check("") is False


def test_whitespace_only_returns_false():
    td = TurnDetector(name_variants=["Misha"], cooldown_seconds=0)
    assert td.check("   \t\n  ") is False


# ---------------------------------------------------------------------------
# 8. reset_cooldown() clears the cooldown so next match triggers
# ---------------------------------------------------------------------------

def test_reset_cooldown_allows_immediate_retrigger():
    td = TurnDetector(name_variants=["Misha"], cooldown_seconds=60.0)
    assert td.check("Hi Misha") is True
    # Cooldown active — next call would be suppressed
    assert td.check("Misha again") is False
    # After reset, should trigger again
    td.reset_cooldown()
    assert td.check("Misha once more") is True


# ---------------------------------------------------------------------------
# 9. Buffer caps at 20 chunks (oldest dropped)
# ---------------------------------------------------------------------------

def test_buffer_caps_at_20():
    td = TurnDetector(name_variants=["X"], cooldown_seconds=0)
    for i in range(25):
        td.check(f"chunk{i}")
    # Buffer should hold at most 20 entries
    assert len(td._transcript_buffer) == 20
    # Oldest (chunk0..chunk4) must be gone; newest (chunk5..chunk24) remain
    assert td._transcript_buffer[0] == "chunk5"
    assert td._transcript_buffer[-1] == "chunk24"
