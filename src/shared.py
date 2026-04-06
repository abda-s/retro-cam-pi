"""Shared constants and types for rpi-tft-camera."""

from multiprocessing import Queue, Value
from queue import Full, Empty
from typing import Tuple

# Display configuration
DISPLAY_RESOLUTION: Tuple[int, int] = (128, 160)
DISPLAY_ROTATION: int = 2
SPI_PORT: int = 0
SPI_DEVICE: int = 0
GPIO_DC: int = 23
GPIO_RST: int = 24

# Camera configuration
CAPTURE_RESOLUTION: Tuple[int, int] = (320, 240)
CAPTURE_FORMAT: str = "RGB888"

# SPI speed configuration
SPI_SPEED_HIGH: int = 40_000_000  # 40 MHz
SPI_SPEED_FALLBACK: int = 8_000_000  # 8 MHz

# Queue configuration
QUEUE_MAXSIZE: int = 2

# Feedback configuration
FEEDBACK_DURATION: float = 2.0

# File configuration
FILE_FORMAT: str = "PNG"
TIMESTAMP_FORMAT: str = "%Y%m%d_%H%M%S"