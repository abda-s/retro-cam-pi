"""Process worker module for rpi-tft-camera.

Handles frame processing (resizing) using OpenCV cv2.
Runs in a separate process for parallel processing.
"""

import time
from multiprocessing import Queue, Value
from queue import Empty
from typing import Tuple, Optional

try:
    import cv2
except ImportError:
    raise ImportError("opencv-python-headless not installed. Run: pip3 install opencv-python-headless")

import numpy as np


def process_worker(
    capture_queue_display: Queue,
    display_queue: Queue,
    running_flag: Value,
    display_size: Tuple[int, int],
) -> None:
    """Process frames: resize for display.

    This function runs in a separate process (Core 2).
    Takes full-resolution frames from capture queue,
    resizes them to display resolution using cv2.resize,
    and pushes to display queue.

    Args:
        capture_queue_display: Queue with full-resolution frames
        display_queue: Queue for resized frames (for display)
        running_flag: Shared flag to control worker loop
        display_size: Tuple of (width, height) for target display

    Returns:
        None
    """
    target_w, target_h = display_size

    print(f"Process worker started: target size {display_size} | using cv2.resize INTER_LINEAR")

    while running_flag.value:
        try:
            frame = capture_queue_display.get(timeout=0.1)
        except Empty:
            continue
        except Exception:
            continue

        try:
            # cv2.resize takes (width, height) tuple
            resized = cv2.resize(
                frame,
                (target_w, target_h),
                interpolation=cv2.INTER_LINEAR
            )
        except Exception as e:
            print(f"Process worker resize error: {e}")
            continue

        # Push resized numpy array to display queue
        try:
            display_queue.put_nowait(resized)
        except Exception:
            try:
                display_queue.get_nowait()
                display_queue.put_nowait(resized)
            except Exception:
                pass

    print("Process worker stopped")