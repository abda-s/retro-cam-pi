# Technical Reference

## System Specifications

### Hardware
- **Raspberry Pi**: 3 Model B, ARM Cortex-A53 64-bit @ 1.2GHz
- **RAM**: 1GB LPDDR2
- **Camera**: OV5647 (2592x1944, 10-bit GBRG)
- **Display**: ST7735R (128x160, RGB666, 4-wire SPI)

### Communication
- **SPI Clock**: Up to 80MHz (40MHz configured)
- **GPIO Pins**: MOSI (10), SCLK (11), CS (8), D/C (23), RST (24)

## Architecture

### Modules (16 total)
```
main.py               - Application orchestration
worker_runtime.py     - Worker processes/queues/shared flags
camera_worker.py      - Camera worker orchestration
frame_pipeline.py     - Lores/photo frame capture pipeline
recording_pipeline.py - Stop/merge/restart recording pipeline
process_worker.py     - cv2 resize for display
display_manager.py    - ST7735 display, frame buffering
overlay_renderer.py   - Overlay image rendering helpers
media_browser.py      - Browse saved files
thumbnail_cache.py    - Disk + memory thumbnail cache
filter_manager.py     - 7 retro filter effects
audio_service.py      - Audio detect/test/record helpers
video_service.py      - FFmpeg merge helper
feedback_state.py     - Short-lived feedback state
config_manager.py     - Configuration
input_manager.py      - Non-blocking key detection
logger.py             - Centralized logging
```

### Multi-Core Processing
```
Core 1: capture_worker  -> Camera + recording pipeline
Core 2: process_worker  -> cv2.resize INTER_LINEAR
Core 3+: main loop      -> PIL convert + SPI display @ 40MHz
```

### Video Processing Chain
```
stop_recording()
  └── ffmpeg_merge(video + audio) -> final .mp4
```

Video filters are intentionally disabled for recorded video (stability + speed).
Filters apply to live preview and saved images.

## Performance

| Metric | Value | Notes |
|--------|-------|-------|
| FPS | 30-35 | 40 MHz SPI |
| Memory | ~12MB | - |
| CPU | 75% | 3-4 cores |
| Display | 128x160 | Matches lores stream |

### Frame Processing (30 FPS target)
- Camera capture: 5-8ms (20%)
- YUV→RGB: 3-5ms (15%)
- Display SPI: 5-8ms (25%)
- Total: ~17-27ms/frame

## Filters

Apply to live feed and saved images (not videos):

| Index | Name | Implementation |
|-------|------|---------------|
| 0 | NONE | Return original |
| 1 | SEPIA | Sepia + fade + fine grain |
| 2 | SILVER | CLAHE B&W + contrast + grain |
| 3 | 70s FILM | Warm cast + halation + grain |
| 4 | 80s VHS | Chroma shift + scanlines |
| 5 | 80s VHS+ | Blur/bleed + jitter + scanlines + noise |
| 6 | SUPER 8 | Vignette + warm cast + flicker + grain |

## Display Rotation

Values: 0, 1, 2, 3 (0° increments)

Config in `src/config_manager.py`:
```python
self.display_rotation = 2  # Default
```

## Configuration

Key settings in `src/config_manager.py`:
- `display_resolution`: (128, 160)
- `capture_resolution`: (640, 480)
- `lores_resolution`: (128, 160) - matches display
- `spi_speed_hz`: 40_000_000
- `save_directory`: ~/Pictures/captures
- `audio_device`: hw:CARD=Device,DEV=0 (auto-detected)

## Key Dependencies

- `picamera2` - Camera capture
- `PIL/Pillow` - Image processing  
- `luma.lcd` - ST7735 driver
- `opencv-python-headless` - cv2 resize
- `ffmpeg` - Audio/video merge and video thumbnails
- `numpy` - Array operations
