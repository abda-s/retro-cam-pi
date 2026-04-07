# Technical Documentation

Complete technical details for the RPi TFT Camera Display project.

## 📋 System Specifications

### Raspberry Pi 3 Model B
- **CPU**: Broadcom BCM2837, quad-core ARM Cortex-A53 64-bit SoC @ 1.2GHz
- **RAM**: 1GB LPDDR2 SDRAM
- **Architecture**: aarch64 (ARM 64-bit)
- **OS**: Debian Bookworm
- **Python**: 3.13.5

### Camera Module (OV5647)
- **Max Resolution**: 2592x1944 (5MP)
- **Interface**: MIPI CSI-2
- **Driver**: ov5647 (libcamera v0.6.0+rpt20251202)
- **Color Format**: RGB 10-bit (GBRG pattern)

### TFT Display (ST7735R)
- **Resolution**: 128x160 pixels
- **Driver**: ST7735R (262K colors, RGB 6-6-6)
- **Interface**: 4-wire SPI
- **Backlight**: Always-on (connected to 3.3V)
- **Aspect Ratio**: 4:5 (portrait)

### Communication Interface (SPI)
- **Protocol**: 4-wire SPI
- **Clock Speed**: Up to 80MHz (configured automatically)
- **Pins Used**: GPIO 8 (CS), GPIO 10 (MOSI), GPIO 11 (SCLK)
- **Control Pins**: GPIO 23 (D/C), GPIO 24 (RST)

## 🏗️ Software Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                      │
│                   camera_tft_display.py                  │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
┌───────▼─────────┐                   ┌───────▼──────────┐
│   Picamera2      │                   │   luma.lcd        │
│   Camera Layer   │                   │   Display Layer   │
└───────┬─────────┘                   └───────┬──────────┘
        │                                       │
┌───────▼─────────┐                   ┌───────▼──────────┐
│   libcamera      │                   │   spidev          │
│   Hardware Abstraction             │   SPI Driver      │
└───────┬─────────┘                   └───────┬──────────┘
        │                                       │
┌───────▼─────────┐                   ┌───────▼──────────┐
│   V4L2          │                   │   GPIO            │
│   Kernel Driver  │                   │   Hardware Access │
└───────┬─────────┘                   └───────┬──────────┘
        │                                       │
┌───────────────────────┴──────────────────────────────┐
│              Raspberry Pi Hardware                  │
│     (Camera ISP, SPI Controller, GPIO)          │
└───────────────────────────────────────────────────────┘
```

### Data Flow

#### Live Video Feed Loop
1. **Picamera2** captures frame from camera (320x240 RGB888 numpy array)
2. **NumPy array** converted to PIL Image
3. **PIL Image** resized to display resolution (128x160) using LANCZOS resampling
4. **Display frame** sent to TFT via SPI (RGB 6-6-6 format conversion)
5. **Loop repeats** at target 8-12 FPS

#### Image Capture Flow
1. **User presses 't'** (detected via `select()` on stdin)
2. **Current frame** captured as numpy array (320x240)
3. **NumPy array** converted to PIL Image
4. **PIL Image** saved as PNG to disk (original resolution)
5. **Feedback overlay** displayed on TFT for 2 seconds
6. **Live feed** resumes automatically

## 🔧 Implementation Details

### Camera Initialization
```python
picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"size": (320, 240), "format": "RGB888"}
)
picam2.configure(config)
picam2.start()
```

**Why 320x240?**
- Optimal balance between quality and performance
- Minimal processing overhead for 8-12 FPS target
- Still provides good image quality for 128x160 display
- Original resolution preserved for saved images

### Display Initialization
```python
serial = spi(port=0, device=0, gpio_DC=23, gpio_RST=24)
device = st7735(serial, rotate=1)
```

**Why rotate=1?**
- Physical display orientation is 128x160 (4:5 aspect ratio)
- Rotation 1 (90° clockwise) gives 160x128 (better landscape)
- Matches camera's 4:3 aspect ratio more closely

### Frame Processing Pipeline

```python
# Capture frame (320x240 RGB888)
frame = picam2.capture_array("main")  # NumPy array, shape=(240, 320, 3)

# Convert to PIL Image
frame_image = Image.fromarray(frame)  # RGB888 format

# Resize to display resolution
frame_image = frame_image.resize(
    (display.width, display.height),
    Image.Resampling.LANCZOS
)

# Display on TFT (automatic RGB888 → RGB666 conversion)
device.display(frame_image)
```

### Key Detection Strategy

```python
if select.select([sys.stdin], [], [], 0)[0]:
    key = sys.stdin.read(1)
    if key.lower() == 't':
        # Capture image
```

**Advantages:**
- Non-blocking (doesn't pause video feed)
- No external dependencies required
- Works in terminal environment
- Fast response time (<1ms)

### Performance Optimization

#### Memory Management
- **Single frame buffer**: Only stores current frame in memory
- **Immediate save**: No frame accumulation before save
- **Cleanup on exit**: All resources released properly

#### Processing Efficiency
- **Minimize conversions**: Keep data in numpy/PIL format as long as possible
- **Low capture resolution**: 320x240 reduces processing time
- **Efficient resize**: LANCZOS provides good quality with acceptable speed
- **Direct display**: No intermediate rendering steps

#### SPI Communication
- **Automatic clock speed**: libcamera/spidev negotiate optimal speed
- **RGB format conversion**: Handled by luma.lcd library
- **4-wire SPI**: Standard mode for ST7735R display

## 📊 Performance Analysis

### v4.2.1 Results (Frame Buffering + Optimized Lores)

| Metric | v4.2.0 | v4.2.1 | Improvement |
|--------|---------|---------|-------------|
| FPS | 25-32 | 30-35 | ~10% |
| Lores Resolution | 320×240 | 128×160 | 4× fewer pixels |
| Aspect Ratio Match | No | Yes | Perfect match |
| Tearing Artifacts | Present | None | Fixed |
| SPI Speed | 40 MHz | 40 MHz | Unchanged |

### v3.0.0 Results (40 MHz SPI)

| Metric | v2.1.1 | v3.0.0 | Improvement |
|--------|--------|--------|-------------|
| FPS | 10-15 | 25-32 | **2-3×** |
| SPI Speed | 8 MHz | 40 MHz | 5× |
| Resize | PIL BILINEAR | cv2 INTER_LINEAR | 3-4× |

### Frame Processing Times (on RPi 3B - v4.2.1)

| Operation | Time (ms) | Percentage |
|-----------|-----------|------------|
| Camera capture (lores) | 5-8 | 25% |
| YUV→RGB conversion | 3-5 | 18% |
| NumPy → PIL conversion | 2-3 | 10% |
| Overlay composition | 2-3 | 10% |
| SPI display transfer | 5-8 | 25% |
| **Total** | **17-27** | **100%** |

### Achievable FPS

| Resolution | Target FPS | Actual FPS | Notes |
|------------|------------|------------|-------|
| 128×160 lores → 128×160 display | 30-35 | 30-35 | No resize, perfect match |
| 320×240 lores → 128×160 display | 25-32 | 25-32 | Requires resize, slower |

### Frame Buffering Strategy

To prevent tearing artifacts during fast camera movement, v4.2.1 implements frame buffering:

```python
# Display manager uses thread-safe busy flag
with self._display_lock:
    if self._display_busy:
        self._skipped_frames += 1  # Skip frame, prevent tearing
        return
    self._display_busy = True

# Display frame (blocking SPI transfer)
self._display.display(image)

# Always clear busy flag
finally:
    with self._display_lock:
        self._display_busy = False
```

**Benefits:**
- Prevents mid-frame updates (tearing)
- Thread-safe implementation using `threading.Lock`
- Tracks skipped frames for monitoring
- Graceful degradation during fast motion

**Trade-offs:**
- May skip 1-5 frames during very fast camera movement
- At 30-35 FPS, skipping is imperceptible
- Prioritizes display stability over maximum frame rate
| 640x480 → 128x160 | 5-8 | 5-7 | Better quality |

### Memory Usage

- **Frame buffer**: ~230KB (320x240x3 bytes RGB888)
- **Resized frame**: ~62KB (128x160x3 bytes RGB888)
- **Overhead**: ~5MB (Python + libraries)
- **Total**: ~6MB (minimal memory footprint)

## 🔒 Error Handling Strategy

### Display Errors
- **On-screen display**: Error message shown on TFT screen
- **Console logging**: Detailed error printed to terminal
- **Graceful degradation**: Application continues if possible
- **Recovery attempt**: Try to resume after errors

### Hardware Failures
- **Camera not found**: Display error message, allow manual camera check
- **Display not responding**: Log error, attempt re-initialization
- **SPI communication failure**: Log error, retry operation

### User Input Errors
- **Invalid key press**: Ignore non-'t' keys
- **Multiple captures**: Process sequentially, don't queue
- **File save failure**: Log error, display feedback on screen

## 🧪 Testing Methodology

### Unit Testing
- **Camera initialization**: Verify camera starts successfully
- **Display initialization**: Verify TFT responds correctly
- **Frame capture**: Test capture at different resolutions
- **Image save**: Verify file creation and format
- **Key detection**: Test 't' key response

### Integration Testing
- **Full video feed**: Test continuous display for 10+ minutes
- **Image capture**: Test 50+ consecutive captures
- **Performance**: Monitor FPS over extended periods
- **Memory**: Check for memory leaks over time
- **Error recovery**: Test behavior after induced errors

### System Testing
- **Cold boot**: Test automatic startup
- **Hot plugging**: Test camera/disconnect scenarios
- **Power cycling**: Test behavior after power cycles
- **Long-term stability**: Run for 24+ hours

## 🔧 Advanced Configuration

### Custom Resolutions

Edit `config/display_config.py`:

```python
# For higher quality capture
CAPTURE_RESOLUTION = (640, 480)

# For faster performance
CAPTURE_RESOLUTION = (160, 120)
```

### Display Rotation

Change `DISPLAY_ROTATION` in config:
- 0 = 0° (portrait, 128x160)
- 1 = 90° (landscape, 160x128)
- 2 = 180° (portrait, 128x160)
- 3 = 270° (landscape, 160x128)

### Save Location

Modify `SAVE_DIRECTORY`:
```python
SAVE_DIRECTORY = "~/Pictures/custom_folder"
```

### Image Format

Change `FILE_FORMAT` in config:
- "PNG" (lossless, larger files)
- "JPEG" (compressed, smaller files)

## 🐛 Known Limitations

### Performance
- **SPI bottleneck**: Display update limited by SPI speed
- **Python overhead**: Interpretation adds processing time
- **Memory constraints**: RPi 3B limited to 1GB RAM
- **CPU constraints**: Single-threaded processing

### Display Quality
- **Aspect ratio distortion**: 4:3 camera → 4:5 display
- **Color conversion**: RGB888 → RGB666 (18-bit) loss
- **Stretch artifacts**: LANCZOS resize creates minor artifacts

### Camera Limitations
- **Rolling shutter**: Fast motion may show artifacts
- **Fixed focus**: OV5647 has fixed focus distance
- **Low light**: Reduced quality in dim environments

## 🚀 Future Enhancements

### Planned Features
- **Aspect ratio preservation**: Letterboxing for correct proportions
- **Brightness/contrast controls**: Real-time image adjustment
- **Timestamp overlay**: Display capture time on screen
- **Multiple capture modes**: Burst capture, timed capture
- **Video recording**: Save video clips instead of stills

### Advanced Features
- **Motion detection**: Auto-capture on movement
- **Face detection**: Highlight faces in frame
- **Web streaming**: Stream video over network
- **Touch screen support**: Add touch controls
- **Additional sensors**: Display temperature, humidity, etc.

## 📝 Code Style Guidelines

### Python Conventions
- PEP 8 compliant
- Type hints for function parameters
- Docstrings for all functions
- Error handling with specific exceptions
- Resource cleanup using context managers

### Performance Guidelines
- Minimize object creation in loops
- Use efficient data structures
- Profile bottlenecks before optimization
- Test optimizations across different RPi models
- Document performance trade-offs

## 📚 References

- [Picamera2 API Documentation](https://github.com/raspberrypi/picamera2)
- [luma.lcd API Documentation](https://luma-lcd.readthedocs.io/)
- [ST7735R Datasheet](https://www.crystalfontz.com/controllers/Sitronix/ST7735R.pdf)
- [Raspberry Pi SPI Documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)
- [libcamera Documentation](https://libcamera.org/docs.html)

---

**Version:** 4.2.1
**Last Updated:** 2026-04-07
