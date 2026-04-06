"""Configuration manager for rpi-tft-camera.

Loads and provides access to all configuration settings.
"""

from pathlib import Path
from typing import Tuple, Optional
import os


class Config:
    """Configuration manager for camera and display settings."""

    def __init__(self):
        # Display settings
        self.display_resolution: Tuple[int, int] = (128, 160)
        self.display_rotation: int = 2
        self.spi_port: int = 0
        self.spi_device: int = 0
        self.gpio_dc: int = 23
        self.gpio_rst: int = 24
        self.spi_speed_hz: int = 40_000_000

        # Camera settings
        self.capture_resolution: Tuple[int, int] = (320, 240)
        self.capture_format: str = "RGB888"

        # Queue settings
        self.queue_maxsize: int = 2

        # Storage settings
        self.save_directory: Path = Path.home() / "Pictures" / "captures"
        self.file_format: str = "PNG"
        self.timestamp_format: str = "%Y%m%d_%H%M%S"

        # Feedback settings
        self.feedback_duration: float = 2.0

        # Video recording settings
        self.video_resolution: Tuple[int, int] = (640, 480)
        self.video_bitrate: int = 3_000_000  # 3 Mbps
        self.video_codec: str = "h264"
        self.video_format: str = "mkv"
        self.audio_device: str = "default"  # PulseAudio default input (USB mic)
        self.audio_enabled: bool = True
        self.audio_sync: float = -0.3  # Audio sync offset in seconds

        # Ensure save directory exists
        self.save_directory.mkdir(parents=True, exist_ok=True)

    def get_display_size(self) -> Tuple[int, int]:
        """Get display width and height."""
        return (self.display_resolution[0], self.display_resolution[1])

    def get_capture_size(self) -> Tuple[int, int]:
        """Get capture resolution."""
        return self.capture_resolution

    def get_video_size(self) -> Tuple[int, int]:
        """Get video recording resolution."""
        return self.video_resolution


class ConfigLoader:
    """Loads configuration from environment or defaults."""

    @staticmethod
    def load() -> Config:
        """Load configuration with environment variable overrides."""
        config = Config()

        # Environment variable overrides
        if capture_res := os.getenv("CAPTURE_RESOLUTION"):
            parts = capture_res.split("x")
            if len(parts) == 2:
                config.capture_resolution = (int(parts[0]), int(parts[1]))

        if rotation := os.getenv("DISPLAY_ROTATION"):
            config.display_rotation = int(rotation)

        if speed := os.getenv("SPI_SPEED"):
            config.spi_speed_hz = int(speed)

        if save_dir := os.getenv("SAVE_DIRECTORY"):
            config.save_directory = Path(save_dir)
            config.save_directory.mkdir(parents=True, exist_ok=True)

        return config