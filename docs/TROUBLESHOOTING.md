# Troubleshooting Guide

Common issues and solutions for the RPi TFT Camera Display project.

### Application won't exit with Ctrl+C
- **PLANNED IMPROVEMENTS in v2.1.0**: Comprehensive signal handling overhaul
- **Root Causes**: Picamera2 blocking operations don't respect signals, signal propagation issues, blocking queue operations
- **Symptoms**: 
  - Python tracebacks on Ctrl+C
  - Workers don't stop cleanly
  - Processes may hang or become zombies
  - Resources not cleaned up
- **Partial Fix in v2.0.2**: Improved KeyboardInterrupt handlers around blocking operations
- **Planned Complete Fix**: Multi-layer signal handling with frequent shutdown checks
- **Components**:
  1. Global signal handler (sets shutdown flag immediately)
  2. Worker-level signal handlers (redundant protection)
  3. Frequent shutdown checks in all loops (every iteration)
  4. Timeout-based queue operations (no indefinite blocking)
  5. Enhanced stop_workers() with longer timeouts and terminate fallback
- **Documentation**: See `docs/CTRL_C_SHUTDOWN.md` for detailed technical approach
- **Implementation Plan**: See `docs/PLANNED_IMPROVEMENTS.md` for complete plan
- **Expected Result**: Clean shutdown in 3-5 seconds, no tracebacks, all processes terminate

## 🔍 Quick Diagnosis

### Problem: 't' Key Requires Enter (Pressing 't' Does Nothing)
- **PLANNED FIX in v2.1.0**: Terminal raw mode implementation
- **Root Cause**: Terminal in canonical (line-buffered) mode
- **Symptom**: Pressing 't' alone does nothing, needs 't' + Enter
- **Current Workaround**: Press 't' then Enter (works with current version)
- **Solution**: Switch to raw terminal mode for character-by-character input
- **Documentation**: See `docs/TERMINAL_RAW_MODE.md` for technical details
- **Implementation Plan**: See `docs/PLANNED_IMPROVEMENTS.md` for complete plan

### Problem: Capture Fails with "Queue Empty" Error
- **PLANNED FIX in v2.1.0**: Shared memory buffer for last frame
- **Root Cause**: capture_queue_save (Queue A) can be empty when user presses 't'
- **Symptom**: "Warning: No frame available for capture (Queue A empty)"
- **Impact**: User cannot capture images even though video is playing
- **Solution**: Add shared memory array that always contains latest frame
- **Benefits**: Capture always succeeds, no race conditions, faster frame access
- **Memory Impact**: +231 KB (negligible with ~150MB available)
- **Documentation**: See `docs/SHARED_MEMORY_BUFFER.md` for technical details
- **Implementation Plan**: See `docs/PLANNED_IMPROVEMENTS.md` for complete plan

### Problem: Nothing works at all
1. Check power supply is connected and providing adequate current
2. Verify Raspberry Pi is booting (check for activity LEDs)
3. Confirm SD card is properly inserted
4. Check network connection (for initial setup)

### Problem: Display doesn't work, camera works
See "Display Issues" section below

### Problem: Camera doesn't work, display works
See "Camera Issues" section below

### Problem: Both work but poor performance
See "Performance Issues" section below

## 🖥️ Display Issues

### Issue: Display is completely dark (no backlight)

**Symptoms:**
- No light from display
- Screen appears black even in bright light

**Possible Causes:**
1. VCC not connected to 3.3V
2. GND not connected properly
3. Backlight LED not connected
4. Display module defective

**Solutions:**
```bash
# 1. Check power connections
# Verify VCC is connected to Pin 1 (3.3V)
# Verify GND is connected to Pin 6

# 2. Test backlight directly
# Connect LED pin to 3.3V and LED- to GND
# Backlight should turn on

# 3. Check for power on 3.3V rail
multimeter - test voltage on Pin 1
# Should read ~3.3V
```

**Code Test:**
```python
# Try forcing backlight on
device = st7735(serial, rotate=1)
device.backlight(True)
```

### Issue: White screen only (no image)

**Symptoms:**
- Display lights up (backlight working)
- Screen remains white, no image displayed
- No text or graphics visible

**Possible Causes:**
1. SPI not enabled
2. Wrong SPI connections
3. Display not initialized
4. Data/Command pin wrong

**Solutions:**
```bash
# 1. Check if SPI is enabled
ls /dev/spi*
# Should show: /dev/spidev0.0 and/or /dev/spidev0.1

# If not present, enable SPI:
sudo raspi-config
# Interface Options → SPI → Enable
# Reboot

# 2. Verify SPI connections
# SDA should be on Pin 19 (GPIO 10)
# SCK should be on Pin 23 (GPIO 11)
# CS should be on Pin 24 (GPIO 8)

# 3. Check permissions
groups cam
# Should include: spi gpio
# If not: sudo usermod -a -G spi,gpio cam
# Logout and login again
```

**Code Test:**
```python
# Test display initialization
from luma.core.interface.serial import spi
from luma.lcd.device import st7735

try:
    serial = spi(port=0, device=0, gpio_DC=23, gpio_RST=24)
    device = st7735(serial, rotate=1)
    print("Display initialized successfully!")
    print(f"Resolution: {device.width}x{device.height}")
except Exception as e:
    print(f"Display failed: {e}")
```

### Issue: Flickering display

**Symptoms:**
- Display lights up but image flickers
- Random horizontal or vertical lines
- Intermittent display

**Possible Causes:**
1. Loose connections
2. SPI speed too high
3. Power supply insufficient
4. EMI/RF interference

**Solutions:**
```bash
# 1. Check all connections
# Reseat all jumper wires
# Ensure good contact on all pins

# 2. Reduce SPI speed (in code)
# This is handled automatically, but you can try:
# Lower capture resolution in config:
CAPTURE_RESOLUTION = (160, 120)

# 3. Check power supply
# Ensure power supply provides at least 2.5A
# Measure voltage on 5V rail (should be ~5V)

# 4. Reduce interference
# Keep wires short
# Avoid running near high-frequency signals
# Use twisted pair for SPI data
```

### Issue: Display shows random patterns

**Symptoms:**
- Colored noise or static
- Incorrect colors
- Ghost images

**Possible Causes:**
1. Wrong data connections
2. Incorrect D/C pin
3. Wrong RST pin
4. SPI communication errors

**Solutions:**
```bash
# 1. Verify data connections
# SDA (MOSI) → Pin 19 (GPIO 10)
# SCK (SCLK) → Pin 23 (GPIO 11)
# CS → Pin 24 (GPIO 8)

# 2. Check control pins
# D/C (Data/Command) → Pin 16 (GPIO 23)
# RST (Reset) → Pin 18 (GPIO 24)

# 3. Verify no pin conflicts
# Ensure no other devices using GPIO 8, 10, 11, 23, 24

# 4. Check for shorts
# Use multimeter to check no continuity between adjacent pins
```

## 📷 Camera Issues

### Issue: Camera not detected

**Symptoms:**
- Application shows camera initialization error
- `rpicam-still` doesn't work
- No video feed on display

**Possible Causes:**
1. Camera not connected
2. Camera ribbon cable not seated properly
3. Camera module defective
4. libcamera not installed

**Solutions:**
```bash
# 1. Check camera connection
# Verify ribbon cable is fully inserted
# Check cable is not damaged
# Ensure blue side faces away from board

# 2. Test camera with rpicam-still
rpicam-still -o test.jpg
# If this works, camera is functional

# 3. Check camera detection
rpicam-still --list-cameras
# Should show: Available cameras
# 0 : ov5647 [2592x1944 10-bit GBRG]

# 4. Check camera permissions
groups cam
# Should include: video
# If not: sudo usermod -a -G video cam
# Logout and login again

# 5. Check libcamera installation
python3 -c "import libcamera; print(libcamera.__version__)"
# Should print version number

# 6. Check video devices
ls -la /dev/video*
# Should show /dev/video0 (camera)
```

### Issue: Camera works but poor image quality

**Symptoms:**
- Dark or washed out images
- Incorrect colors
- Blurry images
- Poor low-light performance

**Possible Causes:**
1. Auto-exposure not settled
2. Low light conditions
3. Camera focus issues
4. Lens dirty

**Solutions:**
```bash
# 1. Allow auto-exposure to settle
# Add delay after camera start in code:
picam2.start()
time.sleep(2)  # Allow 2 seconds for auto-exposure

# 2. Test in better lighting
# Try outdoor or well-lit indoor conditions
# OV5647 performs poorly in very low light

# 3. Check camera focus
# OV5647 has fixed focus (~20cm to infinity)
# Cannot be adjusted

# 4. Clean lens
# Use soft cloth or lens cleaning tissue
# Avoid scratching lens surface

# 5. Adjust camera controls (if needed)
# Can be done programmatically in Picamera2
picam2.set_controls({"ExposureTime": 10000, "AnalogueGain": 1.0})
```

### Issue: Camera works but slow performance

**Symptoms:**
- Low frame rate (<5 FPS)
- Long lag between capture and display
- System sluggish

**Possible Causes:**
1. Capture resolution too high
2. System overloaded
3. Poor cooling
4. Memory issues

**Solutions:**
```bash
# 1. Lower capture resolution
# Edit config/display_config.py:
CAPTURE_RESOLUTION = (160, 120)  # Lower resolution

# 2. Close other applications
# Stop unnecessary services
# Close web browsers, etc.

# 3. Check CPU usage
top
# Look for high CPU usage
# Camera should use ~30-40% of one core

# 4. Check memory
free -h
# Should have >100MB available
# If low, consider lighter OS

# 5. Check system temperature
vcgencmd measure_temp
# Should be <70°C
# If high, improve cooling
```

## ⚡ Performance Issues

### Issue: Frame rate lower than expected

**Symptoms:**
- Display shows <5 FPS
- Video looks choppy
- Laggy response to key press

**Possible Causes:**
1. Capture resolution too high
2. Resize method too slow
3. System overloaded
4. SPI speed limitations

**Solutions:**
```bash
# 1. Lower capture resolution
# In config/display_config.py:
CAPTURE_RESOLUTION = (160, 120)  # Fastest
# or
CAPTURE_RESOLUTION = (320, 240)  # Balanced (recommended)

# 2. Use faster resize method
# Edit config/display_config.py:
RESIZE_METHOD = "NEAREST"  # Fastest, lower quality
# or
RESIZE_METHOD = "BILINEAR"  # Medium speed/quality
# or
RESIZE_METHOD = "LANCZOS"  # Best quality (default)

# 3. Optimize code
# Ensure single frame buffer
# Avoid unnecessary conversions
# Use efficient algorithms

# 4. Check for bottlenecks
# Monitor CPU usage per core:
top
# Look for processes using high CPU

# 5. Consider hardware upgrade
# RPi 4/5 have better performance
# Better cooling can prevent throttling
```

### Issue: Memory usage too high

**Symptoms:**
- System slows over time
- Application crashes
- High memory usage

**Possible Causes:**
1. Frame accumulation
2. Memory leaks
3. Large image buffers
4. Too many background processes

**Solutions:**
```bash
# 1. Check memory usage
free -h
# Look at Mem: available and Swap: used

# 2. Monitor memory over time
watch -n 1 free -h
# Watch for memory growth

# 3. Check for memory leaks
# Restart application periodically
# Monitor memory before/after restart

# 4. Reduce memory usage
# Lower capture resolution
# Use single frame buffer
# Close other applications

# 5. Use lighter OS
# Consider Raspberry Pi OS Lite
# Remove unnecessary packages
```

## 🔌 Connection Issues

### Issue: Cannot connect to Raspberry Pi

**Symptoms:**
- SSH connection refused
- Connection timeout
- Network unreachable

**Solutions:**
```bash
# 1. Verify network connection
ping 192.168.1.112

# 2. Check IP address
# On Pi: hostname -I
# Should show: 192.168.1.112

# 3. Check SSH is running
sudo systemctl status ssh
# Should show: active (running)
# If not: sudo systemctl start ssh

# 4. Check firewall
# Ensure port 22 is open
# On Pi: sudo ufw status

# 5. Try direct connection (if on same network)
ssh cam@192.168.1.112
# Test login and permissions
```

### Issue: SPI not working

**Symptoms:**
- No /dev/spi* devices
- SPI errors in logs
- Display not responding

**Solutions:**
```bash
# 1. Check if SPI is enabled
ls /dev/spi*
# If nothing listed, SPI is disabled

# 2. Enable SPI
sudo raspi-config
# Navigate: Interface Options → SPI → Yes
# Reboot when prompted

# 3. Verify SPI in config
cat /boot/firmware/config.txt | grep spi
# Should show: dtparam=spi=on

# 4. Check SPI driver
lsmod | grep spi
# Should show: spi_bcm2835 or similar

# 5. Test SPI manually
spidev-test -D /dev/spidev0.0
# Should show SPI information
```

## 🐛 Application Issues

### Issue: Application crashes on startup

**Symptoms:**
- Python error immediately
- "Module not found" errors
- Application won't start

**Solutions:**
```bash
# 1. Check Python version
python3 --version
# Should be Python 3.11+

# 2. Check for missing modules
python3 camera_tft_display.py
# Look for "ModuleNotFoundError"

# 3. Install missing dependencies
cd ~/rpi-tft-camera/src
bash install_dependencies.sh

# 4. Check permissions
groups cam
# Should include: spi gpio video
# Add missing groups:
sudo usermod -a -G spi,gpio,video cam
# Logout and login again

# 5. Run with verbose output
python3 -v camera_tft_display.py
# See more detailed error information
```

### Issue: Key press not detected

**Symptoms:**
- Pressing 't' doesn't capture image
- No response to keyboard input

**Solutions:**
```bash
# 1. Check terminal settings
# Run in terminal, not GUI
# Ensure terminal has focus

# 2. Test key detection
# Press other keys to see if they register
# Try uppercase 'T' as well

# 3. Check for input blocking
# Ensure no other programs reading stdin
# Check for TTY issues

# 4. Verify code is running
# Check console output for "FPS" updates
# Ensure application is not paused

# 5. Try different terminal
# Some terminals don't work well with select()
# Try standard terminal or ssh
```

### Issue: Images not saving

**Symptoms:**
- Pressing 't' shows no save
- Capture directory empty
- "Image saved!" not shown

**Solutions:**
```bash
# 1. Check directory exists
ls ~/Pictures/captures/
# If not found, create:
mkdir -p ~/Pictures/captures

# 2. Check directory permissions
ls -ld ~/Pictures/captures/
# Should show: drwxr-xr-x
# If not: chmod 755 ~/Pictures/captures

# 3. Check disk space
df -h
# Ensure sufficient free space

# 4. Check write permissions
touch ~/Pictures/captures/test.txt
# Should succeed
# Remove test file: rm ~/Pictures/captures/test.txt

# 5. Check error messages
# Look at console output for error
# Check for disk I/O errors
```

## 🔧 System Issues

### Issue: Raspberry Pi overheating

**Symptoms:**
- System slows down
- Frame rate drops
- Thermal throttling

**Solutions:**
```bash
# 1. Check temperature
vcgencmd measure_temp
# Should be <70°C for good performance

# 2. Check for throttling
vcgencmd get_throttled
# If output is not 0x0, throttling occurred

# 3. Improve cooling
# Ensure case has adequate ventilation
# Add heatsinks or fan
# Ensure ambient temperature is reasonable

# 4. Reduce load
# Lower capture resolution
# Close other applications
# Reduce FPS target

# 5. Monitor temperature over time
watch -n 5 vcgencmd measure_temp
# Watch for temperature increase
```

### Issue: System runs out of memory

**Symptoms:**
- Application crashes
- System becomes unresponsive
- High swap usage

**Solutions:**
```bash
# 1. Check memory usage
free -h
# Look at Mem: available and Swap: used

# 2. Identify memory hogs
top
# Press M to sort by memory
# Look for processes using high memory

# 3. Restart application
# Application may have memory leak
# Restart periodically

# 4. Reduce memory usage
# Lower capture resolution
# Use single frame buffer
# Close other applications

# 5. Consider system upgrade
# RPi 4/5 have more memory
# Can swap SD card for one with more space
```

## 📞 Getting Help

### Before Asking for Help

1. **Gather Information:**
   - Raspberry Pi model: `cat /proc/cpuinfo`
   - OS version: `cat /etc/os-release`
   - Python version: `python3 --version`
   - Error messages: Copy full error output
   - System logs: Check relevant logs

2. **Try These Steps:**
   - Restart Raspberry Pi
   - Reinstall dependencies
   - Check all connections
   - Review error messages
   - Test components separately

3. **Document the Problem:**
   - What were you trying to do?
   - What happened instead?
   - What have you tried already?
   - What's the exact error message?
   - Can you reproduce it consistently?

### Where to Get Help

- **Documentation:** Read TECHNICAL.md for detailed info
- **Wiring Guide:** Review WIRING.md for connection issues
- **Online Forums:** Raspberry Pi Forums
- **GitHub Issues:** Check project repository issues
- **Community:** Stack Overflow, Reddit r/raspberry_pi

---

**Version:** 1.0.0
**Last Updated:** 2026-04-06
