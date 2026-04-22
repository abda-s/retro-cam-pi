"""Recording stop/restart pipeline for camera worker."""

import subprocess
import threading
import time
from pathlib import Path

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

        rotation = getattr(worker, '_camera_rotation', 0)
        
        if audio_path and audio_path.exists() and video_path:
            # Use temp output file to avoid conflict with existing video file
            # Note: Use string formatting since with_suffix() requires dot prefix
            final_path = video_path.parent / f"{video_path.stem}_done.mp4"
            temp_path = video_path.parent / f"{video_path.stem}_merged.mp4"
            
            # Define callback to handle post-merge operations
            def on_merge_complete(success: bool, output_path: Path) -> None:
                logger.debug(f"Merge complete callback: success={success}, output={output_path.name}")
                if success and output_path.exists():
                    try:
                        # Rename temp file to final _done.mp4
                        output_path.rename(final_path)
                        logger.info(f"Renamed to final: {final_path.name}")
                    except Exception as exc:
                        logger.error(f"Failed to rename merged file: {exc}")
                else:
                    logger.warning(f"Merge failed or output not found: success={success}, exists={output_path.exists() if output_path else 'N/A'}")
            
            # Start merge in background (non-blocking) with callback
            logger.debug(f"Starting ffmpeg merge: {temp_path.name}")
            ffmpeg_merge(video_path, audio_path, temp_path, rotation, on_merge_complete)
            
            # Note: merge runs in background. After completion, ffmpeg will delete
            # original .mp4 and .wav files, then callback renames _merged to _done.
            # Media browser only shows *_done.mp4 files, so incomplete videos hidden.
        else:
            logger.warning("Step 5b: No audio to merge - processing video without audio")
            if video_path is not None:
                final_path = video_path.parent / f"{video_path.stem}_done.mp4"
                
                # Apply rotation to video if needed (non-blocking)
                if rotation > 0:
                    temp_rotated = video_path.parent / f"{video_path.stem}_rotated.mp4"
                    
                    def run_rotation():
                        try:
                            vf_filter = f"transpose={2 if rotation == 270 else 1}" if rotation in (90, 270) else "transpose=2,transpose=2"
                            subprocess.run([
                                "ffmpeg", "-y", "-i", str(video_path),
                                "-vf", vf_filter,
                                "-c:v", "libx264", "-preset", "fast",
                                "-c:a", "copy", str(temp_rotated)
                            ], capture_output=True, timeout=120)
                            if temp_rotated.exists():
                                video_path.unlink()
                                temp_rotated.rename(final_path)
                                logger.debug(f"Rotation complete: {final_path.name}")
                            else:
                                logger.warning("Rotation failed - temp file not created")
                        except Exception as exc:
                            logger.warning(f"Video rotation failed: {exc}")
                            if video_path.exists():
                                video_path.rename(final_path)
                    
                    # Run rotation in background thread
                    threading.Thread(target=run_rotation, daemon=True).start()
                    logger.debug("Started background rotation")
                else:
                    # No rotation needed, just rename to _done
                    if video_path.exists():
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
