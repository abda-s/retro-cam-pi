"""Filter manager for rpi-tft-camera.

Applies retro/analog filter effects to frames using OpenCV.
"""

import cv2
import numpy as np
from typing import Tuple


FILTER_NAMES = [
    "NONE",
    "SEPIA",
    "SILVER",
    "70s FILM",
    "80s VHS",
    "80s VHS+",
    "SUPER 8"
]

FILTER_COUNT = len(FILTER_NAMES)


class FilterManager:
    """Applies retro filters to video frames."""

    @staticmethod
    def apply_filter(frame: np.ndarray, filter_index: int) -> np.ndarray:
        """Apply filter to BGR frame.

        Args:
            frame: BGR numpy array (from camera)
            filter_index: Index of filter to apply (0-N)

        Returns:
            Modified frame with filter applied
        """
        if filter_index == 0 or filter_index >= FILTER_COUNT:
            return frame

        if filter_index == 1:
            return FilterManager._apply_sepia(frame)
        elif filter_index == 2:
            return FilterManager._apply_silver_screen(frame)
        elif filter_index == 3:
            return FilterManager._apply_70s_film(frame)
        elif filter_index == 4:
            return FilterManager._apply_vhs_simple(frame)
        elif filter_index == 5:
            return FilterManager._apply_vhs_complex(frame)
        elif filter_index == 6:
            return FilterManager._apply_super8(frame)

        return frame

    @staticmethod
    def get_filter_name(filter_index: int) -> str:
        """Get display name for filter index."""
        if 0 <= filter_index < FILTER_COUNT:
            return FILTER_NAMES[filter_index]
        return "NONE"

    @staticmethod
    def cycle_filter(current_index: int) -> int:
        """Get next filter index."""
        return (current_index + 1) % FILTER_COUNT

    @staticmethod
    def _apply_sepia(frame: np.ndarray) -> np.ndarray:
        """Apply sepia tone with mild fade and grain."""
        result = frame.astype(np.float32)
        sepia_kernel = np.array(
            [
                [0.272, 0.534, 0.131],
                [0.349, 0.686, 0.168],
                [0.393, 0.769, 0.189],
            ],
            dtype=np.float32,
        )
        result = cv2.transform(result, sepia_kernel)
        faded = cv2.addWeighted(result, 0.9, np.full_like(result, 18), 0.1, 0)
        noise = np.random.normal(0, 5, frame.shape).astype(np.float32)
        return np.clip(faded + noise, 0, 255).astype(np.uint8)

    @staticmethod
    def _apply_silver_screen(frame: np.ndarray) -> np.ndarray:
        """Apply classic silver-screen B&W with film grain."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        gray = cv2.GaussianBlur(gray, (0, 0), 0.6)
        gray = cv2.convertScaleAbs(gray, alpha=1.15, beta=5)
        result = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR).astype(np.float32)
        grain = np.random.normal(0, 6, frame.shape).astype(np.float32)
        return np.clip(result + grain, 0, 255).astype(np.uint8)

    @staticmethod
    def _apply_70s_film(frame: np.ndarray) -> np.ndarray:
        """Apply 70s Kodak-like warm stock with gentle halation."""
        result = frame.astype(np.float32)
        result[:, :, 2] *= 1.12
        result[:, :, 1] *= 1.06
        result[:, :, 0] *= 0.9
        glow = cv2.GaussianBlur(result, (0, 0), 1.1)
        result = cv2.addWeighted(result, 0.86, glow, 0.14, 0)
        result = cv2.convertScaleAbs(result, alpha=1.02, beta=4).astype(np.float32)
        result = np.clip(result, 0, 255)
        noise = np.random.normal(0, 10, frame.shape).astype(np.float32)
        result = np.clip(result + noise, 0, 255)
        return result.astype(np.uint8)

    @staticmethod
    def _apply_vhs_simple(frame: np.ndarray) -> np.ndarray:
        """Apply light VHS effect with chroma shift and scanlines."""
        b, g, r = cv2.split(frame)
        r_shifted = np.roll(r, 2, axis=1)
        b_shifted = np.roll(b, -2, axis=1)
        result = cv2.merge([b_shifted, g, r_shifted])
        result = np.clip(result.astype(np.float32) * 0.94, 0, 255)
        scan = np.ones((frame.shape[0], 1, 1), dtype=np.float32)
        scan[::2] *= 0.92
        result *= scan
        result = np.clip(result, 0, 255).astype(np.uint8)
        return result

    @staticmethod
    def _apply_vhs_complex(frame: np.ndarray) -> np.ndarray:
        """Apply stronger VHS effect: bleed, jitter, scanlines, noise."""
        b, g, r = cv2.split(frame)
        r_blur = cv2.GaussianBlur(r, (5, 5), 0)
        b_blur = cv2.GaussianBlur(b, (5, 5), 0)
        r_shifted = np.roll(r_blur, 4, axis=1)
        b_shifted = np.roll(b_blur, -4, axis=1)
        result = cv2.merge([b_shifted, g, r_shifted])
        if np.random.rand() < 0.15:
            result = np.roll(result, 1, axis=0)
        gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
        gray_3ch = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        result = cv2.addWeighted(result, 0.84, gray_3ch, 0.16, 0)
        result = result.astype(np.float32)
        scan = np.ones((frame.shape[0], 1, 1), dtype=np.float32)
        scan[::2] *= 0.9
        result *= scan
        noise = np.random.normal(0, 10, frame.shape).astype(np.float32)
        result = np.clip(result.astype(np.float32) + noise, 0, 255).astype(np.uint8)
        return result

    @staticmethod
    def _apply_super8(frame: np.ndarray) -> np.ndarray:
        """Apply Super 8 look with warm cast, vignette, flicker, grain."""
        h, w = frame.shape[:2]
        center_x, center_y = w // 2, h // 2
        Y, X = np.ogrid[:h, :w]
        dist = np.sqrt((X - center_x) ** 2 + (Y - center_y) ** 2)
        max_dist = np.sqrt(center_x ** 2 + center_y ** 2)
        vignette = np.clip(1 - (dist / max_dist) * 0.72, 0, 1)
        vignette = vignette[:, :, np.newaxis]
        result = frame.astype(np.float32)
        result[:, :, 2] *= 1.22
        result[:, :, 1] *= 1.08
        result[:, :, 0] *= 0.84
        flicker = 1.0 + np.random.uniform(-0.05, 0.05)
        result *= flicker
        result = result * vignette
        noise = np.random.normal(0, 16, frame.shape).astype(np.float32)
        result = np.clip(result + noise, 0, 255)
        return result.astype(np.uint8)
