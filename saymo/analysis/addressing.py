"""Classify whether a trigger transcript is addressed to the user."""

from __future__ import annotations

import re
from dataclasses import dataclass


_QUESTION_STARTERS = (
    "как ", "что ", "где ", "когда ", "почему ", "зачем ", "кто ",
    "сколько ", "какие ", "какой ", "какая ", "расскажи", "поделись", "опиши",
    "what ", "how ", "why ", "when ", "where ", "who ",
    "tell me", "can you", "could you", "do you",
)

_NARRATED_MENTION_PATTERNS = (
    r"\bкак\s+{trigger}\s+(?:вчера\s+|раньше\s+)?(?:говорил|говорила|сказал|сказала|писал|писала)\b",
    r"\bпо\s+словам\s+{trigger}\b",
    r"\bсо\s+слов\s+{trigger}\b",
    r"\b{trigger}\s+(?:вчера\s+|раньше\s+)?(?:говорил|говорила|сказал|сказала|писал|писала)\b",
)


@dataclass(frozen=True)
class AddressingDecision:
    """Decision used by diagnostics and auto-mode response gating."""

    label: str
    confidence: float
    trigger: str = ""
    is_question: bool = False
    question: str = ""
    reason: str = ""


def expand_trigger_phrases(
    trigger_phrases: list[str],
    fuzzy_expansions: dict[str, list[str]] | None = None,
) -> list[str]:
    """Return trigger phrases plus configured STT fuzzy variants."""
    fuzzy_expansions = fuzzy_expansions or {}
    expanded: set[str] = set()
    for phrase in trigger_phrases:
        if not phrase:
            continue
        expanded.add(phrase)
        expanded.add(phrase.lower())
        for key, variants in fuzzy_expansions.items():
            if phrase.lower() == key.lower():
                expanded.update(v for v in variants if v)
    return sorted(expanded, key=len, reverse=True)


def looks_like_question(text: str) -> bool:
    """Heuristic used by trigger diagnostics and addressing classification."""
    t = text.strip()
    if not t:
        return False
    if "?" in t:
        return True
    lower = t.lower()
    return any(starter in lower for starter in _QUESTION_STARTERS)


def classify_addressing(
    transcript: str,
    trigger_phrases: list[str],
) -> AddressingDecision:
    """Classify whether a transcript window is worth answering.

    Labels:
    - ``addressed_to_me``: direct mention or direct question to the trigger.
    - ``generic_team_question``: team/profile trigger with a question.
    - ``mentioned_not_addressed``: the trigger is being talked about, not called.
    - ``no_trigger``: no configured trigger phrase appears.
    - ``ignore``: empty transcript or empty trigger configuration.
    """
    text = " ".join((transcript or "").split())
    if not text:
        return AddressingDecision("ignore", 0.0, reason="empty transcript")
    if not trigger_phrases:
        return AddressingDecision("ignore", 0.0, reason="no trigger phrases configured")

    lower = text.lower()
    matched = ""
    for phrase in sorted((p for p in trigger_phrases if p), key=len, reverse=True):
        if re.search(re.escape(phrase), text, re.IGNORECASE):
            matched = phrase
            break

    if not matched:
        return AddressingDecision("no_trigger", 0.0, reason="no trigger phrase in transcript")

    trigger_re = re.escape(matched.lower())
    for pattern in _NARRATED_MENTION_PATTERNS:
        if re.search(pattern.format(trigger=trigger_re), lower, re.IGNORECASE):
            return AddressingDecision(
                "mentioned_not_addressed",
                0.9,
                trigger=matched,
                is_question=False,
                reason="narrated mention pattern",
            )

    is_question = looks_like_question(text)
    question = _extract_question_text(text, matched) if is_question else ""
    teamish = any(token in matched.lower() for token in ("team", "команд", "команде", "вашей"))
    if teamish and is_question:
        return AddressingDecision(
            "generic_team_question",
            0.8,
            trigger=matched,
            is_question=True,
            question=question,
            reason="team trigger with question",
        )

    return AddressingDecision(
        "addressed_to_me",
        0.85 if is_question else 0.65,
        trigger=matched,
        is_question=is_question,
        question=question,
        reason="direct trigger mention",
    )


def should_answer_decision(decision: AddressingDecision) -> bool:
    """Whether auto-mode should continue to response resolution."""
    return decision.label not in {"ignore", "no_trigger", "mentioned_not_addressed"}


def _extract_question_text(text: str, trigger: str) -> str:
    """Best-effort short question snippet for diagnostics."""
    idx = text.lower().find(trigger.lower())
    if idx >= 0:
        tail = text[idx + len(trigger):].strip(" ,:;—-")
        if tail:
            return tail
    return text
