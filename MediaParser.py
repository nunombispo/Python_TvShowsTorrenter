import os


class MediaParser:
    def __init__(self):
        pass

    def process_media(self, media_path):
        list_files = []
        for r, d, f in os.walk(media_path):
            for file in f:
                list_files.append(file)
        return list_files
