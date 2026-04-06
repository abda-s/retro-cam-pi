# KeyboardInterrupt Handling Fixes

## Problem

When pressing Ctrl+C, the application would hang and show Python tracebacks because:
1. camera.capture_array() is a blocking I/O operation
2. Workers couldn't gracefully exit while in blocking calls
3. KeyboardInterrupt wasn't caught properly

## Solution

Added try/except KeyboardInterrupt around all blocking operations:

### In capture_worker():
- camera.capture_array() wrapped in try/except
- Checks shutdown_requested more frequently
- Better error messages

### In process_worker():
- PIL Image.fromarray() wrapped in try/except
- frame.resize() wrapped in try/except
- Checks shutdown_requested more frequently

### In main run():
- Explicit KeyboardInterrupt exception handling
- Clearer shutdown messages
- Better error feedback

## Testing

After this fix, Ctrl+C should:
1. Show: "KeyboardInterrupt - Shutting down gracefully"
2. Stop all workers within 3-5 seconds
3. Clean shutdown with no tracebacks
4. Display: "All workers stopped" message


