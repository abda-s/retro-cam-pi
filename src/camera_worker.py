"""Camera worker module for rpi-tft-camera.

Handles camera capture using Picamera2.
Runs in a separate process for parallel processing.
"""

import time
from multiprocessing import Queue, Value
from queue import Full, Empty
from typing import Tuple, Optional

try:
    from picamera2 import Picamera2
except ImportError:
    raise ImportError("picamera2 not installed. Run: sudo apt install python3-picamera2")

import numpy as np


def capture_worker(
    capture_queue_save: Queue,
    capture_queue_display: Queue,
    capture_count: Value,
    running_flag: Value,
    capture_resolution: Tuple[int, int],
) -> None:
    """Capture frames from camera and push to queues.

    This function runs in a separate process (Core 1).
    Captures RGB888 frames from Picamera2, swaps BGR to RGB,
    and pushes to save and display queues.

    Args:
        capture_queue_save: Queue for full-resolution frames (for saving)
        capture_queue_display: Queue for full-resolution frames (for display)
        capture_count: Shared counter for total captures
        running_flag: Shared flag to control worker loop
        capture_resolution: Tuple of (width, height) for capture

    Returns:
        None
    """
    camera: Optional[Picamera2] = None

    try:
        camera = Picamera2()
        config = camera.create_preview_configuration(
            main={"size": capture_resolution, "format": "RGB888"}
        )
        camera.configure(config)
        camera.start()
        print(f"Capture worker started: {capture_resolution} | format: RGB888")

        while running_flag.value:
            try:
                frame = camera.capture_array("main")
            except Exception as e:
                print(f"capture_array error: {e}")
                time.sleep(0.005)
                continue

            # BGR to RGB: swap channels 0 and 2
            # RGB888 from picamera2 is stored as BGR in memory
            frame = frame[:, :, ::-1].copy()

            # Push to save queue (drop oldest if full)
            try:
                capture_queue_save.put_nowait(frame)
            except Full:
                try:
                    capture_queue_save.get_nowait()
                    capture_queue_save.put_nowait(frame)
                except Exception:
                    pass

            # Push to display queue (drop oldest if full)
            try:
                capture_queue_display.put_nowait(frame)
            except Full:
                try:
                    capture_queue_display.get_nowait()
                    capture_queue_display.put_nowait(frame)
                except Exception:
                    pass

        camera.stop()
        print("Capture worker stopped")

    except Exception as e:
        print(f"Capture worker fatal error: {e}")
    finally:
        if camera is not None:
            try:
                camera.stop()
            except Exception:
                pass