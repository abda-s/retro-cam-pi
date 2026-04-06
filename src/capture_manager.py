"""Capture manager for rpi-tft-camera.

Handles image capture, saving, and capture count tracking.
"""

import time
from datetime import datetime
from multiprocessing import Queue, Value
from pathlib import Path
from queue import Empty
from typing import Optional, Tuple

try:
    from PIL import Image
    import cv2
except ImportError as e:
    raise ImportError(f"Missing library: {e}")

import numpy as np


class CaptureManager:
    """Manages image capture and saving operations."""

    def __init__(
        self,
        save_directory: Path,
        capture_resolution: Tuple[int, int] = (320, 240),
        file_format: str = "PNG",
        timestamp_format: str = "%Y%m%d_%H%M%S",
        feedback_duration: float = 2.0,
    ) -> None:
        """Initialize capture manager.

        Args:
            save_directory: Directory to save captured images
            capture_resolution: Original capture resolution (width, height)
            file_format: Image file format (PNG, JPEG)
            timestamp_format: Format for timestamp in filename
            feedback_duration: How long to show feedback overlay (seconds)
        """
        self._save_directory = save_directory
        self._capture_resolution = capture_resolution
        self._file_format = file_format
        self._timestamp_format = timestamp_format
        self._feedback_duration = feedback_duration

        # Ensure save directory exists
        self._save_directory.mkdir(parents=True, exist_ok=True)

        # Feedback state
        self._feedback_message: str = ""
        self._feedback_timer: float = 0.0
        self._last_error: str = ""

    @property
    def save_directory(self) -> Path:
        """Get save directory path."""
        return self._save_directory

    @property
    def capture_resolution(self) -> Tuple[int, int]:
        """Get capture resolution."""
        return self._capture_resolution

    @property
    def last_error(self) -> str:
        """Get last error message."""
        return self._last_error

    @property
    def feedback_duration(self) -> float:
        """Get feedback duration."""
        return self._feedback_duration

    def set_feedback(self, message: str) -> None:
        """Set feedback message to display.

        Args:
            message: Feedback message
        """
        self._feedback_message = message
        self._feedback_timer = time.time()

    def is_feedback_active(self) -> bool:
        """Check if feedback overlay should be active.

        Returns:
            True if feedback is still active
        """
        return (time.time() - self._feedback_timer) < self._feedback_duration

    def reset_feedback(self) -> None:
        """Reset feedback state."""
        self._feedback_message = ""
        self._feedback_timer = 0.0

    def capture_image(
        self,
        capture_queue_save: Queue,
        capture_queue_display: Queue,
        capture_count: Value,
    ) -> Tuple[bool, Optional[Path]]:
        """Capture and save an image.

        Uses fallback strategy to ensure capture always succeeds:
        1. Try save queue first (non-blocking)
        2. Fall back to display queue
        3. Wait briefly for any frame

        Args:
            capture_queue_save: Queue with full-resolution frames for saving
            capture_queue_display: Queue with full-resolution frames for display
            capture_count: Shared counter for total captures

        Returns:
            Tuple of (success: bool, filename: Optional[Path])
        """
        try:
            timestamp = datetime.now().strftime(self._timestamp_format)
            filename = self._save_directory / f"capture_{timestamp}.{self._file_format.lower()}"

            frame: Optional[np.ndarray] = None

            # Try save queue first (non-blocking)
            try:
                frame = capture_queue_save.get_nowait()
            except Empty:
                pass

            # Fallback: try display queue (same full-res frames)
            if frame is None:
                try:
                    frame = capture_queue_display.get_nowait()
                except Empty:
                    pass

            # Last resort: wait briefly for any capture frame
            if frame is None:
                try:
                    frame = capture_queue_save.get(timeout=0.1)
                except Empty:
                    pass

            if frame is None:
                print("Warning: No frame available for capture")
                return False, None

            # If frame is from display queue (resized), upsample it
            if (frame.shape[0] != self._capture_resolution[1] or 
                frame.shape[1] != self._capture_resolution[0]):
                frame = cv2.resize(
                    frame, 
                    (self._capture_resolution[0], self._capture_resolution[1])
                )

            # Frame is already RGB after swap in capture worker
            image = Image.fromarray(frame)
            image.save(filename)

            capture_count.value += 1
            return True, filename

        except Exception as e:
            self._last_error = f"Capture failed: {str(e)}"
            print(f"ERROR: {self._last_error}")
            return False, None

    def save_frame(self, frame: np.ndarray, filename: Path) -> bool:
        """Save a frame directly to file.

        Args:
            frame: RGB numpy array
            filename: Output file path

        Returns:
            True if successful
        """
        try:
            image = Image.fromarray(frame)
            image.save(filename)
            return True
        except Exception as e:
            self._last_error = f"Save failed: {str(e)}"
            return False