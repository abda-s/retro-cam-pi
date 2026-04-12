#!/usr/bin/env python3
"""Physical button test utility with software debounce.

Wiring expected (active-low, pull-up):
- SHUTTER -> GPIO 5  (Pin 29)
- MODE    -> GPIO 6  (Pin 31)
- VIEW    -> GPIO 13 (Pin 33)
- NEXT    -> GPIO 19 (Pin 35)
- PREV    -> GPIO 26 (Pin 37)

Each button should connect GPIO -> switch -> GND.
"""

import argparse
import time
from dataclasses import dataclass

import RPi.GPIO as GPIO


BUTTON_PINS = {
    "SHUTTER": 5,
    "MODE": 6,
    "VIEW": 13,
    "NEXT": 19,
    "PREV": 26,
}

DEFAULT_DEBOUNCE_MS = 80
DEFAULT_POLL_MS = 5


@dataclass
class ButtonState:
    name: str
    pin: int
    raw: bool
    stable: bool
    last_change: float


def _is_pressed(pin: int) -> bool:
    """Active-low read with pull-up configuration."""
    return GPIO.input(pin) == GPIO.LOW


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Debounced GPIO button test")
    parser.add_argument(
        "--debounce-ms",
        type=int,
        default=DEFAULT_DEBOUNCE_MS,
        help=f"Debounce time in milliseconds (default: {DEFAULT_DEBOUNCE_MS})",
    )
    parser.add_argument(
        "--poll-ms",
        type=int,
        default=DEFAULT_POLL_MS,
        help=f"Poll interval in milliseconds (default: {DEFAULT_POLL_MS})",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    debounce_ms = max(1, args.debounce_ms)
    poll_ms = max(1, args.poll_ms)

    print("=== Button Test (Debounced) ===")
    print(f"Debounce: {debounce_ms}ms | Poll: {poll_ms}ms")
    print("Press Ctrl+C to exit\n")

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    states: dict[str, ButtonState] = {}
    now = time.monotonic()

    for name, pin in BUTTON_PINS.items():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        initial = _is_pressed(pin)
        states[name] = ButtonState(
            name=name,
            pin=pin,
            raw=initial,
            stable=initial,
            last_change=now,
        )
        print(f"{name:<8} GPIO {pin:<2} initial={'PRESSED' if initial else 'released'}")

    print("\nReady. Try pressing buttons...\n")

    debounce_s = debounce_ms / 1000.0
    poll_s = poll_ms / 1000.0

    try:
        while True:
            t = time.monotonic()

            for state in states.values():
                current = _is_pressed(state.pin)

                if current != state.raw:
                    state.raw = current
                    state.last_change = t

                if state.stable != state.raw and (t - state.last_change) >= debounce_s:
                    state.stable = state.raw
                    event = "PRESSED" if state.stable else "released"
                    print(f"[{time.strftime('%H:%M:%S')}] {state.name:<8} {event}")

            time.sleep(poll_s)

    except KeyboardInterrupt:
        print("\nExiting button test...")
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    main()
