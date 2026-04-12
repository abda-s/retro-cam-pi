"""rpi-tft-camera - Raspberry Pi TFT Camera Display

Modular package for displaying live camera feed on 128x160 TFT LCD.

Modules:
    - camera_worker: Picamera2 capture process
    - process_worker: cv2 resize process
    - display_manager: ST7735 display handling
    - capture_manager: Image capture/save
    - config_manager: Configuration loading
    - main: Application orchestration
"""

from .camera_worker import capture_worker
from .process_worker import process_worker
from .display_manager import DisplayManager
from .capture_manager import CaptureManager
from .config_manager import Config, ConfigLoader
from .filter_manager import FilterManager
from .video_filter_processor import apply_filter_to_video, process_video_in_background

__version__ = "4.2.8"
__all__ = [
    "capture_worker",
    "process_worker",
    "DisplayManager",
    "CaptureManager",
    "Config",
    "ConfigLoader",
    "FilterManager",
    "apply_filter_to_video",
    "process_video_in_background",
]