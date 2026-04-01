from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
import re

from .eztv import EZtv, EZtvTorrent, pick_best_by_size
from .media_parser import MediaParser
from .settings import Settings, SettingsData
from .tvshows import TvShow


@dataclass(frozen=True)
class ShowIndex:
    imdb_id: str
    name: str
    last_season: int | None
    last_episode: int | None


@dataclass(frozen=True)
class LinkResult:
    imdb_id: str
    name: str
    next_season: int
    next_episode: int
    torrent: EZtvTorrent | None


def _infer_show_root(marker_path: Path) -> Path:
    """
    Try to infer the show root folder from where the imdb marker lives.

    Handles marker files that might be placed inside season folders or Synology @eaDir.
    """
    p = marker_path.parent
    if p.name == "@eaDir":
        p = p.parent
    # Season folder patterns: S1, S01, Season 1, Season_01
    if re.fullmatch(r"(?i)s\d{1,2}", p.name) or re.fullmatch(r"(?i)season[ _]?\d{1,2}", p.name):
        return p.parent
    return p


def _index_library(media_root: str | Path) -> list[ShowIndex]:
    """
    Build per-show index using `.imdb` marker filenames for imdb_id + show title,
    and video filenames for the latest episode.
    """
    media_parser = MediaParser()
    marker_files, video_files = media_parser.scan_library(media_root)

    # Discover shows by IMDB markers
    shows_by_imdb: dict[str, str] = {}
    seed_episode_by_imdb: dict[str, tuple[int, int]] = {}
    show_root_by_imdb: dict[str, Path] = {}
    for marker in marker_files:
        tv = TvShow.parse_imdb_marker(marker.name)
        if not tv or not tv.imdb_id or not tv.name:
            continue
        shows_by_imdb[tv.imdb_id] = tv.name
        show_root_by_imdb[tv.imdb_id] = _infer_show_root(marker)
        if tv.season is not None and tv.episode is not None:
            seed_episode_by_imdb[tv.imdb_id] = (tv.season, tv.episode)

    # Index latest episode by show root folder (more reliable than title matching).
    latest_by_imdb: dict[str, tuple[int, int]] = {}
    for imdb_id, root in show_root_by_imdb.items():
        best: tuple[int, int] | None = None
        for video in video_files:
            try:
                # Fast path: ignore files outside the show's folder tree.
                video.relative_to(root)
            except ValueError:
                continue

            parsed = TvShow.parse_episode_from_video(video.name)
            if not parsed or parsed.season is None or parsed.episode is None:
                continue
            cand = (parsed.season, parsed.episode)
            if best is None or cand > best:
                best = cand

        if best is not None:
            latest_by_imdb[imdb_id] = best

    indexed: list[ShowIndex] = []
    for imdb_id, name in sorted(shows_by_imdb.items(), key=lambda kv: kv[1].lower()):
        last = latest_by_imdb.get(imdb_id)
        if last is None:
            last = seed_episode_by_imdb.get(imdb_id)
        last_season, last_episode = last if last else (None, None)
        indexed.append(ShowIndex(imdb_id=imdb_id, name=name, last_season=last_season, last_episode=last_episode))

    return indexed


def _next_episode(last_season: int | None, last_episode: int | None) -> tuple[int, int, int, int] | None:
    if last_season is None or last_episode is None:
        return None
    return (last_season, last_episode + 1, last_season + 1, 1)


def _print_next_episodes(indexed: list[ShowIndex]) -> None:
    print("")
    print("Next episodes:")
    for show in indexed:
        targets = _next_episode(show.last_season, show.last_episode)
        if targets is None:
            print(f"- {show.name} (imdb:{show.imdb_id}) next: unknown (could not determine last episode)")
            continue
        season, episode, _next_season, _next_episode_num = targets
        print(f"- {show.name} (imdb:{show.imdb_id}) next: S{season:02d}E{episode:02d}")


def _search_eztv_and_write_links(indexed: list[ShowIndex], output_path: str | Path = "links.txt") -> None:
    eztv = EZtv()
    results: list[LinkResult] = []

    for show in indexed:
        targets = _next_episode(show.last_season, show.last_episode)
        if targets is None:
            results.append(LinkResult(imdb_id=show.imdb_id, name=show.name, next_season=0, next_episode=0, torrent=None))
            continue

        season, episode, next_season, next_episode = targets
        print("")
        print(f"Searching EZTV for {show.name} (imdb:{show.imdb_id}) next: S{season:02d}E{episode:02d}")

        torrents = eztv.search_imdb(
            imdb_id=show.imdb_id,
            season=season,
            episode=episode,
            next_season=next_season,
            next_episode=next_episode,
            min_seeds=2,
        )
        best = pick_best_by_size(torrents, min_mb=300, max_mb=500) if torrents else None
        if best:
            print(f"  Picked: {best.size_mb}MB seeds={best.seeds} ({best.filename})")
        else:
            print("  No torrent found (or EZTV blocked).")

        results.append(LinkResult(imdb_id=show.imdb_id, name=show.name, next_season=season, next_episode=episode, torrent=best))

    out = Path(output_path)
    lines: list[str] = []
    for r in results:
        if r.next_season and r.next_episode:
            header = f"{r.name} (imdb:{r.imdb_id}) next: S{r.next_season:02d}E{r.next_episode:02d}"
        else:
            header = f"{r.name} (imdb:{r.imdb_id}) next: unknown"
        lines.append(header)
        if r.torrent is None:
            lines.append("torrent_url: -")
            lines.append("magnet: -")
        else:
            lines.append(f"torrent_url: {r.torrent.torrent_url or '-'}")
            lines.append(f"magnet: {r.torrent.magnet_url or '-'}")
        lines.append("")

    out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {out} ({len(results)} shows)")


def run(settings_path: str | None = None) -> None:
    settings_loader = Settings(settings_path=settings_path)
    data = settings_loader.load()

    print(f"Settings file: {settings_loader.path}")
    print(f"Media path: {data.media_path}")
    print(f"Download folder: {data.download_folder}")

    indexed = _index_library(data.media_path)
    if not indexed:
        print("No TV shows detected from .imdb markers in media path.")
        return

    max_shows_env = os.getenv("MAX_SHOWS")
    max_shows = int(max_shows_env) if max_shows_env else None
    if max_shows is not None:
        indexed = indexed[:max_shows]

    _print_next_episodes(indexed)
    _search_eztv_and_write_links(indexed, output_path="links.txt")

