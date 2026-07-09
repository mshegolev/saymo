"""Tests for the built-in F5 preview corpus."""

from __future__ import annotations

import pytest

from saymo.tts.f5_corpus import (
    get_f5_preview_corpus_entry,
    list_f5_preview_categories,
    list_f5_preview_corpus,
    resolve_f5_preview_corpus_selection,
)


REQUIRED_CATEGORIES = (
    "acknowledgement",
    "standup",
    "multi_sentence",
    "clause_heavy",
    "handoff",
)


def test_default_corpus_covers_required_categories():
    assert list_f5_preview_categories() == REQUIRED_CATEGORIES

    corpus = list_f5_preview_corpus()
    for category in REQUIRED_CATEGORIES:
        entries = [entry for entry in corpus if entry.category == category]
        assert len(entries) >= 2


def test_get_f5_preview_corpus_entry_returns_canonical_entry():
    entry = get_f5_preview_corpus_entry("standup-blocked")

    assert entry.category == "standup"
    assert entry.label == "Standup blocked"


def test_resolve_f5_preview_corpus_selection_by_category_keeps_corpus_order():
    entries = resolve_f5_preview_corpus_selection(categories=["standup"])

    assert [entry.id for entry in entries] == ["standup-progress", "standup-blocked"]
    assert {entry.category for entry in entries} == {"standup"}


def test_resolve_f5_preview_corpus_selection_by_ids_preserves_requested_order():
    entries = resolve_f5_preview_corpus_selection(
        ids=["standup-blocked", "handoff-direct"]
    )

    assert [entry.id for entry in entries] == ["standup-blocked", "handoff-direct"]


def test_resolve_f5_preview_corpus_selection_all_returns_full_corpus():
    assert resolve_f5_preview_corpus_selection(categories=("all",)) == list_f5_preview_corpus()


def test_resolve_f5_preview_corpus_selection_rejects_unknown_category():
    with pytest.raises(ValueError) as excinfo:
        resolve_f5_preview_corpus_selection(categories=["unknown"])

    message = str(excinfo.value)
    assert "Unknown F5 preview corpus category" in message
    assert "acknowledgement" in message
    assert "standup" in message


def test_resolve_f5_preview_corpus_selection_rejects_unknown_id():
    with pytest.raises(ValueError) as excinfo:
        resolve_f5_preview_corpus_selection(ids=["missing-entry"])

    message = str(excinfo.value)
    assert "Unknown F5 preview corpus id" in message
    assert "standup-blocked" in message
    assert "handoff-direct" in message
