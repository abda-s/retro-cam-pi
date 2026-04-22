"""Media browser module for rpi-tft-camera.

Handles browsing saved images and videos with thumbnail generation.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from datetime import datetime

try:
    from PIL import Image
except ImportError:
    raise ImportError("PIL not installed. Run: pip3 install pillow")

from logger import get_logger
from thumbnail_cache import ThumbnailCache


class MediaBrowser:
    """Manages browsing of saved media files (images and videos)."""

    def __init__(
        self,
        save_directory: Path,
        display_size: Tuple[int, int] = (128, 160),
    ) -> None:
        """Initialize media browser.

        Args:
            save_directory: Directory containing captured media files
            display_size: Display dimensions (width, height) for full-screen images
        """
        self._save_directory = save_directory
        self._display_size = display_size
        self._logger = get_logger(__name__)
        self._logger.info(f"MediaBrowser initialized with display size: {display_size}")

        # Browser state
        self._files: List[Path] = []
        self._current_index: int = 0
        self._temp_dir: Optional[tempfile.TemporaryDirectory] = None

        self._thumbnail_cache = ThumbnailCache(
            save_directory=save_directory,
            display_size=display_size,
            logger=self._logger,
        )
        self._logger.info(f"MediaBrowser cache directory: {self._thumbnail_cache.cache_dir}")

    @property
    def file_count(self) -> int:
        """Return number of discovered media files."""
        return len(self._files)

    def scan_directory(self) -> bool:
        """Scan save directory for media files and sort by newest first.

        Returns:
            True if files were found, False otherwise
        """
        if not self._save_directory.exists():
            return False

        self._files = []

        # Find all PNG files (photos)
        self._files.extend(self._save_directory.glob('*.png'))

        # Find only _done.mp4 files (completed videos)
        # This prevents race condition: don't show _merged.mp4 while it's being processed
        self._files.extend(self._save_directory.glob('*_done.mp4'))

        if not self._files:
            self._logger.info(f"MediaBrowser: no files found in {self._save_directory}")
            return False

        # Sort by modification time (newest first)
        self._files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        # Reset index
        self._current_index = 0

        # Load existing cache from disk (persistent across restarts)
        self._thumbnail_cache.load_from_disk(self._files)

        self._logger.info(f"MediaBrowser: found {len(self._files)} files")
        for f in self._files[:10]:  # Show first 10
            self._logger.debug(f"MediaBrowser file: {f.name}")
        if len(self._files) > 10:
            self._logger.debug(f"MediaBrowser: and {len(self._files) - 10} more files")

        # Validate cache entries
        self._thumbnail_cache.validate(self._files)

        return True

    def get_current_file(self) -> Optional[Path]:
        """Get current file path.

        Returns:
            Path to current file, or None if no files
        """
        if not self._files:
            return None
        return self._files[self._current_index]

    def get_file_info(self) -> Optional[Dict]:
        """Get information about current file.

        Returns:
            Dict with 'filename', 'size', 'modified', 'type', or None
        """
        file_path = self.get_current_file()
        if file_path is None:
            return None

        stat = file_path.stat()
        file_ext = file_path.suffix.lower()
        file_type = 'video' if file_ext == '.mp4' else 'image'

        return {
            'filename': file_path.name,
            'size': self._format_size(stat.st_size),
            'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
            'type': file_type,
            'index': self._current_index + 1,
            'total': len(self._files),
        }

    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format.

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted string (e.g., "1.2 MB")
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def get_thumbnail(self) -> Optional[Image.Image]:
        """Get thumbnail for current file.

        Returns:
            PIL Image of thumbnail, or None on error
        """
        file_path = self.get_current_file()
        if file_path is None:
            return None

        # Check cache first (silent - no logging for every frame)
        cached = self._thumbnail_cache.get(file_path)
        if cached is not None:
            return cached

        try:
            file_ext = file_path.suffix.lower()
            if file_ext in ['.mp4']:
                # Video: extract first frame using ffmpeg
                self._logger.debug(f"MediaBrowser: processing video {file_path.name}")
                thumbnail = self._extract_video_thumbnail(file_path)
            else:
                # Image (PNG): load and resize
                thumbnail = self._load_image_thumbnail(file_path)

            if thumbnail:
                self._thumbnail_cache.set(file_path, thumbnail)
                return thumbnail
            else:
                self._logger.warning(f"MediaBrowser: failed to create thumbnail for {file_path.name}")

        except Exception as e:
            self._logger.warning(f"MediaBrowser: thumbnail error for {file_path.name}: {e}")

        return None

    def _load_image_thumbnail(self, file_path: Path) -> Optional[Image.Image]:
        """Load and resize image to full display size.

        Args:
            file_path: Path to image file

        Returns:
            PIL Image resized to display size, or None on error
        """
        try:
            image = Image.open(file_path)
            self._logger.debug(f"MediaBrowser: image size {image.size}, mode {image.mode}")

            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Resize to full display dimensions (stretch to fit)
            target_size = self._display_size
            image = image.resize(target_size, Image.Resampling.LANCZOS)
            self._logger.debug(f"MediaBrowser: resized image to {image.size}")

            return image

        except Exception as e:
            self._logger.warning(f"MediaBrowser: image load error for {file_path.name}: {e}")
            return None

    def _extract_video_thumbnail(self, file_path: Path) -> Optional[Image.Image]:
        """Extract first frame from video using ffmpeg.

        Args:
            file_path: Path to video file

        Returns:
            PIL Image resized to display size, or None on error
        """
        if self._temp_dir is None:
            self._temp_dir = tempfile.TemporaryDirectory()

        try:
            # Use ffmpeg to extract first frame at full display resolution
            width, height = self._display_size
            self._logger.debug(f"MediaBrowser: extracting thumbnail from {file_path.name}")
            self._logger.debug(f"MediaBrowser: thumbnail target {width}x{height}")

            cmd = [
                'ffmpeg',
                '-hide_banner',
                '-y',
                '-i', str(file_path),
                '-vframes', '1',
                '-vf', f'scale={width}:{height}',
                '-f', 'image2pipe',
                '-pix_fmt', 'rgb24',
                '-vcodec', 'rawvideo',
                '-'
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,  # Capture stderr for debugging
                stdin=subprocess.DEVNULL
            )

            self._logger.debug(f"MediaBrowser: ffmpeg thumbnail return code {result.returncode}")

            if result.returncode != 0:
                error_msg = result.stderr.decode('utf-8', errors='replace')
                self._logger.warning(f"MediaBrowser: ffmpeg thumbnail error: {error_msg[:1000]}")
                # Return fallback placeholder instead of None
                return self._create_video_placeholder(file_path.name)

            if result.stdout:
                # Calculate expected size: width * height * 3 (RGB)
                expected_size = width * height * 3
                actual_size = len(result.stdout)
                self._logger.debug(
                    f"MediaBrowser: thumbnail bytes {actual_size} (expected {expected_size})"
                )

                if actual_size == expected_size:
                    # Convert raw bytes to PIL Image
                    image = Image.frombytes('RGB', (width, height), result.stdout)
                    self._logger.debug("MediaBrowser: video thumbnail created successfully")
                    return image
                else:
                    self._logger.warning(
                        f"MediaBrowser: thumbnail size mismatch expected {expected_size}, got {actual_size}"
                    )
                    # Return fallback placeholder
                    return self._create_video_placeholder(file_path.name)
            else:
                self._logger.warning("MediaBrowser: no output from ffmpeg thumbnail extraction")
                return self._create_video_placeholder(file_path.name)

        except FileNotFoundError:
            self._logger.error("MediaBrowser: ffmpeg not found - video thumbnails disabled")
            # Return fallback placeholder
            return self._create_video_placeholder(file_path.name)
        except Exception as e:
            self._logger.warning(f"MediaBrowser: video thumbnail error: {e}")
            import traceback
            traceback.print_exc()
            # Return fallback placeholder
            return self._create_video_placeholder(file_path.name)

    def _create_video_placeholder(self, filename: str) -> Image.Image:
        """Create a placeholder image for videos when thumbnail extraction fails.

        Args:
            filename: Video filename to display

        Returns:
            PIL Image placeholder
        """
        try:
            width, height = self._display_size
            from PIL import ImageDraw, ImageFont

            # Create dark gray background
            image = Image.new('RGB', (width, height), (80, 80, 80))
            draw = ImageDraw.Draw(image)

            # Draw "VIDEO" text
            text = "VIDEO"
            text_bbox = draw.textbbox((0, 0), text)
            text_width = text_bbox[2] - text_bbox[0]
            text_x = (width - text_width) // 2
            text_y = height // 2 - 20
            draw.text((text_x, text_y), text, fill=(255, 255, 255))

            # Draw filename (truncated)
            max_name_width = width - 20
            truncated_name = filename
            name_bbox = draw.textbbox((0, 0), truncated_name)
            name_width = name_bbox[2] - name_bbox[0]

            while name_width > max_name_width and len(truncated_name) > 4:
                truncated_name = truncated_name[:-4] + "..."
                name_bbox = draw.textbbox((0, 0), truncated_name)
                name_width = name_bbox[2] - name_bbox[0]

            name_x = (width - name_width) // 2
            name_y = height // 2 + 10
            draw.text((name_x, name_y), truncated_name, fill=(200, 200, 200))

            # Draw border
            draw.rectangle([5, 5, width-6, height-6], outline=(100, 100, 100), width=2)

            self._logger.debug(f"MediaBrowser: created video placeholder for {filename}")
            return image

        except Exception as e:
            self._logger.warning(f"MediaBrowser: error creating placeholder: {e}")
            # Last resort: return a simple gray image
            return Image.new('RGB', self._display_size, (80, 80, 80))

    def _create_processing_placeholder(self) -> Image.Image:
        """Create placeholder for video still being processed (ffmpeg merge).

        Returns:
            PIL Image placeholder with "Processing..." message
        """
        try:
            width, height = self._display_size
            from PIL import ImageDraw

            # Create dark blue background
            image = Image.new('RGB', (width, height), (20, 30, 60))
            draw = ImageDraw.Draw(image)

            # Draw "Processing..." text
            text = "Processing..."
            text_bbox = draw.textbbox((0, 0), text)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            text_x = (width - text_width) // 2
            text_y = (height - text_height) // 2 - 10
            draw.text((text_x, text_y), text, fill=(100, 150, 255))

            # Draw spinning indicator (simple animated dots)
            import time
            dot_count = int(time.time()) % 3 + 1
            dots = "." * dot_count
            dot_text = f"Merge{dots}"
            dot_bbox = draw.textbbox((0, 0), dot_text)
            dot_width = dot_bbox[2] - dot_bbox[0]
            dot_x = (width - dot_width) // 2
            dot_y = text_y + text_height + 10
            draw.text((dot_x, dot_y), dot_text, fill=(150, 180, 220))

            # Draw border
            draw.rectangle([5, 5, width-6, height-6], outline=(60, 100, 180), width=2)

            return image

        except Exception as e:
            self._logger.warning(f"MediaBrowser: error creating processing placeholder: {e}")
            return Image.new('RGB', self._display_size, (20, 30, 60))

    def next_file(self) -> bool:
        """Move to next file.

        Returns:
            True if moved successfully, False if at end
        """
        if not self._files or self._current_index >= len(self._files) - 1:
            return False

        self._current_index += 1
        return True

    def prev_file(self) -> bool:
        """Move to previous file.

        Returns:
            True if moved successfully, False if at start
        """
        if not self._files or self._current_index <= 0:
            return False

        self._current_index -= 1
        return True

    def has_files(self) -> bool:
        """Check if there are any files to browse.

        Returns:
            True if files exist, False otherwise
        """
        return len(self._files) > 0

    def delete_current_file(self) -> Tuple[bool, str]:
        """Delete current file from filesystem and cache.

        Returns:
            Tuple of (success, message)
        """
        if not self._files:
            return False, "No files"

        file_path = self.get_current_file()
        if file_path is None:
            return False, "No current file"

        # Don't allow deleting the last file
        if len(self._files) == 1:
            return False, "Cannot delete last file"

        try:
            # Remove from filesystem
            file_path.unlink()
            self._logger.info(f"MediaBrowser: deleted file {file_path.name}")

            # Remove from in-memory cache
            self._thumbnail_cache.remove(file_path)

            # Store index before removing
            old_index = self._current_index

            # Remove from files list
            self._files.remove(file_path)

            # Adjust index - move to next file, or stay at last
            if old_index >= len(self._files):
                self._current_index = max(0, len(self._files) - 1)
            # If we deleted not the last file, stay at same index (now points to next file)

            self._logger.info(f"MediaBrowser: delete complete {file_path.name}")
            return True, "Deleted!"

        except PermissionError:
            return False, "Permission denied"
        except Exception as e:
            self._logger.warning(f"MediaBrowser: delete error: {e}")
            return False, f"Delete failed: {e}"

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._temp_dir:
            try:
                self._temp_dir.cleanup()
            except Exception:
                pass
            self._temp_dir = None
        self._thumbnail_cache.clear()
