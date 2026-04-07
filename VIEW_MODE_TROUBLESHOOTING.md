# View Mode Troubleshooting Guide

## Quick Diagnostic Commands

When you run the app and enter View Mode (press 'm'), you should see debug output in the terminal starting with `[MediaBrowser]`.

## Expected Debug Output

### When Entering View Mode
```
[MediaBrowser] Initialized with display size: (128, 160)
[MediaBrowser] Found 5 files:
  - video_0407_173001.mp4
  - capture_0407_172945.png
  - ...
```

### When Navigating to a Video
```
[MediaBrowser] Getting thumbnail: video_0407_173001.mp4
[MediaBrowser] Processing as VIDEO: video_0407_173001.mp4
[MediaBrowser] Extracting video thumbnail: video_0407_173001.mp4
[MediaBrowser] Target size: 128x160
[MediaBrowser] Running ffmpeg...
[MediaBrowser] FFmpeg return code: 0
[MediaBrowser] Video output size: 61440 bytes (expected 61440)
[MediaBrowser] Video thumbnail created successfully
[MediaBrowser] Thumbnail created: (128, 160)
```

### When Navigating to an Image
```
[MediaBrowser] Getting thumbnail: capture_0407_172945.png
[MediaBrowser] Processing as IMAGE: capture_0407_172945.png
[MediaBrowser] Original image size: (640, 480), mode: RGB
[MediaBrowser] Resized to: (128, 160)
[MediaBrowser] Thumbnail created: (128, 160)
```

## Common Issues & Solutions

### Issue 1: Videos Not Showing in Counter
**Symptom**: Only images counted, videos ignored

**Solution**:
- Check if your videos are `.mp4` or `.mkv` format
- Debug output should show video files in "Found X files:" list
- If not shown, check they're in `~/Pictures/captures/` directory

**Check**:
```bash
ls -lh ~/Pictures/captures/
```

### Issue 2: Black Screen When Viewing Videos
**Symptom**: Entire screen black, only text overlays show

**Causes**:
1. FFmpeg not installed
2. FFmpeg can't read the video file
3. Video corruption

**Solution**:
- Check FFmpeg is installed:
```bash
ffmpeg -version
```
- If not installed:
```bash
sudo apt update
sudo apt install ffmpeg
```

**Debug Clues**:
- "FFmpeg not found" → Install ffmpeg
- "FFmpeg return code: 1" → Video file issue
- "Size mismatch" → Video format not supported

### Issue 3: Black Bar on Display
**Symptom**: Black bar on left or right side of display

**Solution**:
- Check debug output shows: `Resized to: (128, 160)`
- If showing correct size, the issue is with image paste operation
- Restart the app to clear thumbnail cache

**Debug Clues**:
```
[MediaBrowser] Resized to: (128, 160)  ← Should be this
```
If showing `(100, 75)` or anything else, the resize is wrong.

### Issue 4: Videos Show "VIDEO" Placeholder
**Symptom**: Gray screen with "VIDEO" text instead of actual video frame

**Cause**: Video thumbnail extraction failed but fallback kicked in

**Solution**:
- Check the debug output for the specific error
- Common errors:
  - "No output from ffmpeg"
  - "Size mismatch"
  - "FFmpeg failed with code X"

**Try**:
```bash
# Test if ffmpeg can read the video manually
ffmpeg -i ~/Pictures/captures/your_video.mp4 -vframes 1 -vf scale=128:160 /tmp/test.png
```

If this command works, there might be a pipe issue. Try using a temp file instead:
1. Extract to temp file first
2. Load from temp file
3. Delete temp file

### Issue 5: No Debug Output
**Symptom**: No `[MediaBrowser]` messages in terminal

**Cause**: View mode not being entered or media_browser not being called

**Solution**:
- Make sure you're pressing 'm' + Enter (not just 'm')
- Check terminal shows "Entering VIEW MODE" message
- If not, the app is still in live mode

## Manual Testing

### Test FFmpeg Manually
```bash
cd ~/Pictures/captures

# Test with your video file
ffmpeg -hide_banner -i your_video.mp4 -vframes 1 -vf scale=128:160 -f image2pipe -pix_fmt rgb24 -vcodec rawvideo - > /tmp/test.rgb

# Check file size
ls -lh /tmp/test.rgb
# Should be exactly 61440 bytes (128*160*3)

# Clean up
rm /tmp/test.rgb
```

### Test PIL Image Loading
```bash
cd ~/Pictures/captures

python3 << 'EOF'
from PIL import Image
import sys

img = Image.open('your_video.png')
print(f"Original size: {img.size}, mode: {img.mode}")

resized = img.resize((128, 160), Image.Resampling.LANCZOS)
print(f"Resized to: {resized.size}")
EOF
```

## Advanced Troubleshooting

### Enable More Verbose FFmpeg Logging
In `media_browser.py`, change:
```python
stderr=subprocess.PIPE,  # Current: captures for debugging
```
to:
```python
stderr=None,  # Show all ffmpeg output in terminal
```

### Check File Permissions
```bash
# Check if files are readable
ls -l ~/Pictures/captures/

# Should show -rw-r--r-- or -rw-rw-r--
# If showing other permissions, fix:
chmod 644 ~/Pictures/captures/*
```

### Check Disk Space
```bash
df -h ~/Pictures/captures/
```

If disk is full, thumbnail generation will fail.

## Summary Checklist

When you experience issues, check these in order:

1. ✅ Videos are in `.mp4` or `.mkv` format
2. ✅ Videos are in `~/Pictures/captures/` directory
3. ✅ FFmpeg is installed (`ffmpeg -version`)
4. ✅ Debug output shows files being found
5. ✅ Debug output shows correct display size (128, 160)
6. ✅ No file permission issues
7. ✅ Sufficient disk space

If all checks pass but issues persist, copy the full debug output (all `[MediaBrowser]` lines) for further diagnosis.
