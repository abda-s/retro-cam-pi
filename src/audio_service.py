"""Audio helpers for rpi-tft-camera.

Provides USB audio device detection, quick health checks, and
background audio recording via ALSA `arecord`.
"""

import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

from logger import get_logger

_logger = get_logger(__name__)


def detect_usb_audio_device() -> Optional[str]:
    """Auto-detect USB audio device from ALSA.

    Returns:
        Device string like 'hw:CARD=Device,DEV=0' or None if not found.
    """
    try:
        result = subprocess.run(
            ["arecord", "-L"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        for line in result.stdout.split("\n"):
            line = line.strip()
            if "USB" in line and "hw:" in line:
                parts = line.split()
                for part in parts:
                    if part.startswith("hw:"):
                        return part

        _logger.warning("No USB audio device found")
        return None
    except Exception as exc:
        _logger.warning(f"Auto-detect audio device failed: {exc}")
        return None


def test_audio_device(device: str) -> bool:
    """Test whether an ALSA device can record audio."""
    try:
        temp_file = Path(tempfile.gettempdir()) / "audio_test.wav"
        cmd = [
            "arecord",
            "-D",
            device,
            "-f",
            "S16_LE",
            "-r",
            "44100",
            "-c",
            "1",
            "-d",
            "1",
            str(temp_file),
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=5)

        if result.returncode == 0 and temp_file.exists() and temp_file.stat().st_size > 1000:
            temp_file.unlink()
            return True

        if temp_file.exists():
            temp_file.unlink()
        return False
    except Exception as exc:
        _logger.warning(f"Audio device test failed: {exc}")
        return False


class AudioRecorder:
    """Background audio recorder using ALSA arecord."""

    def __init__(self, device: str = "hw:2,0", sample_rate: int = 44100):
        self._device = device
        self._sample_rate = sample_rate
        self._process: Optional[subprocess.Popen] = None
        self._temp_file: Optional[Path] = None

    def start(self, output_path: Path) -> bool:
        """Start audio recording to temp WAV file."""
        self._temp_file = output_path.with_suffix(".wav")

        cmd = [
            "arecord",
            "-D",
            self._device,
            "-f",
            "S16_LE",
            "-r",
            str(self._sample_rate),
            "-c",
            "1",
            str(self._temp_file),
        ]

        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        _logger.debug(f"Audio recording started: {cmd}")
        return True

    def stop(self) -> Optional[Path]:
        """Stop audio recording and return audio file path."""
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
        """Return True when recording process is active."""
        return self._process is not None and self._process.poll() is None

    def cleanup(self) -> None:
        """Remove temporary audio file if present."""
        if self._temp_file and self._temp_file.exists():
            self._temp_file.unlink()
            _logger.debug(f"Audio temp file cleaned: {self._temp_file}")
