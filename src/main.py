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
from queue import Empty
from typing import Optional

try:
    from PIL import Image
except ImportError:
    print("Error: PIL not found")
    sys.exit(1)

# Import project modules
from display_manager import DisplayManager
from config_manager import Config
from input_manager import InputManager
from media_browser import MediaBrowser
from feedback_state import FeedbackState
from overlay_renderer import (
    create_feedback_overlay,
    create_filter_overlay,
    create_video_overlay,
)
from worker_runtime import WorkerRuntime
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

        # UI feedback manager
        self._feedback = FeedbackState(duration=config.feedback_duration)

        # Media browser (for viewing saved files)
        # NOTE: Will be initialized with actual display size AFTER display is initialized
        # See run() method where we call _init_media_browser()
        self._media_browser: MediaBrowser = None

        # View mode state (False = Live, True = View Saved)
        self._view_mode = False

        # Worker runtime (created after display init, when size is known)
        self._worker_runtime: Optional[WorkerRuntime] = None

        # Filter control names (shared index is in WorkerRuntime)
        self._filter_names = ["NONE", "SEPIA", "SILVER", "70s FILM", "80s VHS", "80s VHS+", "SUPER 8"]
        self._filter_feedback_timer = 0.0

        # Overlay state
        self._feedback_overlay = None
        self._filter_overlay = None

        # FPS tracking
        self._frame_times = []
        self._last_fps_print = 0.0
        
        # Video recording state
        self._is_recording = False
        self._recording_start_time = 0.0

    def _total_saved_media_count(self) -> int:
        """Count all saved images and videos on disk."""
        try:
            patterns = ("*.png", "*.mp4", "*.mkv")
            total = 0
            for pattern in patterns:
                total += sum(1 for _ in self._config.save_directory.glob(pattern))
            return total
        except Exception as exc:
            self._logger.warning(f"Failed to count saved media: {exc}")
            return 0

    @property
    def _runtime(self) -> WorkerRuntime:
        """Typed accessor for initialized worker runtime."""
        if self._worker_runtime is None:
            raise RuntimeError("WorkerRuntime not initialized")
        return self._worker_runtime

    def initialize(self) -> bool:
        """Initialize hardware (display)."""
        return self._display_manager.initialize()

    def _init_media_browser(self) -> None:
        """Initialize media browser with actual display size after display is initialized."""
        # Use DisplayManager's ACTUAL size (handles rotation: 160x128 or 128x160)
        actual_size = self._display_manager.size
        self._logger.info(f"MediaBrowser display size: {actual_size}")
        self._media_browser = MediaBrowser(
            save_directory=self._config.save_directory,
            display_size=actual_size,
        )

    def check_for_input(self) -> str:
        """Check for key input (non-blocking)."""
        return self._input_manager.check_for_input() or ''

    def show_error(self, message: str) -> None:
        """Show error message on display."""
        self._display_manager.show_error(message)

    def _toggle_mode(self) -> None:
        """Toggle between live mode and media browser mode."""
        self._view_mode = not self._view_mode
        self._feedback_overlay = None

        if self._view_mode:
            self._logger.info("Entering VIEW MODE")
            self._feedback.set("VIEW MODE")
            if self._media_browser.scan_directory():
                self._logger.info(f"Found {self._media_browser.file_count} files")
            else:
                self._logger.info("No files found")
            return

        self._logger.info("Returning to LIVE VIEW")
        self._feedback.set("LIVE VIEW")

    def _handle_view_mode_input(self, key: str) -> None:
        """Handle key input while browsing saved media."""
        if key == "n":
            if self._media_browser.next_file():
                current = self._media_browser.get_current_file()
                if current is not None:
                    self._logger.info(f"Next file: {current.name}")
        elif key == "p":
            if self._media_browser.prev_file():
                current = self._media_browser.get_current_file()
                if current is not None:
                    self._logger.info(f"Prev file: {current.name}")
        elif key == "d":
            success, message = self._media_browser.delete_current_file()
            if success:
                self._feedback.set("Deleted!")
                self._logger.info("Deleted current file")
            else:
                self._feedback.set(f"Error: {message}")
                self._logger.warning(f"Delete failed: {message}")
            self._feedback_overlay = None

    def _handle_live_mode_input(self, key: str) -> None:
        """Handle key input while in live camera mode."""
        if key == "t":
            self._runtime.request_image_capture()
            self._logger.info("Capturing image...")
            self._feedback.set("Saved!")
            self._feedback_overlay = None
            return

        if key == "v":
            if self._is_recording:
                self._runtime.stop_video_recording()
                self._is_recording = False
                self._logger.info("Video recording stopped")
                self._feedback.set("Video Saved!")
                self._feedback_overlay = None
            else:
                self._runtime.start_video_recording()
                self._is_recording = True
                self._recording_start_time = time.time()
                self._logger.info("Recording started...")
            return

        if key == "f":
            current = self._runtime.filter_index.value
            self._runtime.filter_index.value = (current + 1) % len(self._filter_names)
            filter_name = self._filter_names[self._runtime.filter_index.value]
            self._logger.info(f"Filter: {filter_name}")
            self._filter_feedback_timer = time.time()
            self._filter_overlay = None

    def _handle_key_input(self, key: str) -> None:
        """Route key input based on current app mode."""
        if key == "m":
            self._toggle_mode()
            return

        if self._view_mode:
            self._handle_view_mode_input(key)
            return

        self._handle_live_mode_input(key)

    def run(self) -> None:
        """Run the main application loop."""
        if not self.initialize():
            return

        # Initialize media browser AFTER display is initialized (to get actual size)
        self._init_media_browser()

        # Initialize worker runtime now that display size is known
        self._worker_runtime = WorkerRuntime(self._config, self._display_manager.size)

        self._running = True
        self._logger.info("=== Camera TFT Display (v4.2.7) ===")
        self._logger.info("Press 't' + Enter to capture | Press 'v' + Enter to start/stop video | Press 'm' + Enter to toggle view mode | Ctrl+Z to stop")

        self._runtime.start(self._logger)
        time.sleep(1.0)

        self._last_fps_print = time.time()

        try:
            while self._running:
                loop_start = time.time()

                # Handle key input
                key = self.check_for_input()

                self._handle_key_input(key)

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
                        frame_rgb = self._runtime.display_queue.get(timeout=0.005)
                    except Empty:
                        continue
                    except Exception:
                        continue

                    # Convert numpy array to PIL Image
                    frame_image = Image.fromarray(frame_rgb)

                    # Handle video recording overlay
                    if self._is_recording:
                        rec_duration = time.time() - self._recording_start_time
                        video_overlay = create_video_overlay(frame_image.size, rec_duration)
                        frame_image = Image.alpha_composite(
                            frame_image.convert('RGBA'), video_overlay
                        ).convert('RGB')
                    # Handle capture feedback overlay
                    elif self._feedback.is_active():
                        if self._feedback_overlay is None:
                            msg = self._feedback.message
                            self._feedback_overlay = create_feedback_overlay(
                                frame_image.size,
                                msg,
                                self._total_saved_media_count(),
                            )

                        frame_image = Image.alpha_composite(
                            frame_image.convert('RGBA'), self._feedback_overlay
                        ).convert('RGB')
                    else:
                        self._feedback_overlay = None

                    # Handle filter name overlay (shows for 2 seconds after change)
                    if self._view_mode is False and (time.time() - self._filter_feedback_timer < 2.0):
                        if self._filter_overlay is None:
                            f_name = self._filter_names[self._runtime.filter_index.value]
                            self._filter_overlay = create_filter_overlay(frame_image.size, f_name)

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
                        
                        status = f"LIVE | FPS: {fps:.1f} | Media: {self._total_saved_media_count()}"
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
            if self._is_recording and self._worker_runtime is not None:
                self._runtime.stop_video_recording()

            if self._worker_runtime is not None:
                self._runtime.stop(self._logger)
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
        self._logger.info(f"Total saved media: {self._total_saved_media_count()}")
        self._logger.info(f"Saved to: {self._config.save_directory}")
        self._logger.info("Done.")


def main() -> None:
    """Main entry point."""
    config = Config()
    app = CameraTFTApp(config)
    app.run()


if __name__ == "__main__":
    main()
