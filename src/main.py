#!/usr/bin/env python3
"""
RPi TFT Camera Display - Modular Version
Version: 4.2.0 - Dual encoder (H264 for video + lores for display)

Uses Picamera2's dual encoder feature:
  - H264 encoder for video recording (proper timing)
  - Lores stream for TFT display
"""

import sys
import select
import time
import os
from datetime import datetime
from multiprocessing import Process, Queue, Value
from queue import Empty
from pathlib import Path
from typing import Tuple

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Error: PIL not found")
    sys.exit(1)

try:
    import numpy as np
except ImportError:
    print("Error: numpy not found")
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

        # Capture manager (for images)
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
        self._capture_queue_display = Queue(maxsize=config.queue_maxsize)
        self._display_queue = Queue(maxsize=config.queue_maxsize)

        # Shared flags
        self._running_flag = Value('b', True)
        self._capture_count = Value('i', 0)
        
        # Video recording control
        # 0 = idle, 1 = start recording, 2 = stop recording
        self._video_flag = Value('i', 0)
        
        # Image capture control
        # 0 = idle, 1 = capture
        self._image_capture_flag = Value('i', 0)

        # Overlay state
        self._feedback_overlay = None
        self._video_overlay = None

        # FPS tracking
        self._frame_times = []
        self._last_fps_print = 0.0
        
        # Video recording state
        self._is_recording = False
        self._recording_start_time = 0.0

    def initialize(self) -> bool:
        """Initialize hardware (display)."""
        return self._display_manager.initialize()

    def start_workers(self) -> None:
        """Start worker processes."""
        print("\nStarting workers...")

        # Capture worker with dual stream support
        self._capture_process = Process(
            target=capture_worker,
            args=(
                self._capture_queue_display,
                self._capture_count,
                self._running_flag,
                self._video_flag,
                self._image_capture_flag,
                self._config.video_resolution,
                self._config.capture_resolution,
                self._config.save_directory,
                self._config.audio_enabled,
                self._config.audio_device,
            )
        )
        self._capture_process.start()
        print(f"✓ Capture worker (Core 1) — video={self._config.video_resolution}, display={self._config.capture_resolution}")

        # Process worker for display resize
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
                    proc.terminate()
                    proc.join(timeout=1)

        print("All workers stopped")

    def check_for_input(self) -> str:
        """Check for key input (non-blocking)."""
        if select.select([sys.stdin], [], [], 0)[0]:
            try:
                key = os.read(sys.stdin.fileno(), 1)
                key_lower = key.lower()
                if key_lower == b't':
                    return 't'
                elif key_lower == b'v':
                    return 'v'
            except Exception:
                pass
        return ''

    def show_error(self, message: str) -> None:
        """Show error message on display."""
        self._display_manager.show_error(message)

    def _create_video_overlay(self, frame_size: Tuple[int, int], duration: float) -> Image.Image:
        """Create video recording overlay."""
        overlay_img = Image.new('RGBA', frame_size, (0, 0, 0, 100))
        draw = ImageDraw.Draw(overlay_img)

        # Blinking REC indicator
        if int(time.time() * 2) % 2 == 0:
            draw.ellipse([(5, 5), (15, 15)], fill=(255, 0, 0, 255))

        draw.text((20, 5), "REC", fill=(255, 0, 0, 255))

        # Duration
        mins = int(duration) // 60
        secs = int(duration) % 60
        duration_text = f"{mins:02d}:{secs:02d}"
        draw.text((5, 20), duration_text, fill=(255, 255, 255, 255))

        return overlay_img

    def run(self) -> None:
        """Run the main application loop."""
        if not self.initialize():
            return

        self._running = True
        print("\n=== Camera TFT Display (v4.2.0 - Dual Encoder) ===")
        print("Press 't' + Enter to capture | Press 'v' + Enter to start/stop video | Ctrl+Z to stop\n")

        self.start_workers()
        time.sleep(1.0)

        self._last_fps_print = time.time()

        try:
            while self._running:
                loop_start = time.time()

                # Handle key input
                key = self.check_for_input()

                if key == 't':
                    # Image capture - trigger the capture via flag
                    self._image_capture_flag.value = 1
                    # Note: actual save happens in capture_worker
                    print("Capturing image...")

                elif key == 'v':
                    # Toggle video recording
                    if self._is_recording:
                        # Stop recording
                        self._video_flag.value = 2
                        self._is_recording = False
                        print("Video recording stopped")
                        self._capture_manager.set_feedback("Video Saved!")
                        self._feedback_overlay = None
                    else:
                        # Start recording
                        self._video_flag.value = 1
                        self._is_recording = True
                        self._recording_start_time = time.time()
                        print("Recording started...")

                # Get resized frame from display queue
                try:
                    frame_rgb = self._display_queue.get(timeout=0.005)
                except Empty:
                    continue
                except Exception:
                    continue

                # Convert numpy array to PIL Image
                frame_image = Image.fromarray(frame_rgb)

                # Handle video recording overlay
                if self._is_recording:
                    rec_duration = time.time() - self._recording_start_time
                    video_overlay = self._create_video_overlay(frame_image.size, rec_duration)
                    frame_image = Image.alpha_composite(
                        frame_image.convert('RGBA'), video_overlay
                    ).convert('RGB')
                # Handle capture feedback overlay
                elif self._capture_manager.is_feedback_active():
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

                # Print status every 5 seconds
                now = time.time()
                if now - self._last_fps_print >= 5.0:
                    avg_time = sum(self._frame_times) / len(self._frame_times) if self._frame_times else 1
                    fps = 1.0 / avg_time if avg_time > 0 else 0
                    
                    status = f"FPS: {fps:.1f} | Captures: {self._capture_count.value}"
                    if self._is_recording:
                        rec_duration = int(time.time() - self._recording_start_time)
                        status += f" | REC: {rec_duration}s"
                    
                    print(status)
                    self._last_fps_print = now

        except Exception as e:
            print(f"\nFatal error: {e}")
            self.show_error("Fatal Error")
        finally:
            # Stop video if recording
            if self._is_recording:
                self._video_flag.value = 2
            
            self.stop_workers()
            self.cleanup()

    def cleanup(self) -> None:
        """Clean up resources."""
        print("Cleaning up...")
        self._display_manager.cleanup()
        print(f"Total captures: {self._capture_count.value}")
        print(f"Saved to: {self._config.save_directory}")
        print("Done.")


def main() -> None:
    """Main entry point."""
    config = Config()
    app = CameraTFTApp(config)
    app.run()


if __name__ == "__main__":
    main()