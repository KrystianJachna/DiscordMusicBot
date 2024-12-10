import asyncio
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import logging

import yt_dlp
from discord import FFmpegPCMAudio


@dataclass
class Song:
    """
    Dataclass to store song information.

    :param title:    The title of the song.
    :param url:      The URL of the song.
    :param duration: The duration of the song in seconds.
    :param file_path: The path to the downloaded audio file (private).
    """
    title: str
    url: str
    duration: int
    thumbnail: str | None

    @property
    def source(self) -> FFmpegPCMAudio:
        """
        Creates and returns a new FFmpegPCMAudio object for streaming.

        :return: FFmpegPCMAudio object.
        """
        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }
        return FFmpegPCMAudio(self.url, **ffmpeg_options)


class MusicDownloader:
    """
    Class to prepare music from YouTube. Uses youtube-dl to extract information from a YouTube URL.

    :param download_folder: The folder to download the music to
    """

    class NoResultsFound(Exception):
        def __init__(self, query: str) -> None:
            super().__init__(f"No results found for: {query}\nPlease try a different search query")

    def __init__(self, download_folder: Optional[Path] = Path('downloads'), *, quiet: bool = False) -> None:
        self.DOWNLOAD_FOLDER = download_folder
        os.makedirs(self.DOWNLOAD_FOLDER, exist_ok=True)
        self.youtube_regex = re.compile(
            r"http(?:s?):\/\/(?:www\.)?youtu(?:be\.com\/watch\?v=|\.be\/)([\w\-\_]*)(&(amp;)?‌​[\w\?‌​=]*)?"
        )
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': quiet,
            'no_playlist': True,
            'match_filter': yt_dlp.utils.match_filter_func("!is_live"),
            'noplaylist': True
        }
        self.extract_url_opts = {
            'quiet': quiet,
            'extract_flat': True,
            'force_generic_extractor': True,
        }
        self._songs: dict[str, Song] = {}  # dict(url: Song)

    async def prepare_song(self, arg: str) -> Song:
        """
        Get a song object with streaming URL from a YouTube URL or search query.

        :param arg: The YouTube URL or search query.
        :return:    The song object.
        """
        url = await asyncio.to_thread(self._get_url, arg)
        if url in self._songs:
            logging.info(f"Song already fetched: {url}")
            return self._songs[url]
        info = await asyncio.to_thread(self._extract_info, url)
        song = Song(
            title=info['title'],
            url=info['url'],
            duration=info['duration'],
            thumbnail=info.get('thumbnail', None)
        )
        self._songs[url] = song
        return song

    def _extract_info(self, url: str) -> dict:
        """
        Extract information from a YouTube URL without downloading the file.

        :param url: The YouTube URL.
        :return:    The information about the video.
        """
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)  # Set download=False

    def _get_url(self, arg: str) -> str:
        """
        Get the url from a command argument

        :param arg: The command argument
        :return:    The url
        """
        return arg if self.youtube_regex.match(arg) else self._search_url(arg)

    def _search_url(self, query: str) -> str:
        """
        Search the url from a search query using youtube-dl

        :raise ValueError: If the search query does not return any results
        :param query: The search query
        :return:      The url
        """
        with yt_dlp.YoutubeDL(self.extract_url_opts) as ydl:
            search = ydl.extract_info(f"ytsearch:{query}", download=False)
        if not search['entries']:
            raise MusicDownloader.NoResultsFound(query)
        return search['entries'][0]['url']

    # currently using prepare_song to stream the song instead of downloading it
    # async def download(self, arg: str) -> Song:
    #     """
    #     Download a song from a youtube url or search query
    #
    #     :param url: The youtube url or search query
    #     :return:   The song object
    #     """
    #     url = await asyncio.to_thread(self._get_url, arg)
    #     if url in self._downloaded_songs:
    #         logging.info(f"Song already downloaded: {url}")
    #         return self._downloaded_songs[url]
    #     info = await asyncio.to_thread(self._extract_info, url)
    #     yt_thumbnail = info.get('thumbnail', None)
    #     original_file = f"{info['id']}.mp3"
    #     original_file_path = self.DOWNLOAD_FOLDER / original_file
    #     random_file = f"{uuid4()}.mp3"
    #     random_file_path = self.DOWNLOAD_FOLDER / random_file
    #     os.rename(original_file_path, random_file_path)
    #     song = Song(info['title'], info['webpage_url'], info['duration'], yt_thumbnail, random_file_path)
    #     self._downloaded_songs[url] = song
    #     return song
