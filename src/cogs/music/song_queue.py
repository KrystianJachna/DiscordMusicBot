import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional

from .messages import *
from .music_downloader import SongDownloader, DownloaderException, PlaylistFoundException, PlaylistExtractor, \
    PlaylistNotFoundError
from .song import SongRequest
from random import shuffle


class SongQueue(ABC):
    class EndOfPlaylistException(Exception):
        def __init__(self):
            super().__init__("End of playlist reached.")

    @abstractmethod
    async def next(self) -> Song:
        pass

    @abstractmethod
    async def add(self, song_request: SongRequest) -> None:
        pass

    @abstractmethod
    async def clear_queue(self) -> None:
        pass

    @abstractmethod
    async def get_queue_info(self) -> list[str]:
        pass

    @abstractmethod
    async def queue_length(self) -> int:
        pass

    @abstractmethod
    async def shuffle(self) -> None:
        pass


class BgDownloadSongQueue(SongQueue):

    def __init__(self, song_downloader: SongDownloader):
        self._music_downloader = song_downloader
        self._downloaded_songs: list[Song] = []
        self._waiting_queries: list[SongRequest] = []
        self._processing_task: Optional[asyncio.Task] = None
        self._song_available = asyncio.Event()

    async def next(self) -> Song:
        if not self._downloaded_songs and not self._processing_task:
            raise SongQueue.EndOfPlaylistException
        await self._song_available.wait()
        if not self._downloaded_songs:  # edge case when the queue is cleared
            raise SongQueue.EndOfPlaylistException
        song = self._downloaded_songs.pop(0)
        if not self._downloaded_songs:
            self._song_available.clear()
        return song

    async def add(self, song_request: SongRequest) -> None:
        self._waiting_queries.append(song_request)
        if not self._processing_task:
            self._processing_task = asyncio.create_task(self._process_queue())

    async def clear_queue(self) -> None:
        if self._processing_task:
            self._processing_task.cancel()
        self._waiting_queries.clear()
        self._downloaded_songs.clear()
        self._song_available.clear()

    async def get_queue_info(self) -> list[str]:
        return [song.title for song in self._downloaded_songs] + [sr.title for sr in self._waiting_queries]

    async def queue_length(self) -> int:
        return len(await self.get_queue_info())

    async def shuffle(self) -> None:
        shuffle(self._downloaded_songs)
        shuffle(self._waiting_queries)

    async def _process_queue(self) -> None:
        try:
            while self._waiting_queries:
                song_request = self._waiting_queries[0]
                embed_message = None
                try:
                    song = await self._music_downloader.prepare_song(song_request.title)
                    embed_message = added_to_queue(song, await self.queue_length())
                    self._downloaded_songs.append(song)
                    self._song_available.set()
                except PlaylistFoundException:
                    try:
                        playlist_extractor = PlaylistExtractor(song_request.title)
                        playlist = await playlist_extractor.get_playlist_requests(song_request)
                        self._waiting_queries.extend(playlist.songs)
                        embed_message = added_playlist_to_queue(playlist)
                    except DownloaderException as e:
                        embed_message = e.embed(song_request.title)
                except DownloaderException as e:
                    embed_message = e.embed(song_request.title)
                except Exception as e:
                    if isinstance(e, asyncio.CancelledError):
                        raise e
                    embed_message = download_error(song_request.title)
                    logging.error(e, exc_info=True)
                finally:
                    if not song_request.quiet:
                        await song_request.ctx.send(embed=embed_message)
                    self._waiting_queries.remove(song_request)
        except asyncio.CancelledError:
            pass
        finally:
            self._processing_task = None
