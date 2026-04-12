# RPi TFT Camera Display

Display live camera feed on a 128x160 TFT LCD screen with instant image capture functionality.

## 🎯 Features

- **Live Video Feed**: Real-time camera display on 128x160 TFT screen (30-35 FPS with multi-core)
- **Instant Capture**: Press 't' to capture high-resolution images instantly
- **Smart Storage**: Captures saved at original resolution (640x480 PNG) - full quality!
- **Visual Feedback**: On-screen confirmation when images are saved
- **Graceful Exit**: Stop application with Ctrl+Z
- **Multi-Core Optimization**: Uses 3-4 Raspberry Pi 3B cores for optimal performance
- **Optimized Display Pipeline**: Lores stream (128x160) matches display size, no resizing needed
- **Frame Buffering**: Prevents tearing artifacts during fast camera movement
- **Color Correction**: BGR to RGB conversion for correct colors
- **Display Rotation**: 180° rotation option for proper orientation
- **FPS Optimized (v4.2.0+)**: 40 MHz SPI, matched aspect ratio, ~35 FPS!
- **Video Recording**: Press 'v' to record video (H264, non-blocking with CircularOutput2)
- **Dual Stream**: Main stream (640x480) for video, Lores stream (128x160) for display
- **View Saved Footage**: Press 'm' to browse and view saved images and videos (v4.2.2+)
- **Modular Architecture**: Clean separation of concerns with 10 modules

## 📋 Requirements

### Hardware
- Raspberry Pi 3 Model B (or any Pi with camera support)
- Raspberry Pi Camera Module (OV5647 tested)
- 1.8" TFT LCD Display 128x160 with ST7735R driver
- Jumper wires for connections
- MicroSD card (16GB+ recommended)
- Power supply for Raspberry Pi

### Software
- Raspberry Pi OS (Bookworm or newer)
- Python 3.13+
- libcamera (v0.6.0+)
- Network connection (for initial setup)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd ~/rpi-tft-camera
chmod +x setup.sh
sudo ./setup.sh
```

### 2. Log Out and Log In
**Required** for group permissions to take effect.

### 3. Run the Application

```bash
cd ~/rpi-tft-camera/src
python3 main.py
```

## 🔧 Known Issues and Planned Fixes

### Issue 1: Terminal Line Buffering (Pressing 't' Requires Enter)
**Current Problem:** Terminal is in canonical (line-buffered) mode, so pressing 't' alone does nothing. User must press 't' + Enter.

**Planned Fix:** Switch to raw terminal mode during key detection
- Disable line buffering (character-by-character input)
- 't' key works immediately without Enter
- Automatically restore terminal settings after key detection

**Status:** 🔄 Not Implemented (low priority - works with Enter)
**Documentation:** See `docs/TERMINAL_RAW_MODE.md` for technical details

### Issue 2: Capture Queue Empty (Sometimes No Frame to Capture)
**Current Problem:** When user presses 't', capture_queue_save might be empty, causing capture failures.

**Planned Fix:** Use separate queue architecture to ensure reliable capture
- Worker maintains latest frame in display queue
- Main process can fall back to latest frame if needed

**Status:** ✅ Fixed in v3.0.0 (multiple fallbacks implemented)

## 🔍 Debugging Assistance

### Quick Kill During Development

**If application hangs during testing:**
```bash
# Kill all Python processes immediately
killall -9 python3

# Or kill specifically:
pkill -9 -f "camera_tft_optimized"
```

**For more debugging options, see `docs/DEBUGGING_ASSISTANCE.md`**

## 📖 Usage

### Application Options

**Standard Version (Single-Threaded):**
- File: `camera_tft_display.py`
- Performance: 8-10 FPS
- Cores used: 1 (25% utilization)
- Memory: ~6MB

**Optimized Version (Multi-Core with Separate Capture Queues):**
- File: `camera_tft_optimized.py`
- Performance: 18-22 FPS (2.2x faster!)
- Cores used: 3-4 (75% utilization)
- Memory: ~12MB
- Features: Separate capture queues for saving full-resolution images

### Controls
- **'t' key**: Capture current frame and save as PNG (320x240 full resolution)
- **'v' key**: Start/stop video recording (640x480 with audio)
- **'m' key**: Toggle between Live View and View Saved Footage mode
- **'n' key** (in View Mode): Navigate to next file
- **'p' key** (in View Mode): Navigate to previous file
- **'d' key** (in View Mode): Delete current file
- **Ctrl+Z**: Stop application

### What Happens When You Press 't' (Optimized Version)

1. Live feed continues smoothly (no pause!)
2. Current frame is captured at original resolution (320x240) from Queue A
3. Image is saved to `~/Pictures/captures/capture_YYYYMMDD_HHMMSS.png`
4. "Saved!" message appears on screen
5. Live feed continues without interruption

### What Happens When You Press 'v'

1. First press: Start video recording with audio
   - "REC" indicator appears on TFT (blinking red dot + timer)
   - Video saved to `~/Pictures/captures/video_YYYYMMDD_HHMMSS.mkv`
2. Second press: Stop recording
   - "Video Saved!" message appears on screen
   - Video file finalizes

### What Happens When You Press 'm'

1. **Enter View Mode**:
    - Live camera feed pauses
    - Application scans `~/Pictures/captures/` for images and videos
    - Files are displayed sorted by newest first
    - Image/video shown full-screen (stretched to fit 128x160)
    - Filename and file index shown (e.g., "3/10")
    - File type indicator ([IMAGE] or [VIDEO])
    - Navigation hints displayed at bottom
    - Persistent thumbnail cache is loaded from `.thumbnails/` directory

2. **Navigate in View Mode**:
    - Press 'n' to view next file
    - Press 'p' to view previous file
    - For videos: displays first frame full-screen
    - Press 'd' to delete current file (shows "Deleted!" feedback)
    - Cannot delete the last remaining file

3. **Return to Live Mode**:
    - Press 'm' again to return to live camera feed
    - Camera feed resumes immediately

### File Storage

- **Location**: `~/Pictures/captures/`
- **Images**: PNG (320x240), naming: `capture_YYYYMMDD_HHMMSS.png`
- **Videos**: MKV (640x480), naming: `video_YYYYMMDD_HHMMSS.mkv`
- **Audio**: USB mic (hw:2,0), AAC codec

### Performance Comparison

| Version | FPS | Cores | Memory | Features |
|---------|-----|--------|--------|-----------|
| Standard | 8-10 | 1 (25%) | 6MB | Basic capture |
| Optimized v2.1.x | 10-15 | 3-4 (75%) | 12MB | Multi-core, BILINEAR |
| **v3.0.0** | **25-32** | **3-4 (75%)** | **12MB** | **40 MHz SPI, cv2 resize** |
| **v4.0.0** | **25-32** | **3-4 (75%)** | **12MB** | **Modular architecture** |
| **v4.1.0** | **25-32** | **3-4 (75%)** | **12MB** | **Video recording (initial)** |
| **v4.2.0** | **25-32** | **3-4 (75%)** | **12MB** | **Dual stream, CircularOutput2** |
| **v4.2.2** | **30-35** | **3-4 (75%)** | **12MB** | **Optimized lores (128x160), Frame buffering** |
| **v4.2.3** | **30-35** | **3-4 (75%)** | **12MB** | **View saved footage mode** |
| **v4.2.4** | **30-35** | **3-4 (75%)** | **12MB** | **Full-screen images, fixed video thumbnails, fixed UI** |
| **v4.2.5** | **30-35** | **3-4 (75%)** | **12MB** | **Added .mp4 support, debug logging, video placeholder** |
| **v4.2.6** | **30-35** | **3-4 (75%)** | **12MB** | **Smart cache validation, automatic black bar fix** |
| **v4.2.7** | **30-35** | **3-4 (75%)** | **12MB** | **Delete files in view mode, persistent cache, cleaner logs** |

## 🏗️ Architecture (v4.2.2)

The application is split into 11 independent modules for maintainability:

| Module | Responsibility | Public API |
|--------|----------------|------------|
| `camera_worker.py` | Picamera2 capture, BGR→RGB swap | `capture_worker(...)` |
| `process_worker.py` | Frame passthrough for display | `process_worker(...)` |
| `display_manager.py` | ST7735 init, display, cleanup, frame buffering | `DisplayManager` class |
| `capture_manager.py` | Image save, feedback overlay | `CaptureManager` class |
| `media_browser.py` | Browse saved images and videos | `MediaBrowser` class |
| `video_recorder.py` | Video recording with audio | `VideoRecorder` class |
| `config_manager.py` | Config loading, env override | `Config` class |
| `shared.py` | Queue sizes, SPI speeds, defaults | Constants |
| `input_manager.py` | Non-blocking key detection | `InputManager` class |
| `logger.py` | Centralized logging with file & console output | `get_logger()` |
| `main.py` | Orchestration only | `main()` |

### Process Architecture

```
Core 1: capture_worker  — picamera2 RGB888, BGR→RGB swap → queues
Core 2: process_worker  — frame passthrough (no resize needed) → display_queue
Core 3+: main loop      — PIL convert + luma display @ 40 MHz
       + video_recorder — FfmpegOutput with ALSA audio input
```

## 🔧 Hardware Setup

### TFT Display Wiring

Connect your TFT display to Raspberry Pi GPIO header:

| LCD Pin | Name | Connect To | RPi Pin |
|---------|------|------------|---------|
| 1 | VCC | 3.3V Power | Pin 1 |
| 2 | GND | Ground | Pin 6 |
| 3 | RESET | GPIO 24 | Pin 18 |
| 4 | D/C or A0 | Data/Command | GPIO 23 | Pin 16 |
| 5 | SDA or DIN | SPI Data (MOSI) | GPIO 10 | Pin 19 |
| 6 | SCK or CLK | SPI Clock (SCLK) | GPIO 11 | Pin 23 |
| 7 | CS | Chip Select (CE0) | GPIO 8 | Pin 24 |
| 8 | LED | Backlight | 3.3V | Pin 1 |

**⚠️ Important Safety Notes:**
- Double-check VCC and GND connections
- Use 3.3V, NOT 5V (unless your display specifically requires 5V)
- Verify pin labels on your specific display module
- Triple-check all connections before powering on

### Camera Connection

- Connect camera module to camera ribbon cable port on Raspberry Pi
- Ensure ribbon cable is inserted fully and locked
- Camera should be detected automatically

## 📁 Project Structure

```
rpi-tft-camera/
├── README.md                      # This file
├── TECHNICAL.md                   # Detailed technical documentation
├── setup.sh                       # Main installation script
├── .gitignore                     # Git ignore patterns
├── src/
│   ├── __init__.py                # Package init
│   ├── main.py                    # Entry point (v4.0.0)
│   ├── camera_worker.py           # Capture process
│   ├── process_worker.py          # Resize process
│   ├── display_manager.py        # ST7735 display handling
│   ├── capture_manager.py        # Image capture/save
│   ├── config_manager.py         # Configuration loader
│   ├── shared.py                  # Constants and types
│   └── requirements.txt           # Python dependencies
├── config/
│   └── display_config.py          # Legacy config file
└── docs/
    ├── WIRING.md                  # Complete wiring guide
    └── TROUBLESHOOTING.md         # Common issues & solutions
```

## ⚙️ Configuration

The application uses `src/config_manager.py` for configuration (with environment variable support).

To customize, edit `src/config_manager.py` or set environment variables:

```bash
export CAPTURE_RESOLUTION=640x480
export DISPLAY_ROTATION=1
export SPI_SPEED=40000000
export SAVE_DIRECTORY=/home/cam/Pictures/captures
```

Legacy `config/display_config.py` is kept for reference but not used by v4.0.0.

## 🔍 Troubleshooting

### Application won't stop
- Use Ctrl+Z to stop (not Ctrl+C)
- Or manually: `killall python3`

### No display output
- Check wiring connections
- Verify SPI is enabled: `ls /dev/spi*`
- Check permissions: `groups cam` (should include spi, gpio)

### Camera not working
- Verify camera connection: `rpicam-still -o test.jpg`
- Check camera permissions: `groups cam` (should include video)
- Ensure libcamera is installed: `rpicam-still --list-cameras`
- Stop any other camera applications: `killall rpicam-still`

### Low performance
- Lower capture resolution in `config/display_config.py`
- Close other applications
- Check CPU usage: `top`

### High memory usage
- Check queue sizes: Monitor "Queue Sizes" output

### View mode not showing videos
- **Check file format**: Ensure videos are `.mp4` or `.mkv` format (now supported in v4.2.5)
- **Check debug output**: Terminal will show `[MediaBrowser]` messages when entering view mode
- **Verify ffmpeg installed**: `ffmpeg -version` - required for video thumbnails
- **Check file location**: Videos must be in `~/Pictures/captures/` directory

### Black bars on display
- **Debug output**: Terminal shows `[MediaBrowser] Resized to: (128, 160)` - confirms full-screen
- **Clear cache**: Restart app to rebuild thumbnail cache if issue persists

For more detailed troubleshooting, see `docs/TROUBLESHOOTING.md`.

## 📊 Performance

v3.0.0 on Raspberry Pi 3 Model B:

| Setting | Resolution | FPS | Quality | Notes |
|---------|-------------|------|---------|--------|
| Default | 320x240 → 160x128 | **25-32** | Good | **30 FPS!** |
| High | 640x480 → 160x128 | 15-20 | Better | Slower |
| Low | 160x120 → 160x128 | 30-35 | Lower | Faster |

## 🤝 Contributing

Contributions welcome! Please feel free to submit issues or pull requests.

## 📄 License

This project is provided as-is for educational and hobbyist use.

## 📞 Support

For detailed technical information, see:
- `TECHNICAL.md` - System architecture and implementation details
- `docs/WIRING.md` - Complete wiring guide
- `docs/TROUBLESHOOTING.md` - Common issues and solutions

## 🔗 Resources

- [Picamera2 Documentation](https://github.com/raspberrypi/picamera2)
- [luma.lcd Documentation](https://luma-lcd.readthedocs.io/)
- [Raspberry Pi Camera Documentation](https://www.raspberrypi.com/documentation/computers/camera.html)

## 🙏 Acknowledgments

- Picamera2 library by Raspberry Pi Foundation
- luma.lcd library by Richard Hull
- libcamera by Raspberry Pi Foundation
- ST7735 display driver integration

---

**Version:** 4.2.8
**Last Updated:** 2026-04-12

## 🎉 New in v4.2.8

### Video Processing with Filter
- **Video + audio recording**: Records video and audio separately
- **FFmpeg merge**: On stop, merges video + audio into .merged.mp4
- **Filter chaining**: Filter processing waits for ffmpeg to complete before starting
- **Background processing**: Video filter runs in background thread

#### Known Issues
- **Filter processing fails during muxing**: PyAV `[Errno 22] Invalid argument` error when writing filtered video
- **Cause**: Output stream `time_base` not properly configured
- **Fix**: Add `time_base = Fraction(1, fps)` to output stream in video_filter_processor.py
- **Status**: 🔄 Pending fix

### Code Fixes Applied
1. Fixed `camera_worker.py`: Corrected indentation issues, `ffmpeg_merge()` now returns thread
2. Fixed `video_filter_processor.py`: Changed `fps = in_stream.rate` to `fps = int(in_stream.average_rate) else 30`

### View Mode Delete Functionality
- **Delete files**: Press 'd' to delete current file while in View Mode
- **Safety**: Cannot delete the last remaining file
- **Auto-cleanup**: Removes both source file and thumbnail cache
- **Feedback**: Shows "Deleted!" message on display
- **Auto-advance**: Automatically moves to next file after delete

### View Mode Logging Improvements
- **Reduced log spam**: Removed per-frame cache logs (was 30-35 logs/sec)
- **Cleaner terminal**: Now shows only meaningful diagnostic information
- **Better focus**: Can easily see camera, recording, and video processing logs
- **Smart logging**: Kept useful logs (validation, processing, errors) while removing spam

## 🎉 New in v4.2.6

### View Saved Footage Mode Improvements
- **Smart cache validation**: Auto-detects and fixes mismatched thumbnail sizes
- **Automatic black bar fix**: Rebuilds invalid thumbnails at correct size (128x160)
- **Selective cache rebuild**: Only rebuilds thumbnails that don't match display size
- **Detailed validation logging**: Shows which thumbnails are valid or invalid

## 🎉 New in v4.2.5

### View Saved Footage Mode Improvements
- **Added .mp4 support**: Videos in .mp4 format now supported (not just .mkv)
- **Debug logging**: Extensive [MediaBrowser] output for troubleshooting
- **Video placeholder**: Falls back to "VIDEO" placeholder if thumbnail extraction fails

## 🎉 New in v4.2.4

### View Saved Footage Mode Improvements
- **Full-screen images**: Images and videos now fill entire 128x160 display
- **Fixed video thumbnails**: Video thumbnails now display correctly
- **Fixed navigation hints**: Navigation text now visible at bottom of screen
- Images stretched to fit display (full-screen coverage)

## 🎉 New in v4.2.3

### View Saved Footage Mode
- Press **'m'** to toggle between Live View and View Mode
- Browse saved images and videos directly on TFT display
- Navigate with **'n'** (next) and **'p'** (previous)
- Videos display first frame as thumbnail
- Files sorted newest first
- Shows file index, filename, and type on display
