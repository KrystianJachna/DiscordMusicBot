import asyncio
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import logging
from traceback import format_exc
from cachetools import LRUCache
from abc import ABC, abstractmethod

import yt_dlp
from discord import FFmpegPCMAudio


@dataclass
class Song:
    """
    Dataclass to store song information. The stream URL is prepared when the song source is requested.

    :param title:     The title of the song
    :param url:       The URL of the song
    :param duration:  The duration of the song
    :param thumbnail: The thumbnail of the song
    :param stream_url: The stream URL of the song

    :param _ydl_opts: The youtube-dl options to extract the stream URL
    """
    title: str
    url: str
    duration: int
    thumbnail: Optional[str]
    stream_url: Optional[str] = None

    _ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_playlist': True,
        'match_filter': yt_dlp.utils.match_filter_func("!is_live"),
        'noplaylist': True
    }
    _ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }


    async def get_source(self) -> FFmpegPCMAudio:
        """
        Get the source of the song. Prepare the stream URL if it is not already prepared.

        :return: The source of the song
        """
        if not self.stream_url:
            await asyncio.to_thread(self._prepare_stream)
        return FFmpegPCMAudio(self.stream_url, **self._ffmpeg_options)

    def _prepare_stream(self) -> None:
        """
        Prepare the stream URL of the song and store it in the stream_url attribute.

        :return: None
        """
        with yt_dlp.YoutubeDL(self._ydl_opts) as ydl:
            info = ydl.extract_info(self.url, download=False)
        self.stream_url = info['url']



class MusicFactory:
    """
    Class to download music from YouTube using youtube-dl.
    """

    class NoResultsFound(Exception):
        """
        Exception to raise when no results are found for a search query.

        :param query: The search query
        """
        def __init__(self, query: str) -> None:
            super().__init__(f"No results found for: {query}\nPlease try a different search query")

    def __init__(self):
        self.youtube_regex = re.compile(
            r"http(?:s?):\/\/(?:www\.)?youtu(?:be\.com\/watch\?v=|\.be\/)([\w\-\_]*)(&(amp;)?‌​[\w\?‌​=]*)?"
        )
        self.extract_url_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': True,
        }
        self.song_cache: SongsCache = LRUSongsCache()

    async def prepare_song(self, query: str) -> Song:
        """
        Get a song object with streaming URL from a YouTube URL or search query.

        :param query: The YouTube URL or search query.
        :return:    The song object.
        """
        if query in self.song_cache:
            return self.song_cache[query]
        url, title, thumbnail, duration = await asyncio.to_thread(self._extract_info, query)
        song = Song(title, url, duration, thumbnail)
        self.song_cache[query] = song
        return song


    def _extract_info(self, query: str) -> tuple[str, str, str, float]:
        """
        Search the url from a search query using youtube-dl

        :raise ValueError: If the search query does not return any results
        :param query: The search query
        :return:      The url
        """
        query = query if self.youtube_regex.match(query) else f"ytsearch:{query}"

        with yt_dlp.YoutubeDL(self.extract_url_opts) as ydl:
            search = ydl.extract_info(query, download=False)
            print(search)
        if not search['entries']:
            raise MusicFactory.NoResultsFound(query)

        song_info = search['entries'][0]
        url = song_info['url']
        title = song_info['title']
        thumbnail = song_info['thumbnails'][0]['url']
        duration = song_info['duration']

        return url, title, thumbnail, duration

class SongsCache(ABC):
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
        self._url_cache: LRUCache[str, Song] = LRUCache(maxsize=song_size)       # url -> song
        self._query_cache: LRUCache[str, str] = LRUCache(maxsize=query_size)     # query -> url
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
