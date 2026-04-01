from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SettingsData:
    media_path: str
    download_folder: str


class Settings:
    """
    Loads and persists configuration.

    Lookup order:
    - Explicit path passed to ctor
    - $TVSHOWS_TORRENTER_SETTINGS
    - ./settings.json (repo/root working dir)
    - ~/.config/tvshows-torrenter/settings.json (XDG)
    """

    def __init__(self, settings_path: str | Path | None = None) -> None:
        self._settings_path = self._resolve_settings_path(settings_path)

    @property
    def path(self) -> Path:
        return self._settings_path

    def load(self) -> SettingsData:
        if not self._settings_path.exists():
            data = self._ask_user()
            self.save(data)
            return data

        raw = json.loads(self._settings_path.read_text(encoding="utf-8"))
        return self._parse(raw)

    def save(self, data: SettingsData) -> None:
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"mediaPath": data.media_path, "downloadFolder": data.download_folder}
        self._settings_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def _parse(self, raw: dict[str, Any]) -> SettingsData:
        media_path = str(raw.get("mediaPath") or "").strip()
        download_folder = str(raw.get("downloadFolder") or "").strip()
        if not media_path:
            raise ValueError(f"Missing 'mediaPath' in {self._settings_path}")
        if not download_folder:
            raise ValueError(f"Missing 'downloadFolder' in {self._settings_path}")
        return SettingsData(media_path=media_path, download_folder=download_folder)

    def _ask_user(self) -> SettingsData:
        print("SETTINGS:")
        media_path = input(" * What's the media path location: ").strip()
        download_folder = input(" * What's the download folder path: ").strip()
        return SettingsData(media_path=media_path, download_folder=download_folder)

    def _resolve_settings_path(self, settings_path: str | Path | None) -> Path:
        if settings_path is not None:
            return Path(settings_path).expanduser().resolve()

        env = os.getenv("TVSHOWS_TORRENTER_SETTINGS")
        if env:
            return Path(env).expanduser().resolve()

        cwd_candidate = Path.cwd() / "settings.json"
        if cwd_candidate.exists():
            return cwd_candidate.resolve()

        xdg = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
        return (xdg / "tvshows-torrenter" / "settings.json").expanduser().resolve()

