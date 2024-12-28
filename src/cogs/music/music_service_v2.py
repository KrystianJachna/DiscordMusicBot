import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional

from discord import VoiceClient
from traceback import format_exc

from .messages import *
from .music_downlaoder import SongFactory
from .music_service import MusicQueue
from .song_cache import LRUSongsCache


class SongQueue(ABC):
    class EndOfPlaylistException(Exception):
        def __init__(self):
            super().__init__("End of playlist reached.")

    @abstractmethod
    async def next(self) -> Song:
        pass

    @abstractmethod
    async def add(self, query: str) -> None:
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

    def __init__(self, song_queue: SongQueue, voice_client: VoiceClient):
        self._now_playing: Optional[Song] = None
        self._voice_client = voice_client
        self._song_queue = song_queue
        self._loop = False
        self._processing_queue = False
        self._looped_songs: list[Song] = []
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

    async def stop(self) -> None:
        await self._song_queue.clear_queue()
        if self._processing_task:
            self._processing_task.cancel()
        self._voice_client.stop()
        await self._voice_client.disconnect()

    async def play(self, query: str) -> None:
        await self._song_queue.add(query)
        if not self._processing_queue:
            self._processing_task = asyncio.create_task(self._process_song_queue())

    async def _process_song_queue(self) -> None:
        self._processing_queue = True
        try:
            while True:
                try:
                    self._now_playing = await self._song_queue.next()
                except MusicQueue.EndOfPlaylistException:
                    if self._loop and self._looped_songs:
                        self._now_playing = self._looped_songs.pop(0)
                    else:
                        break
                source = await self._now_playing.get_source()
                finished = asyncio.Event()
                self._voice_client.play(source, after=lambda e: self._after_playing(e, finished))
                await finished.wait()
                if self._loop:
                    self._looped_songs.append(self._now_playing)
        except asyncio.CancelledError:
            logging.debug("Processing queue cancelled")
        finally:
            self._processing_queue = False

    def _after_playing(self, error: Optional[Exception], finished: asyncio.Event) -> None:
        self._now_playing = None
        if error:
            logging.error(f"Error playing song: {error}")
            logging.debug(format_exc())
        finished.set()


class BgDownloadSongQueue(SongQueue):

    def __init__(self, song_cache: LRUSongsCache):
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._song_cache = song_cache

    async def next(self) -> Song:
        query = await self._queue.get()
        song = self._song_cache.get(query)
        if not song:
            song = await SongFactory.from_query(query)
            self._song_cache.add(song)
        return song

    async def add(self, query: str) -> None:
        await self._queue.put(query)

    async def clear_queue(self) -> None:
        self._queue = asyncio.Queue()

    async def get_queue_info(self) -> list[str]:
        return list(self._queue)
