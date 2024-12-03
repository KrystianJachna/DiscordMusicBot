import os
from pathlib import Path
from typing import Optional
from cogs.music.song import Song
from uuid import uuid4
import asyncio

import yt_dlp


class MusicDownloader:
    def __init__(self, download_folder: Optional[Path] = Path('downloads')) -> None:
        self.DOWNLOAD_FOLDER = download_folder
        os.makedirs(self.DOWNLOAD_FOLDER, exist_ok=True)
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{self.DOWNLOAD_FOLDER}/{uuid4()}.%(ext)s',
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
        Download a song from a youtube url

        :param url: The youtube url
        :return:   The song object
        """
        info = await asyncio.to_thread(self._extract_info, url)
        return Song(title=info['title'], file=Path(self.DOWNLOAD_FOLDER) / f"{info['id']}.mp3")

    def _extract_info(self, url: str) -> dict:
        """
        Extract information from a youtube url

        :param url: The youtube url
        :return:   The information
        """
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
