"""Recording stop/restart pipeline for camera worker."""

import threading
import time

from picamera2 import Picamera2

from video_service import ffmpeg_merge


def run_stop_pipeline(worker, logger) -> None:
    """Stop recording, process output files, and restart camera in background."""

    def safe_camera_restart() -> None:
        logger.debug("Step 1: Stopping camera recording...")
        try:
            worker._camera.stop_recording()
            logger.debug("Step 1a: stop_recording() OK")
        except Exception as exc:
            logger.warning(f"Step 1a: stop_recording error: {exc}")

        logger.debug("Step 2: Stopping audio recorder...")
        audio_path = None
        if worker._audio_recorder.is_recording():
            try:
                audio_path = worker._audio_recorder.stop()
                logger.debug("Step 2a: audio stop OK")
            except Exception as exc:
                logger.warning(f"Step 2a: audio stop error: {exc}")

        worker._is_recording = False
        video_path = worker._current_video_file
        worker._current_video_file = None
        logger.debug(f"Step 3: Recording stopped: {video_path}")

        worker._encoder = None

        logger.debug("Step 4: Waiting for audio flush...")
        time.sleep(0.5)

        logger.debug("Step 5: Saving video without filter")

        if audio_path and audio_path.exists() and video_path:
            temp_merged = video_path.with_suffix(".merged.mp4")
            ffmpeg_merge(video_path, audio_path, temp_merged)

            final_path = video_path.with_suffix(".mp4")
            if temp_merged.exists():
                temp_merged.rename(final_path)
        else:
            logger.warning("Step 5b: No audio to merge - processing video without audio")
            if video_path is not None:
                final_path = video_path.with_suffix(".mp4")
                if video_path.exists() and video_path != final_path:
                    video_path.rename(final_path)

        logger.debug("Step 6: Restarting camera...")
        try:
            logger.debug("Step 6a: Calling camera.stop()...")
            worker._camera.stop()
            logger.debug("Step 6a: camera.stop() OK")
        except Exception as exc:
            logger.warning(f"Step 6a: camera.stop() error: {exc}")

        time.sleep(0.5)

        try:
            logger.debug("Step 6b: Calling camera.start()...")
            worker._camera.start()
            logger.debug("Step 6b: camera.start() OK")
        except Exception as exc:
            logger.error(f"Step 6b: camera.start() FAILED: {exc}")
            logger.error("Step 6c: Attempting camera reinitialization...")
            try:
                worker._camera = Picamera2()
                config = worker._camera.create_video_configuration(
                    main={"size": worker._capture_resolution, "format": "RGB888"},
                    lores={"size": worker._lores_resolution},
                )
                worker._camera.configure(config)
                worker._camera.start()
                logger.debug("Step 6c: Camera reinitialized OK")
            except Exception as exc2:
                logger.error(f"Step 6c: Camera reinit FAILED: {exc2}")
                logger.error("Step 6c: Camera is broken - need manual restart")
                worker._camera = None

        logger.debug("Step 7: Camera restart complete - ready for next recording")

    thread = threading.Thread(target=safe_camera_restart, daemon=False)
    thread.start()
    logger.debug("Camera restart thread started")
