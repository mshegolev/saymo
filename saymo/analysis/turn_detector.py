"""Detect when it's the user's turn to speak during a standup call.

Uses fuzzy keyword matching across sliding window of transcript chunks.
Handles Whisper misspellings: "Миш", "миша", "Мишка", "Михоил", etc.
"""

import logging
import re
import time

logger = logging.getLogger("saymo.analysis.turn")

# Common Whisper misspellings for Russian names
FUZZY_EXPANSIONS = {
    "Михаил": ["Михаил", "Михоил", "Михаел", "михаил", "Микаил"],
    "Миша": ["Миша", "Миш", "Мишa", "миша", "Мишка", "Мишань", "Мишу"],
    "Mikhail": ["Mikhail", "Mikail", "Mihail", "mikhail"],
    "Misha": ["Misha", "Mesha", "misha"],
}


class TurnDetector:
    """Detects when someone calls the user's name in a transcript.

    Searches across the last 2 transcript chunks (sliding window)
    to catch names that might span chunk boundaries.
    """

    def __init__(
        self,
        name_variants: list[str],
        cooldown_seconds: float = 45.0,
    ):
        # Build expanded pattern list with fuzzy variants
        all_names = set()
        for name in name_variants:
            all_names.add(name)
            all_names.add(name.lower())
            # Add fuzzy expansions if available
            for key, expansions in FUZZY_EXPANSIONS.items():
                if name.lower() == key.lower():
                    all_names.update(expansions)

        self.patterns = [
            re.compile(re.escape(name), re.IGNORECASE)
            for name in sorted(all_names, key=len, reverse=True)
        ]

        self.cooldown = cooldown_seconds
        self._last_trigger_time: float = 0
        self._prev_chunk: str = ""
        self._transcript_buffer: list[str] = []

        logger.info(f"Turn detector: {len(self.patterns)} patterns, {cooldown_seconds}s cooldown")

    def check(self, text: str) -> bool:
        """Check if transcript contains the user's name.

        Searches in current chunk AND combined with previous chunk
        to catch names split across boundaries.
        """
        if not text.strip():
            return False

        self._transcript_buffer.append(text)
        if len(self._transcript_buffer) > 20:
            self._transcript_buffer.pop(0)

        # Check cooldown
        now = time.time()
        if now - self._last_trigger_time < self.cooldown:
            return False

        # Search in: current chunk + overlap with previous
        search_texts = [
            text,
            self._prev_chunk + " " + text,  # catch names split between chunks
        ]

        self._prev_chunk = text

        for search_text in search_texts:
            for pattern in self.patterns:
                if pattern.search(search_text):
                    self._last_trigger_time = now
                    logger.info(f"TRIGGER: '{pattern.pattern}' in: {search_text[:100]}")
                    return True

        return False

    def reset_cooldown(self):
        self._last_trigger_time = 0

    @property
    def recent_transcript(self) -> str:
        return " ".join(self._transcript_buffer[-5:])
