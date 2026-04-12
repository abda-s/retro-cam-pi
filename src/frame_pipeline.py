"""Frame capture and save helpers for camera worker."""

from pathlib import Path
from typing import Optional

import numpy as np


def _apply_filter_if_enabled(frame_rgb: np.ndarray, filter_value: int) -> np.ndarray:
    """Apply configured filter to an RGB frame when enabled."""
    if filter_value <= 0:
        return frame_rgb

    from filter_manager import FilterManager

    return FilterManager.apply_filter(frame_rgb, filter_value)


def capture_lores_frame(camera, filter_value: int) -> Optional[np.ndarray]:
    """Capture and process one low-resolution frame for display."""
    if camera is None:
        return None

    try:
        frame_yuv = camera.capture_array("lores")

        import cv2

        frame_rgb = cv2.cvtColor(frame_yuv, cv2.COLOR_YUV420p2RGB)
        frame_rgb = frame_rgb[:, :, ::-1]
        return _apply_filter_if_enabled(frame_rgb, filter_value)
    except Exception:
        return None


def capture_and_save_main_frame(camera, filename: Path, filter_value: int, logger) -> bool:
    """Capture one main-stream frame, apply filter, and save to disk."""
    if camera is None:
        return False

    try:
        frame = camera.capture_array("main")
        frame_rgb = frame[:, :, ::-1].copy()
        frame_rgb = _apply_filter_if_enabled(frame_rgb, filter_value)

        from PIL import Image

        Image.fromarray(frame_rgb).save(filename)
        logger.debug(f"Image saved: {filename}")
        return True
    except Exception as exc:
        logger.debug(f"Image capture error: {exc}")
        return False
