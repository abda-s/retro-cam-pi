# Debugging Assistance for RPi TFT Camera Display

## Quick Problem Resolution

When developing or debugging the camera TFT display, you may need to quickly kill processes, diagnose issues, or recover from stuck states.

## Quick Kill Methods

### Method 1: Killall (Fastest)

Kill all Python processes immediately.

```bash
# Kill all Python3 processes
killall -9 python3

# Or more specifically:
killall -9 python3 camera_tft
```

**How it Works:**
- `-9` = SIGKILL (cannot be caught or ignored)
- Terminates all processes matching pattern
- Immediate effect (no graceful shutdown)
- No cleanup (processes die instantly)

**When to Use:**
- Application is completely stuck (no response to anything)
- Need immediate termination
- Don't care about cleanup or file closure
- Development/debugging emergency

**Pros:**
- ✅ Simple one-liner
- ✅ Guaranteed to work
- ✅ Instant effect

**Cons:**
- ❌ No graceful shutdown
- ❌ Camera may be left in bad state
- ❌ No file closure
- ❌ May corrupt shared resources

### Method 2: Pkill (More Targeted)

Kill processes matching specific patterns.

```bash
# Kill by exact name pattern
pkill -9 -f "camera_tft_optimized"

# Kill by partial match
pkill -9 -f "python3.*camera_tft"

# Kill main script only (leave other Python alone)
pkill -9 -f "python3.*camera_tft_display"
```

**How it Works:**
- `-9` = SIGKILL (forceful)
- `-f` = match full command line (more precise)
- Finds processes matching pattern
- Sends kill signal to each match

**When to Use:**
- Kill specific application without killing others
- More precise than killall
- Want to preserve other Python processes

**Pros:**
- ✅ More targeted than killall
- ✅ Doesn't kill unrelated Python scripts
- ✅ Still immediate

**Cons:**
- ❌ Still no graceful shutdown
- ❌ Pattern matching may be imprecise
- ❌ Same resource corruption risks as killall

### Method 3: Kill by PID (Most Control)

Manually identify and kill specific processes by PID.

```bash
# Find PIDs
ps aux | grep camera_tft_optimized

# Output example:
# cam  12345  0.5  1.2  85420  12384 pts/0  Ss+  0:00 python3 camera_tft_optimized.py
# cam  12346  0.3  0.1  87654  12384 pts/0  R  +  0:00 python3 camera_tft_optimized.py
# cam  12347  0.2  0.0  85420  12384 pts/0  S  +  0:00 python3 camera_tft_optimized.py
#             ^^^^
#             This is PID (2nd column)

# Kill specific PIDs
kill -9 12345  # Main process
kill -9 12346  # Capture worker
kill -9 12347  # Process worker
```

**How to Read ps aux Output:**
```
USER  PID  %CPU %MEM  VSZ   RSS TTY   STAT START   TIME COMMAND
cam 12345  0.5  1.2  85420 12384 pts/0  Ss+  0:00 python3 camera_tft_optimized.py
     ^^^^ (this is the PID)
```

**When to Use:**
- Need maximum control
- Want to kill specific processes selectively
- Understand process structure

**Pros:**
- ✅ Most precise control
- ✅ Can choose which processes to kill
- ✅ Guaranteed to work

**Cons:**
- ❌ Requires manual PID lookup
- ❌ Tedious if many instances
- ❌ Same no graceful shutdown

### Method 4: Process Status Check

Check what's running before killing.

```bash
# Check if camera_tft processes are running
ps aux | grep camera_tft

# Count how many instances
ps aux | grep camera_tft | wc -l

# Check for zombie processes
ps aux | grep camera_tft | grep defunct

# Detailed process info
ps aux | grep camera_tft | grep -v grep
```

**When to Use:**
- Verify process state before/after changes
- Check for zombie processes
- Understand process hierarchy
- Debugging process leaks

### Method 5: Kill All Python (Emergency)

```bash
# Nuclear option - kill ALL python processes
killall -9 python

# Alternative using pkill
pkill -9 python
```

**When to Use:**
- Emergency cleanup
- Python completely stuck system-wide
- Don't need to preserve anything
- Last resort

## Debugging Tools

### Tool 1: Process Monitoring

```bash
# Real-time process monitoring
watch -n 1 'ps aux | grep camera_tft'

# Monitor CPU usage
top -p $(pgrep -f camera_tft_optimized | head -1)

# Monitor memory usage
top -p $(pgrep -f camera_tft_optimized | head -1) -o %MEM

# Monitor all resources
htop
```

### Tool 2: Log Monitoring

```bash
# Watch application logs (if logging to file)
tail -f /path/to/logfile

# Monitor console output (if running in tmux/screen)
# Attach to session:
tmux attach -t camera_session
screen -r camera_session

# Check error logs
journalctl -f python3 --since "5 minutes ago"
```

### Tool 3: Debug Mode

Run application with debug logging enabled.

```bash
# Run with debug output
python3 -v camera_tft_optimized.py  # Python verbose mode

# Add custom debug flags
DEBUG=1 python3 camera_tft_optimized.py

# Use Python debugger
python3 -m pdb camera_tft_optimized.py
```

### Tool 4: System Monitoring

```bash
# Check CPU temperature
vcgencmd measure_temp

# Check for thermal throttling
vcgencmd get_throttled
# Output: 0x0 = no throttling
# Non-zero = throttling occurred

# Check memory usage
free -h

# Check disk I/O
iostat -x 1

# Check network traffic (if applicable)
ifconfig
```

## Common Debugging Scenarios

### Scenario 1: Application Starts But No Video

**Symptoms:**
- Application shows "Starting workers..."
- No FPS output
- TFT screen is black
- Console shows no updates

**Diagnosis Steps:**
```bash
# 1. Check if processes are running
ps aux | grep camera_tft_optimized

# Expected: 3 processes (main + 2 workers)
# If only 1 process: workers failed to start

# 2. Check camera is detected
rpicam-still --list-cameras
# Should show: "Available cameras" with camera info
# If error: camera not connected

# 3. Check SPI device exists
ls -la /dev/spi*
# Should show: /dev/spidev0.0 and /dev/spidev0.1
# If missing: SPI not enabled

# 4. Check display in use
ls -la /dev/video*
# Too many video devices = conflict possible
```

**Possible Causes:**
1. Camera not connected
2. SPI not enabled
3. Dependencies not installed
4. Permission issues
5. Worker processes crashed

**Solutions:**
```bash
# Check camera
sudo rpicam-still -o /tmp/test.jpg
# If this works: camera OK, issue is in code
# If this fails: camera problem, check hardware

# Check SPI
sudo raspi-config
# Navigate to Interface Options → SPI → Enable
# Reboot required

# Check permissions
groups cam
# Should include: spi, gpio, video
# If missing: sudo usermod -a -G spi,gpio,video cam
```

### Scenario 2: Video Playing But No Capture on 't'

**Symptoms:**
- FPS shows 12-18
- Video on TFT looks good
- Pressing 't' does nothing
- Or shows "queue empty" error

**Diagnosis Steps:**
```bash
# 1. Check if capture queue is being populated
# In code, add debug output:
print(f"Queue A size: {capture_queue_save.qsize()}")
print(f"Queue B size: {capture_queue_display.qsize()}")
print(f"Queue C size: {display_queue.qsize()}")

# Should see:
# Queue A: 1-2 frames (should have data)
# Queue B: 1-2 frames (should have data)
# Queue C: 1-2 frames (should have data)

# 2. Check if workers are alive
ps aux | grep camera_tft_optimized
# Should show 3 processes

# 3. Test input detection
# In check_for_capture():
print("DEBUG: Waiting for key press...")
# Try typing random letters
# Should see output if detected
```

**Possible Causes:**
1. Terminal line buffering (needs Enter)
2. Capture queue not being populated
3. Input detection not working
4. capture_image() failing silently

**Solutions:**
```bash
# 1. Test input directly
# On terminal, type 't' then Enter
# If works: issue is line buffering (needs raw mode)

# 2. Check save directory
ls -la ~/Pictures/captures/
# If empty: capture_image() is failing

# 3. Check for error messages
# Run application, press 't'
# Look for any error output

# 4. Test with standard version
python3 camera_tft_display.py
# If this works: issue specific to optimized version
```

### Scenario 3: Application Crashes on Startup

**Symptoms:**
- Application starts then immediately crashes
- Python traceback shown
- Application exits immediately

**Diagnosis Steps:**
```bash
# 1. Run with verbose mode
python3 -v camera_tft_optimized.py 2>&1 | tee debug.log

# 2. Check traceback carefully
# Look at first error message
# Common errors:
# - ModuleNotFoundError: missing dependency
# - PermissionError: can't access GPIO/SPI
# - RuntimeError: camera/display issue
# - ValueError: configuration problem

# 3. Check hardware connections
# Verify all pins connected correctly
# Use multimeter to check voltages
# Check for short circuits

# 4. Check system logs
journalctl -xe | grep -i camera_tft
dmesg | tail -50
```

**Common Startup Errors:**
```python
# Error 1: ModuleNotFoundError
ModuleNotFoundError: No module named 'picamera2'
Solution: sudo apt install python3-picamera2

# Error 2: PermissionError
PermissionError: [Errno 13] Permission denied
Solution: sudo chmod 666 /dev/spi*
Solution: sudo usermod -a -G spi,gpio cam

# Error 3: RuntimeError
RuntimeError: Failed to configure camera
Solution: Check camera is not in use by other appSolution: killall rpicam-still

# Error 4: OSError
OSError: [Errno 2] No such file or directory
Solution: Check save directory exists
mkdir -p ~/Pictures/captures
```

### Scenario 4: Performance Degrades Over Time

**Symptoms:**
- FPS starts at 18-22
- Drops to 8-10 after few minutes
- Keeps dropping to 5-8
- Application becomes sluggish

**Diagnosis Steps:**
```bash
# 1. Monitor CPU temperature
vcgencmd measure_temp
# >70°C = throttling (CPU slowed down)

# 2. Check for throttling
vcgencmd get_throttled
# Non-zero = throttling occurred
# Check https://www.raspberrypi.com/documentation/computers/raspberry-pi/configtxt/overclocking.html

# 3. Monitor memory usage
watch -n 5 'free -h'
# Look for increasing memory usage
# Look for Swap usage (indicates memory pressure)

# 4. Check CPU usage
top
# Look at %CPU column
# Should be 20-40% total (3 cores @ 10-15% each)
# >80% = bottleneck

# 5. Check for memory leaks
# Run for extended period (30+ minutes)
# Watch memory usage
# If keeps increasing: memory leak
```

**Possible Causes:**
1. CPU throttling (overheating)
2. Memory leaks
3. Process buildup (workers not exiting)
4. Frame accumulation (queues not being consumed)
5. Resource contention (other processes)

**Solutions:**
```bash
# 1. Improve cooling
# Add heatsinks or fan
# Ensure good airflow
# Lower ambient temperature

# 2. Check for memory leaks
# Add debug output for queue sizes
# Look for growing memory usage
# Restart application periodically

# 3. Reduce load
# Lower capture resolution
# Close other applications
# Check for runaway processes

# 4. Fix process leaks
# Ensure workers exit cleanly
# Verify no zombie processes
# Use proper cleanup in finally blocks
```

## Debug Script Template

Create a debug script for troubleshooting:

```python
#!/usr/bin/env python3
"""
Debug script for camera TFT display
"""

import sys
import os
from pathlib import Path

def check_camera():
    """Check if camera is detected"""
    print("Checking camera...")
    os.system("rpicam-still --list-cameras")
    print()

def check_spi():
    """Check if SPI is available"""
    print("Checking SPI...")
    try:
        import spidev
        spi_devices = [d for d in os.listdir('/dev') if d.startswith('spi')]
        if spi_devices:
            print(f"✓ SPI devices found: {spi_devices}")
        else:
            print("✗ No SPI devices found")
    except ImportError:
        print("✗ spidev module not installed")
    print()

def check_permissions():
    """Check user permissions"""
    print("Checking permissions...")
    os.system("groups")
    print()

def check_directory():
    """Check save directory"""
    print("Checking save directory...")
    save_dir = Path.home() / "Pictures" / "captures"
    if save_dir.exists():
        file_count = len(list(save_dir.glob("*.png")))
        print(f"✓ Save directory exists: {save_dir}")
        print(f"  Files: {file_count}")
        print(f"  Space: {sum(f.stat().st_size for f in save_dir.glob('*.png')) / (1024*1024):.1f} MB")
    else:
        print(f"✗ Save directory missing: {save_dir}")
        save_dir.mkdir(parents=True, exist_ok=True)
        print(f"  Created: {save_dir}")
    print()

def check_processes():
    """Check for running camera processes"""
    print("Checking processes...")
    os.system("ps aux | grep camera_tft")
    print()

def main():
    print("=" * 50)
    print("Camera TFT Display Debug")
    print("=" * 50)
    print()
    
    check_camera()
    check_spi()
    check_permissions()
    check_directory()
    check_processes()
    
    print("Debug complete.")

if __name__ == "__main__":
    main()
```

**Usage:**
```bash
# Save as debug_camera.py
chmod +x debug_camera.py

# Run before/after main application
./debug_camera.py

# This will check:
# - Camera detection
# - SPI availability
# - User permissions
# - Save directory status
# - Running processes
```

## Debug Logging Template

Add comprehensive debug logging to application:

```python
# Add at top of file
import logging
import sys

def setup_debug_logging():
    """Setup debug logging to file and console"""
    # Create logger
    logger = logging.getLogger('camera_tft')
    logger.setLevel(logging.DEBUG)
    
    # File handler (detailed logs)
    file_handler = logging.FileHandler('/tmp/camera_tft_debug.log')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    # Console handler (important messages only)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(file_format)
    logger.addHandler(console_handler)
    
    return logger

# In main class:
logger = setup_debug_logging()

# Use throughout code:
logger.debug(f"Worker started, PID: {os.getpid()}")
logger.info(f"Display initialized: {width}x{height}")
logger.error(f"Capture failed: {error}")
```

**Log Levels:**
```python
logger.debug("Detailed debugging info")  # Only to file
logger.info("Important events")          # File + console
logger.warning("Warnings")                # File + console
logger.error("Errors")                    # File + console
```

## Recovery Procedures

### Recovery 1: Stuck Application

```bash
# If application is completely stuck:
killall -9 python3

# Verify all processes killed
ps aux | grep camera_tft

# Check for zombie processes
ps aux | grep camera_tft | grep defunct

# If zombies: kill parent processes
# Find parent PID and kill it
```

### Recovery 2: Corrupted Terminal

```bash
# If terminal is corrupted after application crash:
reset
# OR
stty sane
# OR
exec bash

# These reset terminal to sane state
```

### Recovery 3: Camera Left in Bad State

```bash
# If camera left in bad state (can't access after crash):
# Stop any other camera apps
killall rpicam-still

# Wait a moment
sleep 2

# Start test capture
rpicam-still -o /tmp/camera_test.jpg

# If this works: camera OK
# If this fails: camera issue, may need reboot
```

### Recovery 4: Shared Memory Issues

```bash
# If shared memory is corrupted (after planned implementation):
# Kill all processes
killall -9 python3

# Wait for cleanup
sleep 3

# Restart application
python3 ~/rpi-tft-camera/src/camera_tft_optimized.py

# Shared memory should be fresh
```

## Best Practices

### Development Best Practices

1. **Always run in tmux/screen:**
   ```bash
   tmux new -s camera_session
   python3 camera_tft_optimized.py
   # If crashes: tmux attach -t camera_session
   ```

2. **Save work before testing:**
   ```bash
   git add -A && git commit -m "WIP: testing changes"
   ```

3. **Use debug branches:**
   ```bash
   git checkout -b debug-signal-handling
   ```

4. **Monitor resources:**
   ```bash
   watch -n 1 'free -h && vcgencmd measure_temp'
   ```

### Debugging Workflow

```bash
# 1. Start with debug logging
DEBUG=1 python3 camera_tft_optimized.py

# 2. Monitor logs in another terminal
tail -f /tmp/camera_tft_debug.log

# 3. Use process monitoring
watch -n 1 'ps aux | grep camera_tft'

# 4. Have kill command ready
# In clipboard: killall -9 python3

# 5. Test thoroughly before pushing
# Test Ctrl+C
# Test capture
# Test startup/shutdown cycles
```

## References

- **Linux Process Management:** `man kill`, `man killall`, `man pkill`
- **Process Monitoring:** `man ps`, `man top`, `man htop`
- **System Monitoring:** `man vcgencmd`, `man free`, `man vmstat`
- **Debug Logging:** https://docs.python.org/3/library/logging.html
- **Multiprocessing Debugging:** https://docs.python.org/3/library/multiprocessing.html#multiprocessing-programming

---

**Version:** 1.0.0
**Purpose:** Quick problem resolution and debugging assistance
**Last Updated:** 2026-04-06
