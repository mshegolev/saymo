"""Base protocol for call providers (Glip, Zoom, MTS-Link, etc.)."""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class MeetingStatus:
    app_running: bool = False
    meeting_found: bool = False
    tab_info: tuple[int, int] | None = None
    mic_is_correct: bool = False


class CallProvider(Protocol):
    """Abstract interface for meeting call automation.

    Implement this for each provider: Glip, Zoom, MTS-Link, Teams.
    """

    name: str

    def check_ready(self) -> MeetingStatus:
        """Check if the meeting is active and accessible."""
        ...

    def activate_meeting(self) -> bool:
        """Bring meeting window/tab to focus."""
        ...

    def toggle_mute(self) -> None:
        """Toggle mute/unmute (e.g., press Space)."""
        ...

    def switch_mic(self, device_name: str) -> bool:
        """Switch microphone to the specified device."""
        ...

    def get_previous_app(self) -> str:
        """Get name of the currently focused app (to restore later)."""
        ...

    def activate_app(self, app_name: str) -> None:
        """Restore focus to a specific app."""
        ...
