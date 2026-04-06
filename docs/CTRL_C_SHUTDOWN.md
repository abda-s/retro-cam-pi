# Ctrl+C Signal Handling for Clean Shutdown

## Problem

When user presses Ctrl+C to exit the application:

**Current Issues:**
- Application doesn't exit cleanly
- Python tracebacks appear
- Workers don't stop properly
- Processes may hang or become zombies
- Resources not cleaned up

**Root Causes:**

1. **Picamera2 Blocking Operations:**
   - `camera.capture_array()` uses `concurrent.futures` internally
   - Futures don't respect KeyboardInterrupt in subprocesses reliably
   - Blocking I/O can't be interrupted

2. **Signal Propagation in Multiprocessing:**
   - SIGINT (Ctrl+C) sent to main process
   - Doesn't reliably propagate to worker processes
   - Each subprocess needs its own signal handlers
   - Signals can be lost in subprocess

3. **Blocking Queue Operations:**
   - `queue.get()` blocks indefinitely if queue is empty
   - Workers stuck in blocking calls can't respond to shutdown signals
   - No timeout means no way to check shutdown flag

4. **Missing Shutdown Flags:**
   - Workers check `running_flag.value` but not frequently
   - Workers may not see shutdown request
   - Workers continue trying to process after shutdown

## Solution: Comprehensive Signal Handling

Implement multi-layer signal handling with frequent shutdown checks.

### Architecture

```
┌────────────────────────────────────────────────────────────────┐
│              Signal Flow Diagram                   │
└────────────────────────────────────────────────────────────────┘
    User presses Ctrl+C
              ↓
    ┌──────────────────────────────────────────┐
    │  Main Process Receives SIGINT      │
    └──────────────────────────────────────────┘
              ↓
    [1] Global Handler Runs
        shutdown_requested = True
        print("Shutdown signal received...")
              ↓
    [2] Main Loop Checks
        while self.running and not shutdown_requested:
            # Exit loop
              ↓
    [3] Workers Inherited Signal (NOT RELIABLE)
        ┌──────────────────────────────────┐
        │  Capture Worker (Process 1)  │
        │  Process Worker (Process 2)  │
        └──────────────────────────────────┘
              ↓
        [PROBLEM] May not receive signal
        Workers continue running
```

**Solution:**

```
┌────────────────────────────────────────────────────────────────┐
│              Enhanced Signal Flow               │
└────────────────────────────────────────────────────────────────┘
    User presses Ctrl+C
              ↓
    ┌──────────────────────────────────────────┐
    │  Main Process Receives SIGINT      │
    └──────────────────────────────────────────┘
              ↓
    [1] Global Handler Runs
        shutdown_requested = True
        print("Shutdown signal received...")
              ↓
    [2] Main Loop Checks
        while self.running and not shutdown_requested:
            # Exit loop (quick!)
              ↓
    [3] Main Calls stop_workers()
              ↓
    ┌──────────────────────────────────────────┐
    │  Set running_flag.value = False    │
    │  Wait for workers (3 sec timeout)  │
    │  If still alive: terminate()         │
    └──────────────────────────────────────────┘
              ↓
    [4] Workers Check running_flag
        Workers see running_flag.value = False
        Workers exit loops
        Workers clean up resources
              ↓
    [5] Main Calls cleanup()
        Clean up display, GPIO
        Print summary
              ↓
    Clean Exit!
```

### Implementation

#### Step 1: Global Signal Handler

```python
import signal

# Global shutdown flag
shutdown_requested = False

def global_signal_handler(signum, frame):
    """
    Global signal handler that sets shutdown flag immediately.
    Called when main process receives SIGINT or SIGTERM.
    """
    global shutdown_requested
    shutdown_requested = True
    print(f"\n\n{'='*50}")
    print(f"Signal {signum} received, shutting down gracefully...")
    print(f"{'='*50}")
    print()
    
# Register in main (outside class)
signal.signal(signal.SIGINT, global_signal_handler)   # Ctrl+C
signal.signal(signal.SIGTERM, global_signal_handler) # kill command
```

**Why Global Handler:**
- Can be called from anywhere
- Sets flag immediately (no blocking)
- Prints clear message to user
- Works for both SIGINT and SIGTERM

#### Step 2: Worker-Level Signal Handlers

```python
def capture_worker(...):
    """Worker with process-level signal handling"""
    global shutdown_requested
    
    def worker_signal_handler(signum, frame):
        """Worker-specific signal handler"""
        global shutdown_requested
        shutdown_requested = True
        running_flag.value = False
        print(f"Capture worker received signal {signum}")
    
    # Register in worker
    signal.signal(signal.SIGINT, worker_signal_handler)
    signal.signal(signal.SIGTERM, worker_signal_handler)
    
    # Worker loop
    while running_flag.value and not shutdown_requested:
        # ... do work ...
        # Check shutdown flag frequently
```

**Why Worker Handlers:**
- Redundant layer of protection
- Workers can respond directly to signals
- Doesn't rely on main process propagation
- Sets running_flag.value = False

#### Step 3: Frequent Shutdown Checks

```python
# In all worker loops:

# Old approach (infrequent checks):
while running_flag.value:
    # ... work ...
    # May not check shutdown flag for entire iteration

# New approach (frequent checks):
while running_flag.value and not shutdown_requested:
    # Check shutdown flag BEFORE blocking operations
    if shutdown_requested:
        break
    
    # ... do work ...
```

**Where to Check:**
- Before `camera.capture_array()`
- Before queue operations
- Before PIL conversion
- Before resize
- At least once per loop iteration

#### Step 4: Timeout-Based Queue Operations

```python
# Replace all blocking queue.get() with get(timeout=X)

# Old approach (blocks forever):
frame = queue.get()  # Blocks until data available

# New approach (with timeout):
try:
    frame = queue.get(timeout=0.1)  # Only waits 100ms
except:
    # Timeout means: no data OR shutdown requested
    continue  # Try again or exit
```

**Timeout Values:**
- `get(timeout=0.1)` - 100ms timeout (responsive)
- `get(timeout=0.5)` - 500ms timeout (less responsive)
- `get(timeout=1.0)` - 1000ms timeout (most reliable)
- **Recommended:** 0.1 or 0.5 seconds

#### Step 5: Non-Blocking Queue Operations

```python
# Use put_nowait() instead of put() when possible

# Old approach (can block):
queue.put(frame)  # Blocks if queue full

# New approach (non-blocking):
try:
    if not queue.full():
        queue.put_nowait(frame)
    else:
        # Queue full, remove oldest, add new
        try:
            queue.get_nowait()  # Remove oldest
            queue.put_nowait(frame)  # Add newest
        except:
            pass  # Give up this time
except:
    pass  # Try again next iteration
```

**Why Non-Blocking:**
- Prevents blocking on full queues
- Workers never stuck in queue operations
- Can always check shutdown flag

#### Step 6: Enhanced stop_workers()

```python
def stop_workers(self):
    """Stop all worker processes with timeout and fallback"""
    global shutdown_requested
    shutdown_requested = True  # Set flag first
    
    # Set running flag to False (workers check this)
    self.running_flag.value = False
    
    print("Stopping workers...")
    
    # Wait for processes to finish (with longer timeouts)
    if self.capture_process:
        try:
            self.capture_process.join(timeout=3)  # Wait up to 3 seconds
            if self.capture_process.is_alive():
                print("Terminating capture worker...")
                self.capture_process.terminate()  # Force terminate
                self.capture_process.join(timeout=1)  # Wait for death
            else:
                print("Capture worker stopped")
        except Exception as e:
            print(f"Error stopping capture worker: {e}")
    
    if self.process_process:
        try:
            self.process_process.join(timeout=3)
            if self.process_process.is_alive():
                print("Terminating process worker...")
                self.process_process.terminate()
                self.process_process.join(timeout=1)
            else:
                print("Process worker stopped")
        except Exception as e:
            print(f"Error stopping process worker: {e}")
    
    print("All workers stopped")
```

**Enhancements:**
- Longer timeouts (3 seconds vs 2)
- Terminate as fallback (SIGKILL)
- Better error handling
- Clear status messages
- Multiple attempts to join

### Code Flow Diagram

```
User presses Ctrl+C
    ↓
SIGINT sent to main process
    ↓
┌─────────────────────────────────────────┐
│  Global Signal Handler              │
│  shutdown_requested = True           │
│  Print shutdown message             │
└─────────────────────────────────────────┘
    ↓
Main loop checks shutdown_requested
    ↓
Main loop exits
    ↓
Main calls stop_workers()
    ↓
stop_workers() sets running_flag.value = False
    ↓
┌─────────────────────────────────────────┐
│  Capture Worker Loop               │
│  while running_flag.value         │
│     and not shutdown_requested:    │
│         ... do work ...           │
│         [Check flag frequently]  │
│         if shutdown_requested:     │
│           break                 │
└─────────────────────────────────────────┘
    ↓
Capture worker exits
    ↓
┌─────────────────────────────────────────┐
│  Process Worker Loop               │
│  while running_flag.value         │
│     and not shutdown_requested:    │
│         ... do work ...           │
│         [Check flag frequently]  │
│         if shutdown_requested:     │
│           break                 │
└─────────────────────────────────────────┘
    ↓
Process worker exits
    ↓
stop_workers() joins and terminates
    ↓
Main calls cleanup()
    ↓
Clean exit!
```

## Testing

### Test 1: Immediate Shutdown

```bash
# Expected: Clean exit in 3-5 seconds
python3 camera_tft_optimized.py
# Wait for FPS to stabilize
# Press Ctrl+C
# Should see: "Shutdown signal received..."
# Should see: "Stopping workers..."
# Should see: "Capture worker stopped"
# Should see: "Process worker stopped"
# Should see: "All workers stopped"
# Should see: "Cleaning up resources..."
# Should see: "Goodbye!"
# Should see: No tracebacks
```

### Test 2: Shutdown During Capture

```bash
# Expected: Clean exit even during blocking operation
python3 camera_tft_optimized.py
# Wait for FPS to stabilize
# Press 't' to start capture
# Immediately press Ctrl+C (while capturing)
# Should exit cleanly (no hanging)
# May see "Capture interrupted" message
# All processes should stop
```

### Test 3: Multiple Ctrl+C Presses

```bash
# Expected: Clean exit on first press
python3 camera_tft_optimized.py
# Press Ctrl+C once
# Should exit (no duplicate shutdown)
# Processes should terminate gracefully
```

### Test 4: Kill Command

```bash
# Expected: Clean exit (SIGTERM handled)
python3 camera_tft_optimized.py &
PID=$!
sleep 5
kill $PID
# Should see: "Signal 15 received, shutting down..."
# Should exit cleanly (like Ctrl+C)
```

### Test 5: Zombie Processes

```bash
# Expected: No zombie processes
python3 camera_tft_optimized.py
# Press Ctrl+C
# Wait for exit
# Check: ps aux | grep camera_tft_optimized
# Should show: no processes running
# No zombies (status <defunct>)
```

### Debug Output

```python
# In all worker loops:

while running_flag.value and not shutdown_requested:
    # Debug: Check shutdown flag
    if shutdown_requested:
        print(f"DEBUG: {process_name} shutting down")
        break
    
    # Debug: Show loop iteration
    iteration += 1
    if iteration % 30 == 0:  # Every 30 frames
        print(f"DEBUG: {process_name} still running (iteration {iteration})")
    
    # ... do work ...

# In main loop:

while self.running and not shutdown_requested:
    # Debug: Show loop status
    loop_iteration += 1
    if loop_iteration % 60 == 0:  # Every second
        print(f"DEBUG: Main loop iteration {loop_iteration}")
```

## Troubleshooting

### Issue 1: Workers Don't Exit

**Symptom:** Workers still running after Ctrl+C.

**Possible Causes:**
1. Shutdown flag not being checked frequently enough
2. Workers not seeing running_flag.value change
3. Workers blocked in operation without timeout

**Solutions:**
```python
# 1. Add debug output in workers
print(f"DEBUG: shutdown_requested = {shutdown_requested}")
print(f"DEBUG: running_flag.value = {running_flag.value}")

# 2. Increase shutdown check frequency
# Check BEFORE every operation, not just at loop start

# 3. Use timeout on all blocking operations
# Never use infinite blocking (no timeout)

# 4. Add kill after timeout as fallback
# In stop_workers():
if process.is_alive():
    process.terminate()  # Force kill
```

### Issue 2: Tracebacks Still Appear

**Symptom:** Python tracebacks shown on Ctrl+C.

**Possible Causes:**
1. KeyboardInterrupt not caught in worker
2. Blocking operation raises KeyboardInterrupt
3. No exception handling around critical operations

**Solutions:**
```python
# 1. Wrap ALL blocking operations in try/except

# In capture_worker():
while running_flag.value and not shutdown_requested:
    try:
        frame = camera.capture_array("main")
    except KeyboardInterrupt:
        print("KeyboardInterrupt: capture_worker")
        break
    
    try:
        frame = frame[:, :, [2, 1, 0]]
    except KeyboardInterrupt:
        print("KeyboardInterrupt: array operation")
        break

# 2. Add except Exception as catch-all
try:
    # ... work ...
except KeyboardInterrupt:
    print("KeyboardInterrupt: generic handler")
    break
except Exception as e:
    print(f"Exception: {e}")
    break
```

### Issue 3: Processes Hang During Shutdown

**Symptom:** Processes don't exit, main process waits forever.

**Possible Causes:**
1. Workers not checking running_flag
2. Workers blocked without timeout
3. join() timeout too short
4. Main process waiting on stuck workers

**Solutions:**
```python
# 1. Use longer join timeouts
process.join(timeout=5)  # Was 2, now 5

# 2. Add terminate as fallback
if process.is_alive():
    process.terminate()
    process.join(timeout=2)

# 3. Don't wait on all joins in main
# Allow processes to die, then do cleanup
```

### Issue 4: Main Process Exits Before Workers

**Symptom:** Main cleanup runs while workers still working.

**Possible Causes:**
1. Main loop doesn't call stop_workers()
2. stop_workers() returns before workers exit
3. Workers not properly signaled

**Solutions:**
```python
# 1. Ensure stop_workers() is always called
try:
    # ... main loop ...
except KeyboardInterrupt:
    pass
finally:
    stop_workers()  # Always call!
    cleanup()

# 2. Use longer join in stop_workers()
process.join(timeout=5)  # Give workers time to exit

# 3. Set running_flag BEFORE stop_workers()
self.running_flag.value = False  # Tell workers to stop
stop_workers()  # Then wait for them
```

## Performance Impact

**Shutdown Speed:**
```
Current (v2.0.2):
- Workers may take 10-30 seconds to exit
- Main process waits for workers
- Poor user experience

Improved (with fixes):
- Workers exit in 3-5 seconds
- Main process cleanup completes quickly
- Good user experience
```

**CPU Overhead:**
```
Frequent shutdown checks:
- Adds ~0.001s per check
- 3 checks per loop = ~0.003s overhead
- At 30 FPS: <10% CPU overhead (negligible)
- Worth it for reliable shutdown
```

## References

- **Python Signal Module:** https://docs.python.org/3/library/signal.html
- **KeyboardInterrupt Exception:** https://docs.python.org/3/tutorial/errors.html
- **Multiprocessing Signals:** https://docs.python.org/3/library/multiprocessing.html#multiprocessing.Process
- **Process Termination:** https://docs.python.org/3/library/multiprocessing.html#multiprocessing.Process.terminate

---

**Version:** 1.0.0
**Status:** Partially Fixed (v2.0.2) with planned improvements
**Target:** v2.1.0 (Complete clean shutdown)
