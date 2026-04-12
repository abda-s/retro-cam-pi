"""Overlay rendering helpers for camera UI."""

import time
from typing import Tuple

from PIL import Image, ImageDraw


def _draw_scanlines(draw: ImageDraw.ImageDraw, width: int, height: int, alpha: int = 28) -> None:
    """Draw subtle CRT-like scanlines."""
    for y in range(0, height, 3):
        draw.line([(0, y), (width, y)], fill=(20, 12, 6, alpha), width=1)


def _draw_retro_panel(
    draw: ImageDraw.ImageDraw,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    border: Tuple[int, int, int, int],
    fill: Tuple[int, int, int, int],
) -> None:
    """Draw a rounded retro-style panel."""
    draw.rounded_rectangle([(x0, y0), (x1, y1)], radius=5, fill=fill, outline=border, width=2)
    draw.line([(x0 + 2, y0 + 3), (x1 - 2, y0 + 3)], fill=(255, 255, 255, 40), width=1)


def create_video_overlay(frame_size: Tuple[int, int], duration: float) -> Image.Image:
    """Create lightweight retro recording indicator overlay."""
    _width, _height = frame_size
    overlay_img = Image.new("RGBA", frame_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay_img)

    # Simple top-left HUD: no box, just marker + text.
    if int(time.time() * 2) % 2 == 0:
        draw.ellipse([(6, 6), (14, 14)], fill=(255, 70, 35, 255), outline=(255, 200, 120, 220))

    # Tiny shadow gives a CRT-like glow without heavy UI.
    draw.text((19, 4), "REC", fill=(40, 10, 0, 180))
    draw.text((18, 3), "REC", fill=(255, 170, 90, 255))

    mins = int(duration) // 60
    secs = int(duration) % 60
    timer_text = f"{mins:02d}:{secs:02d}"
    draw.text((18, 16), timer_text, fill=(40, 10, 0, 180))
    draw.text((17, 15), timer_text, fill=(255, 236, 190, 245))

    return overlay_img


def create_feedback_overlay(frame_size: Tuple[int, int], message: str, count: int) -> Image.Image:
    """Create retro feedback overlay with total media counter."""
    width, height = frame_size
    overlay_img = Image.new("RGBA", frame_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay_img)

    _draw_scanlines(draw, width, height, alpha=24)
    panel_w = min(width - 6, 124)
    _draw_retro_panel(
        draw,
        3,
        3,
        3 + panel_w,
        36,
        border=(80, 220, 200, 220),
        fill=(4, 20, 22, 165),
    )

    draw.text((8, 8), message, fill=(150, 255, 240, 255))
    draw.text((8, 22), f"MEDIA: {count}", fill=(210, 255, 250, 235))
    return overlay_img


def create_filter_overlay(frame_size: Tuple[int, int], filter_name: str) -> Image.Image:
    """Create retro filter name overlay."""
    width, height = frame_size
    overlay_img = Image.new("RGBA", frame_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay_img)

    y0 = max(4, height - 26)
    y1 = min(height - 3, y0 + 20)
    _draw_retro_panel(
        draw,
        3,
        y0,
        min(width - 4, 154),
        y1,
        border=(255, 188, 76, 220),
        fill=(28, 16, 2, 170),
    )
    draw.text((8, y0 + 5), f"FILTER // {filter_name}", fill=(255, 222, 130, 255))
    return overlay_img
