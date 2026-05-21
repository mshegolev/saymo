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
    r"\b{trigger}\s+(?:думает|считает|видит|планирует|делает|делал|делала|сделал|сделала|готовит|пишет|решает|решил|решила)\b",
)

_THIRD_PERSON_QUESTION_PATTERNS = (
    r"\b(?:что|как|где|когда|почему|зачем)\s+{trigger}\s+(?:думает|считает|видит|планирует|делает|делал|делала|сделал|сделала|готовит|пишет|решает|решил|решила)\b",
)

_FLOOR_HANDOFF_PATTERNS = (
    r"\b(?:слово|словом)\s*,?\s*{trigger}\b",
    r"\b(?:передаю|передаем|даю|даем)\s+слово\s+{trigger}\b",
    r"\b{trigger}\s*,?\s+(?:тебе|вам)\s+слово\b",
)

_DIRECT_HANDOFF_PATTERNS = (
    r"\b{trigger}\s*,?\s+(?:что|как|где|когда|почему|зачем|кто|сколько|какие|какой|какая)\b",
    r"\b{trigger}\s*,?\s+(?:расскажи|поделись|опиши|скажи|можешь|сможешь|давай)\b",
    r"\b{trigger}\s*,?\s+(?:what|how|why|when|where|who)\b",
    r"\b{trigger}\s*,?\s+(?:can\s+you|could\s+you|do\s+you|please\s+tell|tell\s+(?:me|us))\b",
)

_COLLABORATION_MENTION_PATTERNS = (
    r"\b(?:взаимодействуем|взаимодействовали|синхронизируемся|синхронизировались|обсуждаем|обсуждали|работаем|работали)\s+с\s+{trigger}\b",
)

_PLAIN_MENTION_PATTERNS = (
    r"\b(?:helped|worked\s+with|waited\s+for|asked|pinged|mentioned)\s+{trigger}\b",
    r"\b(?:помогал|помогала|помогали|помог|помогла|помогли|ждал|ждала|ждали|жду|ждем|ждём|спросил|спросила|спросили|упоминал|упоминала|упоминали)\s+{trigger}\b",
)

_DIRECT_AFTER_TRIGGER_WORDS = {
    "what", "how", "why", "when", "where", "who", "can", "could", "do",
    "please", "tell", "что", "как", "где", "когда", "почему", "зачем",
    "кто", "сколько", "какие", "какой", "какая", "расскажи", "поделись",
    "опиши", "скажи", "можешь", "сможешь", "давай",
}


@dataclass(frozen=True)
class AddressingDecision:
    """Decision used by diagnostics and auto-mode response gating."""

    label: str
    confidence: float
    trigger: str = ""
    is_question: bool = False
    question: str = ""
    reason: str = ""
    evidence: tuple[str, ...] = ()
    context: str = ""


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
    *,
    handoff_patterns: list[str] | tuple[str, ...] | None = None,
    mention_only_patterns: list[str] | tuple[str, ...] | None = None,
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
        match = re.search(re.escape(phrase), text, re.IGNORECASE)
        if match:
            matched = match.group(0)
            break

    if not matched:
        return AddressingDecision("no_trigger", 0.0, reason="no trigger phrase in transcript")

    trigger_re = _trigger_pattern(matched.lower())
    context = _matched_context(text, matched)
    is_question = looks_like_question(text)
    question = _extract_question_text(text, matched) if is_question else ""

    for pattern in _FLOOR_HANDOFF_PATTERNS:
        if re.search(pattern.format(trigger=trigger_re), lower, re.IGNORECASE):
            return AddressingDecision(
                "addressed_to_me",
                0.9,
                trigger=matched,
                is_question=False,
                reason="floor handoff phrase",
                evidence=("trigger_phrase", "floor_handoff"),
                context=context,
            )

    for pattern in _clean_patterns(handoff_patterns):
        if _pattern_matches(pattern, trigger_re, lower):
            return AddressingDecision(
                "addressed_to_me",
                0.92,
                trigger=matched,
                is_question=is_question,
                question=question,
                reason="configured handoff pattern",
                evidence=("trigger_phrase", "configured_handoff"),
                context=context,
            )

    for pattern in _clean_patterns(mention_only_patterns):
        if _pattern_matches(pattern, trigger_re, lower):
            return AddressingDecision(
                "mentioned_not_addressed",
                0.92,
                trigger=matched,
                is_question=is_question,
                question=question,
                reason="configured mention-only pattern",
                evidence=("trigger_phrase", "configured_mention_only"),
                context=context,
            )

    for pattern in _THIRD_PERSON_QUESTION_PATTERNS:
        if re.search(pattern.format(trigger=trigger_re), lower, re.IGNORECASE):
            return AddressingDecision(
                "mentioned_not_addressed",
                0.9,
                trigger=matched,
                is_question=True,
                question=text,
                reason="third-person question pattern",
                evidence=("trigger_phrase", "third_person_question"),
                context=context,
            )

    for pattern in _COLLABORATION_MENTION_PATTERNS:
        if re.search(pattern.format(trigger=trigger_re), lower, re.IGNORECASE):
            return AddressingDecision(
                "mentioned_not_addressed",
                0.9,
                trigger=matched,
                is_question=looks_like_question(text),
                question=text if looks_like_question(text) else "",
                reason="collaboration mention pattern",
                evidence=("trigger_phrase", "collaboration_mention"),
                context=context,
            )

    for pattern in _NARRATED_MENTION_PATTERNS:
        if re.search(pattern.format(trigger=trigger_re), lower, re.IGNORECASE):
            return AddressingDecision(
                "mentioned_not_addressed",
                0.9,
                trigger=matched,
                is_question=False,
                reason="narrated mention pattern",
                evidence=("trigger_phrase", "narrated_mention"),
                context=context,
            )

    for pattern in _DIRECT_HANDOFF_PATTERNS:
        if re.search(pattern.format(trigger=trigger_re), lower, re.IGNORECASE):
            return AddressingDecision(
                "addressed_to_me",
                0.9,
                trigger=matched,
                is_question=is_question,
                question=question,
                reason="direct handoff pattern",
                evidence=("trigger_phrase", "direct_handoff"),
                context=context,
            )

    teamish = any(token in matched.lower() for token in ("team", "команд", "команде", "вашей"))
    if teamish and is_question:
        return AddressingDecision(
            "generic_team_question",
            0.8,
            trigger=matched,
            is_question=True,
            question=question,
            reason="team trigger with question",
            evidence=("trigger_phrase", "team_question"),
            context=context,
        )

    if _is_bare_trigger_call(text, trigger_re):
        return AddressingDecision(
            "addressed_to_me",
            0.78,
            trigger=matched,
            is_question=False,
            reason="bare trigger call",
            evidence=("trigger_phrase", "bare_call"),
            context=context,
        )

    for pattern in _PLAIN_MENTION_PATTERNS:
        if re.search(pattern.format(trigger=trigger_re), lower, re.IGNORECASE):
            return AddressingDecision(
                "mentioned_not_addressed",
                0.82,
                trigger=matched,
                is_question=is_question,
                question=question,
                reason="plain trigger mention without handoff evidence",
                evidence=("trigger_phrase", "plain_mention"),
                context=context,
            )

    if not is_question and _looks_like_full_name_mention(lower, trigger_re):
        return AddressingDecision(
            "mentioned_not_addressed",
            0.82,
            trigger=matched,
            is_question=False,
            reason="full-name or surname mention",
            evidence=("trigger_phrase", "full_name_mention"),
            context=context,
        )

    if not is_question:
        return AddressingDecision(
            "mentioned_not_addressed",
            0.72,
            trigger=matched,
            is_question=False,
            reason="plain trigger mention without handoff evidence",
            evidence=("trigger_phrase", "plain_mention"),
            context=context,
        )

    return AddressingDecision(
        "addressed_to_me",
        0.85,
        trigger=matched,
        is_question=True,
        question=question,
        reason="direct question with trigger",
        evidence=("trigger_phrase", "question"),
        context=context,
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


def _matched_context(text: str, trigger: str, *, radius: int = 48) -> str:
    idx = text.lower().find(trigger.lower())
    if idx < 0:
        return text[: radius * 2].strip()
    start = max(0, idx - radius)
    end = min(len(text), idx + len(trigger) + radius)
    return text[start:end].strip()


def _clean_patterns(patterns: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if not patterns:
        return ()
    return tuple(str(pattern).strip() for pattern in patterns if str(pattern).strip())


def _pattern_matches(pattern: str, trigger_re: str, lower: str) -> bool:
    try:
        return bool(re.search(pattern.format(trigger=trigger_re), lower, re.IGNORECASE))
    except (KeyError, IndexError, re.error, ValueError):
        return False


def _is_bare_trigger_call(text: str, trigger_re: str) -> bool:
    cleaned = text.strip().strip(" ,.:;!?—-").lower()
    if not cleaned:
        return False
    return bool(re.fullmatch(trigger_re, cleaned, re.IGNORECASE))


def _looks_like_full_name_mention(lower: str, trigger_re: str) -> bool:
    match = re.search(rf"\b{trigger_re}\s+([\w-]+)", lower, re.IGNORECASE)
    if not match:
        return False
    next_word = match.group(1).strip(" ,.:;!?—-").lower()
    return bool(next_word and next_word not in _DIRECT_AFTER_TRIGGER_WORDS)


def _trigger_pattern(trigger: str) -> str:
    """Return a trigger regex that tolerates simple inflected suffixes."""
    escaped = re.escape(trigger)
    if re.search(r"[а-яё]", trigger, re.IGNORECASE):
        return rf"{escaped}\w*"
    return escaped
