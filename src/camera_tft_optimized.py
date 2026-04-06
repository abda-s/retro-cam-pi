#!/usr/bin/env python3
"""
RPi TFT Camera Display - Optimized Multi-Core Version with Separate Capture Queue
- Multi-core processing for 3-4 Raspberry Pi cores
- 180° display rotation
- BRG to RGB color correction
- Separate capture queues: Queue A (320x240 for saving), Queue B (128x160 for display)
Author: Raspberry Pi Project
Version: 2.0.1 (Multi-Core with Separate Capture Queue)
"""

import sys
import select
import time
import os
import signal
from datetime import datetime
from pathlib import Path
from multiprocessing import Process, Queue, Value, Lock

# Global signal handler for clean shutdown
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
    Worker Process 1: Continuous camera capture with color swap
    Sends frames to BOTH queues: full-res for saving, resized for display
    Runs on Core 1 - handles camera I/O and color correction
    """
    global shutdown_requested
    camera = None
    
    def signal_handler(signum, frame):
        """Handle shutdown signals"""
        global shutdown_requested
        shutdown_requested = True
        running_flag.value = False
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
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
                # Check for shutdown frequently
                if shutdown_requested:
                    break
                
                # Capture frame as numpy array with interrupt handling
                try:
                    frame = camera.capture_array("main")
                except KeyboardInterrupt:
                    print("Capture interrupted during capture_array")
                    break
                
                # Fix color issue: swap R and B channels (BRG -> RGB)
                # OV5647 camera uses SGBRG10 pattern, need to swap channels
                frame = frame[:, :, [2, 1, 0]]  # Swap R and B channels
                
                # Put full-resolution frame in save queue
                try:
                    if not capture_queue_save.full():
                        capture_queue_save.put_nowait(frame)
                    else:
                        # Queue full, drop oldest frame
                        try:
                            capture_queue_save.get_nowait()
                            capture_queue_save.put_nowait(frame)
                        except:
                            pass
                except:
                    # Queue operation failed, probably shutting down
                    break
                
                # Put full-resolution frame in display queue for processing
                try:
                    if not capture_queue_display.full():
                        capture_queue_display.put_nowait(frame)
                    else:
                        # Queue full, drop oldest frame
                        try:
                            capture_queue_display.get_nowait()
                            capture_queue_display.put_nowait(frame)
                        except:
                            pass
                except:
                    # Queue operation failed, probably shutting down
                    break
                        
            except Exception as e:
                if not shutdown_requested:
                    print(f"Capture worker error: {e}")
                time.sleep(0.01)
                
        camera.stop()
        print("Capture worker stopped")
        
    except Exception as e:
        print(f"Capture worker fatal error: {e}")
    finally:
        if camera is not None:
            try:
                camera.stop()
            except:
                pass


def process_worker(capture_queue_display, display_queue, running_flag, display_size):
    """
    Worker Process 2: Image processing (PIL conversion + resize)
    Takes full-res frames from capture queue and produces display-ready frames
    Runs on Core 2 - handles CPU-intensive image processing
    """
    global shutdown_requested
    
    def signal_handler(signum, frame):
        """Handle shutdown signals"""
        global shutdown_requested
        shutdown_requested = True
        running_flag.value = False
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        print(f"Process worker started: {display_size}")
        
        while running_flag.value and not shutdown_requested:
            try:
                # Check for shutdown frequently
                if shutdown_requested:
                    break
                
                # Get full-res frame from capture queue (with timeout to allow graceful exit)
                try:
                    frame = capture_queue_display.get(timeout=0.1)
                except:
                    continue
                
                # Convert numpy array to PIL Image with interrupt handling
                try:
                    frame_image = Image.fromarray(frame)
                except KeyboardInterrupt:
                    print("Process interrupted during PIL conversion")
                    break
                
                # Resize to display resolution (stretch) with interrupt handling
                try:
                    frame_image = frame_image.resize(
                        display_size,
                        Image.Resampling.LANCZOS
                    )
                except KeyboardInterrupt:
                    print("Process interrupted during resize")
                    break
                
                # Put processed frame in display queue
                try:
                    if not display_queue.full():
                        display_queue.put_nowait(frame_image)
                    else:
                        # Queue full, drop oldest frame
                        try:
                            display_queue.get_nowait()
                            display_queue.put_nowait(frame_image)
                        except:
                            pass
                except:
                    # Queue operation failed, probably shutting down
                    break
                        
            except Exception as e:
                if not shutdown_requested:
                    print(f"Process worker error: {e}")
                time.sleep(0.01)
                
        print("Process worker stopped")
        
    except Exception as e:
        print(f"Process worker fatal error: {e}")


class OptimizedCameraDisplay:
    """
    Main Display Controller - Handles TFT display, image saving, and user input
    Runs on Core 3+ - manages display I/O, file I/O, and application state
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
        self.display_rotation = 2  # 180° rotation (upside down from normal)
        self.save_directory = Path.home() / "Pictures" / "captures"
        self.save_directory.mkdir(parents=True, exist_ok=True)

        # Multi-core setup - Option 3: Separate Capture Queues
        self.capture_process = None
        self.process_process = None
        self.capture_queue_save = Queue(maxsize=2)  # Full-res frames for saving (2 frames = ~460KB each)
        self.capture_queue_display = Queue(maxsize=2)  # Full-res frames for display processing (2 frames = ~460KB each)
        self.display_queue = Queue(maxsize=2)  # Resized frames for display (2 frames = ~62KB each)
        self.running_flag = Value('b', True)
        self.capture_count = Value('i', 0)
        self.frame_lock = Lock()  # Protect shared operations

    def initialize_hardware(self):
        """Initialize TFT display hardware"""
        try:
            # Initialize TFT display
            serial = spi(port=0, device=0, gpio_DC=23, gpio_RST=24)
            self.display = st7735(serial, rotate=self.display_rotation)

            print(f"Display initialized: {self.display.width}x{self.display.height}")
            print(f"Display rotation: {self.display_rotation} (180°)")
            print(f"Save directory: {self.save_directory}")
            print(f"Capture resolution: {self.capture_resolution} (full-res for saving)")

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
        print("\nStarting multi-core workers (Option 3: Separate Capture Queues)...")
        
        # Start capture worker (Core 1)
        self.capture_process = Process(
            target=capture_worker,
            args=(self.capture_queue_save, self.capture_queue_display, self.capture_count, 
                   self.running_flag, self.capture_resolution)
        )
        self.capture_process.start()
        print("✓ Capture worker started (Core 1)")
        print("  → Output: Queue A (320x240 for saving) + Queue B (320x240 for display processing)")

        # Start processing worker (Core 2)
        self.process_process = Process(
            target=process_worker,
            args=(self.capture_queue_display, self.display_queue, self.running_flag,
                   (self.display.width, self.display.height))
        )
        self.process_process.start()
        print("✓ Process worker started (Core 2)")
        print("  → Output: Queue C (128x160 for display)")

        # Main process handles display and UI (Core 3+)
        print("✓ Display controller running (Core 3+)")
        print("\nQueue Architecture:")
        print("  Capture Worker → [Queue A: Full-Res] → Main Process (Saving)")
        print("  Capture Worker → [Queue B: Full-Res] → Process Worker → [Queue C: Resized] → Main Process (Display)")

    def stop_workers(self):
        """Stop all worker processes"""
        print("Stopping workers...")
        global shutdown_requested
        shutdown_requested = True
        
        # Set running flag to False
        self.running_flag.value = False
        
        # Wait for processes to finish (with timeout)
        if self.capture_process:
            try:
                self.capture_process.join(timeout=3)
                if self.capture_process.is_alive():
                    print("Terminating capture worker...")
                    self.capture_process.terminate()
                    self.capture_process.join(timeout=1)
                else:
                    print("Capture worker stopped")
            except Exception as e:
                print(f"Error stopping capture worker: {e}")

        if self.process_process:
            try:
                self.process_process.join(timeout=3)
                if self.process_process.is_alive():
                    print("Terminating process worker...")
                    self.process_process.terminate()
                    self.process_process.join(timeout=1)
                else:
                    print("Process worker stopped")
            except Exception as e:
                print(f"Error stopping process worker: {e}")
        
        print("All workers stopped")

    def capture_image(self):
        """
        Capture and save current frame with full original resolution
        Gets frame from Queue A (capture_queue_save) which contains 320x240 frames
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.save_directory / f"capture_{timestamp}.png"

            # Get full-resolution frame from save queue
            if not self.capture_queue_save.empty():
                frame = self.capture_queue_save.get()
                
                # Convert to PIL Image and save
                image = Image.fromarray(frame)
                image.save(filename)
                
                with self.frame_lock:
                    self.capture_count.value += 1
                
                return True, filename
            else:
                # No frame available
                print("Warning: No frame available for capture (Queue A empty)")
                return False, None

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
        """Main application loop - Display controller with saving"""
        if not self.initialize_hardware():
            return

        self.running = True
        print("\n=== Camera TFT Display Running (Multi-Core with Separate Capture Queues) ===")
        print("Press 't' to capture image (saves full 320x240 resolution)")
        print("Press Ctrl+C to exit\n")
        print("Performance: Using 3-4 cores")
        print("Memory Usage: ~12MB (3 queues with 2 frames each)\n")

        # Set up signal handler for main process
        def signal_handler(signum, frame):
            """Handle shutdown signals"""
            print("\n\nShutdown signal received...")
            self.running = False
            global shutdown_requested
            shutdown_requested = True
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start worker processes
        self.start_workers()
        
        # Wait a moment for workers to start
        time.sleep(0.5)

        frame_times = []
        last_fps_update = time.time()
        fps_display = 0
        queue_monitor_update = time.time()

        try:
            while self.running and not shutdown_requested:
                loop_start = time.time()

                # Check for capture trigger (gets frame from Queue A)
                if self.check_for_capture():
                    success, filename = self.capture_image()
                    if success:
                        print(f"✓ Image saved: {filename}")
                        self.display_feedback("Saved!")
                    else:
                        print(f"✗ Capture failed: {self.last_error}")
                        self.display_feedback("Error!")

                # Get processed frame and display (from Queue C)
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
                    
                    # Monitor queue sizes
                    current_time = time.time()
                    if current_time - queue_monitor_update >= 5.0:
                        print(f"FPS: {fps_display:.1f} | Captures: {self.capture_count.value}")
                        print(f"Queue Sizes: Save={self.capture_queue_save.qsize()} DisplayProc={self.capture_queue_display.qsize()} Display={self.display_queue.qsize()}")
                        queue_monitor_update = current_time
                    else:
                        print(f"FPS: {fps_display:.1f} | Captures: {self.capture_count.value}")
                    
                    last_fps_update = current_time

        except KeyboardInterrupt:
            print("\n\nKeyboardInterrupt - Shutting down gracefully ===")
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
