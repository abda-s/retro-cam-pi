#!/usr/bin/env python3
"""
RPi TFT Camera Display - Modular Version
Version: 4.0.0 - Refactored for modularity

Architecture (3 processes):
  Core 1: capture_worker  — picamera2 RGB888, BGR→RGB swap
  Core 2: process_worker  — cv2.resize (INTER_LINEAR)
  Core 3+: main loop      — PIL convert + luma display @ 40 MHz

Module Structure:
  - camera_worker.py    : Capture process
  - process_worker.py   : Resize process
  - display_manager.py : ST7735 TFT handling
  - capture_manager.py : Image save/count
  - config_manager.py  : Configuration loader
  - shared.py          : Constants
  - main.py            : Orchestration
"""

import sys
import select
import time
import os
from multiprocessing import Process, Queue, Value
from queue import Empty

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Error: PIL not found. Run: pip3 install pillow --break-system-packages")
    sys.exit(1)

try:
    import numpy as np
except ImportError:
    print("Error: numpy not found. Run: pip3 install numpy")
    sys.exit(1)

# Import project modules
from camera_worker import capture_worker
from process_worker import process_worker
from display_manager import DisplayManager
from capture_manager import CaptureManager
from config_manager import Config


class CameraTFTApp:
    """Main application class for camera TFT display."""

    def __init__(self, config: Config):
        """Initialize application with configuration.

        Args:
            config: Configuration object
        """
        self._config = config
        self._running = False

        # Display manager
        self._display_manager = DisplayManager(
            spi_port=config.spi_port,
            spi_device=config.spi_device,
            gpio_dc=config.gpio_dc,
            gpio_rst=config.gpio_rst,
            rotation=config.display_rotation,
            spi_speed_hz=config.spi_speed_hz,
        )

        # Capture manager
        self._capture_manager = CaptureManager(
            save_directory=config.save_directory,
            capture_resolution=config.capture_resolution,
            file_format=config.file_format,
            timestamp_format=config.timestamp_format,
            feedback_duration=config.feedback_duration,
        )

        # Worker processes
        self._capture_process: Process = None
        self._process_process: Process = None

        # Queues
        self._capture_queue_save = Queue(maxsize=config.queue_maxsize)
        self._capture_queue_display = Queue(maxsize=config.queue_maxsize)
        self._display_queue = Queue(maxsize=config.queue_maxsize)

        # Shared flags
        self._running_flag = Value('b', True)
        self._capture_count = Value('i', 0)

        # Feedback overlay state
        self._feedback_overlay = None

        # FPS tracking
        self._frame_times = []
        self._last_fps_print = 0.0

    def initialize(self) -> bool:
        """Initialize hardware (display).

        Returns:
            True if initialization successful
        """
        return self._display_manager.initialize()

    def start_workers(self) -> None:
        """Start worker processes."""
        print("\nStarting workers...")

        # Capture worker (Core 1)
        self._capture_process = Process(
            target=capture_worker,
            args=(
                self._capture_queue_save,
                self._capture_queue_display,
                self._capture_count,
                self._running_flag,
                self._config.capture_resolution,
            )
        )
        self._capture_process.start()
        print("✓ Capture worker (Core 1) — RGB888 + BGR→RGB swap")

        # Process worker (Core 2)
        display_size = self._display_manager.size
        self._process_process = Process(
            target=process_worker,
            args=(
                self._capture_queue_display,
                self._display_queue,
                self._running_flag,
                display_size,
            )
        )
        self._process_process.start()
        print("✓ Process worker (Core 2) — cv2.resize INTER_LINEAR")
        print("✓ Main display loop (Core 3+)")

    def stop_workers(self) -> None:
        """Stop worker processes gracefully."""
        print("Stopping workers...")
        self._running_flag.value = False

        for proc, name in [
            (self._capture_process, "capture"),
            (self._process_process, "process")
        ]:
            if proc:
                proc.join(timeout=3)
                if proc.is_alive():
                    print(f"Terminating {name} worker...")
                    proc.terminate()
                    proc.join(timeout=1)

        print("All workers stopped")

    def check_for_capture(self) -> bool:
        """Check if user pressed 't' key (non-blocking).

        Returns:
            True if 't' was pressed
        """
        if select.select([sys.stdin], [], [], 0)[0]:
            try:
                key = os.read(sys.stdin.fileno(), 1)
                return key.lower() == b't'
            except Exception:
                return False
        return False

    def show_error(self, message: str) -> None:
        """Show error message on display.

        Args:
            message: Error message
        """
        self._display_manager.show_error(message)

    def run(self) -> None:
        """Run the main application loop."""
        if not self.initialize():
            return

        self._running = True
        print("\n=== Camera TFT Display (v4.0.0 - Modular) ===")
        print("Press 't' + Enter to capture | Ctrl+Z to stop\n")

        self.start_workers()
        time.sleep(0.5)

        self._last_fps_print = time.time()

        try:
            while self._running:
                loop_start = time.time()

                # Handle capture input
                if self.check_for_capture():
                    success, filename = self._capture_manager.capture_image(
                        self._capture_queue_save,
                        self._capture_queue_display,
                        self._capture_count,
                    )
                    if success:
                        print(f"✓ Saved: {filename}")
                        self._capture_manager.set_feedback("Saved!")
                        self._feedback_overlay = None
                    else:
                        print(f"✗ Failed: {self._capture_manager.last_error}")
                        self._capture_manager.set_feedback("Error!")
                        self._feedback_overlay = None

                # Get resized frame from display queue
                try:
                    frame_rgb = self._display_queue.get(timeout=0.005)
                except Empty:
                    continue
                except Exception:
                    continue

                # Convert numpy array to PIL Image
                frame_image = Image.fromarray(frame_rgb)

                # Handle feedback overlay
                if self._capture_manager.is_feedback_active():
                    if self._feedback_overlay is None:
                        overlay_img = Image.new('RGBA', frame_image.size, (0, 0, 0, 100))
                        draw_ov = ImageDraw.Draw(overlay_img)
                        msg = self._capture_manager._feedback_message
                        draw_ov.text((5, 5), msg, fill=(0, 255, 0, 255))
                        draw_ov.text((5, 20), f"#{self._capture_count.value}", fill=(255, 255, 255, 200))
                        self._feedback_overlay = overlay_img

                    frame_image = Image.alpha_composite(
                        frame_image.convert('RGBA'), self._feedback_overlay
                    ).convert('RGB')
                else:
                    self._feedback_overlay = None

                # Display frame
                self._display_manager.display_frame(frame_image)

                # FPS tracking
                frame_time = time.time() - loop_start
                self._frame_times.append(frame_time)
                if len(self._frame_times) > 30:
                    self._frame_times.pop(0)

                # Print FPS every 5 seconds
                now = time.time()
                if now - self._last_fps_print >= 5.0:
                    avg_time = sum(self._frame_times) / len(self._frame_times) if self._frame_times else 1
                    fps = 1.0 / avg_time if avg_time > 0 else 0
                    print(
                        f"FPS: {fps:.1f} | "
                        f"Captures: {self._capture_count.value} | "
                        f"Queues: save={self._capture_queue_save.qsize()} "
                        f"proc={self._capture_queue_display.qsize()} "
                        f"disp={self._display_queue.qsize()}"
                    )
                    self._last_fps_print = now

        except Exception as e:
            print(f"\nFatal error: {e}")
            self.show_error("Fatal Error")
        finally:
            self.stop_workers()
            self.cleanup()

    def cleanup(self) -> None:
        """Clean up resources."""
        print("Cleaning up...")
        self._display_manager.cleanup()
        print(f"Total captures: {self._capture_count.value}")
        print(f"Saved to: {self._capture_manager.save_directory}")
        print("Done.")


def main() -> None:
    """Main entry point."""
    config = Config()
    app = CameraTFTApp(config)
    app.run()


if __name__ == "__main__":
    main()