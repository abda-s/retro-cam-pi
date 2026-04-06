"""Camera worker module for rpi-tft-camera.

Uses CircularOutput2 for non-blocking video recording.
Encoder runs continuously, output switching is instant.
"""

import time
from datetime import datetime
from multiprocessing import Queue, Value
from queue import Full
from pathlib import Path
from typing import Tuple, Optional

try:
    from picamera2 import Picamera2
    from picamera2.encoders import H264Encoder
    from picamera2.outputs import CircularOutput2, PyavOutput
except ImportError:
    raise ImportError("picamera2 not installed")

import numpy as np


class CameraWorker:
    """Camera worker with dual stream support."""
    
    def __init__(
        self,
        capture_resolution: Tuple[int, int] = (640, 480),
        lores_resolution: Tuple[int, int] = (320, 240),
        save_directory: Path = None,
    ):
        self._capture_resolution = capture_resolution
        self._lores_resolution = lores_resolution
        self._save_directory = save_directory or Path.home() / "Pictures" / "captures"
        
        self._camera: Optional[Picamera2] = None
        self._encoder: Optional[H264Encoder] = None
        self._circular: Optional[CircularOutput2] = None
        self._is_recording = False
        self._current_video_file: Optional[Path] = None
        
    def start(self) -> bool:
        """Initialize camera with encoder running continuously."""
        try:
            self._camera = Picamera2()
            
            config = self._camera.create_video_configuration(
                main={"size": self._capture_resolution, "format": "RGB888"},
                lores={"size": self._lores_resolution}
            )
            self._camera.configure(config)
            
            # Create encoder that runs continuously with circular buffer
            self._encoder = H264Encoder(bitrate=3_000_000, repeat=True)
            self._circular = CircularOutput2(buffer_duration_ms=10000)  # 10 sec buffer
            self._encoder.output = self._circular
            
            # Start camera and encoder - encoder runs forever
            self._camera.start()
            self._camera.start_encoder(self._encoder)
            
            print(f"Camera started: main={self._capture_resolution}, lores={self._lores_resolution}")
            print("Encoder running continuously (CircularOutput2)")
            return True
            
        except Exception as e:
            print(f"Camera start error: {e}")
            return False
    
    def start_recording(self, filename: Path) -> bool:
        """Start video recording - instant, no blocking."""
        try:
            self._current_video_file = filename
            # Just open output - encoder already running
            output = PyavOutput(str(filename))
            self._circular.open_output(output)
            self._is_recording = True
            print(f"Recording started: {filename}")
            return True
        except Exception as e:
            print(f"Start recording error: {e}")
            return False
    
    def stop_recording(self) -> Optional[Path]:
        """Stop video recording - instant, no blocking."""
        try:
            # Just close output - encoder keeps running
            self._circular.close_output()
            self._is_recording = False
            filename = self._current_video_file
            self._current_video_file = None
            print(f"Recording stopped: {filename}")
            return filename
        except Exception as e:
            print(f"Stop recording error: {e}")
            self._is_recording = False
            return None
    
    def capture_lores_frame(self) -> Optional[np.ndarray]:
        """Capture a frame from lores stream for display."""
        if not self._camera:
            return None
            
        try:
            frame_yuv = self._camera.capture_array("lores")
            import cv2
            frame_rgb = cv2.cvtColor(frame_yuv, cv2.COLOR_YUV420p2RGB)
            frame_rgb = frame_rgb[:, :, ::-1]  # BGR to RGB
            return frame_rgb
        except Exception:
            return None
    
    def capture_and_save_main_frame(self, filename: Path) -> bool:
        """Capture a frame from main stream and save to file."""
        if not self._camera:
            return False
            
        try:
            frame = self._camera.capture_array("main")
            frame_rgb = frame[:, :, ::-1].copy()
            
            from PIL import Image
            image = Image.fromarray(frame_rgb)
            image.save(filename)
            
            print(f"Image saved: {filename}")
            return True
        except Exception as e:
            print(f"Image capture error: {e}")
            return False
    
    def stop(self):
        """Stop camera and encoder."""
        if self._camera:
            try:
                self._camera.stop_encoder()
                self._camera.stop()
            except Exception:
                pass
            self._camera = None
            self._encoder = None
            self._circular = None


def capture_worker(
    capture_queue_display: Queue,
    capture_count: Value,
    running_flag: Value,
    video_recording_flag: Value,
    image_capture_flag: Value,
    capture_resolution: Tuple[int, int],
    lores_resolution: Tuple[int, int],
    save_directory: Path,
) -> None:
    """Capture frames from camera with dual stream support."""
    camera: Optional[CameraWorker] = None
    
    try:
        camera = CameraWorker(
            capture_resolution=capture_resolution,
            lores_resolution=lores_resolution,
            save_directory=save_directory,
        )
        
        if not camera.start():
            print("Failed to start camera")
            return
            
        print(f"Capture worker started: video={capture_resolution}, display={lores_resolution}")
        
        while running_flag.value:
            # Handle video recording start
            if video_recording_flag.value == 1:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = save_directory / f"video_{timestamp}.mp4"
                camera.start_recording(filename)
                video_recording_flag.value = 0
                
            # Handle video recording stop - instant, no blocking
            elif video_recording_flag.value == 2:
                camera.stop_recording()
                video_recording_flag.value = 0
            
            # Handle image capture
            elif image_capture_flag.value == 1:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = save_directory / f"capture_{timestamp}.png"
                if camera.capture_and_save_main_frame(filename):
                    capture_count.value += 1
                    print(f"✓ Saved: {filename}")
                image_capture_flag.value = 0
            
            # Capture lores frame for display
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
        print("Capture worker stopped")
        
    except Exception as e:
        print(f"Capture worker fatal error: {e}")
    finally:
        if camera:
            camera.stop()