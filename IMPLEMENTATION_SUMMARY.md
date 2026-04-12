# View Saved Footage Mode - Implementation Summary

## Overview
Successfully implemented a new "View Saved Footage" mode for the RPi TFT Camera (v4.2.4). Users can now browse and view saved images and videos directly on the TFT display.

### Version History
- **v4.2.3**: Initial implementation with centered thumbnails
- **v4.2.4**: Full-screen images, fixed video thumbnails, fixed navigation hints visibility
- **v4.2.5**: Added .mp4 support, debug logging, video placeholder fallback
- **v4.2.6**: Smart cache validation, automatic black bar fix

## Files Modified/Created

### New File
- **`src/media_browser.py`** (292 lines)
  - New module for browsing saved media files
  - Handles file scanning, sorting, and thumbnail generation
  - Supports both images (PNG) and videos (MKV)
  - Uses ffmpeg to extract video thumbnails
  - Implements thumbnail caching for performance

### Modified Files

#### 1. `src/main.py`
- Added `MediaBrowser` import and initialization
- Added `_view_mode` state flag
- Added `_media_browser` instance
- Modified input handling:
  - 'm' key toggles between Live and View modes
  - 'n' key navigates to next file (View mode only)
  - 'p' key navigates to previous file (View mode only)
- Added `_render_media_browser()` method for UI rendering
- Modified main loop to handle both modes
- Updated status logging for both modes
- Version updated to 4.2.2

#### 2. `src/display_manager.py`
- Added `draw_browser_overlay()` method
  - Draws file index badge (top right)
  - Draws truncated filename (bottom)
  - Draws file type indicator ([IMAGE]/[VIDEO])
  - Draws navigation hints
- Added `draw_no_files_message()` method
  - Shows "No Files Found" message
  - Shows return to live view hint

#### 3. `src/config_manager.py`
- Added browser configuration:
  - `thumbnail_size = (100, 75)` - Size for video thumbnails
  - `browser_font_size = 10` - Font size for browser UI
  - `show_file_index = True` - Show file index on display

#### 4. `README.md`
- Updated feature list to include View Saved Footage
- Updated controls section with new keys
- Added "What Happens When You Press 'm'" section
- Updated version to 4.2.3
- Updated architecture table (11 modules now)
- Added "New in v4.2.3" section

#### 5. `AGENT.md`
- Updated controls with new keys (m, n, p)

## Features Implemented

### 1. Mode Toggle
- Press 'm' to switch between Live View and View Mode
- Visual feedback when entering/exiting modes
- Live mode pauses camera when entering View mode

### 2. File Browsing
- Automatic scanning of `~/Pictures/captures/` directory
- Finds all `.png`, `.mkv`, and `.mp4` files (v4.2.5 added .mp4)
- Sorts files by modification time (newest first)

### 3. Thumbnail Generation
- **Images**: Load and resize using PIL
- **Videos**: Extract first frame using ffmpeg
- Thumbnails cached for performance
- Size: Full-screen 128x160 (v4.2.4+)
- Placeholder fallback if video extraction fails (v4.2.5)

### 4. Navigation
- 'n' key: Next file
- 'p' key: Previous file
- Wrapping at boundaries (stops at first/last)

### 5. Display UI (128x160 TFT) - Full-Screen Mode
```
┌──────────────────────┐
│                    3/10│  ← File index (y=3)
│                      │
│                      │
│   FULL SCREEN IMAGE   │  ← Covers entire 128x160 (stretched)
│                      │
│                      │
│  video_0407_173045   │  ← Filename (y=125, truncated if needed)
│  [VIDEO]             │  ← Type indicator (y=140)
│ n/p:nav  m:mode     │  ← Navigation hints (y=148)
└──────────────────────┘
```

### 6. Error Handling
- Handles empty capture directory
- Handles corrupted files
- Graceful fallback if ffmpeg not found
- Handles thumbnail generation failures
- **Video placeholder**: Shows "VIDEO" placeholder if thumbnail extraction fails (v4.2.5)
- **Debug logging**: Extensive `[MediaBrowser]` output for troubleshooting (v4.2.5)
- **Smart cache validation**: Auto-detects and fixes mismatched thumbnail sizes (v4.2.6)

## Black Bar Fix (v4.2.6)

### Problem
Cached thumbnails from previous versions (100x75) caused black bars when display expects 128x160.

### Solution
Implemented smart cache validation that:
- Checks each cached thumbnail's size against display dimensions
- Removes only invalid thumbnails (wrong size)
- Keeps valid cached thumbnails (performance)
- Forces rebuild of invalid thumbnails automatically

### Validation Process
1. Browser scans directory for files
2. Cache validation runs automatically
3. Each cached thumbnail is checked:
   - `INVALID`: Size doesn't match display → removed from cache
   - `VALID`: Size matches display → kept in cache
4. Detailed logging shows validation results
5. Invalid thumbnails are rebuilt at correct size when viewed

### Example Validation Output
```
[MediaBrowser] Validating 15 cached thumbnails...
[MediaBrowser] Target size: (128, 160)
[MediaBrowser]   INVALID: old_image.png = (100, 75)
[MediaBrowser]   INVALID: old_video.mp4 = (100, 75)
[MediaBrowser]   VALID: new_image.png = (128, 160)
[MediaBrowser] Cleared 2 invalid thumbnails
[MediaBrowser] All 13 cached thumbnails are valid
```

### Benefits
- ✅ Automatic fix - no user action required
- ✅ Selective rebuild - only invalid thumbnails regenerated
- ✅ Preserves cache - valid thumbnails stay cached
- ✅ Detailed logging - shows exactly what's being fixed
- ✅ Performance - doesn't clear entire cache unnecessarily

## Key Controls

| Key | Live Mode | View Mode |
|-----|-----------|-----------|
| t   | Capture image | - |
| v   | Toggle video | - |
| m   | Enter view mode | Return to live |
| n   | - | Next file |
| p   | - | Previous file |
| Ctrl+Z | Exit app | Exit app |

## Technical Details

### Video Thumbnail Extraction
Uses ffmpeg subprocess to extract first frame:
```bash
ffmpeg -i video.mkv -vframes 1 -vf scale=128:160 -f image2pipe -pix_fmt rgb24 -vcodec rawvideo -
```
- Extracts first frame only
- Resizes to full display size (128x160)
- Outputs raw RGB bytes (128*160*3 = 61,440 bytes)
- Converts to PIL Image via numpy
- Validates output size before conversion

### Performance Considerations
- **View mode**: Camera feed paused (saves CPU)
- **Thumbnail caching**: Avoids repeated extractions
- **Lazy loading**: Thumbnails loaded on-demand
- **Temporary directory**: Uses Python tempfile for video thumbs

### Thread Safety
- Browser operations in main thread only
- No shared state between processes
- Local thumbnail cache (no IPC needed)

## Testing Recommendations

1. **Basic Navigation**:
   - [ ] Toggle modes with 'm'
   - [ ] Navigate with 'n' and 'p'
   - [ ] View multiple files

2. **Image Viewing**:
   - [ ] View PNG images
   - [ ] Verify thumbnails display correctly
   - [ ] Check filename truncation

3. **Video Viewing**:
   - [ ] View MKV videos
   - [ ] Verify first frame displayed
   - [ ] Check [VIDEO] indicator

4. **Edge Cases**:
   - [ ] Test with no files (empty directory)
   - [ ] Test with only images
   - [ ] Test with only videos
   - [ ] Test with corrupted files

5. **Performance**:
   - [ ] Check navigation speed
   - [ ] Verify thumbnail caching works
   - [ ] Check memory usage

## Dependencies

No new Python dependencies required. Uses existing:
- PIL (Pillow) - Image processing
- subprocess - ffmpeg for video thumbs
- tempfile - Temporary file management
- numpy - Raw video frame handling

Note: ffmpeg must be installed on the Pi (already required for audio recording).

## Future Enhancements (Optional)

1. **Delete files** from view mode ('d' key)
2. **Playback videos** on external display
3. **Filter by type** (images/videos only)
4. **Toggle sort order** ('s' key)
5. **Fullscreen thumbnail** mode
6. **File info display** (size, timestamp)

## Notes

- Video thumbnails require ffmpeg installation
- Temporary video thumbnails are cleaned up on exit
- Files sorted by modification time, not filename
- Index is 1-based (first file = 1/10)
- Filename truncated if too long for display width
- Images stretched to fill screen (may affect aspect ratio)

## Version

- **Version**: 4.2.8
- **Release Date**: 2026-04-12
- **Lines of code modified**: ~100
- **Files modified**: 2

---

# Video Processing with Filter - Implementation Summary

## Overview
Implemented video + audio recording with separate processing chain (v4.2.8).

### Version History
- **v4.2.8**: Video processing with filter chaining (current)

## Files Modified

### 1. `src/camera_worker.py`
- Fixed indentation throughout file
- Fixed `ffmpeg_merge()` to return `thread` object (was broken - undefined variable reference)
- Added `import threading` at top of file
- Function now properly returns the thread for chaining

### 2. `src/video_filter_processor.py`
- Changed PyAV FPS detection from `in_stream.rate` to `in_stream.average_rate`
- Added fallback value (30 fps) when average_rate is None
- Fixed: `fps = int(in_stream.average_rate) if in_stream.average_rate else 30`

## Video Processing Chain

```
stop_recording()
  │
  ├── 1. ffmpeg_merge(video_path, audio_path, temp_merged)
  │     - Runs in background thread
  │     - Merges video + audio using ffmpeg
  │     - Creates .complete flag on success
  │     - Returns thread object
  │     - Deletes original files after merge
  │
  └── 2. process_video_in_background(temp_merged, final_path, filter_index)
        - Receives ffmpeg_thread
        - Waits for thread.is_alive() == False (max 30 seconds)
        - Checks .complete flag
        - Then runs apply_filter_to_video()
              - Opens video with PyAV
              - Reads fps from average_rate
              - Applies filter frame by frame
              - Saves to .mp4
```

### Chain Working (confirmed from logs)
```
08:51:12 | FFmpeg merge thread started
08:51:12 | VideoFilter: Waiting for ffmpeg to finish...
08:51:15 | FFmpeg merge complete
08:51:15 | VideoFilter: ffmpeg thread finished after 2.5s
08:51:15 | VideoFilter: ffmpeg complete flag found
```

## Known Issue: Muxing Error

### Error
```
av.error.ValueError: [Errno 22] Invalid argument: '...filtered.mp4'
  at out_container.mux(out_packet)
```

### Root Cause
Output stream `time_base` is not configured.

### Fix (Pending)
Add to `apply_filter_to_video()` in `video_filter_processor.py`:
```python
from fractions import Fraction

out_stream = out_container.add_stream('h264', rate=fps)
out_stream.width = width
out_stream.height = height
out_stream.pix_fmt = 'yuv420p'
out_stream.time_base = Fraction(1, fps)  # ADD THIS
```

## Code Changes

### camera_worker.py Changes
```python
# BEFORE (broken):
def ffmpeg_merge(video_path, audio_path, output_path) -> None:
    ...
    def run_ffmpeg():
        ...
        return thread  # ERROR: thread not defined in this scope
    
    thread = threading.Thread(target=run_ffmpeg, daemon=False)
    thread.start()
    # Never returns anything!

# AFTER (fixed):
def ffmpeg_merge(video_path, audio_path, output_path) -> threading.Thread:
    ...
    def run_ffmpeg():
        ...
        return  # Just return cleanly
    
    thread = threading.Thread(target=run_ffmpeg, daemon=False)
    thread.start()
    return thread  # Proper return
```

### video_filter_processor.py Changes
```python
# BEFORE (broken):
fps = in_stream.rate  # AttributeError: 'VideoStream' has no 'rate'

# AFTER (fixed):
fps = int(in_stream.average_rate) if in_stream.average_rate else 30
```

## Testing Results

| Test | Status |
|------|--------|
| Video recording start | ✅ Works |
| Audio recording | ✅ Works |
| FFmpeg merge | ✅ Works |
| Thread chaining | ✅ Works |
| Filter processing start | ❌ Fails at muxing |
| Complete pipeline | ❌ Pending fix |
