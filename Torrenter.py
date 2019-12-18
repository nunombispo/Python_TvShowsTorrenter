from operator import attrgetter

from Settings import Settings
from MediaParser import MediaParser
from TvShows import TvShows
from EZtv import EZtv


def check_settings():
    # Check settings valid
    settings.check_settings()


def process_files():
    # Process media files
    media_path = settings.get_media_path()
    media_parser = MediaParser()
    return media_parser.process_media(media_path)


def process_tvshows():
    list_tvshows = []
    list_files = process_files()
    for filename in list_files:
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
                eztv.download_torrent(sorted_list[0], settings.get_download_folder())
            else:
                print('No torrent found...')


def main():
    check_settings()
    list_tvshows = process_tvshows()
    search_tvshows(list_tvshows)


if __name__ == "__main__":
    # Init classes
    settings = Settings()
    # Call Main
    main()
