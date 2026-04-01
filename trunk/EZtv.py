import json
from json import JSONDecodeError
from time import sleep

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


class EZtvTorrent:
    def __init__(self, json):
        self.filename = json['filename']
        self.torrent_url = json['torrent_url']
        self.season = int(json['season'])
        self.episode = int(json['episode'])
        self.seeds = int(json['seeds'])
        self.size = int(int(json['size_bytes']) / 1024 / 1024)

    def __str__(self):
        text = "Filename: " + self.filename + "\nSeeds: " + str(self.seeds) + "\nSize: " + str(self.size) + "\nS" + \
               str(self.season) + "\nE" + str(self.episode)
        return text


class EZtv:
    def __init__(self):
        self.search_url_imdb = 'https://eztv1.xyz/api/get-torrents?imdb_id='
        pass

    def _fetch_json_with_requests(self, url):
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def _fetch_json_with_playwright(self, url):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.set_default_navigation_timeout(15000)
                page.set_default_timeout(15000)
                page.goto(url, wait_until="domcontentloaded")
                # If the API returns JSON rendered inside <pre>, grab it.
                pre = page.locator("pre").first
                if pre.count() > 0:
                    text = pre.inner_text()
                else:
                    text = page.content()
                return json.loads(text)
            finally:
                browser.close()

    def search_torrents(self, imdb_id, pagenumber):
        torrent_list = []
        if pagenumber > 1:
            search_url = self.search_url_imdb + str(imdb_id) + '&page=' + str(pagenumber)
        else:
            search_url = self.search_url_imdb + str(imdb_id)
        print(search_url)
        try:
            try:
                eztv_json = self._fetch_json_with_playwright(search_url)
            except (PlaywrightTimeoutError, OSError, ValueError, JSONDecodeError) as e:
                print(f"Playwright fetch failed, falling back to requests: {e}")
                eztv_json = self._fetch_json_with_requests(search_url)
            if int(eztv_json.get('torrents_count', 0)) > 0 and 'torrents' in eztv_json:
                for torrent_json in eztv_json['torrents']:
                    torrent_list.append(EZtvTorrent(torrent_json))
        except (requests.RequestException, JSONDecodeError, ValueError) as e:
            print(f"EZTV request/parse error: {e}")
        return torrent_list

    def search_imdb(self, name, imdb_id, season, episode, next_season, next_episode):
        unfiltered_torrents_list = []
        continue_search = True
        page_number = 1

        # Search all pages
        while continue_search:
            sleep(0.5)
            print('Searching torrent page ' + str(page_number) + ' for IMDB: ' + str(imdb_id))
            tor_list = self.search_torrents(imdb_id, page_number)
            if len(tor_list) > 0:
                page_number += 1
                unfiltered_torrents_list.extend(tor_list)
            else:
                continue_search = False

        torrents_list = []
        # Filter torrents by criteria
        for item in unfiltered_torrents_list:
            if item.season == season and item.episode == episode and item.seeds > 1:
                torrents_list.append(item)

        # Filter again by criteria (for next season)
        if len(torrents_list) == 0:
            for item in unfiltered_torrents_list:
                if item.season == next_season and item.episode == next_episode and item.seeds > 1:
                    torrents_list.append(item)

        return torrents_list

    def download_torrent(self, torrent, downloadfolder_path):
        assert isinstance(torrent, EZtvTorrent)
        url = torrent.torrent_url
        filename = url.split("/")[-1]
        with requests.get(url, timeout=30) as request:
            print('Downloading torrent file ' + torrent.filename + ' ...')
            if request.status_code == 200:
                with open(downloadfolder_path + '/' + filename, 'wb') as f:
                    f.write(request.content)
                    return True
            else:
                print('Error torrent ' + torrent.torrent_url + ' ... (' + str(request.status_code) + ')')
                return False

#if __name__ == "__main__":
#    eztv = EZtv()
#    list_torrent = eztv.search_imdb("Show name", 2741602, 6, 5)
#    eztv.download_torrent(list_torrent[0])
