"""Video recorder module for rpi-tft-camera.

Note: Video recording is now handled directly by camera_worker.py
using Picamera2's dual encoder feature. This module is deprecated.

The camera worker now:
- Uses H264Encoder for video recording (proper timing)
- Uses lores stream for TFT display
- Handles start/stop via shared flags
"""

from pathlib import Path
from typing import Optional, Tuple


class VideoRecorder:
    """Video recording is now handled by camera_worker.
    
    This class is kept for backwards compatibility but does nothing.
    """
    
    def __init__(
        self,
        save_directory: Path,
        video_resolution: Tuple[int, int] = (640, 480),
        video_fps: int = 24,
        timestamp_format: str = "%Y%m%d_%H%M%S",
    ):
        self._save_directory = save_directory
        self._enabled = False
        self._last_error = "Video recording handled by camera_worker"
        
    @property
    def is_recording(self) -> bool:
        return False
        
    @property
    def recording_duration(self) -> float:
        return 0.0
        
    @property
    def current_filename(self) -> Optional[Path]:
        return None
        
    @property
    def last_error(self) -> str:
        return self._last_error
        
    @property
    def is_enabled(self) -> bool:
        return False
        
    def initialize(self) -> bool:
        return True
        
    def start_recording(self) -> bool:
        return False
        
    def add_frame(self, frame) -> None:
        pass
        
    def stop_recording(self) -> Tuple[bool, Optional[Path]]:
        return False, None
        
    def cleanup(self) -> None:
        pass