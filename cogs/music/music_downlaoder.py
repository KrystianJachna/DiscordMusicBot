import asyncio
import os
import re
from pathlib import Path
from typing import Optional
from uuid import uuid4

import yt_dlp
from discord import FFmpegPCMAudio

from cogs.music.song import Song


class MusicDownloader:
    """
    Class to download music from youtube, and extract url from command arguments

    :param download_folder: The folder to download the music to
    """

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

    async def download(self, arg: str) -> Song:
        """
        Download a song from a youtube url or search query

        :param url: The youtube url or search query
        :return:   The song object
        """
        url = await self._get_url(arg)
        info = await asyncio.to_thread(self._extract_info, url)
        original_file = f"{info['id']}.mp3"
        original_file_path = self.DOWNLOAD_FOLDER / original_file
        random_file = f"{uuid4()}.mp3"
        random_file_path = self.DOWNLOAD_FOLDER / random_file
        os.rename(original_file_path, random_file_path)
        return Song(title=info['title'], file=random_file_path, url=info['webpage_url'],
                    source=FFmpegPCMAudio(str(random_file_path)))

    def _extract_info(self, url: str) -> dict:
        """
        Extract information from a youtube url

        :param url: The youtube url
        :return:   The information
        """
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            return ydl.extract_info(url, download=True)

    async def _get_url(self, arg: str) -> str:
        """
        Get the url from a command argument

        :param arg: The command argument
        :return:    The url
        """
        return arg if re.match(self.youtube_regex, arg) else await asyncio.to_thread(self._extract_url, arg)

    @staticmethod
    def _extract_url(query: str) -> str:
        """
        Extract the url from a search query

        :param query: The search query
        :return:      The url
        """
        with yt_dlp.YoutubeDL() as ydl:
            search = ydl.extract_info(f"ytsearch:{query}", download=False)
            return search['entries'][0]['webpage_url']
