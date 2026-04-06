# Shared Memory Buffer for Capture Queue

## Problem

`capture_queue_save` (Queue A) contains full-resolution (320x240) frames for image saving. When user presses 't' to capture image:

**Symptoms:**
- Sometimes shows: "Warning: No frame available for capture (Queue A empty)"
- No image is saved
- capture_queue_save is empty at that moment
- User cannot capture image even though video is playing

**Root Cause:**

Queue A (capture_queue_save) behavior:
- Contains full-resolution (320x240) frames from capture worker
- Main process tries to `get()` from queue when user presses 't'
- If queue is empty, `get()` blocks or `get_nowait()` fails
- Queue can be empty due to:
  1. Race condition: main checks before worker puts frame
  2. Worker not started yet
  3. Timing issues in queue operations
  4. Worker paused momentarily
  5. Queue overflow management dropping all frames

## Solution: Shared Memory Buffer

Add a shared memory array that ALWAYS contains the latest captured frame. Main process reads from shared memory instead of queue.

### Technical Approach

**Concept:**
- Capture worker continuously updates shared memory with latest frame
- Main process always has access to latest frame in shared memory
- Shared memory never empty (always has at least one frame)
- Capture never fails (always has frame to save)

**Implementation:**

```python
from multiprocessing import Array, Value, Lock
import numpy as np

# In __init__:
self.last_frame_shape = (240, 320, 3)  # Height, Width, Channels
self.last_frame_shared = Array('B', 240*320*3)  # ~230KB
self.last_frame_ready = Value('b', False)  # Boolean flag
self.last_frame_lock = Lock()  # Protect access
```

### Architecture

```
┌────────────────────────────────────────────────────────────────┐
│              Capture Worker (Process 1)              │
│                                                       │
│  camera.capture_array("main")                           │
│         ↓                                            │
│  color swap (BRG → RGB)                               │
│         ↓                                            │
│  ┌────────────────────────────────────────┐                │
│  │ Update Shared Memory              │                │
│  │                                 │                │
│  │  np.frombuffer(shared).reshape()  │                │
│  │  np_array[:] = frame            │                │
│  │  last_frame_ready.value = True   │                │
│  └────────────────────────────────────────┘                │
│         ↓                                            │
│  capture_queue_save.put_nowait(frame)                   │
│  capture_queue_display.put_nowait(frame)                  │
└────────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌────────────────────────────────────────────────────────────────┐
│         Shared Memory (240x320x3 bytes)               │
│                                                       │
│  ALWAYS contains latest 320x240 RGB frame               │
│  Updated every ~33ms (at 30 FPS)                         │
│  Never empty (worker updates continuously)                  │
│  Accessible by all processes                                │
└────────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌────────────────────────────────────────────────────────────────┐
│            Main Process (Capture Trigger)                  │
│                                                       │
│  User presses 't'                                       │
│         ↓                                            │
│  ┌────────────────────────────────────────┐                │
│  │ Read from Shared Memory            │                │
│  │                                 │                │
│  │  np.frombuffer(shared).reshape()  │                │
│  │  frame = np_array.copy()          │                │
│  └────────────────────────────────────────┘                │
│         ↓                                            │
│  Image.fromarray(frame)                                │
│         ↓                                            │
│  image.save(filename)                                    │
│         ↓                                            │
│  ✓ Image saved successfully                          │
└────────────────────────────────────────────────────────────────┘
```

### Code Implementation

#### Step 1: Initialize Shared Memory

```python
from multiprocessing import Array, Value, Lock
import numpy as np

# In __init__:
def __init__(self):
    # ... existing init ...
    
    # Shared memory configuration
    self.last_frame_shape = (240, 320, 3)  # H, W, C for numpy array
    
    # Create shared array (240*320*3 = 230,400 bytes)
    self.last_frame_shared = Array('B', 240*320*3)
    
    # Boolean flag to indicate frame is ready
    self.last_frame_ready = Value('b', False)
    
    # Lock to protect access
    self.last_frame_lock = Lock()
    
    print(f"Shared memory initialized: {self.last_frame_shape} = {240*320*3} bytes")
```

#### Step 2: Update Shared Memory in Capture Worker

```python
# In capture_worker() function (Process 1):
while running_flag.value and not shutdown_requested:
    # Capture frame
    frame = camera.capture_array("main")
    
    # Color swap
    frame = frame[:, :, [2, 1, 0]]  # BRG → RGB
    
    # Put in normal queues (for processing and display)
    try:
        if not capture_queue_save.full():
            capture_queue_save.put_nowait(frame)
    except:
        try:
            capture_queue_save.get_nowait()  # Remove oldest
            capture_queue_save.put_nowait(frame)
        except:
            pass
    
    # UPDATE SHARED MEMORY (always have latest frame!)
    np_array = np.frombuffer(self.last_frame_shared.get_obj()).reshape(self.last_frame_shape)
    np_array[:] = frame[:]  # Copy entire array
    self.last_frame_ready.value = True
    
    # Continue loop (next frame will update in ~33ms)
```

#### Step 3: Read from Shared Memory in capture_image()

```python
# In capture_image() method (Main Process):
def capture_image(self):
    """Capture and save using shared memory buffer"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.save_directory / f"capture_{timestamp}.png"
        
        # Always read from shared memory (never empty!)
        if self.last_frame_ready.value:
            # Access shared memory with lock
            with self.last_frame_lock:
                # Convert shared array to numpy
                np_array = np.frombuffer(self.last_frame_shared.get_obj()).reshape(self.last_frame_shape)
                
                # Make a copy (avoid shared memory issues)
                frame = np_array.copy()
                
                # Convert to PIL Image and save
                image = Image.fromarray(frame)
                image.save(filename)
                
                # Increment capture count
                self.capture_count.value += 1
            
            return True, filename
        else:
            # Worker hasn't started yet
            print("Warning: Worker still starting, no frame in shared memory")
            time.sleep(0.5)  # Wait for worker
            
            # Try again after delay
            if self.last_frame_ready.value:
                # Retry same logic
                return self.capture_image()
            else:
                return False, None
                
    except Exception as e:
        self.last_error = f"Capture failed: {str(e)}"
        print(f"ERROR: {self.last_error}")
        return False, None
```

### Performance Analysis

**Memory Usage:**
```
Shared Memory: 230,400 bytes (240*320*3)
= ~225 KB

Queue A (capture_queue_save): ~460 KB (2 frames @ 230KB each)
Queue B (capture_queue_display): ~460 KB (2 frames @ 230KB each)
Queue C (display_queue): ~124 KB (2 frames @ 62KB each)

Total with shared memory: ~1,275 KB (was ~1,044 KB)
Increase: ~231 KB (22% increase)
```

**CPU Usage:**
```
Without shared memory:
- capture_queue_save.get(): ~0.001s (queue operation)
- If queue empty: blocks indefinitely (CPU waiting)

With shared memory:
- np.frombuffer() + copy(): ~0.002s (array operations)
- Always succeeds (no blocking)
- CPU active (better than waiting)
```

**Frame Latency:**
```
Without shared memory:
- Frame saved is 1-2 frames old (from queue)
- Race conditions possible

With shared memory:
- Frame saved is ~33ms old (at 30 FPS)
- Consistent latency (always latest frame)
- No race conditions
```

### Benefits

**✅ Never Empty Queue:**
- Shared memory always contains frame (after worker starts)
- Main process always has something to capture
- No "queue empty" errors

**✅ Always Successful Capture:**
- Capture always succeeds once worker is running
- No race conditions
- No timing issues

**✅ Fast Frame Access:**
- Direct shared memory access (faster than queue.get())
- No queue blocking
- Minimal latency

**✅ Reliable:**
- Worker continuously updates shared memory
- Main process always reads latest frame
- Predictable behavior

**✅ Simple:**
- Easy to understand
- Minimal code complexity
- Clear data flow

### Tradeoffs

**Memory:**
- Additional ~231 KB memory usage
- Negligible for system with ~150MB available

**Frame Freshness:**
- Frame is 1 frame old (~33ms at 30 FPS)
- Acceptable for still image capture
- Not real-time capture (which is fine)

**Complexity:**
- Slightly more complex queue management
- Need to understand shared memory concept
- More initialization code

### Alternative Approaches

#### Option A: Larger Queue (Current Approach)
- Increase queue maxsize from 2 to 5
- Reduces chance of empty queue
- Still can be empty during startup or timing

**Verdict:** Shared memory is more reliable.

#### Option B: Dedicated Capture Queue (Single Frame)
- Separate queue with maxsize=1 for last frame only
- Worker always maintains 1 frame
- Queue never empty

**Verdict:** Similar reliability to shared memory, but more memory.

#### Option C: Lock-Based Queue Protection
- Use lock to ensure main doesn't read while worker writes
- Doesn't prevent empty queue
- Adds complexity without solving problem

**Verdict:** Shared memory is better solution.

## Testing

### Test 1: Worker Startup

```bash
# Expected: Shared memory gets populated quickly
python3 camera_tft_optimized.py
# Wait for FPS output (worker started)
# Press 't'
# Should succeed immediately
```

### Test 2: Continuous Capture

```bash
# Expected: All captures succeed
python3 camera_tft_optimized.py
# Press 't' 10 times quickly
# Should see: "✓ Image saved" 10 times
# No "queue empty" errors
```

### Test 3: Startup Capture

```bash
# Expected: Quick startup (graceful wait)
python3 camera_tft_optimized.py
# Immediately press 't'
# Should see: "Warning: Worker still starting" (once)
# Then: "✓ Image saved" (after ~0.5s)
```

### Test 4: Memory Check

```bash
# Verify memory usage
python3 camera_tft_optimized.py &
PID=$!
sleep 10
ps aux | grep $PID
# Should see ~1,275 KB memory usage (vs ~1,044 KB without)
```

### Debug Output

```python
# In capture_worker():
while running_flag.value:
    frame = camera.capture_array("main")
    
    # Debug: Show update rate
    frame_count += 1
    if frame_count % 30 == 0:  # Every 30 frames (~1 sec)
        print(f"DEBUG: Shared memory updated (frame {frame_count})")
    
    # Update shared memory
    np_array = np.frombuffer(self.last_frame_shared.get_obj()).reshape(self.last_frame_shape)
    np_array[:] = frame[:]
    self.last_frame_ready.value = True

# In capture_image():
def capture_image(self):
    if self.last_frame_ready.value:
        print("DEBUG: Reading from shared memory")
        np_array = np.frombuffer(self.last_frame_shared.get_obj()).reshape(self.last_frame_shape)
        frame = np_array.copy()
        print(f"DEBUG: Frame shape: {frame.shape}")
        # ... save image ...
    else:
        print("DEBUG: Shared memory not ready yet")
```

## Troubleshooting

### Issue 1: Memory Not Being Updated

**Symptom:** Shared memory flag never becomes True.

**Possible Causes:**
1. Worker not running
2. Worker not reaching update code
3. Exception in worker preventing updates

**Solutions:**
```python
# 1. Check worker status in main loop
if time.time() - last_worker_check >= 5.0:
    print(f"DEBUG: Worker alive: {capture_process.is_alive()}")
    print(f"DEBUG: Shared memory ready: {last_frame_ready.value}")
    last_worker_check = time.time()

# 2. Add debug output in worker
print(f"DEBUG: Updating shared memory, shape: {frame.shape}")

# 3. Add try/except in worker loop
try:
    # Update shared memory
except Exception as e:
    print(f"ERROR: Failed to update shared memory: {e}")
```

### Issue 2: Corrupted Frames

**Symptom:** Saved images look corrupted or wrong.

**Possible Causes:**
1. Race condition: reading while writing
2. Memory corruption in shared memory
3. Wrong array shape

**Solutions:**
```python
# 1. Always use lock for access
with self.last_frame_lock:
    # Read or write shared memory
    # This prevents race conditions

# 2. Verify array shape
if np_array.shape != self.last_frame_shape:
    print(f"ERROR: Shape mismatch! Expected {self.last_frame_shape}, got {np_array.shape}")

# 3. Make copy before use
frame = np_array.copy()  # Avoid shared memory issues
```

### Issue 3: High Memory Usage

**Symptom:** Memory usage increases over time.

**Possible Causes:**
1. Memory leak in shared memory access
2. Not releasing frames properly
3. Array growing instead of replacing

**Solutions:**
```python
# 1. Verify we're replacing, not appending
np_array[:] = frame[:]  # Replace content, don't append

# 2. Monitor memory over time
# Check memory usage every minute
# Look for leaks

# 3. Use explicit delete
import gc
gc.collect()  # Force garbage collection if needed
```

### Issue 4: Slow Frame Access

**Symptom:** Capture takes too long (>1 second).

**Possible Causes:**
1. Lock contention
2. Copy overhead
3. Slow shared memory access

**Solutions:**
```python
# 1. Reduce lock contention
# Keep lock critical section minimal
with self.last_frame_lock:
    frame = np_array.copy()
# Release lock immediately after copy

# 2. Profile operations
import time
start = time.time()
np_array = np.frombuffer(...)
frame = np_array.copy()
print(f"DEBUG: Shared memory read took {time.time()-start:.3f}s")

# 3. Use buffer if needed
# Consider alternative: SharedMemory vs Array
# Array is slower, SharedMemory is faster for large data
```

## References

- **Multiprocessing Shared Memory:** https://docs.python.org/3/library/multiprocessing.html#sharing-state-between-processes
- **Multiprocessing Array:** https://docs.python.org/3/library/multiprocessing.html#multiprocessing.Array
- **Numpy Shared Memory:** https://numpy.org/doc/stable/reference/routines.char.html#numpy.frombuffer
- **Shared Memory vs Queues:** Shared memory for read-heavy, queues for passing messages

---

**Version:** 1.0.0
**Status:** Planned (not yet implemented)
**Memory Impact:** +231 KB
**Target:** v2.1.0
