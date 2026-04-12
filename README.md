# RPi TFT Camera Display

Display live camera feed on a 128x160 TFT LCD screen with instant image capture functionality.

## Features

- **Live Video Feed**: Real-time camera display on 128x160 TFT (30-35 FPS)
- **Instant Capture**: Press 't' to capture high-resolution PNG images
- **Video Recording**: Press 'v' to record video with audio (H264 + AAC)
- **Retro Filters**: Press 'f' to cycle through 7 film-style filters (live preview + photos)
- **View Saved Footage**: Press 'm' to browse captured media
- **Multi-Core Optimization**: Uses 3-4 Raspberry Pi cores

## Quick Start

### 1. Install Dependencies
```bash
cd ~/rpi-tft-camera
chmod +x setup.sh
sudo ./setup.sh
```

### 2. Log Out and Log In
Required for group permissions.

### 3. Run the Application
```bash
cd ~/rpi-tft-camera/src
python3 main.py
```

## Controls

| Key | Live Mode | View Mode |
|-----|-----------|-----------|
| t | Capture image | - |
| v | Start/stop video | - |
| f | Cycle filter | - |
| m | Enter view mode | Return to live |
| n | - | Next file |
| p | - | Previous file |
| d | - | Delete file |
| Ctrl+Z | Exit app | Exit app |

## Retro Filters

1. **NONE** - Original camera feed
2. **SEPIA** - Sepia with mild fade and grain
3. **SILVER** - Silver-screen B&W with grain
4. **70s FILM** - Warm stock with soft halation
5. **80s VHS** - Chroma shift + scanlines
6. **80s VHS+** - Strong VHS bleed/jitter/noise
7. **SUPER 8** - Warm vignette + flicker + grain

## File Storage

- **Location**: `~/Pictures/captures/`
- **Images**: `capture_YYYYMMDD_HHMMSS.png`
- **Videos**: `video_YYYYMMDD_HHMMSS.mp4`
- **Note**: Videos are saved unfiltered for speed/stability; filters apply to live view and captured images.

## Troubleshooting Quick Reference

| Issue | Solution |
|-------|---------|
| No display output | Check wiring, verify SPI enabled |
| Camera not working | Run `rpicam-still -o test.jpg` |
| Key needs Enter | This is normal (line-buffered terminal) |
| Application won't stop | Press Ctrl+Z (not Ctrl+C) |

## Logging

- Central logger: `src/logger.py`
- Console + file output at `~/.cache/opencode/rpi-tft-camera/app.log`
- Default level: `INFO` (set to `DEBUG` in `src/logger.py` for verbose diagnostics)

## Requirements

### Hardware
- Raspberry Pi 3 Model B (or compatible)
- Raspberry Pi Camera (OV5647)
- 1.8" TFT LCD 128x160 (ST7735R driver)

### Software
- Raspberry Pi OS (Bookworm)
- Python 3.13+
- libcamera v0.6.+
- ffmpeg (for video thumbnails)

---

**Version:** 4.2.8
