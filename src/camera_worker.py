"""Camera worker module for rpi-tft-camera.

Uses standard Picamera2 for video, separate arecord for audio, ffmpeg merge after.
"""

import time
import threading
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


def detect_usb_audio_device() -> Optional[str]:
    """Auto-detect USB audio device from ALSA.
    
    Returns:
        Device string like 'hw:CARD=Device,DEV=0' or None if not found
    """
    try:
        result = subprocess.run(['arecord', '-L'], 
            capture_output=True, text=True, timeout=5)
        
        for line in result.stdout.split('\n'):
            line = line.strip()
            if 'USB' in line and 'hw:' in line:
                parts = line.split()
                for part in parts:
                    if part.startswith('hw:'):
                        return part
        
        _logger.warning("No USB audio device found")
        return None
    except Exception as e:
        _logger.warning(f"Auto-detect audio device failed: {e}")
        return None


def test_audio_device(device: str) -> bool:
    """Test if audio device can record.
    
    Returns:
        True if device works, False otherwise
    """
    import tempfile
    try:
        temp_file = Path(tempfile.gettempdir()) / "audio_test.wav"
        cmd = [
            'arecord', '-D', device,
            '-f', 'S16_LE', '-r', '44100',
            '-c', '1', '-d', '1', str(temp_file)
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=5)
        
        if result.returncode == 0 and temp_file.exists() and temp_file.stat().st_size > 1000:
            temp_file.unlink()
            return True
        
        if temp_file.exists():
            temp_file.unlink()
        return False
    except Exception as e:
        _logger.warning(f"Audio device test failed: {e}")
        return False


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
            '-c', '1', str(self._temp_file)
        ]
        
        self._process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        _logger.debug(f"Audio recording started: {cmd}")
        return True
    
    def stop(self) -> Optional[Path]:
        """Stop audio recording, return path to audio file."""
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


def ffmpeg_merge(video_path: Path, audio_path: Path, output_path: Path) -> threading.Thread:
    """Merge video and audio using ffmpeg in background."""
    video_path = video_path.resolve()
    audio_path = audio_path.resolve()
    output_path = output_path.resolve()
    
    if output_path.suffix != '.mp4':
        output_path = output_path.with_suffix('.mp4')
    
    _logger.info(f"FFmpeg: Starting merge to {output_path.name}")
    _logger.debug(f"FFmpeg: video={video_path.name}, audio={audio_path.name}")
    
    completion_flag = output_path.with_suffix('.complete')
    
    def run_ffmpeg():
        max_retries = 3
        retry_delay = 0.5
        
        for attempt in range(max_retries):
            if attempt > 0:
                _logger.warning(f"FFmpeg retry {attempt + 1}/{max_retries}...")
                time.sleep(retry_delay)
            
            _logger.debug(f"FFmpeg: Checking files...")
            
            if not video_path.exists():
                _logger.error(f"FFmpeg: Video file NOT FOUND: {video_path}")
                return
            
            if not audio_path.exists():
                _logger.warning(f"FFmpeg: Audio file missing, waiting...")
                time.sleep(1)
                if not audio_path.exists():
                    _logger.error(f"FFmpeg merge FAILED: audio file not found: {audio_path}")
                    return
            
            _logger.debug(f"FFmpeg: Running ffmpeg command...")
            cmd = [
                'ffmpeg', '-hide_banner', '-y',
                '-i', str(video_path),
                '-i', str(audio_path),
                '-c:v', 'copy', '-c:a', 'aac',
                '-map', '0:v', '-map', '1:a',
                '-shortest',
                str(output_path)
            ]
            
            _logger.debug(f"FFmpeg cmd: {' '.join(cmd)}")
            
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            if proc.returncode == 0:
                _logger.info(f"FFmpeg merge complete: {output_path.name}")
                completion_flag.touch()
                if video_path.exists():
                    video_path.unlink()
                    _logger.debug(f"FFmpeg: Deleted original video")
                if audio_path.exists():
                    audio_path.unlink()
                    _logger.debug(f"FFmpeg: Deleted original audio")
                return
            else:
                error_msg = proc.stderr.decode('utf-8', errors='replace').strip()
                error_lines = [line for line in error_msg.split('\n') if 'Error' in line or 'error' in line.lower()]
                error_str = '; '.join(error_lines) if error_lines else error_msg[:300]
                _logger.error(f"FFmpeg attempt {attempt + 1} failed: {error_str}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        
        _logger.error(f"FFmpeg merge FAILED after {max_retries} attempts")
        if audio_path.exists():
            _logger.warning(f"WAV file kept: {audio_path}")
    
    thread = threading.Thread(target=run_ffmpeg, daemon=False)
    thread.start()
    _logger.info(f"FFmpeg merge thread started")
    return thread


class CameraWorker:
    """Camera worker with video+separate audio recording."""
    
    def __init__(
        self,
        capture_resolution: Tuple[int, int] = (640, 480),
        lores_resolution: Tuple[int, int] = (128, 160),
        save_directory: Path = None,
        audio_enabled: bool = True,
        audio_device: str = "hw:CARD=Device,DEV=0",
        filter_index: Value = None,
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
        
        self._camera: Optional[Picamera2] = None
        self._encoder: Optional[H264Encoder] = None
        self._is_recording = False
        self._current_video_file: Optional[Path] = None
        self._audio_recorder = AudioRecorder(device=self._audio_device)
        self._recording_filter_index = 0
    
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
            
            # Capture current filter index at recording start
            self._recording_filter_index = self._filter_index.value if self._filter_index else 0
            
            if self._audio_enabled:
                self._audio_recorder.start(filename)
            
            _logger.debug(f"Recording started: {filename}")
            return True
        except Exception as e:
            _logger.debug(f"Start recording error: {e}")
            return False
    
    def stop_recording(self) -> Optional[Path]:
        """Stop video recording, merge audio, restart camera."""
        def safe_camera_restart():
            """Safely restart camera with error handling."""
            _logger.debug("Step 1: Stopping camera recording...")
            try:
                self._camera.stop_recording()
                _logger.debug("Step 1a: stop_recording() OK")
            except Exception as e:
                _logger.warning(f"Step 1a: stop_recording error: {e}")
            
            _logger.debug("Step 2: Stopping audio recorder...")
            audio_path = None
            if self._audio_recorder.is_recording():
                try:
                    audio_path = self._audio_recorder.stop()
                    _logger.debug("Step 2a: audio stop OK")
                except Exception as e:
                    _logger.warning(f"Step 2a: audio stop error: {e}")
            
            self._is_recording = False
            video_path = self._current_video_file
            self._current_video_file = None
            _logger.debug(f"Step 3: Recording stopped: {video_path}")
            
            self._encoder = None
            
            _logger.debug("Step 4: Waiting for audio flush...")
            time.sleep(0.5)
            
            # Get filter index used during recording
            filter_index = self._recording_filter_index
            
            # Process video in background (if filter applied)
            _logger.debug(f"Step 5: Processing video with filter_index={filter_index}")
            
            ffmpeg_thread = None
            if audio_path and audio_path.exists() and video_path:
                # Merge audio with video first (output as .merged.mp4)
                temp_merged = video_path.with_suffix('.merged.mp4')
                ffmpeg_thread = ffmpeg_merge(video_path, audio_path, temp_merged)
                
                # Apply filter in background if needed
                if filter_index > 0:
                    from video_filter_processor import process_video_in_background
                    final_path = video_path.with_name(f"{video_path.stem}_filtered{video_path.suffix}")
                    _logger.debug(f"Step 5a: VideoFilter will save to {final_path}")
                    process_video_in_background(temp_merged, final_path, filter_index, delete_temp=True, ffmpeg_thread=ffmpeg_thread)
                else:
                    # No filter, rename merged to final
                    final_path = video_path.with_suffix('.mp4')
                    if temp_merged.exists():
                        temp_merged.rename(final_path)
            else:
                _logger.warning("Step 5b: No audio to merge - processing video without audio")
                # Apply filter to original video even without audio
                if filter_index > 0:
                    from video_filter_processor import process_video_in_background
                    final_path = video_path.with_name(f"{video_path.stem}_filtered{video_path.suffix}")
                    _logger.debug(f"Step 5c: VideoFilter will save to {final_path}")
                    process_video_in_background(video_path, final_path, filter_index, delete_temp=True, ffmpeg_thread=None)
                else:
                    # No filter - rename to mp4 if needed
                    final_path = video_path.with_suffix('.mp4')
                    if video_path.exists() and video_path != final_path:
                        video_path.rename(final_path)
            
            # Restart camera - this is the critical step
            _logger.debug("Step 6: Restarting camera...")
            try:
                _logger.debug("Step 6a: Calling camera.stop()...")
                self._camera.stop()
                _logger.debug("Step 6a: camera.stop() OK")
            except Exception as e:
                _logger.warning(f"Step 6a: camera.stop() error: {e}")
            
            time.sleep(0.5)
            
            try:
                _logger.debug("Step 6b: Calling camera.start()...")
                self._camera.start()
                _logger.debug("Step 6b: camera.start() OK")
            except Exception as e:
                _logger.error(f"Step 6b: camera.start() FAILED: {e}")
                _logger.error("Step 6c: Attempting camera reinitialization...")
                try:
                    self._camera = Picamera2()
                    config = self._camera.create_video_configuration(
                        main={"size": self._capture_resolution, "format": "RGB888"},
                        lores={"size": self._lores_resolution}
                    )
                    self._camera.configure(config)
                    self._camera.start()
                    _logger.debug("Step 6c: Camera reinitialized OK")
                except Exception as e2:
                    _logger.error(f"Step 6c: Camera reinit FAILED: {e2}")
                    _logger.error("Step 6c: Camera is broken - need manual restart")
                    self._camera = None
            
            _logger.debug("Step 7: Camera restart complete - ready for next recording")
        
        thread = threading.Thread(target=safe_camera_restart, daemon=False)
        thread.start()
        _logger.debug("Camera restart thread started")
        
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
            if self._filter_index is not None and self._filter_index.value > 0:
                from filter_manager import FilterManager
                frame_rgb = FilterManager.apply_filter(frame_rgb, self._filter_index.value)
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
            
            if self._filter_index is not None and self._filter_index.value > 0:
                from filter_manager import FilterManager
                frame_rgb = FilterManager.apply_filter(frame_rgb, self._filter_index.value)
            
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
    filter_index: Value = None,
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