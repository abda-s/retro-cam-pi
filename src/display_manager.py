"""Display manager for rpi-tft-camera.

Handles ST7735 TFT display initialization, rendering, and cleanup.
"""

from typing import Tuple, Optional
from pathlib import Path
import threading
import time

try:
    from luma.core.interface.serial import spi
    from luma.lcd.device import st7735
    from luma.core.render import canvas
    from PIL import Image
except ImportError as e:
    raise ImportError(f"Missing library: {e}. Run: sudo apt install python3-luma.lcd")

try:
    import RPi.GPIO as GPIO
except ImportError:
    raise ImportError("RPi.GPIO not installed. Run: sudo apt install python3-rpi.gpio")


class DisplayManager:
    """Manages ST7735 TFT display operations."""

    def __init__(
        self,
        spi_port: int = 0,
        spi_device: int = 0,
        gpio_dc: int = 23,
        gpio_rst: int = 24,
        rotation: int = 2,
        spi_speed_hz: int = 40_000_000,
    ) -> None:
        """Initialize display manager.

        Args:
            spi_port: SPI port number (0 or 1)
            spi_device: SPI device number (0 or 1)
            gpio_dc: GPIO pin for Data/Command
            gpio_rst: GPIO pin for Reset
            rotation: Display rotation (0=0°, 1=90°, 2=180°, 3=270°)
            spi_speed_hz: SPI bus speed in Hz
        """
        self._display: Optional[st7735] = None
        self._spi_port = spi_port
        self._spi_device = spi_device
        self._gpio_dc = gpio_dc
        self._gpio_rst = gpio_rst
        self._rotation = rotation
        self._spi_speed_hz = spi_speed_hz
        self._width: int = 0
        self._height: int = 0
        
        # Frame buffering to prevent tearing
        self._display_busy = False
        self._display_lock = threading.Lock()
        self._skipped_frames = 0

    @property
    def width(self) -> int:
        """Get display width in pixels."""
        return self._width

    @property
    def height(self) -> int:
        """Get display height in pixels."""
        return self._height

    @property
    def size(self) -> Tuple[int, int]:
        """Get display size as (width, height)."""
        return (self._width, self._height)
    
    @property
    def skipped_frames(self) -> int:
        """Get count of skipped frames (due to display busy)."""
        return self._skipped_frames
    
    def reset_skipped_frames(self) -> None:
        """Reset the skipped frames counter."""
        with self._display_lock:
            self._skipped_frames = 0
    def initialize(self) -> bool:
        """Initialize the ST7735 display.

        Tries high-speed SPI (40 MHz) first, falls back to 8 MHz if needed.

        Returns:
            True if initialization successful, False otherwise
        """
        # Try 40 MHz first
        display = self._try_initialize(self._spi_speed_hz)
        if display is not None:
            self._display = display
            self._width = display.width
            self._height = display.height
            print(f"Display initialized: {self._width}x{self._height} @ {self._spi_speed_hz // 1_000_000} MHz SPI")
            return True

        # Fall back to 8 MHz
        print(f"40 MHz SPI failed, trying 8 MHz fallback...")
        display = self._try_initialize(8_000_000)
        if display is not None:
            self._display = display
            self._width = display.width
            self._height = display.height
            self._spi_speed_hz = 8_000_000
            print(f"Display initialized: {self._width}x{self._height} @ 8 MHz SPI (fallback)")
            return True

        return False

    def _try_initialize(self, speed_hz: int) -> Optional[st7735]:
        """Try to initialize display at given speed.

        Args:
            speed_hz: SPI speed in Hz

        Returns:
            st7735 device if successful, None otherwise
        """
        try:
            serial = spi(
                port=self._spi_port,
                device=self._spi_device,
                gpio_DC=self._gpio_dc,
                gpio_RST=self._gpio_rst,
                bus_speed_hz=speed_hz
            )
            return st7735(serial, rotate=self._rotation)
        except Exception:
            return None

    def display_frame(self, image: Image.Image) -> None:
        """Display a PIL Image on the TFT with frame buffering to prevent tearing.

        Args:
            image: PIL Image to display
            
        Note:
            If display is currently busy, frame will be skipped to prevent tearing.
            Skipped frames are counted and can be retrieved via skipped_frames property.
        """
        if self._display is None:
            return
        
        # Check if display is busy, skip frame if so (prevents tearing)
        with self._display_lock:
            if self._display_busy:
                self._skipped_frames += 1
                return
            self._display_busy = True
        
        try:
            # Display the frame (blocking call - waits for SPI transfer to complete)
            self._display.display(image)
        finally:
            # Always clear busy flag, even if display failed
            with self._display_lock:
                self._display_busy = False

    def show_error(self, error_msg: str) -> None:
        """Show error message on display.

        Args:
            error_msg: Error message to display
        """
        if self._display is None:
            return

        try:
            with canvas(self._display) as draw:
                draw.rectangle(self._display.bounding_box, fill="black")
                draw.text((5, 10), "ERROR:", fill="red")
                draw.text((5, 30), error_msg, fill="white")
                draw.text((5, 50), "Check terminal", fill="yellow")
        except Exception as e:
            print(f"Could not display error: {e}")

    def show_message(self, message: str, duration: float = 2.0) -> None:
        """Show a message overlay on the display.

        Args:
            message: Message to display
            duration: How long to show message (seconds)
        """
        if self._display is None:
            return

        try:
            with canvas(self._display) as draw:
                draw.rectangle(self._display.bounding_box, fill="black")
                draw.text((10, 60), message, fill="green")
        except Exception:
            pass

    def cleanup(self) -> None:
        """Clean up display resources."""
        if self._display is not None:
            try:
                self._display.cleanup()
            except Exception as e:
                print(f"Display cleanup warning: {e}")
            self._display = None

        try:
            GPIO.cleanup()
        except Exception:
            pass