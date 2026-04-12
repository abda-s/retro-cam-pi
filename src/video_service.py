"""Video helpers for rpi-tft-camera.

Contains ffmpeg-based post-processing utilities used by camera worker.
"""

import subprocess
import threading
import time
from pathlib import Path

from logger import get_logger

_logger = get_logger(__name__)


def ffmpeg_merge(video_path: Path, audio_path: Path, output_path: Path) -> threading.Thread:
    """Merge video and audio using ffmpeg in background."""
    video_path = video_path.resolve()
    audio_path = audio_path.resolve()
    output_path = output_path.resolve()

    if output_path.suffix != ".mp4":
        output_path = output_path.with_suffix(".mp4")

    _logger.info(f"FFmpeg: Starting merge to {output_path.name}")
    _logger.debug(f"FFmpeg: video={video_path.name}, audio={audio_path.name}")

    completion_flag = output_path.with_suffix(".complete")

    def run_ffmpeg():
        max_retries = 3
        retry_delay = 0.5

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
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-y",
                "-i",
                str(video_path),
                "-i",
                str(audio_path),
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-map",
                "0:v",
                "-map",
                "1:a",
                "-shortest",
                str(output_path),
            ]

            _logger.debug(f"FFmpeg cmd: {' '.join(cmd)}")

            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            if proc.returncode == 0:
                _logger.info(f"FFmpeg merge complete: {output_path.name}")
                completion_flag.touch()
                if video_path.exists():
                    video_path.unlink()
                    _logger.debug("FFmpeg: Deleted original video")
                if audio_path.exists():
                    audio_path.unlink()
                    _logger.debug("FFmpeg: Deleted original audio")
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

    thread = threading.Thread(target=run_ffmpeg, daemon=False)
    thread.start()
    _logger.info("FFmpeg merge thread started")
    return thread
