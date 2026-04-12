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
2. SEPIA - Sepia with mild fade and grain
3. SILVER - Silver-screen B&W with grain
4. 70s FILM - Warm stock with soft halation
5. 80s VHS - Chroma shift + scanlines
6. 80s VHS+ - Strong VHS bleed/jitter/noise
7. SUPER 8 - Warm vignette + flicker + grain

## Output
- Location: `~/Pictures/captures/`
- Images: `capture_YYYYMMDD_HHMMSS.png`
- Videos: `video_YYYYMMDD_HHMMSS.mp4`

## Video Processing (v4.2.8)
- Records video + audio separately
- On stop: ffmpeg merges video + audio into final `.mp4`
- Video filters are intentionally disabled (for speed/stability)
- Filters apply to live preview and photo capture only

## Logging
- Logger implementation: `src/logger.py`
- Every module calls `get_logger(__name__)` and logs to:
  - Console (stdout)
  - File: `~/.cache/opencode/rpi-tft-camera/app.log`
- Default level is `INFO`.

### How to use logs on Pi
```bash
# Watch logs live
tail -f ~/.cache/opencode/rpi-tft-camera/app.log

# Search for errors and warnings
grep -E "ERROR|WARNING" ~/.cache/opencode/rpi-tft-camera/app.log
```

### Enable debug logging
Edit `src/logger.py` and change the default logger level:
```python
level: int = logging.DEBUG,
```
Then restart `python3 main.py`.
