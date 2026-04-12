"""Input manager for camera controls.

Primary input source: physical GPIO buttons.
Secondary input source: keyboard (debug fallback).
"""

import select
import sys
import time
from typing import Optional

from logger import get_logger
from input_actions import (
    ACTION_DELETE,
    ACTION_LONG_TOGGLE_SHOOT_MODE,
    ACTION_NEXT,
    ACTION_PREV,
    ACTION_SHUTTER,
    ACTION_TOGGLE_SHOOT_MODE,
    ACTION_TOGGLE_VIEW,
)

try:
    from button_input import ButtonInputSource
except Exception:
    ButtonInputSource = None


class InputManager:
    """Provides high-level input actions for the app."""

    def __init__(
        self,
        buttons_enabled: bool = True,
        button_debounce_ms: int = 80,
        button_long_press_ms: int = 1200,
    ):
        self._logger = get_logger(__name__)
        self._last_key: Optional[str] = None
        self._button_source = None

        if buttons_enabled and ButtonInputSource is not None:
            self._button_source = ButtonInputSource(
                debounce_ms=button_debounce_ms,
                long_press_ms=button_long_press_ms,
            )
            self._button_source.initialize()
            self._logger.info("InputManager: physical buttons enabled")
        elif buttons_enabled and ButtonInputSource is None:
            self._logger.warning("InputManager: button module unavailable, keyboard fallback only")
        else:
            self._logger.info("InputManager: physical buttons disabled by config")

        # Keyboard mappings (debug only)
        self._key_to_action = {
            "t": ACTION_SHUTTER,
            "v": ACTION_SHUTTER,
            "c": ACTION_TOGGLE_SHOOT_MODE,
            "m": ACTION_TOGGLE_VIEW,
            "n": ACTION_NEXT,
            "p": ACTION_PREV,
            "d": ACTION_DELETE,
            "x": ACTION_LONG_TOGGLE_SHOOT_MODE,
            # Keep old 'f' for convenience in debug sessions
            "f": ACTION_NEXT,
        }

    def poll_action(self) -> Optional[str]:
        """Poll one action from buttons first, then keyboard fallback."""
        if self._button_source is not None:
            self._button_source.ensure_ready()
            action = self._button_source.poll_action()
            if action is not None:
                self._logger.debug(f"InputManager action from button: {action}")
                return action

        if select.select([sys.stdin], [], [], 0)[0]:
            try:
                key = sys.stdin.read(1)
                key_lower = key.lower()
                self._last_key = key_lower
                action = self._key_to_action.get(key_lower)
                if action is not None:
                    self._logger.debug(f"InputManager action from keyboard '{key_lower}': {action}")
                return action
            except Exception:
                pass

        return None

    def poll_for_key(self, max_wait: float = 5.0) -> Optional[str]:
        """Legacy helper retained for compatibility with existing code."""
        start = time.time()
        while time.time() - start < max_wait:
            action = self.poll_action()
            if action:
                return action
            time.sleep(0.01)
        return None

    def cleanup(self) -> None:
        """Release GPIO resources owned by input manager."""
        if self._button_source is not None:
            self._button_source.cleanup()

    @property
    def last_key(self) -> Optional[str]:
        """Get the last keyboard key pressed (debug info)."""
        return self._last_key
