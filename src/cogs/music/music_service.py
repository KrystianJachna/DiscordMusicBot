import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional

from discord import VoiceClient
from traceback import format_exc

from .music_downlaoder import SongDownloader
from .song_cache import LRUSongsCache
from discord.ext.commands import Context
from .utils import *
from .song_cache import LRUSongsCache


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

class MusicPlayer:
    class NotPlayingException(Exception):
        def __init__(self):
            super().__init__("Player is not playing")

    def __init__(self, voice_client: VoiceClient, song_queue: SongQueue):
        self._now_playing: Optional[Song] = None
        self._voice_client = voice_client
        self._song_queue = song_queue
        self._loop = False
        self._processing_queue = False
        self._looped_songs: list[Song] = []
        self._clearing_queue = False
        self._processing_task: Optional[asyncio.Task] = None

    async def pause(self) -> None:
        if not self._now_playing:
            raise MusicPlayer.NotPlayingException
        self._voice_client.pause()

    async def resume(self):
        if not self._now_playing:
            raise MusicPlayer.NotPlayingException
        self._voice_client.resume()

    async def skip(self) -> None:
        if not self._now_playing:
            raise MusicPlayer.NotPlayingException
        self._voice_client.stop()

    @property
    def loop(self) -> bool:
        return self._loop

    @loop.setter
    def loop(self, value: bool) -> None:
        self._loop = value

    @property
    def now_playing(self) -> Optional[Song]:
        return self._now_playing

    @property
    def voice_client(self) -> VoiceClient:
        return self._voice_client

    async def stop(self) -> None:
        await self._song_queue.clear_queue()
        if self._processing_task:
            self._processing_task.cancel()
        self._voice_client.stop()
        await self._voice_client.disconnect()

    async def clear_queue(self) -> None:
        await self._song_queue.clear_queue()
        self._looped_songs.clear()
        self._clearing_queue = True

    async def get_queue_info(self) -> list[str]:
        waiting_in_queue = await self._song_queue.get_queue_info()
        now_playing = [self._now_playing.title] if self._now_playing else []
        looped_songs = [song.title for song in self._looped_songs] if self._loop else []
        return now_playing + waiting_in_queue + looped_songs

    async def queue_length(self) -> int:
        return len(await self.get_queue_info())

    async def play(self, query: str, ctx: Context) -> None:
        await self._song_queue.add(query, ctx)
        if not self._processing_queue:
            self._processing_task = asyncio.create_task(self._process_song_queue())

    async def _process_song_queue(self) -> None:
        self._processing_queue = True
        try:
            while True:
                try:
                    self._now_playing = await self._song_queue.next()
                except SongQueue.EndOfPlaylistException:
                    if self.loop and self._looped_songs:
                        self._now_playing = self._looped_songs.pop(0)
                    else:  # TODO: disconnect after timeout
                        break
                source = await self._now_playing.get_source()
                finished = asyncio.Event()
                self._voice_client.play(source, after=lambda e: self._after_playing(e, finished))
                await finished.wait()
                self._now_playing = None
        except asyncio.CancelledError:
            logging.debug("Processing queue cancelled")
        finally:
            self._processing_queue = False

    def _after_playing(self, error: Optional[Exception], finished: asyncio.Event) -> None:
        if self.loop:
            if self._clearing_queue:
                self._clearing_queue = False
            else:
                self._looped_songs.append(self._now_playing)
        self._now_playing = None
        if error:
            logging.error(f"Error playing song: {error}")
            logging.debug(format_exc())
        finished.set()


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

    def __init__(self):
        self._music_downloader = SongDownloader(LRUSongsCache())
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
                    logging.error(e)
                    logging.debug(format_exc())
        except asyncio.CancelledError:
            pass
        finally:
            self._now_processing = None
            self._processing_task = None
