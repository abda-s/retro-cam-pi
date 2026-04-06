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
echo "[1/6] Updating package lists..."
apt update

# Install system dependencies
echo "[2/6] Installing system dependencies..."
apt install -y python3-picamera2 python3-luma.lcd python3-luma.core python3-spidev python3-rpi.gpio python3-pil python3-numpy

# Install OpenCV for cv2.resize (v3.0.0+)
echo "[3/6] Installing OpenCV..."
apt install -y python3-opencv

# Install FFmpeg for video encoding and merging (v4.1.0+)
echo "[3.5/6] Installing FFmpeg..."
apt install -y ffmpeg

# Install sounddevice for audio recording (v4.2.0+)
echo "[3.6/6] Installing PyAudio for audio recording..."
apt install -y portaudio19-dev python3-pyaudio

# Install additional Picamera2 dependencies
echo "[4/6] Installing Picamera2 dependencies..."
apt install -y python3-av python3-libcamera python3-jsonschema python3-libarchive-c python3-openexr python3-pidng python3-piexif python3-prtl python3-simplejpeg python3-tqdm python3-videodev2 python3-kms++

# Create save directory
echo "[5/6] Creating save directory..."
mkdir -p /home/cam/Pictures/captures
chown cam:cam /home/cam/Pictures/captures

# Configure user permissions
echo "[6/6] Configuring user permissions..."
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
echo "  python3 main.py"
echo ""
echo "Controls:"
echo "  Press 't' + Enter to capture image"
echo "  Press Ctrl+Z to stop"
