#!/bin/bash
# Setup script for RPi TFT Camera Display
# This script installs all dependencies and configures the system

set -e  # Exit on error

echo "==================================="
echo "RPi TFT Camera Display Setup"
echo "==================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

# Update package lists
echo "[1/5] Updating package lists..."
apt update

# Install system dependencies
echo "[2/5] Installing system dependencies..."
apt install -y python3-picamera2 python3-luma.lcd python3-luma.core python3-spidev python3-rpi.gpio python3-pil python3-numpy

# Install additional Picamera2 dependencies
echo "[3/5] Installing Picamera2 dependencies..."
apt install -y python3-av python3-libcamera python3-jsonschema python3-libarchive-c python3-openexr python3-pidng python3-piexif python3-prctl python3-simplejpeg python3-tqdm python3-videodev2 python3-kms++

# Create save directory
echo "[4/5] Creating save directory..."
mkdir -p /home/cam/Pictures/captures
chown cam:cam /home/cam/Pictures/captures

# Configure user permissions
echo "[5/5] Configuring user permissions..."
usermod -a -G spi,gpio,video cam 2>/dev/null || true

echo ""
echo "==================================="
echo "Setup Complete!"
echo "==================================="
echo ""
echo "Please logout and login again for group permissions to take effect."
echo ""
echo "Usage:"
echo "  cd ~/rpi-tft-camera/src"
echo "  python3 camera_tft_display.py"
echo ""
echo "Controls:"
echo "  Press 't' to capture image"
echo "  Press Ctrl+C to exit"
