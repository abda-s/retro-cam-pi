"""Thumbnail cache management for media browser."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image


class ThumbnailCache:
    """Manages in-memory and on-disk thumbnail cache."""

    def __init__(self, save_directory: Path, display_size: Tuple[int, int], logger):
        self._save_directory = save_directory
        self._display_size = display_size
        self._logger = logger
        self._cache: Dict[Path, Image.Image] = {}

        self._cache_dir: Path = save_directory / ".thumbnails"
        self._cache_dir.mkdir(exist_ok=True)

    @property
    def cache_dir(self) -> Path:
        """Return thumbnail cache directory path."""
        return self._cache_dir

    def get(self, file_path: Path) -> Optional[Image.Image]:
        """Return cached thumbnail for file if present."""
        return self._cache.get(file_path)

    def set(self, file_path: Path, thumbnail: Image.Image) -> None:
        """Store thumbnail in memory and on disk."""
        self._cache[file_path] = thumbnail
        self._save_to_disk(file_path, thumbnail)

    def remove(self, file_path: Path) -> None:
        """Remove thumbnail from memory and disk cache."""
        if file_path in self._cache:
            del self._cache[file_path]

        cache_path = self._cache_dir / f"{file_path.stem}.png"
        if cache_path.exists():
            try:
                cache_path.unlink()
                self._logger.debug(f"MediaBrowser: removed cache {cache_path.name}")
            except Exception as exc:
                self._logger.warning(f"MediaBrowser: failed to remove cache: {exc}")

    def clear(self) -> None:
        """Clear in-memory cache."""
        self._cache.clear()

    def load_from_disk(self, files: List[Path]) -> None:
        """Load matching cache files from disk into memory."""
        if not self._cache_dir.exists():
            return

        loaded_count = 0
        valid_files = set(files)

        for cache_file in self._cache_dir.glob("*.png"):
            try:
                original_name = cache_file.stem
                original_file = self._resolve_original_file(original_name)

                if original_file is None or original_file not in valid_files:
                    cache_file.unlink()
                    self._logger.debug(f"MediaBrowser: removed stale cache {cache_file.name}")
                    continue

                with Image.open(cache_file) as img:
                    thumbnail = img.copy()

                if thumbnail.size != self._display_size:
                    cache_file.unlink()
                    self._logger.debug(
                        f"MediaBrowser: removed wrong-size cache for {original_file.name}"
                    )
                    continue

                self._cache[original_file] = thumbnail
                loaded_count += 1

            except Exception:
                try:
                    cache_file.unlink()
                    self._logger.debug(f"MediaBrowser: removed invalid cache {cache_file.name}")
                except Exception:
                    pass

        if loaded_count > 0:
            self._logger.info(f"MediaBrowser: loaded {loaded_count} thumbnails from disk cache")

    def validate(self, files: List[Path]) -> None:
        """Validate cache entries against current file list and display size."""
        if not self._cache:
            self._logger.debug("MediaBrowser: no cached thumbnails (generate on first view)")
            return

        valid_files = set(files)
        invalid_files = []

        self._logger.info(f"MediaBrowser: validating {len(self._cache)} cached thumbnails")
        self._logger.debug(f"MediaBrowser: thumbnail target size {self._display_size}")

        for file_path, thumbnail in list(self._cache.items()):
            if file_path not in valid_files:
                invalid_files.append(file_path)
                continue
            if thumbnail.size != self._display_size:
                self._logger.debug(
                    f"MediaBrowser: invalid cache size for {file_path.name}: {thumbnail.size}"
                )
                invalid_files.append(file_path)

        for file_path in invalid_files:
            self.remove(file_path)

        if invalid_files:
            self._logger.info(f"MediaBrowser: cleared {len(invalid_files)} invalid thumbnails")

        valid_count = len(self._cache)
        if valid_count > 0:
            self._logger.info(f"MediaBrowser: {valid_count} cached thumbnails are valid")

    def _save_to_disk(self, file_path: Path, thumbnail: Image.Image) -> None:
        """Save thumbnail to disk cache."""
        try:
            cache_path = self._cache_dir / f"{file_path.stem}.png"
            thumbnail.save(cache_path, "PNG")
        except Exception as exc:
            self._logger.warning(f"MediaBrowser: failed to save thumbnail to cache: {exc}")

    def _resolve_original_file(self, stem: str) -> Optional[Path]:
        """Resolve thumbnail stem back to source media file path."""
        for ext in (".png", ".mp4", ".mkv"):
            candidate = self._save_directory / f"{stem}{ext}"
            if candidate.exists():
                return candidate
        return None
