"""Video filter processor for rpi-tft-camera.

Applies retro filter effects to videos using PyAV + OpenCV filters.
Runs in background to avoid blocking camera.
PyAV provides reliable video I/O on Raspberry Pi (bypasses OpenCV backend issues).
"""

import cv2
import numpy as np
import threading
import time
from pathlib import Path
from typing import Optional

from logger import get_logger
from filter_manager import FilterManager

_logger = get_logger(__name__)


def apply_filter_to_video(
    input_video: Path,
    output_video: Path,
    filter_index: int,
    delete_input: bool = False,
) -> bool:
    """Apply filter to video file using PyAV for I/O + OpenCV for filtering.

    Args:
        input_video: Path to input video (with audio)
        output_video: Path to save filtered video
        filter_index: Filter index (0-6)
        delete_input: Whether to delete input file after processing

    Returns:
        True if successful
    """
    try:
        import av
    except ImportError:
        _logger.error("PyAV not installed: pip3 install av")
        return False

    _logger.debug(f"VideoFilter: opening {input_video} with PyAV")
    
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
        # Open input video with PyAV
        in_container = av.open(str(input_video))
        in_stream = in_container.streams.video[0]
        
        fps = int(in_stream.average_rate) if in_stream.average_rate else 30
        width = in_stream.width
        height = in_stream.height
        
        # Count total frames for progress
        total_frames = in_stream.frames
        if total_frames == 0:
            # If frames not known, estimate from duration
            total_duration = in_stream.duration
            if total_duration:
                total_frames = int(total_duration * fps)
            else:
                total_frames = 0
        
        _logger.debug(f"VideoFilter: {width}x{height} @ {fps}, ~{total_frames} frames")

        # Open output video
        out_container = av.open(str(output_video), 'w')
        
        # Create H.264 encoder (use libx264 for compatibility)
        out_stream = out_container.add_stream('h264', rate=fps)
        out_stream.width = width
        out_stream.height = height
        out_stream.pix_fmt = 'yuv420p'
        out_stream.options = {'preset': 'fast', 'crf': '23'}
        
        processed = 0
        log_interval = 10

        # Process each frame
        for packet in in_container.demux(in_stream):
            for frame in packet.decode():
                # Convert PyAV frame to numpy array
                img = frame.to_ndarray(format='bgr24')
                
                # Apply filter using existing FilterManager
                if filter_index > 0:
                    img = FilterManager.apply_filter(img, filter_index)
                
                # Convert back to PyAV frame
                new_frame = av.VideoFrame.from_ndarray(img, format='bgr24')
                new_frame.pts = frame.pts
                new_frame.time_base = frame.time_base
                
                # Encode and write
                for out_packet in out_stream.encode(new_frame):
                    out_container.mux(out_packet)
                
                processed += 1
                if processed % log_interval == 0:
                    if total_frames > 0:
                        progress = (processed / total_frames) * 100
                        _logger.debug(f"Filtering: {processed} frames ({progress:.0f}%)")
                    else:
                        _logger.debug(f"Filtering: {processed} frames")

        # Flush encoder
        for out_packet in out_stream.encode():
            out_container.mux(out_packet)

        # Close containers
        out_container.close()
        in_container.close()

        _logger.debug(f"Video filtered: {output_video.name}")

        if delete_input and input_video.exists():
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
            _logger.info(f"Video saved with filter: {final_video.name}")
        else:
            _logger.warning(f"Filter failed, using unfiltered: {temp_video.name}")
            if not final_video.exists() and temp_video.exists():
                temp_video.rename(final_video)
        
        # Clean up completion flag
        if completion_flag.exists():
            completion_flag.unlink()
    
    thread = threading.Thread(target=run, daemon=False)
    thread.start()
    _logger.info(f"Background video processing thread started: filter={filter_index}")
