#!/usr/bin/env python3
"""
RPi TFT Camera Display - Optimized Multi-Core Version
- Multi-core processing for 3-4 Raspberry Pi cores
- 180° display rotation
- BRG to RGB color correction
- Hybrid balanced approach for optimal performance
Author: Raspberry Pi Project
Version: 2.0.0 (Multi-Core)
"""

import sys
import select
import time
import os
from datetime import datetime
from pathlib import Path
from multiprocessing import Process, Queue, Value, Lock

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


def capture_worker(capture_queue, capture_count, running_flag, capture_resolution):
    """
    Worker Process 1: Continuous camera capture with color swap
    Runs on Core 1 - handles camera I/O and color correction
    """
    try:
        camera = Picamera2()
        config = camera.create_preview_configuration(
            main={"size": capture_resolution, "format": "RGB888"}
        )
        camera.configure(config)
        camera.start()
        
        print(f"Capture worker started: {capture_resolution}")
        
        while running_flag.value:
            try:
                # Capture frame as numpy array
                frame = camera.capture_array("main")
                
                # Fix color issue: swap R and B channels (BRG -> RGB)
                # OV5647 camera uses SGBRG10 pattern, need to swap channels
                frame = frame[:, :, [2, 1, 0]]  # Swap R and B channels
                
                # Put frame in queue for processing
                if not capture_queue.full():
                    capture_queue.put(frame)
                else:
                    # Queue full, drop oldest frame
                    try:
                        capture_queue.get_nowait()
                        capture_queue.put(frame)
                    except:
                        pass
                        
            except Exception as e:
                print(f"Capture worker error: {e}")
                time.sleep(0.01)
                
        camera.stop()
        print("Capture worker stopped")
        
    except Exception as e:
        print(f"Capture worker fatal error: {e}")


def process_worker(capture_queue, display_queue, running_flag, display_size):
    """
    Worker Process 2: Image processing (PIL conversion + resize)
    Runs on Core 2 - handles CPU-intensive image processing
    """
    try:
        print(f"Process worker started: {display_size}")
        
        while running_flag.value:
            try:
                # Get frame from capture queue (with timeout to allow graceful exit)
                try:
                    frame = capture_queue.get(timeout=0.1)
                except:
                    continue
                
                # Convert numpy array to PIL Image
                frame_image = Image.fromarray(frame)
                
                # Resize to display resolution (stretch)
                frame_image = frame_image.resize(
                    display_size,
                    Image.Resampling.LANCZOS
                )
                
                # Put processed frame in display queue
                if not display_queue.full():
                    display_queue.put(frame_image)
                else:
                    # Queue full, drop oldest frame
                    try:
                        display_queue.get_nowait()
                        display_queue.put(frame_image)
                    except:
                        pass
                        
            except Exception as e:
                print(f"Process worker error: {e}")
                time.sleep(0.01)
                
        print("Process worker stopped")
        
    except Exception as e:
        print(f"Process worker fatal error: {e}")


class OptimizedCameraDisplay:
    """
    Main Display Controller - Handles TFT display and user input
    Runs on Core 3+ - manages display I/O and application state
    """

    def __init__(self):
        self.camera = None
        self.display = None
        self.running = False
        self.feedback_timer = 0
        self.feedback_message = ""
        self.last_error = ""

        # Configuration
        self.capture_resolution = (320, 240)
        self.display_rotation = 2  # 180° rotation (upside down)
        self.save_directory = Path.home() / "Pictures" / "captures"
        self.save_directory.mkdir(parents=True, exist_ok=True)

        # Multi-core setup
        self.capture_process = None
        self.process_process = None
        self.capture_queue = Queue(maxsize=2)  # Double-buffer
        self.display_queue = Queue(maxsize=2)  # Double-buffer
        self.running_flag = Value('b', True)
        self.capture_count = Value('i', 0)

    def initialize_hardware(self):
        """Initialize TFT display hardware"""
        try:
            # Initialize TFT display
            serial = spi(port=0, device=0, gpio_DC=23, gpio_RST=24)
            self.display = st7735(serial, rotate=self.display_rotation)

            print(f"Display initialized: {self.display.width}x{self.display.height}")
            print(f"Display rotation: {self.display_rotation} (180°)")
            print(f"Save directory: {self.save_directory}")

            return True

        except Exception as e:
            self.last_error = f"Hardware init failed: {str(e)}"
            self.show_error_on_display("Init Error")
            print(f"ERROR: {self.last_error}")
            return False

    def show_error_on_display(self, error_msg):
        """Display error message on TFT screen"""
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
        """Start capture and processing worker processes"""
        print("\nStarting multi-core workers...")
        
        # Start capture worker (Core 1)
        self.capture_process = Process(
            target=capture_worker,
            args=(self.capture_queue, self.capture_count, self.running_flag, 
                   self.capture_resolution)
        )
        self.capture_process.start()
        print("✓ Capture worker started (Core 1)")

        # Start processing worker (Core 2)
        self.process_process = Process(
            target=process_worker,
            args=(self.capture_queue, self.display_queue, self.running_flag,
                   (self.display.width, self.display.height))
        )
        self.process_process.start()
        print("✓ Process worker started (Core 2)")

        # Main process handles display and UI (Core 3+)
        print("✓ Display controller running (Core 3+)")

    def stop_workers(self):
        """Stop all worker processes"""
        print("Stopping workers...")
        
        # Set running flag to False
        self.running_flag.value = False
        
        # Wait for processes to finish (with timeout)
        if self.capture_process:
            self.capture_process.join(timeout=2)
            if self.capture_process.is_alive():
                self.capture_process.terminate()
                print("Capture worker terminated")
            else:
                print("Capture worker stopped")

        if self.process_process:
            self.process_process.join(timeout=2)
            if self.process_process.is_alive():
                self.process_process.terminate()
                print("Process worker terminated")
            else:
                print("Process worker stopped")

    def capture_image(self):
        """Capture and save current frame with original resolution"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.save_directory / f"capture_{timestamp}.png"

            # Get current frame from display queue (most recent processed frame)
            if not self.display_queue.empty():
                frame_image = self.display_queue.get()
                frame_image.save(filename)
            else:
                # No frame available, can't capture
                print("Warning: No frame available for capture")
                return False, None

            self.capture_count.value += 1
            return True, filename

        except Exception as e:
            self.last_error = f"Capture failed: {str(e)}"
            print(f"ERROR: {self.last_error}")
            return False, None

    def display_feedback(self, message):
        """Display feedback overlay on live feed"""
        self.feedback_message = message
        self.feedback_timer = time.time()

    def check_for_capture(self):
        """Check if 't' key was pressed"""
        if select.select([sys.stdin], [], [], 0)[0]:
            key = sys.stdin.read(1)
            if key.lower() == 't':
                return True
        return False

    def run(self):
        """Main application loop - Display controller"""
        if not self.initialize_hardware():
            return

        self.running = True
        print("\n=== Camera TFT Display Running (Multi-Core) ===")
        print("Press 't' to capture image")
        print("Press Ctrl+C to exit\n")
        print("Performance: Using 3-4 cores\n")

        # Start worker processes
        self.start_workers()
        
        # Wait a moment for workers to start
        time.sleep(0.5)

        frame_times = []
        last_fps_update = time.time()
        fps_display = 0

        try:
            while self.running:
                loop_start = time.time()

                # Check for capture trigger
                if self.check_for_capture():
                    success, filename = self.capture_image()
                    if success:
                        print(f"✓ Image saved: {filename}")
                        self.display_feedback("Saved!")
                    else:
                        print(f"✗ Capture failed: {self.last_error}")
                        self.display_feedback("Error!")

                # Get processed frame and display
                try:
                    frame_image = self.display_queue.get(timeout=0.05)

                    # Add feedback overlay if active
                    if time.time() - self.feedback_timer < 2.0:
                        draw = ImageDraw.Draw(frame_image)
                        # Semi-transparent overlay background
                        overlay = Image.new('RGBA', frame_image.size, (0, 0, 0, 128))
                        frame_image = Image.alpha_composite(frame_image.convert('RGBA'), overlay)
                        draw = ImageDraw.Draw(frame_image)

                        # Draw feedback text
                        draw.text((5, 5), self.feedback_message, fill="lime")
                        draw.text((5, 20), str(self.capture_count.value), fill="white")

                    # Display on TFT
                    self.display.display(frame_image)

                except:
                    # No frame available yet, continue
                    pass

                # Calculate FPS
                frame_time = time.time() - loop_start
                frame_times.append(frame_time)
                if len(frame_times) > 10:
                    frame_times.pop(0)

                # Update FPS display every second
                current_time = time.time()
                if current_time - last_fps_update >= 1.0:
                    if frame_times:
                        avg_time = sum(frame_times) / len(frame_times)
                        fps_display = 1.0 / avg_time if avg_time > 0 else 0
                    print(f"FPS: {fps_display:.1f} | Captures: {self.capture_count.value} | Queue Sizes: Capture={self.capture_queue.qsize()} Display={self.display_queue.qsize()}")
                    last_fps_update = current_time

        except KeyboardInterrupt:
            print("\n\n=== Shutting down gracefully ===")
        except Exception as e:
            print(f"\nERROR: Unexpected error: {e}")
            self.show_error_on_display("Fatal Error")
        finally:
            self.stop_workers()
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        print("Cleaning up resources...")

        if self.display:
            try:
                self.display.cleanup()
                print("Display cleaned up")
            except Exception as e:
                print(f"Display cleanup warning: {e}")

        GPIO.cleanup()
        print("GPIO cleaned up")

        print(f"\nTotal images captured: {self.capture_count.value}")
        print(f"Images saved in: {self.save_directory}")
        print("Goodbye!")


def main():
    """Main entry point"""
    # Disable GPIO warnings
    GPIO.setwarnings(False)

    # Create and run optimized camera display
    app = OptimizedCameraDisplay()
    app.run()


if __name__ == "__main__":
    main()
