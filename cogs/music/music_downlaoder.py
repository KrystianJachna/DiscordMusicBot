import asyncio
import os
from pathlib import Path
from typing import Optional
from uuid import uuid4

import yt_dlp

from cogs.music.song import Song


class MusicDownloader:
    def __init__(self, download_folder: Optional[Path] = Path('downloads')) -> None:
        self.DOWNLOAD_FOLDER = download_folder
        os.makedirs(self.DOWNLOAD_FOLDER, exist_ok=True)
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

    async def download(self, url: str) -> Song:
        """
        Download a song from a youtube url, rename the file to a random name

        :param url: The youtube url
        :return:   The song object
        """
        info = await asyncio.to_thread(self._extract_info, url)
        original_file = f"{info['id']}.mp3"
        original_file_path = self.DOWNLOAD_FOLDER / original_file
        random_file = f"{uuid4()}.mp3"
        random_file_path = self.DOWNLOAD_FOLDER / random_file
        os.rename(original_file_path, random_file_path)
        return Song(title=info['title'], file=random_file_path)

    def _extract_info(self, url: str) -> dict:
        """
        Extract information from a youtube url

        :param url: The youtube url
        :return:   The information
        """
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            return ydl.extract_info(url, download=True)
