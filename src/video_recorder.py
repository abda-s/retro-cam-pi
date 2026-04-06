"""Video recorder module for rpi-tft-camera.

Handles video recording with audio using Picamera2's FfmpegOutput.
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

try:
    from picamera2 import Picamera2
    from picamera2.encoders import H264Encoder
    from picamera2.outputs import FfmpegOutput
except ImportError:
    raise ImportError("picamera2 not installed. Run: sudo apt install python3-picamera2")


class VideoRecorder:
    """Manages video recording with audio."""

    def __init__(
        self,
        save_directory: Path,
        video_resolution: Tuple[int, int] = (640, 480),
        video_bitrate: int = 3_000_000,
        audio_device: str = "hw:2,0",
        audio_enabled: bool = True,
        audio_sync: float = -0.3,
        timestamp_format: str = "%Y%m%d_%H%M%S",
    ) -> None:
        """Initialize video recorder.

        Args:
            save_directory: Directory to save videos
            video_resolution: Video resolution (width, height)
            video_bitrate: Video bitrate in bps
            audio_device: ALSA audio device (e.g., "hw:2,0")
            audio_enabled: Whether to record audio
            audio_sync: Audio sync offset in seconds
            timestamp_format: Format for timestamp in filename
        """
        self._save_directory = save_directory
        self._video_resolution = video_resolution
        self._video_bitrate = video_bitrate
        self._audio_device = audio_device
        self._audio_enabled = audio_enabled
        self._audio_sync = audio_sync
        self._timestamp_format = timestamp_format

        self._picam2: Optional[Picamera2] = None
        self._encoder: Optional[H264Encoder] = None
        self._output: Optional[FfmpegOutput] = None

        self._is_recording: bool = False
        self._recording_start_time: float = 0.0
        self._current_filename: Optional[Path] = None
        self._last_error: str = ""

        # Ensure save directory exists
        self._save_directory.mkdir(parents=True, exist_ok=True)

    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._is_recording

    @property
    def recording_duration(self) -> float:
        """Get current recording duration in seconds."""
        if self._is_recording:
            return time.time() - self._recording_start_time
        return 0.0

    @property
    def current_filename(self) -> Optional[Path]:
        """Get current video filename."""
        return self._current_filename

    @property
    def last_error(self) -> str:
        """Get last error message."""
        return self._last_error

    def initialize(self, capture_resolution: Tuple[int, int] = (640, 480)) -> bool:
        """Initialize Picamera2 for video recording.

        Args:
            capture_resolution: Camera capture resolution

        Returns:
            True if initialization successful
        """
        try:
            self._picam2 = Picamera2()

            # Create video configuration
            video_config = self._picam2.create_video_configuration(
                main={"size": capture_resolution}
            )
            self._picam2.configure(video_config)

            # Create encoder with specified bitrate
            self._encoder = H264Encoder(self._video_bitrate)

            return True

        except Exception as e:
            self._last_error = f"Failed to initialize camera: {str(e)}"
            return False

    def start_recording(self) -> bool:
        """Start video recording with audio.

        Returns:
            True if recording started successfully
        """
        if self._is_recording:
            return False

        if self._picam2 is None or self._encoder is None:
            if not self.initialize():
                return False

        try:
            # Generate filename
            timestamp = datetime.now().strftime(self._timestamp_format)
            filename = self._save_directory / f"video_{timestamp}.mkv"
            self._current_filename = filename

            # Create FFmpeg output with audio
            self._output = FfmpegOutput(
                output_filename=str(filename),
                audio=self._audio_enabled,
                audio_device=self._audio_device if self._audio_enabled else "default",
                audio_sync=self._audio_sync,
            )

            # Start recording
            self._picam2.start_recording(self._encoder, self._output)

            self._is_recording = True
            self._recording_start_time = time.time()

            print(f"Recording started: {filename}")
            return True

        except Exception as e:
            self._last_error = f"Failed to start recording: {str(e)}"
            print(f"ERROR: {self._last_error}")
            return False

    def stop_recording(self) -> Tuple[bool, Optional[Path]]:
        """Stop video recording.

        Returns:
            Tuple of (success, filename)
        """
        if not self._is_recording:
            return False, None

        try:
            if self._picam2 is not None:
                self._picam2.stop_recording()

            self._is_recording = False
            duration = time.time() - self._recording_start_time

            print(f"Recording stopped: {self._current_filename} ({duration:.1f}s)")

            filename = self._current_filename
            self._current_filename = None
            self._output = None

            return True, filename

        except Exception as e:
            self._last_error = f"Failed to stop recording: {str(e)}"
            print(f"ERROR: {self._last_error}")
            self._is_recording = False
            return False, None

    def cleanup(self) -> None:
        """Clean up video recorder resources."""
        if self._is_recording:
            self.stop_recording()

        if self._picam2 is not None:
            try:
                self._picam2.close()
            except Exception:
                pass
            self._picam2 = None
            self._encoder = None
            self._output = None