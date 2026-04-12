# App Flow and Architecture

This document explains how the app works end-to-end, what each module is responsible for, and how data moves through the system.

## High-Level Overview

The app runs as a small multi-process pipeline:

1. `capture_worker` reads camera frames and handles image/video capture.
2. `process_worker` resizes frames for TFT display.
3. `main.py` handles UI state, overlays, input, browser mode, and display output.

Supporting modules provide focused responsibilities (audio, ffmpeg merge, overlays, cache, logging, etc.).

## Runtime Topology

```text
Keyboard input (stdin)
        |
        v
   main.py (UI loop)
        |
        |  display_queue (resized RGB frames)
        v
 process_worker <---- capture_queue_display ---- capture_worker
      (cv2.resize)         (full lores RGB)

capture_worker also:
  - captures photos (PNG)
  - records video (H264) + audio (WAV)
  - merges A/V with ffmpeg -> final MP4

main.py also:
  - draws overlays (REC, feedback, filter name)
  - renders media browser view
  - pushes final frames to ST7735 display via DisplayManager
```

## Startup Flow

1. `main.py` creates `CameraTFTApp(config)`.
2. App initializes display through `DisplayManager.initialize()`.
3. App initializes `MediaBrowser` with actual rotated display size.
4. App creates `WorkerRuntime` (queues + shared flags + process handles).
5. `WorkerRuntime.start()` launches:
   - capture process (`capture_worker`)
   - resize process (`process_worker`)
6. Main loop starts reading key input and rendering frames.

## Main Loop Flow (`src/main.py`)

Each loop iteration:

1. Poll input (`InputManager.check_for_input()`).
2. Route key by mode:
   - live mode: capture image, toggle recording, cycle filter
   - view mode: next/prev/delete media file
   - toggle mode: live <-> view
3. Render frame:
   - live mode: pop frame from `display_queue`, apply overlays
   - view mode: render selected media thumbnail + browser overlay
4. Display frame via `DisplayManager.display_frame()`.
5. Every 5s print status (FPS, capture count, recording duration, file info).

## Capture Pipeline (`src/camera_worker.py`)

`capture_worker` owns camera-side behavior:

- `video_recording_flag`:
  - `1` -> start recording
  - `2` -> stop recording and process output
- `image_capture_flag`:
  - `1` -> capture and save PNG
- always captures lores frames for live display

Implementation is split into focused modules:

- `frame_pipeline.py`
  - `capture_lores_frame()` for display feed
  - `capture_and_save_main_frame()` for photo capture
- `recording_pipeline.py`
  - `run_stop_pipeline()` for stop/merge/restart workflow
- `audio_service.py`
  - audio device detection/test + `AudioRecorder`
- `video_service.py`
  - ffmpeg merge helper (`video + wav -> mp4`)

## Recording Flow (Current Behavior)

When recording starts:

1. `CameraWorker.start_recording()` starts H264 recording.
2. If audio enabled, `AudioRecorder.start()` begins WAV capture.

When recording stops:

1. Camera recording stops.
2. Audio recording stops.
3. ffmpeg merges video + audio.
4. Output is saved as final MP4.
5. Camera is restarted safely for the next session.

Note: Video filters are intentionally disabled for recorded videos (stability/speed). Filters apply to live preview and photos.

## View Mode Flow (`src/media_browser.py`)

1. On entering view mode, app scans `~/Pictures/captures/`.
2. `MediaBrowser` reads image/video files and sets current index.
3. Thumbnail lookup order:
   - in-memory cache
   - disk cache (`.thumbnails/`)
   - generate new thumbnail (PIL for images, ffmpeg for videos)
4. Browser overlay shows filename/type/index.
5. Delete removes media file + associated cached thumbnail.

Cache responsibilities are isolated in `src/thumbnail_cache.py`.

## WorkerRuntime Responsibilities (`src/worker_runtime.py`)

`WorkerRuntime` centralizes process/queue/shared state:

- creates shared queues and flags
- starts/stops worker processes
- provides methods for UI actions:
  - `request_image_capture()`
  - `start_video_recording()`
  - `stop_video_recording()`
- exposes shared values/queues used by main loop

This keeps process wiring out of `main.py`.

## Overlay and UI State

- `overlay_renderer.py` creates reusable overlay images:
  - recording overlay
  - feedback overlay
  - filter-name overlay
- `feedback_state.py` manages short-lived feedback message timing.

## Logging Model

- `src/logger.py` defines `get_logger(__name__)`.
- Logs go to:
  - console (stdout)
  - file: `~/.cache/opencode/rpi-tft-camera/app.log`
- Default level is `INFO`.

Typical module pattern:

```python
from logger import get_logger

_logger = get_logger(__name__)
_logger.info("Message")
_logger.warning("Warning")
_logger.error("Error")
```

## Key Files and Responsibilities

- `src/main.py`: app loop, input routing, overlays, rendering
- `src/worker_runtime.py`: worker lifecycle + shared state
- `src/camera_worker.py`: capture worker orchestration
- `src/frame_pipeline.py`: frame/photo capture helpers
- `src/recording_pipeline.py`: stop/merge/restart sequence
- `src/process_worker.py`: display resize process
- `src/display_manager.py`: ST7735 rendering
- `src/media_browser.py`: media browsing and navigation
- `src/thumbnail_cache.py`: thumbnail persistence/validation
- `src/filter_manager.py`: retro image filters
- `src/audio_service.py`: audio detection/recording helpers
- `src/video_service.py`: ffmpeg merge helper
- `src/input_manager.py`: non-blocking key polling
- `src/config_manager.py`: app configuration

## Shutdown Flow

On exit/error:

1. If recording, request stop recording.
2. `WorkerRuntime.stop()` joins/terminates worker processes safely.
3. Display and media browser resources are cleaned up.
4. Final capture stats are logged.
