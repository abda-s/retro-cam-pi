"""Small feedback state helper for UI overlays."""

import time


class FeedbackState:
    """Stores short-lived feedback messages for UI overlays."""

    def __init__(self, duration: float = 2.0):
        self._duration = duration
        self._message = ""
        self._start_time = 0.0

    @property
    def message(self) -> str:
        """Current feedback message."""
        return self._message

    def set(self, message: str) -> None:
        """Set message and restart timer."""
        self._message = message
        self._start_time = time.time()

    def is_active(self) -> bool:
        """Return True while message should be shown."""
        return (time.time() - self._start_time) < self._duration

    def clear(self) -> None:
        """Clear message and timer."""
        self._message = ""
        self._start_time = 0.0
