from __future__ import annotations

import json
import os
from dataclasses import dataclass
from json import JSONDecodeError
from time import sleep

import requests

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    _HAS_PLAYWRIGHT = True
except Exception:
    PlaywrightTimeoutError = Exception  # type: ignore[misc,assignment]
    sync_playwright = None  # type: ignore[assignment]
    _HAS_PLAYWRIGHT = False


@dataclass(frozen=True)
class EZtvTorrent:
    filename: str
    torrent_url: str | None
    magnet_url: str | None
    season: int
    episode: int
    seeds: int
    size_mb: int

    @classmethod
    def from_json(cls, payload: dict) -> "EZtvTorrent":
        size_mb = int(int(payload["size_bytes"]) / 1024 / 1024)
        magnet = payload.get("magnet_url") or payload.get("magnet") or payload.get("magnetURI") or None
        torrent_url = payload.get("torrent_url") or payload.get("torrent") or payload.get("url") or None
        return cls(
            filename=payload["filename"],
            torrent_url=torrent_url,
            magnet_url=magnet,
            season=int(payload["season"]),
            episode=int(payload["episode"]),
            seeds=int(payload["seeds"]),
            size_mb=size_mb,
        )


def pick_best_by_size(
    torrents: list[EZtvTorrent],
    *,
    min_mb: int = 300,
    max_mb: int = 500,
) -> EZtvTorrent | None:
    """
    Prefer a torrent within [min_mb, max_mb]. If none exist, pick the closest outside the range.
    """
    if not torrents:
        return None

    mid = (min_mb + max_mb) / 2.0

    def score(t: EZtvTorrent) -> tuple[int, float, int]:
        if min_mb <= t.size_mb <= max_mb:
            # In-range wins; then prefer closer to mid; then more seeds.
            return (0, abs(t.size_mb - mid), -t.seeds)
        # Outside-range: distance to nearest boundary; then closer to mid; then more seeds.
        dist = min(abs(t.size_mb - min_mb), abs(t.size_mb - max_mb))
        return (1, float(dist) + abs(t.size_mb - mid) / 1000.0, -t.seeds)

    return sorted(torrents, key=score)[0]


class EZtv:
    def __init__(self, base_url: str | None = None) -> None:
        self._base_urls = [
            base_url,
            "https://eztvx.to/api/get-torrents?imdb_id=",
            "https://eztv.re/api/get-torrents?imdb_id=",
            "https://eztv1.xyz/api/get-torrents?imdb_id=",
        ]
        self._base_urls = [u for u in self._base_urls if u]

    def _fetch_json_with_requests(self, url: str) -> dict:
        resp = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
                "Accept": "application/json,text/plain,*/*",
            },
        )
        resp.raise_for_status()
        return resp.json()

    def _fetch_json_with_playwright(self, url: str) -> dict:
        if not _HAS_PLAYWRIGHT or sync_playwright is None:
            raise RuntimeError("Playwright not available")

        user_agent = os.getenv(
            "EZTV_USER_AGENT",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
        )
        headless = os.getenv("EZTV_HEADLESS", "1").strip() not in {"0", "false", "False", "no", "NO"}
        debug = os.getenv("EZTV_DEBUG", "0").strip() in {"1", "true", "True", "yes", "YES"}

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )
            try:
                context = browser.new_context(
                    user_agent=user_agent,
                    locale="en-US",
                    extra_http_headers={
                        "Accept": "application/json,text/plain,*/*",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Referer": "https://eztvx.to/",
                    },
                    java_script_enabled=True,
                )
                page = context.new_page()
                page.set_default_navigation_timeout(20000)
                page.set_default_timeout(20000)

                # Capture the actual network response body for the API URL.
                resp = page.goto(url, wait_until="domcontentloaded")
                if resp is None:
                    raise ValueError("No response from page.goto")

                body = resp.text()
                try:
                    return json.loads(body)
                except JSONDecodeError:
                    # Some hosts render JSON in <pre>. Try that before failing.
                    pre = page.locator("pre").first
                    if pre.count() > 0:
                        return json.loads(pre.inner_text())

                    if debug:
                        snippet = body[:300].replace("\n", "\\n")
                        raise ValueError(f"Non-JSON response (status={resp.status}): {snippet}")
                    raise
            finally:
                browser.close()

    def search_torrents(self, imdb_id: str, page_number: int) -> list[EZtvTorrent]:
        for base in self._base_urls:
            torrent_list: list[EZtvTorrent] = []
            if page_number > 1:
                url = f"{base}{imdb_id}&page={page_number}"
            else:
                url = f"{base}{imdb_id}"

            print(url)
            try:
                try:
                    eztv_json = self._fetch_json_with_playwright(url)
                except (PlaywrightTimeoutError, OSError, ValueError, JSONDecodeError, RuntimeError) as e:
                    print(f"Playwright fetch failed, falling back to requests: {e}")
                    eztv_json = self._fetch_json_with_requests(url)

                if int(eztv_json.get("torrents_count", 0)) > 0 and "torrents" in eztv_json:
                    for torrent_json in eztv_json["torrents"]:
                        torrent_list.append(EZtvTorrent.from_json(torrent_json))
                return torrent_list
            except (requests.RequestException, JSONDecodeError, ValueError) as e:
                print(f"EZTV request/parse error: {e}")
                continue

        return []

    def search_imdb(
        self,
        imdb_id: str,
        season: int,
        episode: int,
        next_season: int,
        next_episode: int,
        min_seeds: int = 1,
    ) -> list[EZtvTorrent]:
        unfiltered: list[EZtvTorrent] = []
        page_number = 1

        while True:
            sleep(0.5)
            print(f"Searching torrent page {page_number} for IMDB: {imdb_id}")
            page = self.search_torrents(imdb_id, page_number)
            if not page:
                break
            page_number += 1
            unfiltered.extend(page)

        def _match(item: EZtvTorrent, s: int, e: int) -> bool:
            return item.season == s and item.episode == e and item.seeds >= min_seeds

        matched = [t for t in unfiltered if _match(t, season, episode)]
        if not matched:
            matched = [t for t in unfiltered if _match(t, next_season, next_episode)]
        return matched

    def download_torrent(self, torrent: EZtvTorrent, downloadfolder_path: str) -> bool:
        url = torrent.torrent_url
        if not url:
            print("No torrent_url available to download (magnet-only result).")
            return False
        filename = url.split("/")[-1]
        dest = f"{downloadfolder_path.rstrip('/')}/{filename}"
        with requests.get(url, timeout=30) as request:
            print(f"Downloading torrent file {torrent.filename} ...")
            if request.status_code == 200:
                with open(dest, "wb") as f:
                    f.write(request.content)
                return True
            print(f"Error torrent {torrent.torrent_url} ... ({request.status_code})")
            return False

