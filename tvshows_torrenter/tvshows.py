from __future__ import annotations

from dataclasses import dataclass
import re

try:
    import PTN  # type: ignore

    _HAS_PTN = True
except Exception:
    PTN = None  # type: ignore[assignment]
    _HAS_PTN = False


@dataclass
class TvShow:
    imdb_id: str | None = None
    name: str | None = None
    season: int | None = None
    episode: int | None = None

    def __str__(self) -> str:
        if not self.name or self.season is None or self.episode is None:
            return "Unknown TV show"
        imdb = f" IMDB: {self.imdb_id}" if self.imdb_id else ""
        return f"{self.name}{imdb} S{self.season} E{self.episode}"

    @staticmethod
    def _normalize_title(title: str) -> str:
        title = title.strip().title()
        if "los angeles" in title.lower():
            title = title.lower().replace("los angeles", "la").strip().title()
        if title.lower().startswith("the "):
            title = title[4:].strip()
        if title.lower().endswith(" us"):
            title = title[:-3].strip()
        return title

    @staticmethod
    def _parse_with_regex(normalized: str) -> tuple[str, int, int] | None:
        """
        Best-effort parser for typical TV release names.
        Examples:
          - Some.Show.S01E02.1080p.WEB-DL.mkv
          - Some Show - 1x02 - Episode Title.mkv
        """
        sxe = re.search(r"(?i)\bS(\d{1,2})E(\d{1,3})\b", normalized)
        if not sxe:
            sxe = re.search(r"(?i)\b(\d{1,2})x(\d{1,3})\b", normalized)
        if not sxe:
            return None

        season = int(sxe.group(1))
        episode = int(sxe.group(2))

        title_part = normalized[: sxe.start()]
        title_part = re.sub(r"[._\-]+", " ", title_part).strip()
        title_part = re.sub(r"\s+", " ", title_part).strip()
        if not title_part:
            return None

        return title_part, season, episode

    @classmethod
    def parse_imdb_marker(cls, marker_filename: str) -> "TvShow | None":
        """
        Parse IMDB marker filenames like:
          - American.Horror.Story.S01E01....imdb.1844624
          - Some.Show.imdb.1844624

        Returns a TvShow with `imdb_id`, `name`, and optional `season`/`episode`
        if they can be parsed from the name portion.
        """
        normalized = marker_filename.replace("_", ".")

        m = re.search(r"(?i)\.imdb\.(\d{6,9})\b", normalized)
        if not m:
            m = re.search(r"(?i)\b(\d{6,9})\.imdb\b", normalized)
        if not m:
            return None

        imdb_id = m.group(1)
        left = normalized[: m.start()]
        left = left.rstrip(".- _")

        # Try to parse season/episode from the left side; if not present,
        # fall back to a title-only best effort.
        parsed = cls._parse_with_regex(left)
        if parsed:
            raw_title, season, episode = parsed
            title = cls._normalize_title(raw_title)
            return cls(imdb_id=imdb_id, name=title, season=season, episode=episode)

        title_part = re.sub(r"[._\-]+", " ", left).strip()
        title_part = re.sub(r"\s+", " ", title_part).strip()
        if not title_part:
            return None
        title = cls._normalize_title(title_part)
        return cls(imdb_id=imdb_id, name=title, season=None, episode=None)

    @classmethod
    def parse_episode_from_video(cls, video_filename: str) -> "TvShow | None":
        """
        Parse a video filename into (show name, season, episode).
        IMDB ids are not expected in normal video names.
        """
        normalized = video_filename.replace("_", ".")
        if _HAS_PTN and PTN is not None:
            try:
                info = PTN.parse(normalized)
                title = cls._normalize_title(info["title"])
                season = int(info["season"])
                episode = info["episode"]
                if isinstance(episode, list):
                    episode = episode[-1]
                episode = int(episode)
                return cls(imdb_id=None, name=title, season=season, episode=episode)
            except Exception:
                return None

        parsed = cls._parse_with_regex(normalized)
        if not parsed:
            return None
        raw_title, season, episode = parsed
        title = cls._normalize_title(raw_title)
        return cls(imdb_id=None, name=title, season=season, episode=episode)

    @classmethod
    def from_filename(cls, filename: str) -> "TvShow | None":
        try:
            normalized = filename.replace("_", ".")
            imdb_id: str | None = None

            if "imdb" in normalized.lower():
                imdb_id = normalized.split(".")[-1]
                normalized = normalized.replace("imdb", "")

            if _HAS_PTN and PTN is not None:
                info = PTN.parse(normalized)
                title = cls._normalize_title(info["title"])
                season = int(info["season"])
                episode = info["episode"]
                if isinstance(episode, list):
                    episode = episode[-1]
                episode = int(episode)
            else:
                parsed = cls._parse_with_regex(normalized)
                if not parsed:
                    return None
                raw_title, season, episode = parsed
                title = cls._normalize_title(raw_title)

            return cls(imdb_id=imdb_id, name=title, season=season, episode=episode)
        except Exception:
            return None

    def merge_newer(self, other: "TvShow") -> bool:
        """
        Merge `other` into `self` if `other` represents the same show and
        is newer (season/episode). Returns True if a merge happened.
        """
        if not self.name or not other.name or self.name.lower() != other.name.lower():
            return False

        if other.imdb_id:
            self.imdb_id = other.imdb_id

        if self.season is None or self.episode is None:
            self.season = other.season
            self.episode = other.episode
            return True

        if other.season is None or other.episode is None:
            return False

        if other.season > self.season:
            self.season = other.season
            self.episode = other.episode
            return True

        if other.season == self.season and other.episode > self.episode:
            self.episode = other.episode
            return True

        return False

