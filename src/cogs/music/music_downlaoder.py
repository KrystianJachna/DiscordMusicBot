import asyncio
import re
from dataclasses import dataclass
from typing import Optional
import logging
from traceback import format_exc
from cachetools import LRUCache
from abc import ABC, abstractmethod
from youtube_search import YoutubeSearch

import yt_dlp
from discord import FFmpegPCMAudio
from pathlib import Path


@dataclass
class Song:
    title: str
    url: str
    duration: int
    thumbnail: Optional[str]
    _stream_url: Optional[str]

    _ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    async def get_source(self) -> FFmpegPCMAudio:
        # every time get_source is called, the FFmpegPCMAudio object is created
        # it has to be created every time because it is not reusable
        return FFmpegPCMAudio(self._stream_url, **self._ffmpeg_options)


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


class MusicFactory:
    class NoResultsFoundException(Exception):

        def __init__(self, query: str) -> None:
            super().__init__(f"No results found for: {query}\nPlease try a different search query")

    class LiveFoundException(Exception):

        def __init__(self, query: str) -> None:
            super().__init__(f"Live stream found for: {query}\nPlease try a different search query")

    class AgeRestrictedException(Exception):

        def __init__(self, query: str) -> None:
            super().__init__(f"Age restricted song found for: {query}\nPlease try a different search query")

    def __init__(self, cookies_path: Path = Path('cookies.txt')):
        self._youtube_regex = re.compile(
            r"http(?:s?):\/\/(?:www\.)?youtu(?:be\.com\/watch\?v=|\.be\/)([\w\-\_]*)(&(amp;)?‌​[\w\?‌​=]*)?"
        )
        self._yt_dlp_opts = {
            'format': 'bestaudio/best',
            'quiet': False,
            'match_filter': '!is_live',
            'logger': YtDlpLogger(),
        }
        self._load_cookies(cookies_path)  # cookies are required to be able to download age-restricted songs
        self._song_cache: SongsCache = LRUSongsCache()

    def _load_cookies(self, cookies_path: Path) -> None:
        if cookies_path.exists():
            logging.info(f"Cookies file loaded from {str(cookies_path)}")
            self._yt_dlp_opts['cookiefile'] = str(cookies_path)
        else:
            logging.info("Cookies file not found. "
                         "Create a cookies.txt file in the root directory for age-restricted songs. "
                         "See README.md for details.")

    async def prepare_song(self, query: str) -> Song:
        if query in self._song_cache:
            logging.debug(f"prepare_song: song found in cache for: {query}")
            return self._song_cache[query]
        song = await asyncio.to_thread(self._construct_song, query)
        self._song_cache[query] = song
        return song

    def _construct_song(self, query: str) -> Song:
        url = self._get_url(query)
        with yt_dlp.YoutubeDL(self._yt_dlp_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except yt_dlp.utils.DownloadError as e:
                error_msg = str(e)
                if "Sign in to confirm your age" in error_msg:
                    raise MusicFactory.AgeRestrictedException(query)
                logging.debug(format_exc())
                raise MusicFactory.NoResultsFoundException(query)

        if info.get('is_live', False):
            raise MusicFactory.LiveFoundException(query)

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
            raise MusicFactory.NoResultsFoundException(query)
        return f"https://www.youtube.com/watch?v={search[0]['id']}"


class SongsCache(ABC):
    # May be implemented with a database or a cache
    @abstractmethod
    def __contains__(self, query: str) -> bool:
        pass

    @abstractmethod
    def __getitem__(self, query: str) -> Song:
        pass

    @abstractmethod
    def __setitem__(self, query: str, song: Song) -> None:
        pass


class LRUSongsCache(SongsCache):
    def __init__(self, song_size: int = 100, query_size: int = 300):
        self._url_cache: LRUCache[str, Song] = LRUCache(maxsize=song_size)  # url -> song
        self._query_cache: LRUCache[str, str] = LRUCache(maxsize=query_size)  # query -> url
        self._youtube_regex = re.compile(
            r"http(?:s?):\/\/(?:www\.)?youtu(?:be\.com\/watch\?v=|\.be\/)([\w\-\_]*)(&(amp;)?‌​[\w\?‌​=]*)?"
        )

    def __contains__(self, key: str) -> bool:
        return key in self._url_cache or key in self._query_cache

    def __getitem__(self, key: str) -> Song:
        if key in self._url_cache:
            return self._url_cache[key]
        return self._url_cache[self._query_cache[key]]

    def __setitem__(self, query: str, song: Song) -> None:
        self._url_cache[song.url] = song
        if self._youtube_regex.match(query):
            self._query_cache[query] = song.url
