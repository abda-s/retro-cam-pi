#!/bin/bash
# Install dependencies for RPi TFT Camera Display

set -e

echo "Installing Python dependencies..."

# Install Picamera2 and related libraries
apt install -y \
    python3-picamera2 \
    python3-luma.lcd \
    python3-luma.core \
    python3-spidev \
    python3-rpi.gpio \
    python3-pil \
    python3-numpy \
    python3-av \
    python3-libcamera \
    python3-jsonschema \
    python3-libarchive-c \
    python3-openexr \
    python3-pidng \
    python3-piexif \
    python3-prctl \
    python3-simplejpeg \
    python3-tqdm \
    python3-videodev2 \
    python3-kms++

echo "Dependencies installed successfully!"
