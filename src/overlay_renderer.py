"""Overlay rendering helpers for camera UI."""

import time
from typing import Tuple

from PIL import Image, ImageDraw


def create_video_overlay(frame_size: Tuple[int, int], duration: float) -> Image.Image:
    """Create recording indicator overlay."""
    overlay_img = Image.new("RGBA", frame_size, (0, 0, 0, 100))
    draw = ImageDraw.Draw(overlay_img)

    if int(time.time() * 2) % 2 == 0:
        draw.ellipse([(5, 5), (15, 15)], fill=(255, 0, 0, 255))

    draw.text((20, 5), "REC", fill=(255, 0, 0, 255))

    mins = int(duration) // 60
    secs = int(duration) % 60
    draw.text((5, 20), f"{mins:02d}:{secs:02d}", fill=(255, 255, 255, 255))

    return overlay_img


def create_feedback_overlay(frame_size: Tuple[int, int], message: str, count: int) -> Image.Image:
    """Create capture/feedback overlay."""
    overlay_img = Image.new("RGBA", frame_size, (0, 0, 0, 100))
    draw = ImageDraw.Draw(overlay_img)
    draw.text((5, 5), message, fill=(0, 255, 0, 255))
    draw.text((5, 20), f"#{count}", fill=(255, 255, 255, 200))
    return overlay_img


def create_filter_overlay(frame_size: Tuple[int, int], filter_name: str) -> Image.Image:
    """Create filter name overlay."""
    overlay_img = Image.new("RGBA", frame_size, (0, 0, 0, 80))
    draw = ImageDraw.Draw(overlay_img)
    draw.text((5, 35), f"FILTER: {filter_name}", fill=(255, 200, 0, 255))
    return overlay_img
