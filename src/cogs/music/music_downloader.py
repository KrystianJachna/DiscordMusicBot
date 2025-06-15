import asyncio
import re
import logging
from typing import Optional

from youtube_search import YoutubeSearch

import yt_dlp
from .song_cache import SongsCache
from .song import Song, SongRequest, PlaylistRequest
from abc import ABC, abstractmethod
from discord import Embed
from config import *
from uuid import uuid4
import os
import requests
from dataclasses import dataclass


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


@dataclass
class NewSongQuery:
    title: str
    original_url: str | None
    unique_id: str
    duration: int
    music_file: Path
    thumbnail_file: Optional[Path] = None


class MusicDownloader:
    _ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': str(DOWNLOAD_FOLDER / '%(id)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'no_playlist': True,
        'quiet': True,
        'match_filter': yt_dlp.utils.match_filter_func("!is_live"),
    }

    def _extract_info(self, url: str) -> dict:
        with yt_dlp.YoutubeDL(self._ydl_opts) as ydl:
            try:
                return ydl.extract_info(url, download=True)
            except yt_dlp.utils.DownloadError as e:
                if "Sign in to confirm your age" in str(e):
                    raise AgeRestrictedException(url)
                raise NoResultsFoundException(url)

    @staticmethod
    def _rename_file(original_file_path: str) -> Path:
        random_file = f"{uuid4()}.mp3"
        random_file_path = DOWNLOAD_FOLDER / random_file
        os.rename(original_file_path, random_file_path)
        return random_file_path

    @staticmethod
    def _save_thumbnail(thumbnail_url: str) -> Path | None:
        response = requests.get(thumbnail_url)
        if response.status_code == 200:
            thumbnail_file = DOWNLOAD_FOLDER / f"{uuid4()}.jpg"
            with open(thumbnail_file, 'wb') as file:
                file.write(response.content)
            return thumbnail_file
        return None

    def download(self, url: str) -> NewSongQuery:
        info = self._extract_info(url)
        song_file_path = self._rename_file(DOWNLOAD_FOLDER / f"{info['id']}.mp3")
        yt_thumbnail_link = info.get('thumbnail', None)
        yt_thumbnail_path = self._save_thumbnail(yt_thumbnail_link) if yt_thumbnail_link else None

        song_query = NewSongQuery(
            title=info['title'],
            original_url=url,
            unique_id=info['id'],
            duration=info['duration'],
            music_file=song_file_path,
            thumbnail_file=yt_thumbnail_path if yt_thumbnail_path else Path(""),
        )
        logging.info(f"Song query created:\n", song_query)
        return song_query


class SongInfoProvider:
    _youtube_regex = re.compile(
        r"https?://(?:www\.)?youtu(?:be\.com/watch\?v=|\.be/)([\w\-_]*)(&(amp;)?‌​[\w?‌​=]*)?"
    )
    _youtube_playlist_regex = re.compile(
        r"(?:https?://)?(?:www\.)?youtube\.com/(?:playlist\?list=|watch\?.*?list=)(.*?)(?:&|$)"
    )
    _yt_dlp_opts = {
        'format': 'bestaudio/best',
        'quiet': False,
        'match_filter': '!is_live',
        'logger': YtDlpLogger(),
    }

    def __init__(self, song_cache: SongsCache):
        self._load_cookies(COOKIES_PATH)  # cookies are required to be able to download age-restricted songs
        self._song_cache: SongsCache = song_cache

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
            return self._song_cache[query]
        song = await asyncio.to_thread(self._construct_song, query)
        self._song_cache[query] = song
        return song

    def _construct_song(self, query: str) -> Song:
        url = self._get_url(query)
        if url in self._song_cache:
            return self._song_cache[url]
        with yt_dlp.YoutubeDL(self._yt_dlp_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except yt_dlp.utils.DownloadError as e:
                if "Sign in to confirm your age" in str(e):
                    raise AgeRestrictedException(query)
                raise NoResultsFoundException(query)

        if info.get('is_live', False):
            raise LiveFoundException(query)

        return Song(title=info['title'],
                    url=url,
                    duration=info['duration'],
                    thumbnail=info['thumbnails'][0]['url'],
                    expires_at=(
                        int(info['url'].split("expire=")[1].split("&")[0])
                        if "expire=" in info['url'] else None
                    ),
                    _stream_url=info['url'])

    def _get_url(self, query: str) -> str:
        if self._youtube_playlist_regex.match(query):
            raise PlaylistFoundException(query)
        if self._youtube_regex.match(query):
            return query
        search = YoutubeSearch(query, max_results=1).to_dict()
        if not search: raise NoResultsFoundException(query)
        return f"https://www.youtube.com/watch?v={search[0]['id']}"


class PlaylistExtractor:
    _playlist_id_regex = re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/.*?list=([a-zA-Z0-9_-]+)")
    _index_regex = re.compile(r"index=(\d+)")
    _ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'logger': YtDlpLogger(),
    }

    def __init__(self, url):
        self._index = self._extract_index(url)
        self._playlist_url = self._get_playlist_url(url)

    async def get_playlist_requests(self, song_request: SongRequest) -> PlaylistRequest:
        with yt_dlp.YoutubeDL(self._ydl_opts) as ydl:
            try:
                playlist_info = ydl.extract_info(self._playlist_url, download=False)
            except yt_dlp.utils.DownloadError as e:
                if "This playlist type is unviewable." in str(e):
                    raise YoutubeMixFoundException(self._playlist_url)
                raise PlaylistNotFoundError(self._playlist_url)

        return PlaylistRequest(title=playlist_info['title'],
                               thumbnail=playlist_info['thumbnails'][0]['url'],
                               total_duration=self._calculate_duration(playlist_info['entries']),
                               length=len(playlist_info['entries']),
                               songs=self._get_song_requests(playlist_info['entries'], song_request),
                               playlist_url=self._playlist_url)

    @staticmethod
    def _calculate_duration(entries: list[dict]) -> int:
        return sum(video['duration'] for video in entries if video["duration"])

    def _get_song_requests(self, entries: list[dict], song_request: SongRequest) -> list[SongRequest]:
        requests = [SongRequest(video['url'], song_request.ctx, quiet=True, _title=video['title']) for video in entries]
        if self._index is not None:
            requests = requests[self._index:] + requests[:self._index]
        return requests

    def _get_playlist_url(self, url: str) -> str:
        match = self._playlist_id_regex.search(url)
        if not match:
            raise PlaylistNotFoundError(url)
        return f"https://www.youtube.com/playlist?list={match.group(1)}"

    def _extract_index(self, url: str) -> Optional[int]:
        match = self._index_regex.search(url)
        return int(match.group(1)) + 1 if match else None


class DownloaderException(Exception, ABC):

    def __init__(self, message: str) -> None:
        super().__init__(message)

    @staticmethod
    @abstractmethod
    def embed(query: str) -> Embed:
        pass

class NoResultsFoundException(DownloaderException):
    @staticmethod
    def embed(query: str) -> Embed:
        message = Embed(title="🔍 No Results Found",
                        description=f"We couldn't find any results for: *\"{query}\"*\n\n",
                        color=ERROR_COLOR)
        message.set_footer(text="💡Tip: Try using different keywords or check your spelling")
        return message


class LiveFoundException(DownloaderException):
    @staticmethod
    def embed(query: str) -> Embed:
        message = Embed(title="🎥 Live Stream",
                        description=f"Found a live stream for: *\"{query}\"*\n"
                                    f"We currently do not support live streams",
                        color=ERROR_COLOR)
        message.set_footer(text="💡Tip: Try using different keywords or search for a different song")
        return message


class AgeRestrictedException(DownloaderException):
    @staticmethod
    def embed(query: str) -> Embed:
        message = Embed(title=" 🔞 Age Restricted Content",
                        description=f"The song: *\"{query}\"* is age restricted. "
                                    "Please provide a `cookies.txt` file in the root directory to play the song\n\n"
                                    "See `README.md` for details",
                        color=ERROR_COLOR)
        message.set_footer(text="💡Tip: Search for a different song")
        return message


class PlaylistFoundException(DownloaderException):
    @staticmethod
    def embed(query: str) -> Embed:
        message = Embed(title="📋 Playlist Found",
                        description=f"Found a playlist for: *\"{query}\"*\n",
                        color=ERROR_COLOR)
        message.set_footer(text="💡Tip: Provide a direct link to a song or search for a different song")
        return message


class YoutubeMixFoundException(DownloaderException):
    @staticmethod
    def embed(query: str) -> Embed:
        message = Embed(title="🎧 Youtube Mix Found",
                        description=f"Found a Youtube Mix for: *\"{query}\"*\n"
                                    "Youtube Mixes are prepared by Youtube for a specific user"
                                    " and we currently do not support them",
                        color=ERROR_COLOR)
        message.set_footer(text="💡Tip: Search for a different playlist")
        return message


class PlaylistNotFoundError(DownloaderException):
    @staticmethod
    def embed(query: str) -> Embed:
        message = Embed(title="📋 Playlist Not Found",
                        description=f"We couldn't find any playlist for: *\"{query}\"*\n\n",
                        color=ERROR_COLOR)
        message.set_footer(text="💡Tip: Check the playlist link and try again")
        return message


class PlaylistInfoExtractorError(DownloaderException):
    @staticmethod
    def embed(query: str) -> Embed:
        message = Embed(title="⛔ Playlist Info Error",
                        description=f"An error occurred while extracting playlist info for: *\"{query}\"*\n\n",
                        color=ERROR_COLOR)
        message.set_footer(text="💡Tip: Search for a different playlist")
        return message
