import asyncio
import re
import logging
from traceback import format_exc
from youtube_search import YoutubeSearch

import yt_dlp
from pathlib import Path
from .song_cache import SongsCache, LRUSongsCache
from .song import Song
from typing import Optional


class YtDlpLogger:
    """
    Custom logger for yt-dlp, because the default logger is too verbose.
    Since yd-dlp uses debug, info, warning, and error, it can be overridden.
    """

    _LOG_PREFIX = "yt-dlp: "

    def debug(self, msg):
        logging.debug(f"{self._LOG_PREFIX}{msg}")

    def info(self, msg):
        logging.info(f"{self._LOG_PREFIX}{msg}")

    def warning(self, msg):
        logging.warning(f"{self._LOG_PREFIX}{msg}")

    def error(self, msg):
        logging.error(f"{self._LOG_PREFIX}{msg}")


class SongFactory:
    """
    Singleton class that constructs a Song object from a search query.
    Because of reading cookies, and the need to cache songs, it is a singleton.
    """
    _instance: Optional['SongFactory'] = None

    class NoResultsFoundException(Exception):

        def __init__(self, query: str) -> None:
            super().__init__(f"No results found for: {query}\nPlease try a different search query")

    class LiveFoundException(Exception):

        def __init__(self, query: str) -> None:
            super().__init__(f"Live stream found for: {query}\nPlease try a different search query")

    class AgeRestrictedException(Exception):

        def __init__(self, query: str) -> None:
            super().__init__(f"Age restricted song found for: {query}\nPlease try a different search query")

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SongFactory, cls).__new__(cls)
        return cls._instance

    def __init__(self, song_cache: SongsCache = LRUSongsCache, cookies_path: Path = Path('cookies.txt')):
        self._youtube_regex = re.compile(
            r"https?://(?:www\.)?youtu(?:be\.com/watch\?v=|\.be/)([\w\-_]*)(&(amp;)?‌​[\w?‌​=]*)?"
        )
        self._yt_dlp_opts = {
            'format': 'bestaudio/best',
            'quiet': False,
            'match_filter': '!is_live',
            'logger': YtDlpLogger(),
        }
        self._load_cookies(cookies_path)  # cookies are required to be able to download age-restricted songs
        self._song_cache: SongsCache = song_cache

    async def prepare_song(self, query: str) -> Song:
        if query in self._song_cache:
            logging.debug(f"prepare_song: song found in cache for: {query}")
            return self._song_cache[query]
        song = await asyncio.to_thread(self._construct_song, query)
        self._song_cache[query] = song
        return song

    def _load_cookies(self, cookies_path: Path) -> None:
        if cookies_path.exists():
            logging.info(f"Cookies file loaded from {str(cookies_path)}")
            self._yt_dlp_opts['cookiefile'] = str(cookies_path)
        else:
            logging.info("Cookies file not found. "
                         "Create a cookies.txt file in the root directory for age-restricted songs. "
                         "See README.md for details.")

    def _construct_song(self, query: str) -> Song:
        url = self._get_url(query)
        with yt_dlp.YoutubeDL(self._yt_dlp_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except yt_dlp.utils.DownloadError as e:
                error_msg = str(e)
                if "Sign in to confirm your age" in error_msg:
                    raise SongFactory.AgeRestrictedException(query)
                logging.debug(format_exc())
                raise SongFactory.NoResultsFoundException(query)

        if info.get('is_live', False):
            raise SongFactory.LiveFoundException(query)

        return Song(title=info['title'],
                    url=url,
                    duration=info['duration'],
                    thumbnail=info['thumbnails'][0]['url'],
                    _stream_url=info['url'])

    def _get_url(self, query: str) -> str:
        if self._youtube_regex.match(query):
            logging.debug(f"_get_url: direct url found for: {query}")
            return query
        search = YoutubeSearch(query, max_results=1).to_dict()
        if not search:
            logging.debug(f"_get_url: No results found for: {query}")
            raise SongFactory.NoResultsFoundException(query)
        return f"https://www.youtube.com/watch?v={search[0]['id']}"
