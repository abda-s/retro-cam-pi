"""Video helpers for rpi-tft-camera.

Contains ffmpeg-based post-processing utilities used by camera worker.
"""

import subprocess
import threading
import time
from pathlib import Path

from logger import get_logger

_logger = get_logger(__name__)


def ffmpeg_merge(video_path: Path, audio_path: Path, output_path: Path, rotation: int = 0, on_complete: callable = None) -> threading.Thread:
    """Merge video and audio using ffmpeg in background.
    
    Args:
        video_path: Path to input video file (.mp4)
        audio_path: Path to input audio file (.wav)
        output_path: Path for output merged file (.mp4)
        rotation: Rotation to apply (0, 90, 180, 270)
        on_complete: Optional callback called when merge completes (success or failure)
                     Callback receives (success: bool, output_path: Path)
        
    Returns:
        Thread object (runs in background)
    """
    video_path = video_path.resolve()
    audio_path = audio_path.resolve()
    output_path = output_path.resolve()

    _logger.info(f"FFmpeg: Starting merge to {output_path.name}")
    _logger.debug(f"FFmpeg: video={video_path.name}, audio={audio_path.name}, rotation={rotation}")

    def run_ffmpeg():
        max_retries = 3
        retry_delay = 0.5
        success = False

        for attempt in range(max_retries):
            if attempt > 0:
                _logger.warning(f"FFmpeg retry {attempt + 1}/{max_retries}...")
                time.sleep(retry_delay)

            _logger.debug("FFmpeg: Checking files...")

            if not video_path.exists():
                _logger.error(f"FFmpeg: Video file NOT FOUND: {video_path}")
                return

            if not audio_path.exists():
                _logger.warning("FFmpeg: Audio file missing, waiting...")
                time.sleep(1)
                if not audio_path.exists():
                    _logger.error(f"FFmpeg merge FAILED: audio file not found: {audio_path}")
                    return

            _logger.debug("FFmpeg: Running ffmpeg command...")
            
            # Build ffmpeg command with optional rotation filter
            vf_filter = None
            if rotation == 90:
                vf_filter = "transpose=1"  # 90° clockwise
            elif rotation == 180:
                vf_filter = "transpose=2,transpose=2"  # 180°
            elif rotation == 270:
                vf_filter = "transpose=2"  # 90° counter-clockwise
            
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-y",
                "-i",
                str(video_path),
                "-i",
                str(audio_path),
            ]
            
            if vf_filter:
                cmd.extend(["-vf", vf_filter])
            
            cmd.extend([
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-c:a",
                "aac",
                "-map",
                "0:v",
                "-map",
                "1:a",
                "-shortest",
                str(output_path),
            ])

            _logger.debug(f"FFmpeg cmd: {' '.join(cmd)}")

            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            if proc.returncode == 0:
                _logger.info(f"FFmpeg merge complete: {output_path.name}")
                success = True
                # Cleanup original files after successful merge
                if video_path.exists():
                    try:
                        video_path.unlink()
                        _logger.debug(f"Deleted original video: {video_path.name}")
                    except Exception as exc:
                        _logger.warning(f"Failed to delete original video: {exc}")
                if audio_path.exists():
                    try:
                        audio_path.unlink()
                        _logger.debug(f"Deleted audio: {audio_path.name}")
                    except Exception as exc:
                        _logger.warning(f"Failed to delete audio: {exc}")
                
                # Call completion callback for success BEFORE returning
                _logger.debug(f"Calling completion callback: on_complete={'Yes' if on_complete else 'No'}, success={success}")
                if on_complete:
                    try:
                        on_complete(success, output_path)
                        _logger.debug("Completion callback executed successfully")
                    except Exception as exc:
                        _logger.error(f"Completion callback error: {exc}")
                
                return

            error_msg = proc.stderr.decode("utf-8", errors="replace").strip()
            error_lines = [
                line
                for line in error_msg.split("\n")
                if "Error" in line or "error" in line.lower()
            ]
            error_str = "; ".join(error_lines) if error_lines else error_msg[:300]
            _logger.error(f"FFmpeg attempt {attempt + 1} failed: {error_str}")

            if attempt < max_retries - 1:
                time.sleep(retry_delay)

        _logger.error(f"FFmpeg merge FAILED after {max_retries} attempts")
        if audio_path.exists():
            _logger.warning(f"WAV file kept: {audio_path}")
        
        # Call the completion callback if provided
        _logger.debug(f"Calling completion callback: on_complete={'Yes' if on_complete else 'No'}, success={success}")
        if on_complete:
            try:
                on_complete(success, output_path)
                _logger.debug("Completion callback executed successfully")
            except Exception as exc:
                _logger.error(f"Completion callback error: {exc}")

    thread = threading.Thread(target=run_ffmpeg, daemon=False)
    thread.start()
    _logger.info("FFmpeg merge thread started")
    return thread
