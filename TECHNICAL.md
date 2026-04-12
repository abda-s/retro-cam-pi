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

### Modules (11 total)
```
main.py              - Orchestration, UI overlays
camera_worker.py   - Picamera2 capture, audio recording
process_worker.py  - cv2 resize for display
display_manager.py - ST7735 display, frame buffering
capture_manager.py - Image capture/save
media_browser.py   - Browse saved files
filter_manager.py - 7 retro filter effects
video_filter_processor.py - Video filter with PyAV
config_manager.py - Configuration
input_manager.py  - Non-blocking key detection
logger.py          - Centralized logging
```

### Multi-Core Processing
```
Core 1: capture_worker  → Camera capture, color swap
Core 2: process_worker  → cv2.resize INTER_LINEAR
Core 3+: main loop      → PIL convert + SPI display @ 40MHz
```

### Video Processing Chain
```
stop_recording()
  └── ffmpeg_merge(video + audio) → .merged.mp4
      └── video_filter_processor (if filter_index > 0)
          └── apply_filter_to_video() → PyAV encoding
```

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

Apply to live feed and saved images:

| Index | Name | Implementation |
|-------|------|---------------|
| 0 | NONE | Return original |
| 1 | SEPIA | cv2.transform with sepia kernel |
| 2 | SILVER | CLAHE grayscale |
| 3 | 70s FILM | Color boost + noise |
| 4 | 80s VHS | RGB channel roll |
| 5 | 80s VHS+ | Gaussian blur + blend + noise |
| 6 | SUPER 8 | Vignette + warm + noise |

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
- `av` (PyAV) - Video encoding
- `numpy` - Array operations