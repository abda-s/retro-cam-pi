"""rpi-tft-camera - Raspberry Pi TFT Camera Display

Modular package for displaying live camera feed on 128x160 TFT LCD.

Modules:
    - camera_worker: Picamera2 capture process
    - process_worker: cv2 resize process
    - display_manager: ST7735 display handling
    - feedback_state: transient UI messages
    - overlay_renderer: UI overlay image helpers
    - audio_service: audio detection and recording
    - video_service: ffmpeg merge helpers
    - config_manager: Configuration loading
    - main: Application orchestration
"""

from .camera_worker import capture_worker
from .process_worker import process_worker
from .display_manager import DisplayManager
from .config_manager import Config, ConfigLoader
from .filter_manager import FilterManager
from .feedback_state import FeedbackState
from .overlay_renderer import create_feedback_overlay, create_filter_overlay, create_video_overlay
from .worker_runtime import WorkerRuntime
from .frame_pipeline import capture_lores_frame, capture_and_save_main_frame
from .recording_pipeline import run_stop_pipeline
from .audio_service import AudioRecorder, detect_usb_audio_device, test_audio_device
from .video_service import ffmpeg_merge
from .video_filter_processor import apply_filter_to_video, process_video_in_background

__version__ = "4.2.8"
__all__ = [
    "capture_worker",
    "process_worker",
    "DisplayManager",
    "Config",
    "ConfigLoader",
    "FilterManager",
    "FeedbackState",
    "create_feedback_overlay",
    "create_filter_overlay",
    "create_video_overlay",
    "WorkerRuntime",
    "capture_lores_frame",
    "capture_and_save_main_frame",
    "run_stop_pipeline",
    "AudioRecorder",
    "detect_usb_audio_device",
    "test_audio_device",
    "ffmpeg_merge",
    "apply_filter_to_video",
    "process_video_in_background",
]
