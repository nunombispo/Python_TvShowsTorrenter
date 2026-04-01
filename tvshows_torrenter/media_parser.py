from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


class MediaParser:
    def __init__(self, video_exts: set[str] | None = None) -> None:
        self._video_exts = video_exts or {".mkv", ".mp4", ".avi", ".mov", ".wmv", ".m4v"}

    def scan_library(
        self,
        media_path: str | Path,
        *,
        use_cache: bool = True,
        cache_path: str | Path | None = None,
    ) -> tuple[list[Path], list[Path]]:
        """
        Returns (imdb_marker_files, video_files) as full paths.

        IMDB marker files are detected by having `.imdb.` in the filename OR a `.imdb` suffix.
        """
        media_path = Path(media_path)
        if not media_path.exists():
            print(f"Media path does not exist: {media_path}")
            return ([], [])

        cache_file = Path(cache_path) if cache_path is not None else Path.cwd() / ".scan_cache.json"
        cache: dict[str, Any] = {}
        if use_cache:
            cache = self._load_cache(cache_file, media_path)

        imdb_markers: list[Path] = []
        video_files: list[Path] = []
        walked_dirs = 0
        last_progress = time.monotonic()
        max_files_env = os.getenv("MAX_FILES")
        max_files = int(max_files_env) if max_files_env else None

        def _should_stop() -> bool:
            return max_files is not None and len(video_files) >= max_files

        print("Scanning media folders...")
        stack: list[Path] = [media_path]
        new_dirs: dict[str, Any] = {}
        while stack:
            root = stack.pop()
            walked_dirs += 1

            now = time.monotonic()
            if walked_dirs % 25 == 0 or (now - last_progress) > 3:
                print(
                    f"  scanned {walked_dirs} folders, found {len(video_files)} video files so far... (latest: {root})"
                )
                last_progress = now

            root_key = str(root)
            try:
                root_mtime_ns = int(root.stat().st_mtime_ns)
            except OSError as err:
                print(f"os.stat error: {err}")
                continue

            cached = cache.get("dirs", {}).get(root_key) if use_cache else None
            if cached and cached.get("mtime_ns") == root_mtime_ns:
                for sub in cached.get("subdirs", []):
                    stack.append(Path(sub))
                for p in cached.get("imdb_markers", []):
                    imdb_markers.append(Path(p))
                for p in cached.get("video_files", []):
                    video_files.append(Path(p))
                    if _should_stop():
                        print(f"Reached MAX_FILES={max_files}; stopping scan early.")
                        print(f"Scan partial: {walked_dirs} folders scanned")
                        return (imdb_markers, video_files)
                new_dirs[root_key] = cached
                continue

            subdirs: list[str] = []
            dir_markers: list[str] = []
            dir_videos: list[str] = []
            try:
                with os.scandir(root) as it:
                    for entry in it:
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                subdirs.append(entry.path)
                                stack.append(Path(entry.path))
                                continue

                            if entry.is_file(follow_symlinks=False):
                                name_lower = entry.name.lower()
                                if ".imdb." in name_lower or name_lower.endswith(".imdb"):
                                    imdb_markers.append(Path(entry.path))
                                    dir_markers.append(entry.path)
                                    continue

                                ext = Path(entry.name).suffix.lower()
                                if ext in self._video_exts:
                                    video_files.append(Path(entry.path))
                                    dir_videos.append(entry.path)
                                    if _should_stop():
                                        print(f"Reached MAX_FILES={max_files}; stopping scan early.")
                                        print(f"Scan partial: {walked_dirs} folders scanned")
                                        new_dirs[root_key] = {
                                            "mtime_ns": root_mtime_ns,
                                            "subdirs": subdirs,
                                            "imdb_markers": dir_markers,
                                            "video_files": dir_videos,
                                        }
                                        if use_cache:
                                            self._save_cache(cache_file, media_path, new_dirs)
                                        return (imdb_markers, video_files)
                        except OSError as err:
                            print(f"os.scandir entry error: {err}")
            except OSError as err:
                print(f"os.scandir error: {err}")

            new_dirs[root_key] = {
                "mtime_ns": root_mtime_ns,
                "subdirs": subdirs,
                "imdb_markers": dir_markers,
                "video_files": dir_videos,
            }

        if use_cache:
            self._save_cache(cache_file, media_path, new_dirs)

        print(f"Scan complete: {walked_dirs} folders scanned")
        return (imdb_markers, video_files)

    def iter_video_files(self, media_path: str | Path) -> list[str]:
        """
        Backwards-compatible helper: returns video *filenames* (not full paths).
        Prefer `scan_library()` for new behavior.
        """
        _markers, videos = self.scan_library(media_path)
        return [p.name for p in videos]

    def _load_cache(self, cache_file: Path, media_root: Path) -> dict[str, Any]:
        try:
            if not cache_file.exists():
                return {"version": 1, "media_root": str(media_root), "dirs": {}}
            raw = json.loads(cache_file.read_text(encoding="utf-8"))
            if raw.get("version") != 1 or raw.get("media_root") != str(media_root):
                return {"version": 1, "media_root": str(media_root), "dirs": {}}
            if not isinstance(raw.get("dirs"), dict):
                raw["dirs"] = {}
            return raw
        except Exception:
            return {"version": 1, "media_root": str(media_root), "dirs": {}}

    def _save_cache(self, cache_file: Path, media_root: Path, dirs: dict[str, Any]) -> None:
        try:
            payload = {"version": 1, "media_root": str(media_root), "dirs": dirs}
            cache_file.write_text(json.dumps(payload), encoding="utf-8")
        except Exception:
            return

