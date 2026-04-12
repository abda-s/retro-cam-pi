"""Video filter processor for rpi-tft-camera.

Applies retro-style filters to recorded videos using ffmpeg.
Runs in a background thread to avoid blocking live camera view.
"""

import subprocess
import threading
import time
from pathlib import Path

from logger import get_logger

_logger = get_logger(__name__)


def apply_filter_to_video(
    input_video: Path,
    output_video: Path,
    filter_index: int,
    delete_input: bool = False,
) -> bool:
    """Apply filter to video file using ffmpeg.

    Args:
        input_video: Path to input video (with audio)
        output_video: Path to save filtered video
        filter_index: Filter index (0-6)
        delete_input: Whether to delete input file after processing

    Returns:
        True if successful
    """
    _logger.debug(f"VideoFilter: opening {input_video} with ffmpeg")
    
    # Check if file exists first
    if not input_video.exists():
        _logger.error(f"VideoFilter: Input file does NOT exist: {input_video}")
        _logger.error(f"VideoFilter: File exists: {input_video.exists()}")
        # List nearby files to help debug
        parent_dir = input_video.parent
        if parent_dir.exists():
            all_files = list(parent_dir.glob('*'))
            _logger.error(f"VideoFilter: Files in {parent_dir.name}: {[f.name for f in all_files]}")
        return False
    
    _logger.debug(f"VideoFilter: File size: {input_video.stat().st_size} bytes")

    try:
        if filter_index <= 0:
            if output_video != input_video:
                output_video.write_bytes(input_video.read_bytes())
            if delete_input and input_video.exists() and input_video != output_video:
                input_video.unlink()
            return True

        filter_map = {
            1: "colorchannelmixer=.393:.769:.189:.0:.349:.686:.168:.0:.272:.534:.131",  # SEPIA
            2: "hue=s=0,eq=contrast=1.35:brightness=0.02",  # SILVER
            3: "eq=contrast=1.08:saturation=1.12:gamma=0.95,noise=alls=10:allf=t",  # 70s FILM
            4: "chromashift=cbh=2:crh=-2,eq=saturation=0.9:contrast=1.02",  # 80s VHS
            5: "gblur=sigma=1.0,chromashift=cbh=3:crh=-3,eq=saturation=0.9:contrast=1.05,noise=alls=8:allf=t",  # 80s VHS+
            6: "vignette=PI/4:0.7,eq=saturation=1.08:gamma_r=0.93:gamma_g=0.97:gamma_b=1.06,noise=alls=12:allf=t",  # SUPER 8
        }

        vf = filter_map.get(filter_index)
        if not vf:
            _logger.warning(f"VideoFilter: unknown filter index {filter_index}, keeping original")
            if output_video != input_video:
                output_video.write_bytes(input_video.read_bytes())
            if delete_input and input_video.exists() and input_video != output_video:
                input_video.unlink()
            return True

        temp_output = output_video.with_suffix(".tmp.mp4")
        if temp_output.exists():
            temp_output.unlink()

        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-i",
            str(input_video),
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "19",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            str(temp_output),
        ]

        start_time = time.time()
        _logger.info(f"VideoFilter: ffmpeg start | filter={filter_index} | input={input_video.name}")
        _logger.debug(f"VideoFilter: ffmpeg cmd: {' '.join(cmd)}")

        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        elapsed = time.time() - start_time
        if proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", errors="replace")
            _logger.error(f"VideoFilter: ffmpeg failed (rc={proc.returncode}) after {elapsed:.1f}s")
            _logger.error(f"VideoFilter: ffmpeg stderr: {stderr[:2000]}")
            if temp_output.exists():
                temp_output.unlink()
            return False

        if not temp_output.exists() or temp_output.stat().st_size == 0:
            _logger.error("VideoFilter: ffmpeg reported success but output is empty/missing")
            if temp_output.exists():
                temp_output.unlink()
            return False

        temp_output.replace(output_video)

        _logger.info(
            f"VideoFilter: ffmpeg complete in {elapsed:.1f}s | "
            f"output={output_video.name} | size={output_video.stat().st_size} bytes"
        )

        if delete_input and input_video.exists() and input_video != output_video:
            input_video.unlink()
            _logger.debug(f"Deleted temp video: {input_video.name}")

        return True

    except Exception as e:
        _logger.error(f"Video filter error: {e}")
        import traceback
        traceback.print_exc()
        return False


def process_video_in_background(
    temp_video: Path,
    final_video: Path,
    filter_index: int,
    delete_temp: bool = True,
    ffmpeg_thread: threading.Thread = None,
) -> None:
    """Run video filter processing in background thread.

    Args:
        temp_video: Input video path (with audio)
        final_video: Output video path
        filter_index: Filter index to apply
        delete_temp: Delete temp video after processing
        ffmpeg_thread: FFmpeg merge thread object (to check if finished)
    """
    # Completion flag created by ffmpeg_merge
    completion_flag = temp_video.with_suffix('.complete')
    
    def run():
        _logger.info(f"VideoFilter: Waiting for ffmpeg to finish...")
        
        # Check if ffmpeg thread was provided and wait for it to complete
        if ffmpeg_thread is not None:
            _logger.debug(f"VideoFilter: Checking ffmpeg thread status (alive={ffmpeg_thread.is_alive()})")
            # Wait for ffmpeg thread to finish (max 30 seconds)
            wait_count = 0
            max_wait = 30
            while wait_count < max_wait and ffmpeg_thread.is_alive():
                time.sleep(0.5)
                wait_count += 0.5
                
                # Log status every 5 seconds
                if wait_count % 5 == 0:
                    _logger.debug(f"VideoFilter: Still waiting for ffmpeg... ({wait_count}s)")
            
            if wait_count >= max_wait:
                _logger.warning(f"VideoFilter: Waited {max_wait}s for ffmpeg, starting anyway")
            else:
                _logger.info(f"VideoFilter: ffmpeg thread finished after {wait_count}s")
        
        # Additional safety: check for completion flag
        _logger.debug(f"VideoFilter: Checking completion flag: {completion_flag}")
        
        if completion_flag.exists():
            _logger.info(f"VideoFilter: ffmpeg complete flag found")
        else:
            _logger.debug(f"VideoFilter: Completion flag not yet present, checking file...")
            # Check if file exists with reasonable size
            if temp_video.exists():
                size = temp_video.stat().st_size
                if size > 1024 * 100:  # At least 1MB
                    _logger.info(f"VideoFilter: File ready ({size} bytes)")
                else:
                    _logger.warning(f"VideoFilter: File too small ({size} bytes), waiting...")
                    time.sleep(2)
        
        _logger.debug(f"VideoFilter: temp={temp_video}, final={final_video}, filter={filter_index}")
        
        if not temp_video.exists():
            _logger.error(f"VideoFilter: Temp file does not exist: {temp_video}")
            return
        
        success = apply_filter_to_video(temp_video, final_video, filter_index, delete_temp)
        
        if success:
            if final_video.exists():
                _logger.info(
                    f"Video saved with filter: {final_video.name} "
                    f"({final_video.stat().st_size} bytes)"
                )
            else:
                _logger.warning(f"Video filter reported success but output is missing: {final_video}")
        else:
            _logger.warning(f"Filter failed, using unfiltered: {temp_video.name}")
            if not final_video.exists() and temp_video.exists():
                temp_video.rename(final_video)
                _logger.info(
                    f"VideoFilter: fallback rename complete: {temp_video.name} -> {final_video.name}"
                )
        
        # Clean up completion flag
        if completion_flag.exists():
            completion_flag.unlink()
    
    thread = threading.Thread(target=run, daemon=False)
    thread.start()
    _logger.info(f"Background video processing thread started: filter={filter_index}")
