import json
from json import JSONDecodeError
from time import sleep

import requests
from bs4 import BeautifulSoup
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

    def search_torrents(self, imdb_id, pagenumber):
        torrent_list = []
        if pagenumber > 1:
            search_url = self.search_url_imdb + str(imdb_id) + '&page=' + str(pagenumber)
        else:
            search_url = self.search_url_imdb + str(imdb_id)
        print(search_url)
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=False,args=["--start-maximized"])
                page = browser.new_page()
                page.goto(search_url)
                page.wait_for_timeout(500)
                html = page.content()
                # With BeautifulSoup get content from tag <pre>
                soup = BeautifulSoup(html, "html.parser")
                # Extract content from <pre> tag
                pre_content = soup.find("pre").text
                # Convert to JSON
                eztv_json = json.loads(pre_content)
                if int(eztv_json['torrents_count']) > 0:
                    if 'torrents' in eztv_json:
                        for torrent_json in eztv_json['torrents']:
                            eztv_torrent = EZtvTorrent(torrent_json)
                            torrent_list.append(eztv_torrent)
            except JSONDecodeError as e:
                print(str(e.msg))
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
        with requests.get(url) as request:
            print('Downloading torrent file ' + torrent.filename + ' ...')
            if request.status_code == 200:
                with open(downloadfolder_path + '/ ' + filename, 'wb') as f:
                    f.write(request.content)
                    return True
            else:
                print('Error torrent ' + torrent.torrent_url + ' ... (' + str(request.status_code) + ')')
                return False

#if __name__ == "__main__":
#    eztv = EZtv()
#    list_torrent = eztv.search_imdb("Show name", 2741602, 6, 5)
#    eztv.download_torrent(list_torrent[0])
