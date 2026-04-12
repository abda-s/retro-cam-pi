# RPi TFT Camera Display

Display live camera feed on a 128x160 TFT LCD screen with instant image capture functionality.

## Features

- **Live Video Feed**: Real-time camera display on 128x160 TFT (30-35 FPS)
- **Instant Capture**: Press 't' to capture high-resolution PNG images
- **Video Recording**: Press 'v' to record video with audio (H264 + AAC)
- **Retro Filters**: Press 'f' to cycle through 7 vintage filters
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
2. **SEPIA** - Classic warm brown tones
3. **SILVER** - 1930s-50s high contrast B&W
4. **70s FILM** - Kodak Portra with grain
5. **80s VHS** - Simple RGB color shift
6. **80s VHS+** - Complex chromatic aberration
7. **SUPER 8** - Warm vignette + film grain

## File Storage

- **Location**: `~/Pictures/captures/`
- **Images**: `capture_YYYYMMDD_HHMMSS.png`
- **Videos**: `video_YYYYMMDD_HHMMSS.mp4`

## Troubleshooting Quick Reference

| Issue | Solution |
|-------|---------|
| No display output | Check wiring, verify SPI enabled |
| Camera not working | Run `rpicam-still -o test.jpg` |
| Key needs Enter | This is normal (line-buffered terminal) |
| Application won't stop | Press Ctrl+Z (not Ctrl+C) |

## Known Issues

- **Video Filter Muxing**: Filtering recorded videos may fail with PyAV error. Video plays but filter isn't applied. This is a known PyAV issue (not user-fixable).

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