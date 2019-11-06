import PTN


class TvShows:
    def __init__(self):
        self.tvShowName = None
        self.tvShowAlias = None
        self.currentSeason = None
        self.currentEpisode = None
        self.nextSeason = None
        self.nextEpisode = None

    def __str__(self):
        text = self.tvShowName + " S" + str(self.currentSeason) + " E" + str(self.currentEpisode)
        return text

    def process_filename(self, filename):
        try:
            filename = filename.replace('_', '.')
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
            self.tvShowName = None
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
                        if int(self.currentSeason) > int(show.currentSeason):
                            show.currentSeason = self.currentSeason
                            show.currentEpisode = self.currentEpisode
                        else:
                            if int(self.currentEpisode) > int(show.currentEpisode):
                                show.currentEpisode = self.currentEpisode
                if found:
                    should_insert = False
                else:
                    should_insert = True
        else:
            should_insert = False
        return should_insert
