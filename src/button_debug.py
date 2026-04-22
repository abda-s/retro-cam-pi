#!/usr/bin/env python3
"""
Button Debugger - Tests physical buttons without camera.
Shows button feedback on ST7735 display and logs to console.
"""

import time
import random
from typing import Optional, Tuple

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Error: PIL not found")
    exit(1)

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("Error: RPi.GPIO not installed")
    exit(1)

from display_manager import DisplayManager
from config_manager import Config
from logger import get_logger
from input_actions import (
    ACTION_SHUTTER,
    ACTION_TOGGLE_SHOOT_MODE,
    ACTION_LONG_TOGGLE_SHOOT_MODE,
    ACTION_TOGGLE_VIEW,
    ACTION_NEXT,
    ACTION_PREV,
    ACTION_DELETE,
)


class ButtonDebugger:
    def __init__(self):
        self._logger = get_logger(__name__)
        self._logger.info("Initializing ButtonDebugger")

        self._display = DisplayManager(
            spi_port=0,
            spi_device=0,
            gpio_dc=23,
            gpio_rst=24,
            rotation=2,
            spi_speed_hz=40_000_000,
        )

        self._button_pins = {
            5: "SHUTTER",
            6: "MODE",
            20: "MODE",
            13: "VIEW",
            19: "NEXT",
            26: "PREV",
        }

        self._debounce_ms = 80
        self._long_press_ms = 1200
        self._debounce_s = max(1, self._debounce_ms) / 1000.0
        self._long_press_s = max(1, self._long_press_ms) / 1000.0

        self._button_states = {}
        self._initialized = False

        self._feedback_message = ""
        self._feedback_start = 0.0
        self._feedback_duration = 2.0

        self._chap_frame = 0
        self._chap_last_update = 0.0
        self._chap_fps = 8

    def _init_gpio(self) -> None:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        self._logger.info(
            f"ButtonDebugger init: debounce={self._debounce_ms}ms, long_press={self._long_press_ms}ms"
        )

        now = time.monotonic()
        for pin in self._button_pins:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            pressed = GPIO.input(pin) == GPIO.LOW
            self._button_states[pin] = {
                "raw": pressed,
                "stable": pressed,
                "last_change": now,
                "press_start": now if pressed else 0.0,
                "long_sent": False,
            }
            self._logger.info(
                f"Pin GPIO{pin} -> {self._button_pins[pin]} | "
                f"{'PRESSED' if pressed else 'released'}"
            )

        self._initialized = True

    def _poll_button(self) -> Optional[str]:
        if not self._initialized:
            return None

        t = time.monotonic()

        for pin in (6, 20):  # MODE on GPIO 6/20
            if pin not in self._button_states:
                continue
            state = self._button_states[pin]
            current = GPIO.input(pin) == GPIO.LOW

            if current != state["raw"]:
                state["raw"] = current
                state["last_change"] = t
                self._logger.info(f"MODE raw edge on GPIO{pin}: {'PRESSED' if current else 'released'}")

            if state["stable"] != state["raw"] and (t - state["last_change"]) >= self._debounce_s:
                state["stable"] = state["raw"]
                if state["stable"]:
                    state["press_start"] = t
                    state["long_sent"] = False
                else:
                    hold_ms = int((t - state["press_start"]) * 1000) if state["press_start"] > 0 else 0
                    if state["press_start"] > 0.0 and not state["long_sent"]:
                        state["press_start"] = 0.0
                        self._set_feedback("MODE (short)")
                        return ACTION_TOGGLE_SHOOT_MODE
                    state["press_start"] = 0.0
                    state["long_sent"] = False

            if (
                state["stable"]
                and not state["long_sent"]
                and state["press_start"] > 0.0
                and (t - state["press_start"]) >= self._long_press_s
            ):
                state["long_sent"] = True
                state["press_start"] = 0.0
                self._set_feedback("MODE (long)")
                return ACTION_LONG_TOGGLE_SHOOT_MODE

        for pin, name in self._button_pins.items():
            if pin in (6,):
                continue
            state = self._button_states[pin]
            current = GPIO.input(pin) == GPIO.LOW

            if current != state["raw"]:
                state["raw"] = current
                state["last_change"] = t
            if state["stable"] != state["raw"] and (t - state["last_change"]) >= self._debounce_s:
                state["stable"] = state["raw"]
                if state["stable"]:
                    state["press_start"] = t
                    self._set_feedback(name)
                    if pin == 5:
                        return ACTION_SHUTTER
                    elif pin == 13:
                        return ACTION_TOGGLE_VIEW
                    elif pin == 19:
                        return ACTION_NEXT
                    elif pin == 26:
                        return ACTION_PREV

        return None

    def _set_feedback(self, message: str) -> None:
        self._feedback_message = message
        self._feedback_start = time.time()
        self._logger.info(f"Button pressed: {message}")

    def _build_chap_animation(self, size: tuple) -> Image.Image:
        w, h = size
        image = Image.new('RGB', (w, h), (0, 0, 0))
        draw = ImageDraw.Draw(image)

        frame = self._chap_frame % 24

        cx = w // 2
        cy = h // 2
        bounce = abs(frame - 12) - 6
        if bounce < 0:
            bounce = 0
        y = cy - bounce * 2

        eye_offset = (frame % 4) - 2
        if eye_offset > 0:
            eye_offset = 0
        elif eye_offset < -2:
            eye_offset = -2

        draw.ellipse([(cx - 12, y - 12), (cx + 12, y + 12)], fill=(255, 200, 100), outline=(200, 150, 50), width=2)

        draw.ellipse([(cx - 7 + eye_offset, y - 4), (cx - 1 + eye_offset, y + 4)], fill=(0, 0, 0))
        draw.ellipse([(cx + 1 + eye_offset, y - 4), (cx + 7 + eye_offset, y + 4)], fill=(0, 0, 0))

        mouth_open = (frame % 8) // 4
        if mouth_open == 0:
            draw.arc([cx - 5, y + 5, cx + 5, y + 10], 0, 180, fill=(50, 30, 0), width=2)
        else:
            draw.ellipse([(cx - 4, y + 6), (cx + 4, y + 9)], fill=(50, 30, 0))

        draw.line([(cx - 15, y + 15), (cx - 8, y + 22)], fill=(255, 200, 100), width=3)
        draw.line([(cx + 15, y + 15), (cx + 8, y + 22)], fill=(255, 200, 100), width=3)

        self._chap_frame += 1

        return image

    def _render_feedback(self, size: Tuple[int, int]) -> Image.Image:
        w, h = size
        image = Image.new('RGB', (w, h), (20, 10, 30))
        draw = ImageDraw.Draw(image)

        draw.rounded_rectangle([(4, 4), (w - 5, h - 5)], radius=8, fill=(30, 20, 40), outline=(255, 200, 100), width=3)

        bbox = draw.textbbox((0, 0), self._feedback_message)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (w - text_w) // 2
        y = (h - text_h) // 2
        draw.text((x, y), self._feedback_message, fill=(255, 220, 150))

        return image

    def run(self) -> None:
        if not self._display.initialize():
            self._logger.error("Display initialization failed")
            return

        self._init_gpio()

        size = self._display.size
        self._logger.info(f"=== Button Debugger ===")
        self._logger.info(f"Display: {size[0]}x{size[1]}")
        self._logger.info("Poll buttons to see feedback")
        self._logger.info("Ctrl+C to exit")

        self._chap_last_update = time.time()

        try:
            while True:
                button = self._poll_button()

                now = time.time()
                feedback_active = (now - self._feedback_start) < self._feedback_duration

                if feedback_active:
                    frame = self._render_feedback(size)
                else:
                    if now - self._chap_last_update >= 1.0 / self._chap_fps:
                        self._chap_last_update = now
                    frame = self._build_chap_animation(size)

                self._display.display_frame(frame)

                time.sleep(0.01)

        except KeyboardInterrupt:
            self._logger.info("Exiting...")
        finally:
            self._cleanup()

    def _cleanup(self) -> None:
        if self._initialized:
            GPIO.cleanup()
        self._display.cleanup()
        self._logger.info("Cleanup complete")


def main():
    debugger = ButtonDebugger()
    debugger.run()


if __name__ == "__main__":
    main()