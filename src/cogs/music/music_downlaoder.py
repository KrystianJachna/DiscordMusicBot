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


class MusicFactory:

    class NoResultsFoundException(Exception):

        def __init__(self, query: str) -> None:
            super().__init__(f"No results found for: {query}\nPlease try a different search query")

    class LiveFoundException(Exception):

        def __init__(self, query: str) -> None:
            super().__init__(f"Live stream found for: {query}\nPlease try a different search query")

    def __init__(self):
        self._youtube_regex = re.compile(
            r"http(?:s?):\/\/(?:www\.)?youtu(?:be\.com\/watch\?v=|\.be\/)([\w\-\_]*)(&(amp;)?‌​[\w\?‌​=]*)?"
        )
        self._yt_dlp_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'match_filter': '!is_live',
        }
        self._song_cache: SongsCache = LRUSongsCache()

    async def prepare_song(self, query: str) -> Song:
        if query in self._song_cache:
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
                logging.debug(format_exc())
                raise MusicFactory.NoResultsFoundException(query)

        if info.get('is_live', False):
            logging.debug(f"Live stream found for: {query}")
            raise MusicFactory.LiveFoundException(query)

        title = info['title']
        thumbnail = info['thumbnails'][0]['url']
        duration = info['duration']
        stream_url = info['url']

        logging.debug(f"Song: {title} - {url} - {duration} - {thumbnail} - {stream_url}")

        return Song(title, url, duration, thumbnail, stream_url)

    def _get_url(self, query: str) -> str:
        if self._youtube_regex.match(query):
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
