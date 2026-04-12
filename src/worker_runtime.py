"""Worker process runtime management."""

from multiprocessing import Process, Queue, Value
from typing import Optional, Tuple

from camera_worker import capture_worker
from config_manager import Config
from process_worker import process_worker


class WorkerRuntime:
    """Owns worker processes, queues, and shared control flags."""

    def __init__(self, config: Config, display_size: Tuple[int, int]):
        self._config = config
        self._display_size = display_size

        self._capture_queue_display = Queue(maxsize=config.queue_maxsize)
        self._display_queue = Queue(maxsize=config.queue_maxsize)

        self._running_flag = Value("b", True)
        self._capture_count = Value("i", 0)
        self._video_flag = Value("i", 0)
        self._image_capture_flag = Value("i", 0)
        self._filter_index = Value("i", 0)

        self._capture_process: Optional[Process] = None
        self._process_process: Optional[Process] = None

    @property
    def display_queue(self) -> Queue:
        """Queue containing resized frames for display."""
        return self._display_queue

    @property
    def capture_count(self) -> Value:
        """Shared capture count value."""
        return self._capture_count

    @property
    def filter_index(self) -> Value:
        """Shared filter index value."""
        return self._filter_index

    def start(self, logger) -> None:
        """Start capture and frame processing workers."""
        logger.info("Starting workers...")

        self._capture_process = Process(
            target=capture_worker,
            args=(
                self._capture_queue_display,
                self._capture_count,
                self._running_flag,
                self._video_flag,
                self._image_capture_flag,
                self._config.video_resolution,
                self._config.lores_resolution,
                self._config.save_directory,
                self._config.audio_enabled,
                self._config.audio_device,
                self._filter_index,
            ),
        )
        self._capture_process.start()
        logger.info(
            f"Capture worker started: video={self._config.video_resolution}, "
            f"lores={self._config.lores_resolution}"
        )

        self._process_process = Process(
            target=process_worker,
            args=(
                self._capture_queue_display,
                self._display_queue,
                self._running_flag,
                self._display_size,
            ),
        )
        self._process_process.start()
        logger.info("Process worker started: cv2.resize INTER_LINEAR")
        logger.info("Main display loop started (Core 3+)")

    def stop(self, logger) -> None:
        """Stop worker processes gracefully."""
        logger.info("Stopping workers...")
        self._running_flag.value = False

        for proc in (self._capture_process, self._process_process):
            if proc:
                proc.join(timeout=3)
                if proc.is_alive():
                    proc.terminate()
                    proc.join(timeout=1)

        logger.info("All workers stopped")

    def request_image_capture(self) -> None:
        """Signal capture worker to save one image."""
        self._image_capture_flag.value = 1

    def start_video_recording(self) -> None:
        """Signal capture worker to start recording video."""
        self._video_flag.value = 1

    def stop_video_recording(self) -> None:
        """Signal capture worker to stop recording video."""
        self._video_flag.value = 2
