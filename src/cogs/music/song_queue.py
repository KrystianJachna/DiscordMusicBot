import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional

from traceback import format_exc

from .music_downlaoder import SongDownloader
from discord.ext.commands import Context
from .messages import *
from .song_cache import SongsCache


class SongQueue(ABC):
    class EndOfPlaylistException(Exception):
        def __init__(self):
            super().__init__("End of playlist reached.")

    @abstractmethod
    async def next(self) -> Song:
        pass

    @abstractmethod
    async def add(self, query: str, ctx: Context) -> None:
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

    def __init__(self, song_cache: SongsCache):
        self._music_downloader = SongDownloader(song_cache)
        self._downloaded_songs: BgDownloadSongQueue.TrackedAsyncQueue = BgDownloadSongQueue.TrackedAsyncQueue()
        self._waiting_queries: list[tuple[str, Context]] = []
        self._now_processing: Optional[str] = None
        self._processing_task: Optional[asyncio.Task] = None

    async def next(self) -> Song:
        if self._downloaded_songs.empty() and not self._processing_task:
            raise SongQueue.EndOfPlaylistException
        return await self._downloaded_songs.get()

    async def add(self, query: str, ctx: Context) -> None:
        self._waiting_queries.append((query, ctx))
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
        waiting_queries = [query for query, _ in self._waiting_queries]
        return downloaded_songs + now_processing + waiting_queries

    async def queue_length(self) -> int:
        return len(await self.get_queue_info())

    async def _process_queue(self) -> None:
        try:
            while self._waiting_queries:
                query, ctx = self._waiting_queries.pop(0)
                self._now_processing = query
                try:
                    song = await self._music_downloader.prepare_song(query)
                    await ctx.send(embed=added_to_queue(song, await self.queue_length()))
                    self._downloaded_songs.put_nowait(song)
                except SongDownloader.AgeRestrictedException:
                    await ctx.send(embed=age_restricted(query))
                except SongDownloader.NoResultsFoundException:
                    await ctx.send(embed=no_results(query))
                except SongDownloader.LiveFoundException:
                    await ctx.send(embed=live_stream(query))
                except Exception as e:
                    if isinstance(e, asyncio.CancelledError): raise e
                    await ctx.send(embed=download_error(query))
                    logging.error(e)
                    logging.debug(format_exc())
        except asyncio.CancelledError:
            pass
        finally:
            self._now_processing = None
            self._processing_task = None
