# Quick Start Guide - Testing View Saved Footage Mode

## Prerequisites

Ensure you have some test files in `~/Pictures/captures/`:
```bash
# Check if files exist
ls -lh ~/Pictures/captures/

# If empty, create test images first
cd ~/Pictures/captures/
```

## Step-by-Step Testing

### 1. Connect to Pi
```bash
ssh cam@192.168.1.112
```

### 2. Run the Application
```bash
cd ~/rpi-tft-camera/src
python3 main.py
```

### 3. Create Test Files (if needed)

#### Option A: Capture Real Content
1. Press 't' + Enter - Capture 3-5 images
2. Press 'v' + Enter - Record a short video (2-3 seconds)
3. Press 'v' + Enter - Stop recording

#### Option B: Create Test Images
```bash
cd ~/Pictures/captures/
python3 << 'EOF'
from PIL import Image, ImageDraw
import time

colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255)]
for i, color in enumerate(colors, 1):
    img = Image.new('RGB', (640, 480), color)
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), f"Test Image {i}", fill=(255, 255, 255))
    timestamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime(time.time() - (6-i)*60))
    img.save(f"capture_{timestamp}.png")
print("Created 5 test images")
EOF
```

### 4. Test View Mode

#### Enter View Mode
- Press **'m'** + Enter
- Display should show: "VIEW MODE" overlay
- Camera feed should pause
- First file should appear with thumbnail

#### Navigate Files
- Press **'n'** + Enter - Go to next file
- Press **'n'** + Enter - Go to next file
- Press **'p'** + Enter - Go back to previous file
- Observe:
  - File index changes (e.g., "1/10" → "2/10")
  - Image/video fills entire screen (128x160)
  - Filename changes
  - Type indicator shows [IMAGE] or [VIDEO]
  - **Navigation hints "n/p:nav m:mode" visible at bottom**

### Verify Video Thumbnails
- Navigate to a video file (.mkv)
- Observe:
  - First frame of video displayed full-screen
  - [VIDEO] indicator appears
  - No error messages in terminal
  - Black screen should NOT appear

#### Return to Live View
- Press **'m'** + Enter
- Display should show: "LIVE VIEW" overlay
- Camera feed should resume

### 5. Test Edge Cases

#### Empty Directory
```bash
# Temporarily move files
mkdir ~/Pictures/captures_backup
mv ~/Pictures/captures/* ~/Pictures/captures_backup/

# Test view mode (should show "No Files Found")
# Press 'm' → should show no files message
# Press 'm' → return to live

# Restore files
mv ~/Pictures/captures_backup/* ~/Pictures/captures/
rmdir ~/Pictures/captures_backup
```

#### Large File Names
- Capture an image → long timestamp filename
- Enter view mode
- Verify filename truncated properly (ends with "...")

#### Videos Only
- Delete all PNG files
- Keep only MKV files
- Enter view mode
- Verify [VIDEO] indicator appears

## Expected Behavior

### View Mode Display
```
┌──────────────────────┐
│                    3/10│  ← File count (right-aligned)
│                      │
│                      │
│   FULL SCREEN IMAGE   │  ← Full 128x160, stretched
│                      │
│                      │
│  capture_0407_170001  │  ← Filename (truncated if too long)
│  [IMAGE]             │  ← Type: [IMAGE] or [VIDEO]
│ n/p:nav  m:mode      │  ← Navigation hints (visible at bottom)
└──────────────────────┘
```

### No Files Display
```
┌──────────────────────┐
│                      │
│   No Files Found     │
│                      │
│ Press 'm' for        │
│    Live View         │
│                      │
│                      │
│ m:live              │
└──────────────────────┘
```

## Troubleshooting

### Issue: No thumbnails appear
**Check**: ffmpeg installed?
```bash
ffmpeg -version
```
**Fix**: Install ffmpeg
```bash
sudo apt install ffmpeg
```

### Issue: "No Files Found" message
**Check**: Files exist in correct location?
```bash
ls -lh ~/Pictures/captures/
```
**Fix**: Ensure files are PNG or MKV format

### Issue: Navigation doesn't work
**Check**: Press Enter after key?
- Make sure to press key AND Enter (line buffering)
- Example: Press 'n', then press Enter

### Issue: View mode doesn't toggle
**Check**: 'm' key recognized?
- Press 'm', then Enter
- Check terminal for "Entering VIEW MODE" or "Returning to LIVE VIEW"

## Performance Notes

- **First file load**: ~100-200ms (thumbnail generation)
- **Subsequent navigation**: ~10-50ms (from cache)
- **Video thumbnails**: Slower than images (ffmpeg extraction)
- **Memory**: ~5-10MB for thumbnail cache

## Cleanup

After testing, you can remove test files:
```bash
cd ~/Pictures/captures/
# Remove test files if desired
rm -f capture_*.png video_*.mkv
```

## Exit

Press **Ctrl+Z** to stop the application.
