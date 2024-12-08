import asyncio
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from uuid import uuid4
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
    _file_path: Path = field(repr=False)

    @property
    def source(self) -> FFmpegPCMAudio:
        """
        Creates and returns a new FFmpegPCMAudio object from the file_path.

        :return: FFmpegPCMAudio object.
        """
        return FFmpegPCMAudio(str(self._file_path))


class MusicDownloader:
    """
    Class to download music from youtube, and extract url from command arguments

    :param download_folder: The folder to download the music to
    """

    class NoResultsFound(Exception):
        def __init__(self, query: str) -> None:
            super().__init__(f"No results found for: {query}\nPlease try a different search query")

    def __init__(self, download_folder: Optional[Path] = Path('downloads')) -> None:
        self.DOWNLOAD_FOLDER = download_folder
        os.makedirs(self.DOWNLOAD_FOLDER, exist_ok=True)
        self.youtube_regex = re.compile(
            r"http(?:s?):\/\/(?:www\.)?youtu(?:be\.com\/watch\?v=|\.be\/)([\w\-\_]*)(&(amp;)?‌​[\w\?‌​=]*)?"
        )
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{self.DOWNLOAD_FOLDER}/%(id)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'no_playlist': True,
            'match_filter': yt_dlp.utils.match_filter_func("!is_live"),
        }
        self._downloaded_songs: dict[str, Song] = {}

    async def download(self, arg: str) -> Song:
        """
        Download a song from a youtube url or search query

        :param url: The youtube url or search query
        :return:   The song object
        """
        url = await asyncio.to_thread(self._get_url, arg)
        if url in self._downloaded_songs:
            logging.info(f"Song already downloaded: {url}")
            return self._downloaded_songs[url]
        info = await asyncio.to_thread(self._extract_info, url)
        original_file = f"{info['id']}.mp3"
        original_file_path = self.DOWNLOAD_FOLDER / original_file
        random_file = f"{uuid4()}.mp3"
        random_file_path = self.DOWNLOAD_FOLDER / random_file
        os.rename(original_file_path, random_file_path)
        song = Song(info['title'], info['webpage_url'], info['duration'], random_file_path)
        self._downloaded_songs[url] = song
        return song

    def _extract_info(self, url: str) -> dict:
        """
        Extract information from a youtube url

        :param url: The youtube url
        :return:   The information
        """
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            return ydl.extract_info(url, download=True)

    def _get_url(self, arg: str) -> str:
        """
        Get the url from a command argument

        :param arg: The command argument
        :return:    The url
        """
        return arg if self.youtube_regex.match(arg) else self._extract_url(arg)

    @staticmethod
    def _extract_url(query: str) -> str:
        """
        Extract the url from a search query

        :raise ValueError: If the search query does not return any results
        :param query: The search query
        :return:      The url
        """
        with yt_dlp.YoutubeDL() as ydl:
            search = ydl.extract_info(f"ytsearch:{query}", download=False)
        if not search['entries']:
            raise MusicDownloader.NoResultsFound(query)
        return search['entries'][0]['webpage_url']
