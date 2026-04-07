# rpi-tft-camera Agent Notes

## SSH Connection
- Host: `cam@192.168.1.112`
- Password: `4625`

## Sync Local → Pi
```bash
sshpass -p '4625' rsync -av --delete /home/abdas/rpi-tft-camera/src/ cam@192.168.1.112:~/rpi-tft-camera/src/
```

## Run on Pi
```bash
ssh cam@192.168.1.112
cd ~/rpi-tft-camera/src
python3 main.py
```

## Controls
- `v` + Enter: Start/stop video+audio recording
- `t` + Enter: Capture image
- Ctrl+Z: Stop app

## Output
- Location: `~/Pictures/captures/`
- Format: `video_YYYYMMDD_HHMMSS.mkv`
