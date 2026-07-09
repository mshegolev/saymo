"""Built-in phrase corpus for F5-TTS timing previews."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class F5PreviewCorpusEntry:
    """One stable phrase entry for F5 preview selection."""

    id: str
    category: str
    label: str
    text: str


F5_PREVIEW_CORPUS: tuple[F5PreviewCorpusEntry, ...] = (
    F5PreviewCorpusEntry(
        id="ack-short",
        category="acknowledgement",
        label="Short acknowledgement",
        text="Got it, I can take that next.",
    ),
    F5PreviewCorpusEntry(
        id="ack-checking",
        category="acknowledgement",
        label="Brief confirmation",
        text="Yes, I see the update, and I am checking the last detail now.",
    ),
    F5PreviewCorpusEntry(
        id="standup-progress",
        category="standup",
        label="Standup progress",
        text=(
            "Yesterday I finished the review path. Today I am tightening the "
            "preview flow. No blocker from my side."
        ),
    ),
    F5PreviewCorpusEntry(
        id="standup-blocked",
        category="standup",
        label="Standup blocked",
        text=(
            "I am blocked on one dependency. I have a workaround ready, but I "
            "need confirmation before switching."
        ),
    ),
    F5PreviewCorpusEntry(
        id="multi-status-summary",
        category="multi_sentence",
        label="Multi-sentence status",
        text=(
            "The first part is complete. The second part is waiting for validation. "
            "I can share the result after this call."
        ),
    ),
    F5PreviewCorpusEntry(
        id="multi-next-steps",
        category="multi_sentence",
        label="Multi-step answer",
        text=(
            "The core flow is ready. The remaining work is cleanup and one small "
            "regression test. I expect to finish it today."
        ),
    ),
    F5PreviewCorpusEntry(
        id="clause-heavy-tradeoff",
        category="clause_heavy",
        label="Clause-heavy tradeoff",
        text=(
            "If we keep the faster setting, the answer feels responsive, but the "
            "pause before the final clause becomes too short."
        ),
    ),
    F5PreviewCorpusEntry(
        id="clause-heavy-condition",
        category="clause_heavy",
        label="Conditional explanation",
        text=(
            "When the cache is fresh, and the profile is approved, the assistant "
            "can speak immediately without rebuilding audio."
        ),
    ),
    F5PreviewCorpusEntry(
        id="handoff-direct",
        category="handoff",
        label="Direct handoff",
        text=(
            "I can own the follow-up, and I will send the concise summary after "
            "the meeting."
        ),
    ),
    F5PreviewCorpusEntry(
        id="handoff-redirect",
        category="handoff",
        label="Redirected handoff",
        text="Please hand that item to me after the demo, and I will confirm the next action.",
    ),
)

_ENTRIES_BY_ID = {entry.id: entry for entry in F5_PREVIEW_CORPUS}
_CATEGORIES = tuple(dict.fromkeys(entry.category for entry in F5_PREVIEW_CORPUS))
_CATEGORY_SET = set(_CATEGORIES)


def list_f5_preview_corpus() -> tuple[F5PreviewCorpusEntry, ...]:
    """Return corpus entries in stable display order."""
    return F5_PREVIEW_CORPUS


def list_f5_preview_categories() -> tuple[str, ...]:
    """Return known corpus categories in stable display order."""
    return _CATEGORIES


def get_f5_preview_corpus_entry(corpus_id: str) -> F5PreviewCorpusEntry:
    """Resolve a corpus entry id case-insensitively."""
    key = _normalize(corpus_id)
    try:
        return _ENTRIES_BY_ID[key]
    except KeyError as exc:
        available = ", ".join(_ENTRIES_BY_ID)
        raise ValueError(
            f"Unknown F5 preview corpus id: {corpus_id}. Available: {available}"
        ) from exc


def resolve_f5_preview_corpus_selection(
    *,
    categories: Sequence[str] | None = None,
    ids: Sequence[str] | None = None,
) -> tuple[F5PreviewCorpusEntry, ...]:
    """Resolve requested categories and ids to corpus entries."""
    selected: list[F5PreviewCorpusEntry] = []
    normalized_categories = [_normalize(category) for category in categories or ()]
    normalized_ids = [_normalize(corpus_id) for corpus_id in ids or ()]

    if not normalized_categories and not normalized_ids:
        return F5_PREVIEW_CORPUS

    if normalized_categories:
        if "all" in normalized_categories:
            selected.extend(F5_PREVIEW_CORPUS)
        else:
            unknown = [
                category
                for category in normalized_categories
                if category not in _CATEGORY_SET
            ]
            if unknown:
                available = ", ".join(_CATEGORIES)
                raise ValueError(
                    "Unknown F5 preview corpus category: "
                    f"{unknown[0]}. Available: {available}"
                )
            selected.extend(
                entry
                for entry in F5_PREVIEW_CORPUS
                if entry.category in normalized_categories
            )

    for corpus_id in normalized_ids:
        try:
            selected.append(_ENTRIES_BY_ID[corpus_id])
        except KeyError as exc:
            available = ", ".join(_ENTRIES_BY_ID)
            raise ValueError(
                f"Unknown F5 preview corpus id: {corpus_id}. Available: {available}"
            ) from exc

    return tuple(dict.fromkeys(selected))


def _normalize(value: str) -> str:
    return str(value or "").strip().lower()
