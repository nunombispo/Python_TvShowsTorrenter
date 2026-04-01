import os
import time


class MediaParser:
    def __init__(self):
        pass

    def process_media(self, media_path):
        if not media_path:
            raise ValueError("mediaPath is missing in settings.json")
        if not os.path.exists(media_path):
            print(f"Media path does not exist: {media_path}")
            return []

        video_exts = {".mkv", ".mp4", ".avi", ".mov", ".wmv", ".m4v"}
        list_files = []
        walked_dirs = 0
        last_progress = time.monotonic()
        max_files_env = os.getenv("MAX_FILES")
        max_files = int(max_files_env) if max_files_env else None

        def _onerror(err):
            print(f"os.walk error: {err}")

        print("Scanning media folders...")
        for root, _dirs, files in os.walk(media_path, onerror=_onerror):
            walked_dirs += 1
            now = time.monotonic()
            if walked_dirs % 25 == 0 or (now - last_progress) > 3:
                print(f"  scanned {walked_dirs} folders, found {len(list_files)} video files so far... (latest: {root})")
                last_progress = now

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in video_exts:
                    list_files.append(file)
                    if max_files is not None and len(list_files) >= max_files:
                        print(f"Reached MAX_FILES={max_files}; stopping scan early.")
                        print(f"Scan partial: {walked_dirs} folders scanned")
                        return list_files

        print(f"Scan complete: {walked_dirs} folders scanned")
        return list_files
