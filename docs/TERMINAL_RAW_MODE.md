# Terminal Raw Mode Fix

## Problem

Current `check_for_capture()` method uses `select.select()` with `sys.stdin.read(1)`, which doesn't work in line-buffered terminal mode.

**Symptoms:**
- Pressing 't' alone does nothing
- User must press 't' + Enter to trigger capture
- Input is ignored until Enter is pressed

**Root Cause:**
- Terminal operates in **canonical mode** (line-buffered)
- Input is buffered until carriage return (Enter)
- `select.select([sys.stdin], [], [], 0)` detects data is available
- But `sys.stdin.read(1)` still blocks waiting for Enter
- Line buffering is handled at OS/terminal level, not Python level

## Solution: Raw Terminal Mode

Switch terminal to **raw mode** temporarily during key detection.

### What is Raw Mode?

**Terminal Modes Explained:**

| Mode | Behavior | Example |
|-------|-----------|----------|
| **Canonical (Line-Buffered)** | Waits for Enter | Type "t" → nothing, press Enter → "t" appears |
| **Raw (Character-Buffered)** | Immediate input | Type "t" → "t" immediately |

**Additional Settings:**
- **Echo:** Show characters as typed (on in canonical, off in raw)
- **Special Keys:** Process special keys (Ctrl+C, etc.) - handled differently in raw mode

### Implementation

```python
import sys
import termios
import tty

def check_for_capture_raw_mode(self):
    """
    Check for 't' key using raw terminal mode.
    This bypasses line buffering and works immediately.
    """
    try:
        # Save current terminal settings
        old_settings = termios.tcgetattr(sys.stdin)
        
        # Set raw mode:
        # - Disable line buffering (character-by-character)
        # - Disable echo (don't show character twice)
        # - Disable special key processing (Ctrl+C, etc.)
        tty.setraw(sys.stdin.fileno())
        
        # Read single character
        # In raw mode, this returns immediately without waiting for Enter
        key = sys.stdin.read(1)
        
        # Restore terminal settings:
        # - Re-enable line buffering
        # - Re-enable echo
        # - Re-enable special keys
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_settings)
        
        # Check if character is 't'
        if key.lower() == 't':
            return True
        
        return False
        
    except Exception as e:
        print(f"Terminal raw mode error: {e}")
        # Terminal settings restored in finally block
        return False
```

### How it Works

**Step-by-Step Process:**

1. **Save Current State:**
   - `termios.tcgetattr(sys.stdin)` saves all terminal attributes
   - Stores echo mode, buffering mode, special key handling

2. **Switch to Raw Mode:**
   - `tty.setraw(sys.stdin.fileno())` changes terminal settings
   - Disables line buffering → single character input
   - Disables echo → prevents character being shown twice
   - Disables special keys → Ctrl+C and others pass as characters

3. **Read Character:**
   - `sys.stdin.read(1)` reads immediately (no waiting for Enter)
   - Returns character as soon as user types it

4. **Restore Terminal:**
   - `termios.tcsetattr(..., termios.TCSADRAIN, old_settings)`
   - TCSADRAIN = drain input (discard any buffered input)
   - Restores original settings completely

5. **Check Key:**
   - Simple string comparison: `key.lower() == 't'`
   - Returns True if 't' was pressed

### Code Flow Diagram

```
User types 't'
    ↓
[Terminal in canonical mode]
    ↓
Character sits in buffer (not sent to Python)
    ↓
User presses Enter
    ↓
Buffer flushed to Python
    ↓
Python receives 't'
    ↓
Trigger capture

VS

User types 't'
    ↓
[Terminal switched to raw mode]
    ↓
Character immediately sent to Python
    ↓
Python receives 't' immediately
    ↓
Trigger capture
    ↓
[Terminal restored to canonical mode]
```

## Implementation Details

### Error Handling

```python
try:
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setraw(sys.stdin.fileno())
    key = sys.stdin.read(1)
    termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_settings)
except termios.error as e:
    print(f"Terminal error: {e}")
    # Settings restored in finally
except IOError as e:
    print(f"IO error: {e}")
    # Settings restored in finally
except Exception as e:
    print(f"Unexpected error: {e}")
    # Settings restored in finally
finally:
    # Ensure settings are always restored
    try:
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_settings)
    except:
        pass
```

### Platform Considerations

**Linux/Unix (Raspberry Pi):**
- ✅ Termios works natively
- ✅ Tty module available
- ✅ Raw mode fully supported

**Windows/Mac:**
- ❌ Termios not available (platform-specific)
- ❌ Requires different approach (msvcrt on Windows)

**Cross-Platform Solution:**
```python
import sys
import platform

def check_for_capture_cross_platform(self):
    """Cross-platform key detection"""
    try:
        if platform.system() == 'Linux':
            return self._check_for_capture_linux()
        elif platform.system() == 'Darwin':  # macOS
            return self._check_for_capture_linux()  # Same approach
        elif platform.system() == 'Windows':
            return self._check_for_capture_windows()  # Different approach
        else:
            return self._check_for_capture_fallback()
    except Exception as e:
        print(f"Platform-specific error: {e}")
        return self._check_for_capture_fallback()

def _check_for_capture_linux(self):
    """Linux/Unix implementation with raw mode"""
    # Raw mode implementation...
    pass

def _check_for_capture_windows(self):
    """Windows implementation"""
    import msvcrt
    key = msvcrt.getch()  # Windows-specific
    if key.lower() == 't':
        return True
    return False

def _check_for_capture_fallback(self):
    """Fallback: use select.select (current broken approach)"""
    if select.select([sys.stdin], [], [], 0)[0]:
        key = sys.stdin.read(1)
        if key.lower() == 't':
            return True
    return False
```

## Testing

### Test Cases

**Test 1: Immediate 't' Key**
```bash
# Expected: Capture triggers immediately
python3 camera_tft_optimized.py
# Type 't' (no Enter)
# Should see: "✓ Image saved: ..."
```

**Test 2: Terminal Restoration**
```bash
# Expected: Terminal works normally after key press
python3 camera_tft_optimized.py
# Press 't'
# Capture should happen
# Try typing other commands - they should work
# Echo should be working
```

**Test 3: Multiple Key Presses**
```bash
# Expected: Each 't' triggers new capture
python3 camera_tft_optimized.py
# Press 't' (capture 1)
# Press 't' (capture 2)
# Press 't' (capture 3)
# Should see 3 captures
```

**Test 4: Error Recovery**
```bash
# Expected: Terminal still works on errors
python3 camera_tft_optimized.py
# Press 't' repeatedly to test error handling
# Verify terminal isn't corrupted
# Verify no echo issues
```

### Debug Output

```python
def check_for_capture_raw_mode_debug(self):
    """Debug version with logging"""
    print("DEBUG: Waiting for key press...")
    
    old_settings = termios.tcgetattr(sys.stdin)
    print(f"DEBUG: Original settings: {old_settings}")
    
    tty.setraw(sys.stdin.fileno())
    print("DEBUG: Switched to raw mode")
    
    key = sys.stdin.read(1)
    print(f"DEBUG: Key pressed: '{key}' (ord: {ord(key)})")
    
    termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_settings)
    print("DEBUG: Restored terminal settings")
    
    return key.lower() == 't'
```

## Troubleshooting

### Issue 1: Terminal Corrupted

**Symptom:** Terminal shows wrong behavior after key press.

**Solution:**
- Ensure terminal settings are restored in `finally` block
- Use `termios.TCSADRAIN` flag to flush input buffer
- Don't exit application before restoring

### Issue 2: Character Shows Twice

**Symptom:** 'tt' shows when you type 't' (echo).

**Cause:** Echo is still enabled in raw mode.

**Solution:**
- Raw mode should disable echo (built-in behavior)
- If persists, manually disable in code:
```python
# After setraw, ensure echo is off
import fcntl
old = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
fcntl.fcntl(sys.stdin, fcntl.F_SETFL, old & ~termios.ECHO)
```

### Issue 3: Ctrl+C Not Working

**Symptom:** Ctrl+C doesn't work after raw mode.

**Cause:** Raw mode disables special key processing.

**Solution:**
- This is expected behavior in raw mode
- We're only reading one character, Ctrl+C is handled differently
- Main loop's KeyboardInterrupt handler should still work
- Or press specific quit key (like 'q')

### Issue 4: Works on Terminal But Not in Script

**Symptom:** Terminal shows correct behavior, but script still doesn't work.

**Cause:** Input might be redirected or piped.

**Solution:**
- Check if stdin is a TTY: `sys.stdin.isatty()`
- If False, use fallback approach
- Provide clear error message

## References

- **Termios Manual:** `man termios` (on Linux)
- **Tty Manual:** `man tty` (on Linux)
- **Python termios module:** https://docs.python.org/3/library/termios.html
- **Python tty module:** https://docs.python.org/3/library/tty.html
- **Terminal I/O:** https://www.tldp.org/HOWTO/Bash-Prompt-HOWTO/x364.html

---

**Version:** 1.0.0
**Status:** Planned (not yet implemented)
**Target:** v2.1.0
