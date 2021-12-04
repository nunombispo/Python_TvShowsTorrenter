import os
import PTN


class TvShows:
    def __init__(self):
        self.imdb_id = None
        self.tvShowName = None
        self.tvShowAlias = None
        self.currentSeason = None
        self.currentEpisode = None

    def __str__(self):
        if self.imdb_id:
            text = self.tvShowName + " IMDB: " + self.imdb_id + " S" + str(self.currentSeason) + " E" + str(self.currentEpisode)
        else:
            text = self.tvShowName + " S" + str(self.currentSeason) + " E" + str(
                self.currentEpisode)
        return text

    def process_imdb_from_file(self, filename):
        new_filename = filename.split('.')[-1]
        self.imdb_id = new_filename

    def process_filename(self, filename):
        try:
            filename = filename.replace('_', '.')
            # print(filename)
            # Check for IMDB file
            if 'imdb' in filename.lower():
                self.process_imdb_from_file(filename)
                filename = filename.replace('imdb', '')
            info = PTN.parse(filename)
            self.tvShowName = info['title'].strip().title()
            # Clean Los Angeles
            if 'los angeles' in self.tvShowName.lower():
                self.tvShowName = self.tvShowName.lower().replace('los angeles', 'la').strip().title()
            # Clean THE
            if self.tvShowName.lower().startswith('the'):
                self.tvShowName = self.tvShowName[3:].strip()
            # Clean US
            if self.tvShowName.lower().endswith('us'):
                self.tvShowName = self.tvShowName[:-2].strip()
            self.currentSeason = info['season']
            self.currentEpisode = info['episode']
        except KeyError:
            self.imdb_id = None
            self.tvShowName = None
            self.tvShowAlias = None
            self.currentSeason = None
            self.currentEpisode = None

    def match_tvshow(self, list_tvshows):
        should_insert = False
        if self.tvShowName:
            if not list_tvshows:
                should_insert = True
            else:
                found = False
                for show in list_tvshows:
                    if self.tvShowName.lower() == show.tvShowName.lower():
                        found = True
                        if self.imdb_id:
                            show.imdb_id = self.imdb_id
                        if int(self.currentSeason) > int(show.currentSeason):
                            show.currentSeason = self.currentSeason
                            show.currentEpisode = self.currentEpisode
                        else:
                            if type(show.currentEpisode) == list:
                                show.currentEpisode = show.currentEpisode[-1]
                            if int(self.currentSeason) == int(show.currentSeason) and int(self.currentEpisode) > int(show.currentEpisode):
                                show.currentEpisode = self.currentEpisode
                if found:
                    should_insert = False
                else:
                    should_insert = True
        else:
            should_insert = False
        return should_insert

