import re

from cachetools import LRUCache
from abc import ABC, abstractmethod

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

    def __init__(self, song_size: int = 100, query_size: int = 300):
        self._url_cache: LRUCache[str, Song] = LRUCache(maxsize=song_size)  # url -> song
        self._query_cache: LRUCache[str, str] = LRUCache(maxsize=query_size)  # query -> url
        self._youtube_regex = re.compile(
            r"https?://(?:www\.)?youtu(?:be\.com/watch\?v=|\.be/)([\w\-_]*)(&(amp;)?‌​[\w?‌​=]*)?"
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
