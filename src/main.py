#!/usr/bin/env python3
"""
RPi TFT Camera Display - Modular Version
Version: 4.2.7 - Added retro filters (f key to cycle)

Uses Picamera2's dual encoder feature:
  - H264 encoder for video recording (proper timing)
  - Lores stream for TFT display
  - Media browser for viewing saved images and videos
  - Smart cache validation to auto-fix display issues
  - Reduced log spam for better terminal readability
  - Fixed: Use actual DisplayManager size (handles 160x128 rotation)
  - Added: 7 retro/analog filters (apply to live feed + saved files)
"""

import sys
import time
import os
from datetime import datetime
from multiprocessing import Process, Queue, Value
from queue import Empty
from pathlib import Path
from typing import Tuple, Optional

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
from input_manager import InputManager
from media_browser import MediaBrowser
from logger import get_logger


class CameraTFTApp:
    """Main application class for camera TFT display."""

    def __init__(self, config: Config):
        self._config = config
        self._running = False
        
        # Logger
        self._logger = get_logger(__name__)
        self._logger.info("Initializing CameraTFTApp")
        
        # Input manager
        self._input_manager = InputManager()

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

        # Media browser (for viewing saved files)
        # NOTE: Will be initialized with actual display size AFTER display is initialized
        # See run() method where we call _init_media_browser()
        self._media_browser: MediaBrowser = None

        # View mode state (False = Live, True = View Saved)
        self._view_mode = False

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

        # Filter control (0-6 index)
        self._filter_index = Value('i', 0)
        self._filter_names = ["NONE", "SEPIA", "SILVER", "70s FILM", "80s VHS", "80s VHS+", "SUPER 8"]
        self._filter_feedback_timer = 0.0

        # Overlay state
        self._feedback_overlay = None
        self._video_overlay = None
        self._filter_overlay = None

        # FPS tracking
        self._frame_times = []
        self._last_fps_print = 0.0
        
        # Video recording state
        self._is_recording = False
        self._recording_start_time = 0.0

    def initialize(self) -> bool:
        """Initialize hardware (display)."""
        return self._display_manager.initialize()

    def _init_media_browser(self) -> None:
        """Initialize media browser with actual display size after display is initialized."""
        # Use DisplayManager's ACTUAL size (handles rotation: 160x128 or 128x160)
        actual_size = self._display_manager.size
        print(f"[MediaBrowser] Using display size: {actual_size}")
        self._media_browser = MediaBrowser(
            save_directory=self._config.save_directory,
            display_size=actual_size,
        )

    def start_workers(self) -> None:
        """Start worker processes."""
        self._logger.info("Starting workers...")

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
                self._config.lores_resolution,
                self._config.save_directory,
                self._config.audio_enabled,
                self._config.audio_device,
                self._filter_index,  # Pass the shared Value object, not its current value
            )
        )
        self._capture_process.start()
        self._logger.info(f"Capture worker started: video={self._config.video_resolution}, lores={self._config.lores_resolution}")

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
        self._logger.info("Process worker started: cv2.resize INTER_LINEAR")
        self._logger.info("Main display loop started (Core 3+)")

    def stop_workers(self) -> None:
        """Stop worker processes gracefully."""
        self._logger.info("Stopping workers...")
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

        self._logger.info("All workers stopped")
    
    def check_for_input(self) -> str:
        """Check for key input (non-blocking)."""
        return self._input_manager.check_for_input() or ''

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

        # Initialize media browser AFTER display is initialized (to get actual size)
        self._init_media_browser()

        self._running = True
        self._logger.info("=== Camera TFT Display (v4.2.7) ===")
        self._logger.info("Press 't' + Enter to capture | Press 'v' + Enter to start/stop video | Press 'm' + Enter to toggle view mode | Ctrl+Z to stop")

        self.start_workers()
        time.sleep(1.0)

        self._last_fps_print = time.time()

        try:
            while self._running:
                loop_start = time.time()

                # Handle key input
                key = self.check_for_input()

                if key == 'm':
                    # Toggle between Live and View mode
                    self._view_mode = not self._view_mode
                    if self._view_mode:
                        # Enter view mode
                        self._logger.info("Entering VIEW MODE")
                        self._capture_manager.set_feedback("VIEW MODE")
                        self._feedback_overlay = None
                        
                        # Scan for files
                        if self._media_browser.scan_directory():
                            self._logger.info(f"Found {len(self._media_browser._files)} files")
                        else:
                            self._logger.info("No files found")
                    else:
                        # Return to live mode
                        self._logger.info("Returning to LIVE VIEW")
                        self._capture_manager.set_feedback("LIVE VIEW")
                        self._feedback_overlay = None

                elif self._view_mode:
                    # View mode navigation
                    if key == 'n':
                        if self._media_browser.next_file():
                            self._logger.info(f"Next file: {self._media_browser.get_current_file().name}")
                    elif key == 'p':
                        if self._media_browser.prev_file():
                            self._logger.info(f"Prev file: {self._media_browser.get_current_file().name}")
                    elif key == 'd':
                        # Delete current file
                        success, message = self._media_browser.delete_current_file()
                        if success:
                            self._capture_manager.set_feedback("Deleted!")
                            self._logger.info(f"Deleted current file")
                        else:
                            self._capture_manager.set_feedback(f"Error: {message}")
                            self._logger.warning(f"Delete failed: {message}")
                        self._feedback_overlay = None

                else:
                    # Live mode controls
                    if key == 't':
                        # Image capture - trigger the capture via flag
                        self._image_capture_flag.value = 1
                        # Note: actual save happens in capture_worker
                        self._logger.info("Capturing image...")
                        
                        # Trigger capture feedback
                        self._capture_manager.set_feedback("Saved!")
                        self._feedback_overlay = None

                    elif key == 'v':
                        # Toggle video recording
                        if self._is_recording:
                            # Stop recording
                            self._video_flag.value = 2
                            self._is_recording = False
                            self._logger.info("Video recording stopped")
                            self._capture_manager.set_feedback("Video Saved!")
                            self._feedback_overlay = None
                        else:
                            # Start recording
                            self._video_flag.value = 1
                            self._is_recording = True
                            self._recording_start_time = time.time()
                            self._logger.info("Recording started...")

                    elif key == 'f':
                        # Cycle through filters
                        current = self._filter_index.value
                        self._filter_index.value = (current + 1) % len(self._filter_names)
                        filter_name = self._filter_names[self._filter_index.value]
                        self._logger.info(f"Filter: {filter_name}")
                        self._filter_feedback_timer = time.time()
                        self._filter_overlay = None

                # Render based on current mode
                if self._view_mode:
                    # View mode: display media browser
                    frame_image = self._render_media_browser()
                    if frame_image is None:
                        # If no files, show "no files" message
                        display_size = self._display_manager.size
                        frame_image = self._display_manager.draw_no_files_message(
                            display_size[0], display_size[1]
                        )
                else:
                    # Live mode: display camera feed
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

                    # Handle filter name overlay (shows for 2 seconds after change)
                    if self._view_mode is False and (time.time() - self._filter_feedback_timer < 2.0):
                        if self._filter_overlay is None:
                            overlay_img = Image.new('RGBA', frame_image.size, (0, 0, 0, 80))
                            draw_f = ImageDraw.Draw(overlay_img)
                            f_name = self._filter_names[self._filter_index.value]
                            draw_f.text((5, 35), f"FILTER: {f_name}", fill=(255, 200, 0, 255))
                            self._filter_overlay = overlay_img

                        frame_image = Image.alpha_composite(
                            frame_image.convert('RGBA'), self._filter_overlay
                        ).convert('RGB')
                    else:
                        self._filter_overlay = None

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
                    if self._view_mode:
                        # View mode status
                        file_info = self._media_browser.get_file_info()
                        if file_info:
                            status = f"VIEW MODE | File {file_info['index']}/{file_info['total']} | {file_info['filename']}"
                        else:
                            status = "VIEW MODE | No files found"
                    else:
                        # Live mode status
                        avg_time = sum(self._frame_times) / len(self._frame_times) if self._frame_times else 1
                        fps = 1.0 / avg_time if avg_time > 0 else 0
                        
                        status = f"LIVE | FPS: {fps:.1f} | Captures: {self._capture_count.value}"
                        skipped = self._display_manager.skipped_frames
                        if skipped > 0:
                            status += f" | Skipped: {skipped}"
                        if self._is_recording:
                            rec_duration = int(time.time() - self._recording_start_time)
                            status += f" | REC: {rec_duration}s"
                    
                    print(status)
                    if not self._view_mode:
                        self._display_manager.reset_skipped_frames()
                    self._last_fps_print = now

        except Exception as e:
            self._logger.error(f"Fatal error: {e}")
            self.show_error("Fatal Error")
        finally:
            # Stop video if recording
            if self._is_recording:
                self._video_flag.value = 2
            
            self.stop_workers()
            self.cleanup()
            # Clean up media browser (if initialized)
            if self._media_browser:
                self._media_browser.cleanup()

    def _render_media_browser(self) -> Optional[Image.Image]:
        """Render media browser view with full-screen images.

        Returns:
            PIL Image with browser UI, or None if no files
        """
        if not self._media_browser.has_files():
            return None

        # Get thumbnail (now full-screen size)
        thumbnail = self._media_browser.get_thumbnail()
        if thumbnail is None:
            return None

        # Get file info
        file_info = self._media_browser.get_file_info()
        if file_info is None:
            return None

        # Create background image (black)
        display_size = self._display_manager.size
        image = Image.new('RGB', display_size, (0, 0, 0))

        # Paste full-screen thumbnail at (0, 0) - no centering needed
        image.paste(thumbnail, (0, 0))

        # Draw browser overlay with filename, index, etc.
        image = self._display_manager.draw_browser_overlay(
            image=image,
            filename=file_info['filename'],
            index=file_info['index'],
            total=file_info['total'],
            file_type=file_info['type'],
        )

        return image

    def cleanup(self) -> None:
        """Clean up resources."""
        self._logger.info("Cleaning up...")
        self._display_manager.cleanup()
        self._logger.info(f"Total captures: {self._capture_count.value}")
        self._logger.info(f"Saved to: {self._config.save_directory}")
        self._logger.info("Done.")


def main() -> None:
    """Main entry point."""
    config = Config()
    app = CameraTFTApp(config)
    app.run()


if __name__ == "__main__":
    main()