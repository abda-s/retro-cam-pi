# Documentation Update Summary

## v3.0.0 - 30 FPS Performance Boost

All documentation has been updated to reflect v3.0.0 changes.

## What Changed

### Performance (v2.1.1 → v3.0.0)
| Metric | Old | New | Improvement |
|--------|-----|-----|-------------|
| FPS | 10-15 | 25-32 | **3×** |
| SPI Speed | 8 MHz | 40 MHz | 5× |
| Resize | PIL | cv2 | 3-4× |

### Key Optimizations
1. **40 MHz SPI** - 5× faster display transfer
2. **cv2.resize** - Replaces PIL Image.resize()
3. **Capture Fallbacks** - Multiple queues ensure capture always works
4. **Single File** - Just `main.py`

## Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| 40 MHz SPI | ✅ Done | Auto-fallback to 8 MHz |
| cv2.resize | ✅ Done | INTER_LINEAR |
| Capture fallbacks | ✅ Done | 3-level fallback |
| Single main.py | ✅ Done | Removed camera_tft_display.py |

## Old Issues (Now Fixed)

- **Capture queue empty** - ✅ Fixed with fallback system
- **Terminal buffering** - Still needs 't' + Enter

---

**Last Updated:** 2026-04-06
**Version:** 3.0.0
