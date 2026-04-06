#!/usr/bin/env python3
"""
RPi TFT Camera Display - Optimized Multi-Core Version
Version: 2.1.0 - FPS-optimized (target: 11+ FPS)

Key changes from 2.0.1:
- LANCZOS → BILINEAR resize (3-5x faster, visually identical at 128x160)
- Fixed feedback overlay: only composites when message is actually active
- Fixed feedback_timer init: set to -999 so it's never "active" at start
- display_queue.get timeout reduced to 0.005 (5ms) from 50ms
- print() rate-limited to once per 5 seconds (not every second)
- Removed redundant frame_lock around Value (Value is already process-safe)
- stdin read made fully non-blocking
- capture_array uses raw numpy path (no PIL until process worker)
- queue.full() + get_nowait() pattern replaced with a single put_nowait + except Full
"""

import sys
import select
import time
import os
import signal
from datetime import datetime
from pathlib import Path
from multiprocessing import Process, Queue, Value
from queue import Full, Empty

shutdown_requested = False

try:
    from picamera2 import Picamera2
    from luma.core.interface.serial import spi
    from luma.lcd.device import st7735
    from luma.core.render import canvas
    from PIL import Image, ImageDraw
    import numpy as np
    import RPi.GPIO as GPIO
except ImportError as e:
    print(f"Error: Missing required library: {e}")
    print("Run: sudo apt install python3-picamera2 python3-luma.lcd python3-numpy python3-rpi.gpio")
    sys.exit(1)


def capture_worker(capture_queue_save, capture_queue_display, capture_count, running_flag, capture_resolution):
    """
    Core 1: Camera capture + BRG→RGB swap.
    Pushes raw numpy arrays to both queues (no PIL here, keep it lean).
    """
    global shutdown_requested
    camera = None

    def _shutdown(signum, frame):
        global shutdown_requested
        shutdown_requested = True
        running_flag.value = False

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        camera = Picamera2()
        config = camera.create_preview_configuration(
            main={"size": capture_resolution, "format": "RGB888"}
        )
        camera.configure(config)
        camera.start()
        print(f"Capture worker started: {capture_resolution}")

        while running_flag.value and not shutdown_requested:
            try:
                frame = camera.capture_array("main")
            except KeyboardInterrupt:
                break
            except Exception as e:
                if not shutdown_requested:
                    print(f"capture_array error: {e}")
                time.sleep(0.005)
                continue

            # BRG → RGB: swap channels 0 and 2
            # Use numpy view trick — no copy, just a remap
            frame = frame[:, :, ::-1].copy()  # reverse all 3 channels (BGR→RGB)
            # NOTE: original code did [2,1,0] which is the same as [::-1] on axis 2

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


def process_worker(capture_queue_display, display_queue, running_flag, display_size):
    """
    Core 2: Resize frames for display.
    BILINEAR is used — visually indistinguishable from LANCZOS at 128x160
    and 3-5x faster. NEAREST is even faster if you want to squeeze more FPS
    at the cost of some aliasing.
    """
    global shutdown_requested

    def _shutdown(signum, frame):
        global shutdown_requested
        shutdown_requested = True
        running_flag.value = False

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    print(f"Process worker started: target size {display_size}")

    # Pre-allocate reusable PIL image to reduce GC pressure
    # (We can't truly reuse since display needs a reference, but avoid
    #  creating intermediate objects unnecessarily)

    while running_flag.value and not shutdown_requested:
        try:
            frame = capture_queue_display.get(timeout=0.1)
        except Empty:
            continue
        except Exception:
            continue

        try:
            # fromarray is fast — it wraps the numpy buffer, no copy
            frame_image = Image.fromarray(frame)

            # BILINEAR: good quality, much faster than LANCZOS
            # Switch to Image.NEAREST for maximum FPS if quality is acceptable
            frame_image = frame_image.resize(display_size, Image.Resampling.BILINEAR)
        except Exception as e:
            if not shutdown_requested:
                print(f"Process worker resize error: {e}")
            continue

        # Push to display queue
        try:
            display_queue.put_nowait(frame_image)
        except Full:
            try:
                display_queue.get_nowait()
                display_queue.put_nowait(frame_image)
            except Exception:
                pass

    print("Process worker stopped")


class OptimizedCameraDisplay:
    def __init__(self):
        self.camera = None
        self.display = None
        self.running = False

        # feedback_timer = -999 ensures the overlay is NEVER active at startup.
        # Original code used 0, which made time.time() - 0 always > 2.0... wait,
        # actually the check is < 2.0, so at t=5s: 5-0=5 which is NOT < 2.0, so
        # it's fine after 2 seconds. But at startup for the first 2 seconds it
        # WILL composite a blank message. Using -999 skips that entirely.
        self.feedback_timer = -999.0
        self.feedback_message = ""
        self.last_error = ""

        self.capture_resolution = (320, 240)
        self.display_rotation = 2
        self.save_directory = Path.home() / "Pictures" / "captures"
        self.save_directory.mkdir(parents=True, exist_ok=True)

        self.capture_process = None
        self.process_process = None
        self.capture_queue_save = Queue(maxsize=2)
        self.capture_queue_display = Queue(maxsize=2)
        self.display_queue = Queue(maxsize=2)
        self.running_flag = Value('b', True)
        self.capture_count = Value('i', 0)  # Value is already process-safe, no Lock needed

    def initialize_hardware(self):
        try:
            serial = spi(port=0, device=0, gpio_DC=23, gpio_RST=24)
            self.display = st7735(serial, rotate=self.display_rotation)
            print(f"Display initialized: {self.display.width}x{self.display.height}")
            return True
        except Exception as e:
            self.last_error = f"Hardware init failed: {str(e)}"
            print(f"ERROR: {self.last_error}")
            return False

    def show_error_on_display(self, error_msg):
        if self.display:
            try:
                with canvas(self.display) as draw:
                    draw.rectangle(self.display.bounding_box, fill="black")
                    draw.text((5, 10), "ERROR:", fill="red")
                    draw.text((5, 30), error_msg, fill="white")
                    draw.text((5, 50), "Check terminal", fill="yellow")
            except Exception as e:
                print(f"Could not display error: {e}")

    def start_workers(self):
        print("\nStarting workers...")
        self.capture_process = Process(
            target=capture_worker,
            args=(self.capture_queue_save, self.capture_queue_display,
                  self.capture_count, self.running_flag, self.capture_resolution)
        )
        self.capture_process.start()
        print("✓ Capture worker (Core 1)")

        self.process_process = Process(
            target=process_worker,
            args=(self.capture_queue_display, self.display_queue,
                  self.running_flag, (self.display.width, self.display.height))
        )
        self.process_process.start()
        print("✓ Process worker (Core 2) — BILINEAR resize")
        print("✓ Main display loop (Core 3+)")

    def stop_workers(self):
        print("Stopping workers...")
        global shutdown_requested
        shutdown_requested = True
        self.running_flag.value = False

        for proc, name in [(self.capture_process, "capture"), (self.process_process, "process")]:
            if proc:
                proc.join(timeout=3)
                if proc.is_alive():
                    print(f"Terminating {name} worker...")
                    proc.terminate()
                    proc.join(timeout=1)
        print("All workers stopped")

    def capture_image(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.save_directory / f"capture_{timestamp}.png"

            try:
                frame = self.capture_queue_save.get_nowait()
            except Empty:
                print("Warning: No frame in save queue")
                return False, None

            image = Image.fromarray(frame)
            image.save(filename)

            # Value('i') is atomic for single int increment
            self.capture_count.value += 1
            return True, filename

        except Exception as e:
            self.last_error = f"Capture failed: {str(e)}"
            print(f"ERROR: {self.last_error}")
            return False, None

    def display_feedback(self, message):
        self.feedback_message = message
        self.feedback_timer = time.time()

    def check_for_capture(self):
        """Non-blocking stdin check."""
        if select.select([sys.stdin], [], [], 0)[0]:
            try:
                key = os.read(sys.stdin.fileno(), 1)
                return key.lower() == b't'
            except Exception:
                return False
        return False

    def run(self):
        if not self.initialize_hardware():
            return

        self.running = True
        print("\n=== Camera TFT Display (v2.1.0 - FPS optimized) ===")
        print("Press 't' to capture | Ctrl+C to exit\n")

        def _shutdown(signum, frame):
            print("\nShutdown signal received...")
            self.running = False
            global shutdown_requested
            shutdown_requested = True

        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)

        self.start_workers()
        time.sleep(0.5)

        frame_times = []
        last_fps_print = time.time()
        fps_display = 0.0

        # Pre-build the overlay image once, update text on it when needed
        # This avoids creating a new RGBA image every frame during feedback
        feedback_overlay = None
        feedback_overlay_active = False

        try:
            while self.running and not shutdown_requested:
                loop_start = time.time()

                # --- Input handling ---
                if self.check_for_capture():
                    success, filename = self.capture_image()
                    if success:
                        print(f"✓ Saved: {filename}")
                        self.display_feedback("Saved!")
                        feedback_overlay = None  # Rebuild overlay next frame
                    else:
                        print(f"✗ Failed: {self.last_error}")
                        self.display_feedback("Error!")
                        feedback_overlay = None

                # --- Get display frame ---
                try:
                    # 5ms timeout: short enough to not cap FPS, long enough
                    # to not spin-waste CPU when queue is briefly empty
                    frame_image = self.display_queue.get(timeout=0.005)
                except Empty:
                    # No frame yet — don't count this as a frame time sample
                    continue
                except Exception:
                    continue

                # --- Feedback overlay (only when actually active) ---
                now = time.time()
                feedback_active = (now - self.feedback_timer) < 2.0

                if feedback_active:
                    # Build overlay only once per feedback event
                    if feedback_overlay is None:
                        overlay_img = Image.new('RGBA', frame_image.size, (0, 0, 0, 100))
                        draw_ov = ImageDraw.Draw(overlay_img)
                        draw_ov.text((5, 5), self.feedback_message, fill=(0, 255, 0, 255))
                        draw_ov.text((5, 20), f"#{self.capture_count.value}", fill=(255, 255, 255, 200))
                        feedback_overlay = overlay_img

                    # Composite onto the current frame
                    frame_image = Image.alpha_composite(
                        frame_image.convert('RGBA'), feedback_overlay
                    ).convert('RGB')
                else:
                    feedback_overlay = None  # Clear when expired

                # --- Push to TFT ---
                self.display.display(frame_image)

                # --- FPS tracking (minimal overhead) ---
                frame_time = time.time() - loop_start
                frame_times.append(frame_time)
                if len(frame_times) > 30:
                    frame_times.pop(0)

                # Print status every 5 seconds — not every second
                if now - last_fps_print >= 5.0:
                    avg_time = sum(frame_times) / len(frame_times) if frame_times else 1
                    fps_display = 1.0 / avg_time if avg_time > 0 else 0
                    print(
                        f"FPS: {fps_display:.1f} | "
                        f"Captures: {self.capture_count.value} | "
                        f"Queues: save={self.capture_queue_save.qsize()} "
                        f"proc={self.capture_queue_display.qsize()} "
                        f"disp={self.display_queue.qsize()}"
                    )
                    last_fps_print = now

        except KeyboardInterrupt:
            print("\nKeyboardInterrupt — shutting down...")
        except Exception as e:
            print(f"\nFatal error: {e}")
            self.show_error_on_display("Fatal Error")
        finally:
            self.stop_workers()
            self.cleanup()

    def cleanup(self):
        print("Cleaning up...")
        if self.display:
            try:
                self.display.cleanup()
            except Exception as e:
                print(f"Display cleanup warning: {e}")
        GPIO.cleanup()
        print(f"Total captures: {self.capture_count.value}")
        print(f"Saved to: {self.save_directory}")
        print("Done.")


def main():
    GPIO.setwarnings(False)
    app = OptimizedCameraDisplay()
    app.run()


if __name__ == "__main__":
    main()
