#!/usr/bin/env python3
"""
Camera TFT Display Configuration
Central configuration for camera capture and TFT display
"""

# Hardware Configuration
DISPLAY_RESOLUTION = (128, 160)  # TFT display resolution
DISPLAY_ROTATION = 1  # 0=0°, 1=90°, 2=180°, 3=270°

# Camera Configuration
CAPTURE_RESOLUTION = (320, 240)  # Original capture resolution
CAPTURE_FORMAT = "RGB888"  # Color format
TARGET_FPS = 8  # Target frames per second

# SPI Configuration
SPI_PORT = 0  # SPI port (0 or 1)
SPI_DEVICE = 0  # SPI device (0 or 1)
GPIO_DC = 23  # Data/Command pin
GPIO_RST = 24  # Reset pin
GPIO_CS = 8  # Chip Select pin

# File Storage Configuration
SAVE_DIRECTORY = "~/Pictures/captures"  # Where to save images
FILE_FORMAT = "PNG"  # Image file format (PNG, JPEG)
TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"  # Timestamp format for filenames

# Display Configuration
FEEDBACK_DURATION = 2.0  # How long to show feedback (seconds)
OVERLAY_ALPHA = 128  # Transparency for feedback overlay (0-255)

# Performance Configuration
RESIZE_METHOD = "LANCZOS"  # Image resize method (NEAREST, LANCZOS, BILINEAR)
FRAME_BUFFER_COUNT = 1  # Number of frame buffers (keep low for memory)

# Error Handling
DISPLAY_ERRORS_ON_SCREEN = True  # Show error messages on TFT
LOG_ERRORS_TO_CONSOLE = True  # Log errors to console
DISPLAY_ERROR_DURATION = 5.0  # How long to show error messages (seconds)
