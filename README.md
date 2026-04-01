**Python TV Shows Torrenter**

This script will scan a media library folder containing TvShows and parse the filenames into series and the seasons/episodes.

At the moment it will parse a folder, parse the filenames and generate a list of TvShows and the last episode

After that it will search and download a torrent from EZTV, the search is done using an API so no parsing involved.

It uses EZTV API with search for an imdb id, the parsing of files will scan for an IMDB file that contains the id, for example:
American.Horror.Story.S01E01.Pilot.HDTV.XviD-FQM.VTV.imdb.1844624

## Run

1) Install dependencies:

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
```

2) Edit `settings.json` (repo root) with your media library path and download folder.

3) Run:

```bash
python torrenter.py
```

Or as a module:

```bash
python -m tvshows_torrenter
```


_Future Development_
- Add a menu to interact with the script