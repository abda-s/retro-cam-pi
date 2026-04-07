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
except ImportError:
    raise ImportError("picamera2 not installed")

import numpy as np

# Logger
from logger import get_logger
_logger = get_logger(__name__)


class AudioRecorder:
    """Background audio recorder using ALSA arecord."""
    
    def __init__(self, device: str = "hw:2,0", sample_rate: int = 44100):
        self._device = device
        self._sample_rate = sample_rate
        self._process: Optional[subprocess.Popen] = None
        self._temp_file: Optional[Path] = None
        self._output_path: Optional[Path] = None
    
    def start(self, output_path: Path) -> bool:
        """Start audio recording to temp WAV file."""
        self._output_path = output_path
        self._temp_file = output_path.with_suffix('.wav')
        
        cmd = [
            'arecord', '-D', self._device,
            '-f', 'S16_LE', '-r', str(self._sample_rate),
            '-c', '1', '-t', 'wav', str(self._temp_file)
        ]
        
        self._process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _logger.debug(f"Audio recording started: {self._temp_file}")
        return True
    
    def stop(self) -> Optional[Path]:
        """Stop audio recording, return path to audio file."""
        import time
        
        if self._process:
            self._process.terminate()
            self._process.wait()
            self._process = None
            time.sleep(0.2)
        
        if self._temp_file and self._temp_file.exists():
            _logger.debug(f"Audio saved: {self._temp_file}")
            return self._temp_file
        return None
    
    def is_recording(self) -> bool:
        return self._process is not None and self._process.poll() is None
    
    def cleanup(self) -> None:
        """Clean up temp audio file."""
        if self._temp_file and self._temp_file.exists():
            self._temp_file.unlink()
            _logger.debug(f"Audio temp file cleaned: {self._temp_file}")


def ffmpeg_merge(video_path: Path, audio_path: Path, output_path: Path) -> None:
    """Merge video and audio using ffmpeg in background."""
    import threading
    import time
    
    video_path = video_path.resolve()
    audio_path = audio_path.resolve()
    output_path = video_path.with_suffix('.mkv')
    
    def run_ffmpeg():
        max_retries = 3
        retry_delay = 0.5
        
        for attempt in range(max_retries):
            if attempt > 0:
                _logger.debug(f"FFmpeg retry {attempt + 1}/{max_retries}...")
                time.sleep(retry_delay)
            
            if not audio_path.exists():
                _logger.debug(f"FFmpeg: audio file missing, waiting...")
                time.sleep(1)
                if not audio_path.exists():
                    _logger.debug(f"FFmpeg merge FAILED: audio file not found")
                    return
            
            cmd = [
                'ffmpeg', '-hide_banner', '-y',
                '-i', str(video_path),
                '-i', str(audio_path),
                '-c:v', 'copy', '-c:a', 'aac',
                '-map', '0:v', '-map', '1:a',
                '-shortest',
                str(output_path)
            ]
            
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            if proc.returncode == 0:
                _logger.debug(f"FFmpeg merge complete: {output_path}")
                if audio_path.exists():
                    audio_path.unlink()
                mp4_path = video_path.with_suffix('.mp4')
                if mp4_path.exists():
                    mp4_path.unlink()
                return
            else:
                error_msg = proc.stderr.decode('utf-8', errors='replace').strip()
                error_lines = [line for line in error_msg.split('\n') if 'Error' in line or 'error' in line.lower()]
                error_str = '; '.join(error_lines) if error_lines else error_msg[:150]
                
                if attempt < max_retries - 1:
                    _logger.debug(f"FFmpeg attempt {attempt + 1} failed: {error_str}")
                    time.sleep(retry_delay)
                else:
                    _logger.debug(f"FFmpeg merge FAILED: {error_str}")
        
        if audio_path.exists():
            _logger.debug(f"WAV file kept: {audio_path}")
    
    thread = threading.Thread(target=run_ffmpeg, daemon=True)
    thread.start()
    _logger.debug(f"FFmpeg merge started: {output_path}")


class CameraWorker:
    """Camera worker with video+separate audio recording."""
    
    def __init__(
        self,
        capture_resolution: Tuple[int, int] = (640, 480),
        lores_resolution: Tuple[int, int] = (128, 160),
        save_directory: Path = None,
        audio_enabled: bool = True,
        audio_device: str = "hw:2,0",
    ):
        self._capture_resolution = capture_resolution
        self._lores_resolution = lores_resolution
        self._save_directory = save_directory or Path.home() / "Pictures" / "captures"
        self._audio_enabled = audio_enabled
        self._audio_device = audio_device
        
        self._camera: Optional[Picamera2] = None
        self._encoder: Optional[H264Encoder] = None
        self._is_recording = False
        self._current_video_file: Optional[Path] = None
        self._audio_recorder = AudioRecorder(device=audio_device)
        
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
            import subprocess
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
        import threading
        
        def stop_and_restart():
            try:
                self._camera.stop_recording()
                self._is_recording = False
                video_path = self._current_video_file
                
                audio_path = None
                if self._audio_recorder.is_recording():
                    audio_path = self._audio_recorder.stop()
                
                self._current_video_file = None
                _logger.debug(f"Recording stopped: {video_path}")
                
                self._encoder = None
                
                _logger.debug("Waiting for audio flush...")
                time.sleep(0.5)
                
                if audio_path and audio_path.exists() and video_path:
                    ffmpeg_merge(video_path, audio_path, video_path)
                
                _logger.debug("Restarting camera after recording...")
                self._camera.stop()
                self._camera.start()
                _logger.debug("Camera restarted - ready for next recording")
                
            except Exception as e:
                _logger.debug(f"Stop recording error: {e}")
                self._is_recording = False
        
        thread = threading.Thread(target=stop_and_restart, daemon=True)
        thread.start()
        
        return self._current_video_file
    
    def capture_lores_frame(self) -> Optional[np.ndarray]:
        """Capture a frame from lores stream for display."""
        if not self._camera:
            return None
            
        try:
            frame_yuv = self._camera.capture_array("lores")
            import cv2
            frame_rgb = cv2.cvtColor(frame_yuv, cv2.COLOR_YUV420p2RGB)
            frame_rgb = frame_rgb[:, :, ::-1]
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
            
            _logger.debug(f"Image saved: {filename}")
            return True
        except Exception as e:
            _logger.debug(f"Image capture error: {e}")
            return False
    
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
