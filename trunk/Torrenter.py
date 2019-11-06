import time

from Settings import Settings
from MediaParser import MediaParser
from TvShows import TvShows


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


def main():
    check_settings()
    process_tvshows()


if __name__ == "__main__":
    # Init classes
    settings = Settings()
    # Call Main
    main()
