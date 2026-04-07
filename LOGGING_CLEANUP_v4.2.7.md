# Logging Reduction - v4.2.7

## What Changed

### Removed Spammy Logs
To reduce terminal log spam during view mode navigation, removed:

1. **`[MediaBrowser] Getting thumbnail: filename`**
   - Was called 30-35 times per second (every frame)
   - Added zero diagnostic value
   - **REMOVED** - Terminal is now much cleaner

2. **`[MediaBrowser] Using cached thumbnail for filename`**
   - Was called 30-35 times per second (every frame)
   - Confirmed cache hit (already obvious)
   - **REMOVED** - Terminal is now much cleaner

### Kept Useful Logs

These logs remain for diagnostics:

1. **Initialization**
   ```
   [MediaBrowser] Initialized with display size: (128, 160)
   ```

2. **File Scanning**
   ```
   [MediaBrowser] Found 15 files:
     - capture_20260407_164357.png
     - ...
   [MediaBrowser] Cache cleared for display size (128, 160)
   ```

3. **Cache Validation**
   ```
   [MediaBrowser] Validating 15 cached thumbnails...
   [MediaBrowser] Target size: (128, 160)
   [MediaBrowser]   INVALID: old_file.png = (100, 75)
   [MediaBrowser]   VALID: new_file.png = (128, 160)
   [MediaBrowser] Cleared 2 invalid thumbnails
   [MediaBrowser] All 13 cached thumbnails are valid
   ```

4. **Image Processing (When Creating New Thumbnails)**
   ```
   [MediaBrowser] Processing IMAGE: new_file.png
   [MediaBrowser] Original image size: (640, 480), mode: RGB
   [MediaBrowser] Resized to: (128, 160)
   [MediaBrowser] Thumbnail created: (128, 160)
   ```

5. **Video Processing (When Creating New Thumbnails)**
   ```
   [MediaBrowser] Processing VIDEO: video_file.mp4
   [MediaBrowser] Extracting video thumbnail: video_file.mp4
   [MediaBrowser] Target size: 128x160
   [MediaBrowser] Running ffmpeg...
   [MediaBrowser] FFmpeg return code: 0
   [MediaBrowser] Video output size: 61440 bytes (expected 61440)
   [MediaBrowser] Video thumbnail created successfully
   ```

6. **Video Placeholder (When Video Extraction Fails)**
   ```
   [MediaBrowser] Created video placeholder for video_file.mp4
   ```

7. **Errors**
   ```
   [MediaBrowser] ERROR: Failed to create thumbnail for filename
   [MediaBrowser] ERROR: Size mismatch! expected X, got Y
   [MediaBrowser] ERROR: No output from ffmpeg
   [MediaBrowser] ERROR: FFmpeg not found - video thumbnails disabled
   [MediaBrowser] Thumbnail ERROR for filename: exception details
   ```

---

## Before and After Comparison

### Before v4.2.7 (Terminal Spam)
```
[MediaBrowser] Initialized with display size: (128, 160)  ← GOOD
[MediaBrowser] Found 15 files:  ← GOOD
  - capture_xxx.png
  ...
[MediaBrowser] Validating 15 cached thumbnails...  ← GOOD
[MediaBrowser] Target size: (128, 160)  ← GOOD
[MediaBrowser]   VALID: capture_xxx.png = (128, 160)  ← GOOD
[MediaBrowser] All 15 cached thumbnails are valid  ← GOOD

[MediaBrowser] Getting thumbnail: capture_xxx.png  ← SPAM (30x/sec!)
[MediaBrowser] Using cached thumbnail for capture_xxx.png  ← SPAM (30x/sec!)
[MediaBrowser] Getting thumbnail: capture_xxx.png  ← SPAM (30x/sec!)
[MediaBrowser] Using cached thumbnail for capture_xxx.png  ← SPAM (30x/sec!)
... (repeats endlessly, floods terminal, can't see other logs)
```

### After v4.2.7 (Clean Output)
```
[MediaBrowser] Initialized with display size: (128, 160)  ← GOOD
[MediaBrowser] Found 15 files:  ← GOOD
  - capture_xxx.png
  ...
[MediaBrowser] Validating 15 cached thumbnails...  ← GOOD
[MediaBrowser] Target size: (128, 160)  ← GOOD
[MediaBrowser] All 15 cached thumbnails are valid  ← GOOD

(silence while navigating - no per-frame spam!)

[MediaBrowser] Processing IMAGE: new_file.png  ← Only when NEW thumbnail created
[MediaBrowser] Original image size: (640, 480), mode: RGB
[MediaBrowser] Resized to: (128, 160)
[MediaBrowser] Thumbnail created: (128, 160)

(silence continues - terminal is usable!)
```

---

## Impact

### Benefits
1. ✅ **Much cleaner terminal** - Can actually see other app logs
2. ✅ **Reduced log spam by ~99%** - Only 2 logs removed, but they were called 30-35 times/sec
3. ✅ **Easier troubleshooting** - Logs now show actual operations, not redundant cache checks
4. ✅ **Better focus** - Can see video processing, cache validation, and errors clearly
5. ✅ **No performance impact** - Just removed 2 print statements

### Terminal Usage
**Before**: Terminal flooded, hard to read, can't see camera/recording logs
**After**: Clean, readable, only meaningful diagnostic output

---

## Version Info

**Version**: 4.2.7
**Release Date**: 2026-04-07
**Changes**: Reduced log spam by removing per-frame cache logs
**Lines removed**: 2 (spammy logs)
**Lines kept**: 20+ (useful diagnostic logs)
