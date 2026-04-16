"""Detect when it's the user's turn to speak during a standup call.

Two detection modes:
1. Keyword spotting — fast regex match on name variants
2. Silence detection — trigger after name + pause (someone is waiting)
"""

import logging
import re
import time

logger = logging.getLogger("saymo.analysis.turn")


class TurnDetector:
    """Detects when someone calls the user's name in a transcript."""

    def __init__(
        self,
        name_variants: list[str],
        cooldown_seconds: float = 30.0,
    ):
        """
        Args:
            name_variants: List of name forms to detect (e.g., ["Михаил", "Миша"]).
            cooldown_seconds: Ignore repeated triggers within this window.
        """
        self.patterns = [
            re.compile(re.escape(name), re.IGNORECASE)
            for name in name_variants
        ]
        self.cooldown = cooldown_seconds
        self._last_trigger_time: float = 0
        self._transcript_buffer: list[str] = []

    def check(self, text: str) -> bool:
        """Check if the transcript text contains the user's name.

        Returns True if triggered (and not in cooldown).
        """
        if not text.strip():
            return False

        self._transcript_buffer.append(text)
        # Keep last 10 chunks
        if len(self._transcript_buffer) > 10:
            self._transcript_buffer.pop(0)

        # Check cooldown
        now = time.time()
        if now - self._last_trigger_time < self.cooldown:
            return False

        # Search for name in current chunk
        for pattern in self.patterns:
            if pattern.search(text):
                self._last_trigger_time = now
                logger.info(f"TRIGGER: detected '{pattern.pattern}' in: {text[:80]}")
                return True

        return False

    def reset_cooldown(self):
        """Reset the cooldown timer (e.g., after speaking is done)."""
        self._last_trigger_time = 0

    @property
    def recent_transcript(self) -> str:
        """Last few transcript chunks joined."""
        return " ".join(self._transcript_buffer)
