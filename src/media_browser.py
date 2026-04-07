"""Media browser module for rpi-tft-camera.

Handles browsing saved images and videos with thumbnail generation.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from datetime import datetime

try:
    from PIL import Image
except ImportError:
    raise ImportError("PIL not installed. Run: pip3 install pillow")

import numpy as np


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
        print(f"[MediaBrowser] Initialized with display size: {display_size}")

        # Browser state
        self._files: List[Path] = []
        self._current_index: int = 0
        self._thumbnail_cache: Dict[Path, Image.Image] = {}
        self._temp_dir: Optional[tempfile.TemporaryDirectory] = None

        # Persistent disk cache for thumbnails
        self._cache_dir: Path = save_directory / ".thumbnails"
        self._cache_dir.mkdir(exist_ok=True)
        print(f"[MediaBrowser] Cache directory: {self._cache_dir}")

    def scan_directory(self) -> bool:
        """Scan save directory for media files and sort by newest first.

        Returns:
            True if files were found, False otherwise
        """
        if not self._save_directory.exists():
            return False

        self._files = []

        # Find all PNG, MKV, and MP4 files
        for ext in ['*.png', '*.mkv', '*.mp4']:
            self._files.extend(self._save_directory.glob(ext))

        if not self._files:
            print(f"[MediaBrowser] No files found in {self._save_directory}")
            return False

        # Sort by modification time (newest first)
        self._files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        # Reset index
        self._current_index = 0

        # Load existing cache from disk (persistent across restarts)
        self._load_cache_from_disk()

        print(f"[MediaBrowser] Found {len(self._files)} files:")
        for f in self._files[:10]:  # Show first 10
            print(f"  - {f.name}")
        if len(self._files) > 10:
            print(f"  ... and {len(self._files) - 10} more")

        # Validate cache entries and rebuild invalid ones
        self._validate_and_rebuild_cache()

        return True

    def _load_cache_from_disk(self) -> None:
        """Load existing thumbnails from disk cache."""
        if not self._cache_dir.exists():
            return

        loaded_count = 0
        for cache_file in self._cache_dir.glob('*.png'):
            try:
                # Load thumbnail from disk
                thumbnail = Image.open(cache_file)

                # Map back to original file (remove .png extension to get original name)
                original_name = cache_file.stem  # e.g., "video_20260407_161729"

                # Check all possible original file extensions
                for ext in ['.png', '.mp4', '.mkv']:
                    original_file = self._save_directory / (original_name + ext)
                    if original_file.exists():
                        self._thumbnail_cache[original_file] = thumbnail
                        loaded_count += 1
                        break
                else:
                    # Original file deleted, remove stale cache
                    cache_file.unlink()
                    print(f"[MediaBrowser] Removed stale cache: {cache_file.name}")

            except Exception as e:
                # Invalid cache file, remove it
                try:
                    cache_file.unlink()
                    print(f"[MediaBrowser] Removed invalid cache: {cache_file.name}")
                except Exception:
                    pass

        if loaded_count > 0:
            print(f"[MediaBrowser] Loaded {loaded_count} thumbnails from disk cache")

    def _save_to_disk_cache(self, file_path: Path, thumbnail: Image.Image) -> None:
        """Save thumbnail to disk cache."""
        try:
            # Always save as PNG (regardless of original file extension)
            # This is because video thumbnails are converted to images
            cache_name = file_path.stem + ".png"
            cache_path = self._cache_dir / cache_name
            thumbnail.save(cache_path, "PNG")
        except Exception as e:
            print(f"[MediaBrowser] Failed to save thumbnail to cache: {e}")

    def _validate_and_rebuild_cache(self) -> None:
        """Validate cache and rebuild invalid thumbnails.

        Checks all cached thumbnails against display size.
        Removes thumbnails that don't match display dimensions.
        Loads valid ones from disk, rebuilds invalid ones.
        """
        target_width, target_height = self._display_size
        target_size = (target_width, target_height)

        # First, try to load missing thumbnails from disk
        for file_path in self._files:
            if file_path in self._thumbnail_cache:
                continue  # Already in memory cache

            # Try to load from disk cache (thumbnails are always saved as .png)
            cache_name = file_path.stem + ".png"
            cache_path = self._cache_dir / cache_name
            if cache_path.exists():
                try:
                    thumbnail = Image.open(cache_path)
                    if thumbnail.size == target_size:
                        self._thumbnail_cache[file_path] = thumbnail
                        print(f"[MediaBrowser] Loaded from disk: {file_path.name}")
                    else:
                        # Wrong size, remove stale cache
                        cache_path.unlink()
                        print(f"[MediaBrowser] Removed stale cache (wrong size): {file_path.name}")
                except Exception:
                    # Invalid cache file
                    try:
                        cache_path.unlink()
                    except Exception:
                        pass

        # Now validate in-memory cache
        if not self._thumbnail_cache:
            print(f"[MediaBrowser] No cached thumbnails (will generate on first view)")
            return

        invalid_files = []
        valid_count = 0

        print(f"[MediaBrowser] Validating {len(self._thumbnail_cache)} cached thumbnails...")
        print(f"[MediaBrowser] Target size: {self._display_size}")

        # Check each cached thumbnail
        for file_path, thumbnail in list(self._thumbnail_cache.items()):
            if thumbnail.size != target_size:
                print(f"[MediaBrowser]   INVALID: {file_path.name} = {thumbnail.size}")
                invalid_files.append(file_path)
            else:
                valid_count += 1
                # Save to disk cache if not already there (save as .png)
                cache_name = file_path.stem + ".png"
                cache_path = self._cache_dir / cache_name
                if not cache_path.exists():
                    self._save_to_disk_cache(file_path, thumbnail)

        # Remove invalid cached thumbnails
        if invalid_files:
            for file_path in invalid_files:
                del self._thumbnail_cache[file_path]
                # Remove stale disk cache (save as .png)
                cache_name = file_path.stem + ".png"
                cache_path = self._cache_dir / cache_name
                if cache_path.exists():
                    try:
                        cache_path.unlink()
                    except Exception:
                        pass
            print(f"[MediaBrowser] Cleared {len(invalid_files)} invalid thumbnails")

        if valid_count > 0:
            print(f"[MediaBrowser] {valid_count} cached thumbnails are valid")

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
        file_type = 'video' if file_ext in ['.mkv', '.mp4'] else 'image'

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
        if file_path in self._thumbnail_cache:
            return self._thumbnail_cache[file_path]

        try:
            file_ext = file_path.suffix.lower()
            if file_ext in ['.mkv', '.mp4']:
                # Video: extract first frame using ffmpeg
                print(f"[MediaBrowser] Processing VIDEO: {file_path.name}")
                thumbnail = self._extract_video_thumbnail(file_path)
            else:
                # Image: load and resize
                thumbnail = self._load_image_thumbnail(file_path)

            if thumbnail:
                self._thumbnail_cache[file_path] = thumbnail
                # Save to disk cache for persistence
                self._save_to_disk_cache(file_path, thumbnail)
                return thumbnail
            else:
                print(f"[MediaBrowser] ERROR: Failed to create thumbnail for {file_path.name}")

        except Exception as e:
            print(f"[MediaBrowser] Thumbnail ERROR for {file_path.name}: {e}")

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
            print(f"[MediaBrowser] Original image size: {image.size}, mode: {image.mode}")

            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Resize to full display dimensions (stretch to fit)
            target_size = self._display_size
            image = image.resize(target_size, Image.Resampling.LANCZOS)
            print(f"[MediaBrowser] Resized to: {image.size}")

            return image

        except Exception as e:
            print(f"[MediaBrowser] Image load error for {file_path.name}: {e}")
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
            print(f"[MediaBrowser] Extracting video thumbnail: {file_path.name}")
            print(f"[MediaBrowser] Target size: {width}x{height}")

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

            print(f"[MediaBrowser] Running ffmpeg...")
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,  # Capture stderr for debugging
                stdin=subprocess.DEVNULL
            )

            print(f"[MediaBrowser] FFmpeg return code: {result.returncode}")

            if result.returncode != 0:
                error_msg = result.stderr.decode('utf-8', errors='replace')
                print(f"[MediaBrowser] FFmpeg error output:\n{error_msg}")
                # Return fallback placeholder instead of None
                return self._create_video_placeholder(file_path.name)

            if result.stdout:
                # Calculate expected size: width * height * 3 (RGB)
                expected_size = width * height * 3
                actual_size = len(result.stdout)
                print(f"[MediaBrowser] Video output size: {actual_size} bytes (expected {expected_size})")

                if actual_size == expected_size:
                    # Convert raw bytes to PIL Image
                    image = Image.frombytes('RGB', (width, height), result.stdout)
                    print(f"[MediaBrowser] Video thumbnail created successfully")
                    return image
                else:
                    print(f"[MediaBrowser] ERROR: Size mismatch! expected {expected_size}, got {actual_size}")
                    # Return fallback placeholder
                    return self._create_video_placeholder(file_path.name)
            else:
                print(f"[MediaBrowser] ERROR: No output from ffmpeg")
                return self._create_video_placeholder(file_path.name)

        except FileNotFoundError:
            print("[MediaBrowser] ERROR: FFmpeg not found - video thumbnails disabled")
            # Return fallback placeholder
            return self._create_video_placeholder(file_path.name)
        except Exception as e:
            print(f"[MediaBrowser] Video thumbnail error: {e}")
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

            print(f"[MediaBrowser] Created video placeholder for {filename}")
            return image

        except Exception as e:
            print(f"[MediaBrowser] Error creating placeholder: {e}")
            # Last resort: return a simple gray image
            return Image.new('RGB', self._display_size, (80, 80, 80))

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
            print(f"[MediaBrowser] Deleted file: {file_path.name}")

            # Remove from in-memory cache
            if file_path in self._thumbnail_cache:
                del self._thumbnail_cache[file_path]

            # Remove from disk cache
            cache_name = file_path.stem + ".png"
            cache_path = self._cache_dir / cache_name
            if cache_path.exists():
                try:
                    cache_path.unlink()
                    print(f"[MediaBrowser] Removed cache: {cache_name}")
                except Exception as e:
                    print(f"[MediaBrowser] Failed to remove cache: {e}")

            # Store index before removing
            old_index = self._current_index

            # Remove from files list
            self._files.remove(file_path)

            # Adjust index - move to next file, or stay at last
            if old_index >= len(self._files):
                self._current_index = max(0, len(self._files) - 1)
            # If we deleted not the last file, stay at same index (now points to next file)

            print(f"[MediaBrowser] Deleted: {file_path.name}")
            return True, "Deleted!"

        except PermissionError:
            return False, "Permission denied"
        except Exception as e:
            print(f"[MediaBrowser] Delete error: {e}")
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
