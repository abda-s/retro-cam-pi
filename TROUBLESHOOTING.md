# Troubleshooting Guide

Common issues and solutions.

## Quick Diagnosis

### Application won't start
```bash
# Check Python and dependencies
python3 --version
pip3 list | grep -E "picamera2|PIL|luma|opencv"

# Check SPI device
ls /dev/spi*

# Check camera detection
rpicam-still --list-cameras
```

### Key press not working
Terminal requires Enter after key. This is normal behavior.
- Press 't' then Enter to capture
- Press 'v' then Enter to record

### Application won't stop
```bash
# Use Ctrl+Z (not Ctrl+C)
# Or manually:
killall -9 python3
```

## Display Issues

### No display output
1. Check wiring (all 8 pins)
2. Verify SPI enabled: `ls /dev/spi*`
3. Test with: `raspi-config` → Interface Options → SPI

### White screen only
- Check SDA (Pin 19), SCK (Pin 23), CS (Pin 24)
- Verify D/C (Pin 16) and RST (Pin 18)

### Flickering display
- Reseat all jumper wires
- Check power supply (2.5A minimum)
- Reduce wire length

## Camera Issues

### Camera not detected
```bash
rpicam-still --list-cameras

# If not found:
# - Check ribbon cable connection
# - Enable camera: raspi-config → Interface Options → Camera
```

### Camera works but no video
Stop other camera apps:
```bash
killall rpicam-still
```

### Poor image quality
- Low light: OV5647 performs poorly in dim conditions
- Check lens is clean

## Performance Issues

### Low FPS
- Lower capture resolution in config_manager.py
- Close other applications
- Check thermal throttling: `vcgencmd measure_temp`

### Memory usage
```bash
free -h
# Should have >100MB available
```

## Video Issues

### Video has no audio
Check USB microphone is detected:
```bash
arecord -L
```

### Video filter fails
Expected behavior: video filters are disabled. Videos are saved unfiltered for speed/stability. Filters apply to live preview and photo capture only.

## View Mode Issues

### No files in view mode
- Check files in ~/Pictures/captures/
- Must be PNG, MKV, or MP4 format

### Videos show black screen
Check ffmpeg installed:
```bash
ffmpeg -version
```

### Thumbnail black bars
Restart app to rebuild thumbnail cache.

## Recovery

### Stuck application
```bash
killall -9 python3

# If terminal corrupted:
reset
```

### Camera in bad state
```bash
killall rpicam-still
sleep 2
rpicam-still -o /tmp/test.jpg
```

### Check for zombie processes
```bash
ps aux | grep python3 | grep defunct
```

## Debug Output

For detailed debugging, modify src/logger.py:
```python
# Change log level from INFO to DEBUG
level: int = logging.DEBUG,
```

Log file location:
```bash
~/.cache/opencode/rpi-tft-camera/app.log
```

Useful commands:
```bash
# Follow logs live
tail -f ~/.cache/opencode/rpi-tft-camera/app.log

# Show recent warnings/errors
grep -E "ERROR|WARNING" ~/.cache/opencode/rpi-tft-camera/app.log | tail -n 50
```
