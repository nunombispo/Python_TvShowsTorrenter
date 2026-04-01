from operator import attrgetter
import os

from Settings import Settings
from MediaParser import MediaParser
from TvShows import TvShows
from EZtv import EZtv


def check_settings():
    # Check settings valid
    settings.check_settings()
    media_path = settings.get_media_path()
    download_folder = settings.get_download_folder()
    print(f"Media path: {media_path}")
    print(f"Download folder: {download_folder}")


def process_files():
    # Process media files
    media_path = settings.get_media_path()
    media_parser = MediaParser()
    files = media_parser.process_media(media_path)
    print(f"Found {len(files)} media files")
    return files


def process_tvshows():
    list_tvshows = []
    list_files = process_files()
    max_shows_env = os.getenv("MAX_SHOWS")
    max_shows = int(max_shows_env) if max_shows_env else None
    for filename in list_files:
        if max_shows is not None and len(list_tvshows) >= max_shows:
            print(f"Reached MAX_SHOWS={max_shows}; stopping early for test run.")
            break
        tvshow = TvShows()
        tvshow.process_filename(filename)
        if tvshow.match_tvshow(list_tvshows):
            list_tvshows.append(tvshow)
    return list_tvshows


def search_tvshows(list_tvshows):
    eztv = EZtv()
    for show in list_tvshows:
        print('')
        print('Getting show ' + str(show) + ' ...')
        if show.imdb_id:
            torrent_list = eztv.search_imdb(show.tvShowName, show.imdb_id, show.currentSeason,
                                            show.currentEpisode + 1,
                                            show.currentSeason + 1, 1)
            if torrent_list:
                sorted_list = sorted(torrent_list, key=attrgetter('size'))
                for torrent in sorted_list:
                    if eztv.download_torrent(torrent, settings.get_download_folder()):
                        break
            else:
                print('No torrent found...')


def main():
    check_settings()
    list_tvshows = process_tvshows()
    if not list_tvshows:
        print("No TV shows detected from media path.")
        return
    search_tvshows(list_tvshows)


if __name__ == "__main__":
    # Init classes
    settings = Settings()
    # Call Main
    main()
