"""Camera worker module for rpi-tft-camera.

Uses standard Picamera2 for video, separate arecord for audio, ffmpeg merge after.
"""

import time
import subprocess
from datetime import datetime
from multiprocessing import Queue, Value
from queue import Full
from pathlib import Path
from typing import Tuple, Optional

try:
    from picamera2 import Picamera2
    from picamera2.encoders import H264Encoder
    from picamera2.outputs import PyavOutput
    from libcamera import Transform
except ImportError:
    raise ImportError("picamera2 not installed")

import numpy as np

# Logger
from logger import get_logger
from audio_service import AudioRecorder, detect_usb_audio_device, test_audio_device
from frame_pipeline import capture_and_save_main_frame, capture_lores_frame
from recording_pipeline import run_stop_pipeline
_logger = get_logger(__name__)


class CameraWorker:
    """Camera worker with video+separate audio recording."""
    
    def __init__(
        self,
        capture_resolution: Tuple[int, int] = (640, 480),
        lores_resolution: Tuple[int, int] = (160, 128),
        save_directory: Path = None,
        audio_enabled: bool = True,
        audio_device: str = "hw:CARD=Device,DEV=0",
        filter_index: Value = None,
        camera_rotation: int = 0,
    ):
        self._capture_resolution = capture_resolution
        self._lores_resolution = lores_resolution
        self._save_directory = save_directory or Path.home() / "Pictures" / "captures"
        self._audio_enabled = audio_enabled
        
        # Auto-detect USB audio device if not specified or invalid
        detected_device = detect_usb_audio_device()
        if detected_device:
            self._audio_device = detected_device
            _logger.debug(f"Auto-detected USB audio: {self._audio_device}")
        else:
            self._audio_device = audio_device
            _logger.warning(f"Using default audio device: {self._audio_device}")
        
        # Test audio device on init
        if audio_enabled:
            if test_audio_device(self._audio_device):
                _logger.debug(f"Audio device test passed: {self._audio_device}")
            else:
                _logger.warning(f"Audio device test FAILED: {self._audio_device} - videos will be silent")
        
        self._filter_index = filter_index
        self._camera_rotation = camera_rotation
        
        self._camera: Optional[Picamera2] = None
        self._encoder: Optional[H264Encoder] = None
        self._is_recording = False
        self._current_video_file: Optional[Path] = None
        self._audio_recorder = AudioRecorder(device=self._audio_device)
    
    def start(self) -> bool:
        """Initialize camera."""
        try:
            self._camera = Picamera2()
            
            config = self._camera.create_video_configuration(
                main={"size": self._capture_resolution, "format": "RGB888"},
                lores={"size": self._lores_resolution}
            )
            self._camera.configure(config)
            
            self._camera.start()
            
            self._encoder = None
            
            _logger.debug(f"Camera started: main={self._capture_resolution}, lores={self._lores_resolution}")
            return True
        
        except Exception as e:
            _logger.debug(f"Camera start error: {e}")
            return False
    
    def start_recording(self, filename: Path) -> bool:
        """Start video recording with separate audio."""
        try:
            subprocess.run(['amixer', '-c', '2', 'set', 'Mic', '100%'], 
                capture_output=True)
            
            self._current_video_file = filename
            
            self._encoder = H264Encoder(bitrate=3_000_000)
            output = PyavOutput(str(filename))
            
            self._camera.start_recording(self._encoder, output)
            self._is_recording = True
            
            if self._audio_enabled:
                self._audio_recorder.start(filename)
            
            _logger.debug(f"Recording started: {filename}")
            return True
        except Exception as e:
            _logger.debug(f"Start recording error: {e}")
            return False
    
    def stop_recording(self) -> Optional[Path]:
        """Stop video recording, merge audio, restart camera."""
        run_stop_pipeline(self, _logger)
        return self._current_video_file
    
    def capture_lores_frame(self) -> Optional[np.ndarray]:
        """Capture a frame from lores stream for display."""
        filter_value = self._filter_index.value if self._filter_index is not None else 0
        return capture_lores_frame(self._camera, filter_value, self._camera_rotation)
    
    def capture_and_save_main_frame(self, filename: Path) -> bool:
        """Capture a frame from main stream and save to file."""
        filter_value = self._filter_index.value if self._filter_index is not None else 0
        return capture_and_save_main_frame(self._camera, filename, filter_value, self._camera_rotation, _logger)
    
    def stop(self):
        """Stop camera and encoder."""
        if self._audio_recorder:
            self._audio_recorder.cleanup()
        if self._camera:
            try:
                if self._is_recording:
                    self._camera.stop_recording()
                self._camera.stop()
            except Exception:
                pass
        self._camera = None
        self._encoder = None


def capture_worker(
    capture_queue_display: Queue,
    capture_count: Value,
    running_flag: Value,
    video_recording_flag: Value,
    image_capture_flag: Value,
    capture_resolution: Tuple[int, int],
    lores_resolution: Tuple[int, int],
    save_directory: Path,
    audio_enabled: bool = True,
    audio_device: str = "hw:2,0",
    filter_index: Value = None,
    camera_rotation: int = 0,
) -> None:
    """Capture frames from camera with dual stream support."""
    camera: Optional[CameraWorker] = None
    
    try:
        camera = CameraWorker(
            capture_resolution=capture_resolution,
            lores_resolution=lores_resolution,
            save_directory=save_directory,
            audio_enabled=audio_enabled,
            audio_device=audio_device,
            filter_index=filter_index,
            camera_rotation=camera_rotation,
        )
        
        if not camera.start():
            _logger.debug("Failed to start camera")
            return
        
        _logger.debug(f"Capture worker started: video={capture_resolution}, display={lores_resolution}")
        
        while running_flag.value:
            if video_recording_flag.value == 1:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = save_directory / f"video_{timestamp}.mp4"
                camera.start_recording(filename)
                video_recording_flag.value = 0
            
            elif video_recording_flag.value == 2:
                camera.stop_recording()
                video_recording_flag.value = 0
            
            elif image_capture_flag.value == 1:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = save_directory / f"capture_{timestamp}.png"
                if camera.capture_and_save_main_frame(filename):
                    capture_count.value += 1
                    _logger.debug(f"✓ Saved: {filename}")
                image_capture_flag.value = 0
            
            frame = camera.capture_lores_frame()
            if frame is not None:
                try:
                    capture_queue_display.put_nowait(frame)
                except Full:
                    try:
                        capture_queue_display.get_nowait()
                        capture_queue_display.put_nowait(frame)
                    except Exception:
                        pass
            
            time.sleep(0.001)
        
        camera.stop()
        _logger.debug("Capture worker stopped")
    
    except Exception as e:
        _logger.debug(f"Capture worker fatal error: {e}")
    finally:
        if camera:
            camera.stop()
