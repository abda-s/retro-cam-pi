"""GPIO button input source with software debounce."""

import time
from dataclasses import dataclass
from typing import Dict, Optional

import RPi.GPIO as GPIO

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


@dataclass
class _ButtonState:
    raw: bool
    stable: bool
    last_change: float
    press_start: float = 0.0
    long_sent: bool = False


class ButtonInputSource:
    """Polls physical buttons and emits high-level actions."""

    def __init__(self, debounce_ms: int = 80, long_press_ms: int = 1200):
        self._logger = get_logger(__name__)
        self._debounce_s = max(1, debounce_ms) / 1000.0
        self._long_press_s = max(1, long_press_ms) / 1000.0
        # Accept MODE from multiple fallback pins to tolerate wiring mistakes.
        # Primary expected pin is GPIO6.
        self._mode_pins = (6, 21, 16, 20)
        # MODE needs to feel responsive; use lower debounce than other buttons.
        self._mode_debounce_s = min(self._debounce_s, 0.04)

        self._pin_to_action = {
            5: ACTION_SHUTTER,
            6: ACTION_TOGGLE_SHOOT_MODE,
            21: ACTION_TOGGLE_SHOOT_MODE,
            16: ACTION_TOGGLE_SHOOT_MODE,
            20: ACTION_TOGGLE_SHOOT_MODE,
            13: ACTION_TOGGLE_VIEW,
            19: ACTION_NEXT,
            26: ACTION_PREV,
        }

        self._states: Dict[int, _ButtonState] = {}
        self._initialized = False

    def initialize(self) -> None:
        """Initialize GPIO inputs with pull-ups."""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        self._logger.info(
            "ButtonInput init: mode=BCM, "
            f"debounce={int(self._debounce_s * 1000)}ms, "
            f"long_press={int(self._long_press_s * 1000)}ms"
        )

        now = time.monotonic()
        for pin in self._pin_to_action:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            pressed = self._is_pressed(pin)
            self._states[pin] = _ButtonState(raw=pressed, stable=pressed, last_change=now)
            self._states[pin].press_start = now if pressed else 0.0
            self._states[pin].long_sent = False
            self._logger.info(
                f"ButtonInput pin setup: GPIO {pin} -> {self._pin_to_action[pin]} | "
                f"initial={'PRESSED' if pressed else 'released'}"
            )

        self._initialized = True

    def ensure_ready(self) -> None:
        """Ensure GPIO mode/pins are still configured for button polling."""
        mode = GPIO.getmode()
        if not self._initialized or mode != GPIO.BCM:
            self._logger.warning(
                f"ButtonInput not ready (initialized={self._initialized}, mode={mode}); reinitializing"
            )
            self.initialize()

    def poll_action(self) -> Optional[str]:
        """Return one debounced action if a button was newly pressed."""
        if not self._initialized:
            return None

        t = time.monotonic()

        # Handle MODE first so it cannot be starved by early returns from other buttons.
        mode_action = self._poll_mode_action(t)
        if mode_action is not None:
            return mode_action

        for pin, action in self._pin_to_action.items():
            if pin in self._mode_pins:
                continue
            state = self._states[pin]
            current = self._is_pressed(pin)

            if current != state.raw:
                state.raw = current
                state.last_change = t
            if state.stable != state.raw and (t - state.last_change) >= self._debounce_s:
                state.stable = state.raw
                if state.stable:
                    state.press_start = t
                    state.long_sent = False
                    self._logger.debug(f"Button press: GPIO {pin} ({action})")
                    self._logger.info(f"Button action: {action}")
                    return action
                else:
                    self._logger.debug(f"Button release: GPIO {pin} ({action})")
                    state.press_start = 0.0
                    state.long_sent = False

        return None

    def _poll_mode_action(self, t: float) -> Optional[str]:
        """Handle MODE with dedicated short/long-press logic."""
        for mode_pin in self._mode_pins:
            if mode_pin not in self._states:
                continue

            state = self._states[mode_pin]
            current = self._is_pressed(mode_pin)

            if current != state.raw:
                state.raw = current
                state.last_change = t
                self._logger.info(
                    f"MODE raw edge on GPIO{mode_pin}: {'PRESSED' if current else 'released'}"
                )

            if state.stable != state.raw and (t - state.last_change) >= self._mode_debounce_s:
                state.stable = state.raw
                if state.stable:
                    state.press_start = t
                    state.long_sent = False
                    self._logger.info(f"MODE debounced press on GPIO{mode_pin}")
                else:
                    hold_ms = int((t - state.press_start) * 1000) if state.press_start > 0 else 0
                    self._logger.info(
                        f"MODE debounced release on GPIO{mode_pin} "
                        f"(held {hold_ms}ms, long_sent={state.long_sent})"
                    )
                    if state.press_start > 0.0 and not state.long_sent:
                        state.press_start = 0.0
                        self._logger.info(f"Button action: {ACTION_TOGGLE_SHOOT_MODE}")
                        return ACTION_TOGGLE_SHOOT_MODE
                    state.press_start = 0.0
                    state.long_sent = False

            if (
                state.stable
                and not state.long_sent
                and state.press_start > 0.0
                and (t - state.press_start) >= self._long_press_s
            ):
                state.long_sent = True
                state.press_start = 0.0
                self._logger.info(f"MODE long press threshold reached on GPIO{mode_pin}")
                self._logger.info(f"Button action: {ACTION_LONG_TOGGLE_SHOOT_MODE}")
                return ACTION_LONG_TOGGLE_SHOOT_MODE

        return None

    def cleanup(self) -> None:
        """Release GPIO resources."""
        if self._initialized:
            GPIO.cleanup()
            self._initialized = False
            self._logger.info("ButtonInput cleanup complete")

    @staticmethod
    def _is_pressed(pin: int) -> bool:
        """Active-low read."""
        return GPIO.input(pin) == GPIO.LOW
