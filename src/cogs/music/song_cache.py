import re

from cachetools import LRUCache
from abc import ABC, abstractmethod
from time import time

from .song import Song


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
    """
    Implements the Least Recently Used (LRU) cache for storing song data and
    related queries. Songs are stored by their URL and queries.
    """

    _youtube_regex = re.compile(
        r"https?://(?:www\.)?youtu(?:be\.com/watch\?v=|\.be/)([\w\-_]*)(&(amp;)?‌​[\w?‌​=]*)?"
    )

    def __init__(self, songs_size: int, queries_size: int):
        self._url_cache: LRUCache[str, Song] = LRUCache(maxsize=songs_size)  # url: song
        self._query_cache: LRUCache[str, str] = LRUCache(maxsize=queries_size)  # query: url

    def __contains__(self, key: str) -> bool:
        if key in self._query_cache:
            song_url = self._query_cache[key]
        elif key in self._url_cache:
            song_url = key
        else:
            return False

        song = self._url_cache.get(song_url)
        if not song:
            return False

        current_time = int(time())

        if song.expires_at + song.duration > current_time:
            return True
        else:
            del self._url_cache[song_url]
            return False

    def __getitem__(self, key: str) -> Song:
        if key in self._url_cache:
            return self._url_cache[key]
        return self._url_cache[self._query_cache[key]]

    def __setitem__(self, query: str, song: Song) -> None:
        if not song.expires_at:
            return
        self._url_cache[song.url] = song
        if self._youtube_regex.match(query):
            self._query_cache[query] = song.url
