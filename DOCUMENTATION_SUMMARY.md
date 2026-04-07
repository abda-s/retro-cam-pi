# Documentation Update Summary

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
**Version:** 4.2.0
