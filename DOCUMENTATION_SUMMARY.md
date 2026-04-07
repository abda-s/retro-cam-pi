# Documentation Update Summary

## v4.2.1 - Display Optimization & Tearing Fix

Documentation updated to reflect display optimizations and frame buffering improvements.

## What Changed

### Display Optimization (v4.2.0 → v4.2.1)
| Feature | Old | New |
|---------|-----|-----|
| Lores Resolution | 320×240 | 128×160 (matches display) |
| Aspect Ratio | 4:3 → 4:5 (stretched) | 4:5 → 4:5 (perfect match) |
| FPS | 25-32 | 30-35 |
| Tearing | Present during fast motion | Eliminated via frame buffering |

### Technical Implementation
1. **Optimized lores stream** - Set to 128×160 to match display exactly
2. **Aspect ratio fix** - Eliminated green bars and distortion
3. **Frame buffering** - Added thread-safe display synchronization
4. **Skip on busy** - Frames skipped if display is updating
5. **Performance tracking** - Skipped frame count shown in status

### Key Files Modified
- `src/config_manager.py` - Added lores_resolution = (128, 160)
- `src/camera_worker.py` - Updated default lores resolution
- `src/display_manager.py` - Added frame buffering logic
- `src/main.py` - Added skipped frame tracking in status output

## Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Lores 128×160 | ✅ Done | Perfect aspect ratio match |
| Frame Buffering | ✅ Done | Thread-safe lock mechanism |
| Tearing Prevention | ✅ Done | Skips frames when display busy |
| Skip Tracking | ✅ Done | Shown in status output |

## Performance Impact

| Metric | Before | After | Improvement |
|---------|---------|--------|-------------|
| FPS | ~25-32 | ~30-35 | ~10% faster |
| Aspect Ratio | Mismatched | Perfect | No distortion |
| Tearing | Present | None | Fixed |
| Green Bar | Yes | No | Fixed |

## Known Notes

- Frame skipping occurs during very fast camera movement
- At 30-35 FPS, skipped frames are minimal (1-5 per 5 seconds)
- Skipped frames are tracked and visible in status output
- Frame skipping prevents tearing artifacts

---

## v4.2.0 - Audio Recording Support

All documentation updated to reflect audio recording feature with USB microphone.

## What Changed

### Audio Recording (v4.1.x → v4.2.0)
| Feature | Old | New |
|---------|-----|-----|
| Video Recording | H264 only | Video + Audio |
| Audio Source | None | USB Mic (hw:2,0) |
| Output Format | MP4 | MKV (merged) |
| Audio Merge | N/A | FFmpeg background |

### Technical Implementation
1. **Separate audio recording** - Uses `arecord` (ALSA) for audio capture
2. **Video as MP4** - Uses `PyavOutput` for proper timestamps
3. **FFmpeg merge** - Combines MP4 + WAV → MKV in background
4. **Camera restart** - Restarts camera after recording to prevent freeze

### Key Files Modified
- `src/camera_worker.py` - Core recording logic with AudioRecorder class
- `src/main.py` - Passes audio config to capture worker

## Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| USB Mic (hw:2,0) | ✅ Done | ALSA device |
| Separate arecord | ✅ Done | WAV output |
| Video as MP4 | ✅ Done | PyavOutput |
| FFmpeg merge | ✅ Done | Background thread |
| Camera restart | ✅ Done | Prevents freeze |
| Cleanup WAV/MP4 | ✅ Done | After merge |

## Known Limitations

- Audio volume depends on USB mic sensitivity
- Short delay (~0.7s) after stopping recording for audio flush

---

**Last Updated:** 2026-04-07
**Version:** 4.2.1
