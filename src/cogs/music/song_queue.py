import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional

from traceback import format_exc

from .messages import *
from .music_downlaoder import SongDownloader, DownloaderException, PlaylistFoundException, PlaylistExtractor
from .song import SongRequest


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


class BgDownloadSongQueue(SongQueue):
    class TrackedAsyncQueue(asyncio.Queue):
        def __init__(self):
            super().__init__()
            self._elements = []

        def put_nowait(self, item):
            super().put_nowait(item)
            self._elements.append(item)

        def get_nowait(self):
            item = super().get_nowait()
            self._elements.remove(item)
            return item

        @property
        def elements(self):
            return self._elements

    def __init__(self, song_downloader: SongDownloader):
        self._music_downloader = song_downloader
        self._downloaded_songs: BgDownloadSongQueue.TrackedAsyncQueue = BgDownloadSongQueue.TrackedAsyncQueue()
        self._waiting_queries: list[SongRequest] = []
        self._now_processing: Optional[str] = None
        self._processing_task: Optional[asyncio.Task] = None

    async def next(self) -> Song:
        if self._downloaded_songs.empty() and not self._processing_task:
            raise SongQueue.EndOfPlaylistException
        return await self._downloaded_songs.get()

    async def add(self, song_request: SongRequest) -> None:
        self._waiting_queries.append(song_request)
        if not self._processing_task:
            self._processing_task = asyncio.create_task(self._process_queue())

    async def clear_queue(self) -> None:
        if self._processing_task:
            self._processing_task.cancel()
        self._waiting_queries.clear()
        self._downloaded_songs = BgDownloadSongQueue.TrackedAsyncQueue()

    async def get_queue_info(self) -> list[str]:
        downloaded_songs = self._downloaded_songs.elements
        downloaded_songs = [song.title for song in downloaded_songs]
        now_processing = [self._now_processing] if self._now_processing else []
        waiting_queries = [sr.title for sr in self._waiting_queries]
        return downloaded_songs + now_processing + waiting_queries

    async def queue_length(self) -> int:
        return len(await self.get_queue_info())

    async def _process_queue(self) -> None:
        try:
            while self._waiting_queries:
                song_request = self._waiting_queries.pop(0)
                self._now_processing = song_request.title
                try:
                    song = await self._music_downloader.prepare_song(song_request.query)
                    if not song_request.quiet:
                        await song_request.ctx.send(embed=added_to_queue(song, await self.queue_length()))
                    self._downloaded_songs.put_nowait(song)
                except PlaylistFoundException as e:
                    playlist_extractor = PlaylistExtractor(song_request.query)
                    playlist = await playlist_extractor.get_playlist_requests(song_request.ctx)
                    self._waiting_queries.extend(playlist.songs)
                    await song_request.ctx.send(embed=added_playlist_to_queue(playlist, await self.queue_length()))
                except DownloaderException as e:
                    if not song_request.quiet:
                        await song_request.ctx.send(embed=e.embed(song_request.title))
                except Exception as e:
                    if isinstance(e, asyncio.CancelledError): raise e
                    if not song_request.quiet:
                        await song_request.ctx.send(embed=download_error(song_request.title))
                    logging.error(e)
                    logging.debug(format_exc())
        except asyncio.CancelledError:
            pass
        finally:
            self._now_processing = None
            self._processing_task = None
