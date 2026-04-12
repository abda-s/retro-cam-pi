# rpi-tft-camera Agent Notes

## SSH Connection
- Host: `cam@192.168.1.112`
- Password: `4625`

## Sync Local → Pi
After updating code, use rsync to update the Pi:
```bash
sshpass -p '4625' rsync -av --delete /home/abdas/rpi-tft-camera/src/ cam@192.168.1.112:~/rpi-tft-camera/src/
```
**abdas will test the updated code on the Pi**

## Run on Pi
```bash
ssh cam@192.168.1.112
cd ~/rpi-tft-camera/src
python3 main.py
```

## Controls
- `v` + Enter: Start/stop video+audio recording
- `t` + Enter: Capture image
- `f` + Enter: Cycle through retro filters
- `m` + Enter: Toggle Live View / View Saved Footage mode
- `n` + Enter: Next file (in View Mode)
- `p` + Enter: Previous file (in View Mode)
- `d` + Enter: Delete current file (in View Mode)
- Ctrl+Z: Stop app

## Filters (press `f` to cycle)
1. NONE - Original camera feed
2. SEPIA - Classic warm brown tones
3. SILVER - 1930s-50s high contrast B&W
4. 70s FILM - Kodak Portra with grain
5. 80s VHS - Simple RGB color shift
6. 80s VHS+ - Complex chromatic aberration
7. SUPER 8 - Warm vignette + film grain

## Output
- Location: `~/Pictures/captures/`
- Format: `video_YYYYMMDD_HHMMSS.mkv`

## Video Processing (v4.2.8)
- Records video + audio separately
- On stop: ffmpeg merges video + audio into .merged.mp4
- Then applies filter if enabled (filter_index > 0)
- Filter processing waits for ffmpeg to complete before starting

### Known Issues
- **Filter processing fails during muxing**: `[Errno 22] Invalid argument` when writing filtered video
- Cause: PyAV `time_base` not set on output stream
- Status: 🔄 Fix pending - need to add `time_base = Fraction(1, fps)` to output stream
