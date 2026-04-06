#!/usr/bin/env python3
"""
RPi TFT Camera Display - Live video feed on 128x160 TFT with instant capture
Author: Raspberry Pi Project
Version: 1.0.0
"""

import sys
import select
import time
import os
from datetime import datetime
from pathlib import Path

try:
    from picamera2 import Picamera2
    from luma.core.interface.serial import spi
    from luma.lcd.device import st7735
    from luma.core.render import canvas
    from PIL import Image, ImageDraw, ImageFont
    import RPi.GPIO as GPIO
except ImportError as e:
    print(f"Error: Missing required library: {e}")
    print("Run: sudo apt install python3-picamera2 python3-luma.lcd python3-rpi.gpio")
    sys.exit(1)


class CameraDisplay:
    """Manages camera capture and TFT display"""

    def __init__(self):
        self.camera = None
        self.display = None
        self.running = False
        self.capture_count = 0
        self.feedback_timer = 0
        self.feedback_message = ""
        self.last_error = ""

        # Configuration
        self.capture_resolution = (320, 240)
        self.display_rotation = 1
        self.save_directory = Path.home() / "Pictures" / "captures"
        self.save_directory.mkdir(parents=True, exist_ok=True)

    def initialize_hardware(self):
        """Initialize camera and display hardware"""
        try:
            # Initialize camera with low resolution for performance
            self.camera = Picamera2()
            config = self.camera.create_preview_configuration(
                main={"size": self.capture_resolution, "format": "RGB888"}
            )
            self.camera.configure(config)
            self.camera.start()

            # Initialize TFT display
            serial = spi(port=0, device=0, gpio_DC=23, gpio_RST=24)
            self.display = st7735(serial, rotate=self.display_rotation)

            print(f"Camera initialized: {self.capture_resolution}")
            print(f"Display initialized: {self.display.width}x{self.display.height}")
            print(f"Save directory: {self.save_directory}")

            return True

        except Exception as e:
            self.last_error = f"Hardware init failed: {str(e)}"
            self.show_error_on_display(f"Init Error")
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

    def capture_image(self):
        """Capture and save current frame with original resolution"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.save_directory / f"capture_{timestamp}.png"

            # Capture frame as numpy array
            frame = self.camera.capture_array("main")

            # Save original resolution image
            image = Image.fromarray(frame)
            image.save(filename)
            self.capture_count += 1

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
        """Main application loop"""
        if not self.initialize_hardware():
            return

        self.running = True
        print("\n=== Camera TFT Display Running ===")
        print("Press 't' to capture image")
        print("Press Ctrl+C to exit\n")

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
                        self.display_feedback(f"Saved!")
                    else:
                        print(f"✗ Capture failed: {self.last_error}")
                        self.display_feedback("Error!")

                # Capture and display frame
                try:
                    frame = self.camera.capture_array("main")
                    frame_image = Image.fromarray(frame)

                    # Resize to display resolution (stretch)
                    frame_image = frame_image.resize(
                        (self.display.width, self.display.height),
                        Image.Resampling.LANCZOS
                    )

                    # Add feedback overlay if active
                    if time.time() - self.feedback_timer < 2.0:
                        draw = ImageDraw.Draw(frame_image)
                        # Semi-transparent overlay background
                        overlay = Image.new('RGBA', frame_image.size, (0, 0, 0, 128))
                        frame_image = Image.alpha_composite(frame_image.convert('RGBA'), overlay)
                        draw = ImageDraw.Draw(frame_image)

                        # Draw feedback text
                        draw.text((5, 5), self.feedback_message, fill="lime")
                        draw.text((5, 20), str(self.capture_count), fill="white")

                    # Display on TFT
                    self.display.display(frame_image)

                except Exception as e:
                    if str(e) != self.last_error:
                        self.last_error = f"Frame error: {str(e)}"
                        print(f"WARNING: {self.last_error}")

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
                    print(f"FPS: {fps_display:.1f} | Captures: {self.capture_count}")
                    last_fps_update = current_time

        except KeyboardInterrupt:
            print("\n\n=== Shutting down gracefully ===")
        except Exception as e:
            print(f"\nERROR: Unexpected error: {e}")
            self.show_error_on_display("Fatal Error")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        print("Cleaning up resources...")

        if self.camera:
            self.camera.stop()
            print("Camera stopped")

        if self.display:
            try:
                self.display.cleanup()
                print("Display cleaned up")
            except Exception as e:
                print(f"Display cleanup warning: {e}")

        GPIO.cleanup()
        print("GPIO cleaned up")

        print(f"\nTotal images captured: {self.capture_count}")
        print(f"Images saved in: {self.save_directory}")
        print("Goodbye!")


def main():
    """Main entry point"""
    # Disable GPIO warnings
    GPIO.setwarnings(False)

    # Create and run camera display
    app = CameraDisplay()
    app.run()


if __name__ == "__main__":
    main()
