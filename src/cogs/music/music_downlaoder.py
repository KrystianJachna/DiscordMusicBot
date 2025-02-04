import asyncio
import re
import logging
from traceback import format_exc
from typing import Optional

from youtube_search import YoutubeSearch

import yt_dlp
from .song_cache import SongsCache
from .song import Song
from abc import ABC, abstractmethod
from discord import Embed
from config import *


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


class DownloaderException(Exception, ABC):

    def __init__(self, message: str) -> None:
        super().__init__(message)

    @abstractmethod
    def embed(self, query: str) -> Embed:
        pass


class NoResultsFoundException(DownloaderException):

    def __init__(self, query: str) -> None:
        super().__init__(f"No results found for: {query}\nPlease try a different search query")

    def embed(self, query: str) -> Embed:
        message = Embed(title="🔍 No Results Found",
                        description=f"We couldn't find any results for: *\"{query}\"*\n\n",
                        color=ERROR_COLOR)
        message.set_footer(text="💡Tip: Try using different keywords or check your spelling")
        return message


class LiveFoundException(DownloaderException):

    def __init__(self, query: str) -> None:
        super().__init__(f"Live stream found for: {query}\nPlease try a different search query")

    def embed(self, query: str) -> Embed:
        message = Embed(title="🎥 Live Stream",
                        description=f"Found a live stream for: *\"{query}\"*\n"
                                    f"We currently do not support live streams",
                        color=ERROR_COLOR)
        message.set_footer(text="💡Tip: Try using different keywords or search for a different song")
        return message


class AgeRestrictedException(DownloaderException):

    def __init__(self, query: str) -> None:
        super().__init__(f"Age restricted song found for: {query}\nPlease try a different search query")

    def embed(self, query: str) -> Embed:
        message = Embed(title=" 🔞 Age Restricted Content",
                        description=f"The song: *\"{query}\"* is age restricted. "
                                    "Please provide a `cookies.txt` file in the root directory to play the song\n\n"
                                    "See `README.md` for details",
                        color=ERROR_COLOR)
        message.set_footer(text="💡Tip: Search for a different song")
        return message


class PlaylistFoundException(DownloaderException):

    def __init__(self, query: str) -> None:
        super().__init__(f"Playlist found for: {query}\nPlease try a different search query")

    def embed(self, query: str) -> Embed:
        message = Embed(title="📋 Playlist Found",
                        description=f"Found a playlist for: *\"{query}\"*\n"
                                    f"We currently do not support playlists",
                        color=ERROR_COLOR)
        message.set_footer(text="💡Tip: Provide a direct link to a song or search for a different song")
        return message


class SongDownloader:

    def __init__(self, song_cache: SongsCache, cookies_path: Optional[Path]):
        self._youtube_regex = re.compile(
            r"https?://(?:www\.)?youtu(?:be\.com/watch\?v=|\.be/)([\w\-_]*)(&(amp;)?‌​[\w?‌​=]*)?"
        )
        self._youtube_playlist_regex = re.compile(
            r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:playlist\?list=|watch\?.*?list=))(.*?)(?:&|$)"
        )
        self._yt_dlp_opts = {
            'format': 'bestaudio/best',
            'quiet': False,
            'match_filter': '!is_live',
            'logger': YtDlpLogger(),
        }
        self._load_cookies(cookies_path)  # cookies are required to be able to download age-restricted songs
        self._song_cache: SongsCache = song_cache

    async def prepare_song(self, query: str) -> Song:
        if query in self._song_cache:
            logging.debug(f"prepare_song: song found in cache for: {query}")
            return self._song_cache[query]
        song = await asyncio.to_thread(self._construct_song, query)
        self._song_cache[query] = song
        return song

    def _load_cookies(self, cookies_path: Path) -> None:
        if not cookies_path:
            return
        if cookies_path.exists():
            logging.info(f"Cookies file loaded from {str(cookies_path)}")
            self._yt_dlp_opts['cookiefile'] = str(cookies_path)
        else:
            logging.info("Cookies file not found. "
                         "Create a cookies.txt file in the root directory for age-restricted songs. "
                         "See README.md for details.")

    def _construct_song(self, query: str) -> Song:
        url = self._get_url(query)
        if url in self._song_cache:
            logging.debug(f"_construct_song: song found in cache for: {query}")
            return self._song_cache[url]
        with yt_dlp.YoutubeDL(self._yt_dlp_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except yt_dlp.utils.DownloadError as e:
                error_msg = str(e)
                if "Sign in to confirm your age" in error_msg:
                    raise AgeRestrictedException(query)
                logging.debug(format_exc())
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
        if self._youtube_regex.match(query):
            if "list=" in query:
                raise PlaylistFoundException(query)
            return query
        elif self._youtube_playlist_regex.match(query):
            raise PlaylistFoundException(query)
        search = YoutubeSearch(query, max_results=1).to_dict()
        if not search: raise NoResultsFoundException(query)
        return f"https://www.youtube.com/watch?v={search[0]['id']}"


class PlaylistExtractor:
    pass
