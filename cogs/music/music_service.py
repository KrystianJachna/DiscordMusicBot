import asyncio
from abc import ABC, abstractmethod

from discord import VoiceClient
from discord.ext import commands

from .music_downlaoder import MusicDownloader, Song


class MusicManager(ABC):
    class EndOfPlaylistException(Exception):
        def __init__(self):
            super().__init__("End of playlist reached.")

    @abstractmethod
    async def next(self) -> Song:
        pass


class MusicPlayer:

    def __init__(self, music_manager: MusicManager, voice_client: VoiceClient):
        self._is_playing = False
        self._loop: None | asyncio.Task = None
        self.music_manager = music_manager
        self.voice_client = voice_client

    async def play_loop(self):
        self._is_playing = True
        while True:
            try:
                song = await self.music_manager.next()
            except MusicManager.EndOfPlaylistException:
                break
            await asyncio.to_thread(self.voice_client.play, song.source)
        self._is_playing = False

    def is_running(self) -> bool:
        return self._is_playing

    def start_loop(self, ctx: commands.Context):
        if self._is_playing:
            raise RuntimeError("The player is already running.")
        self._loop = asyncio.create_task(self.play_loop(), name=f'{self.__class__.__name__}::f{id(self)}')

    def stop_loop(self):
        if self._loop:
            self._loop.cancel()


class MusicQueue(MusicManager):
    def __init__(self) -> None:
        self.downloading_queue: list[str] = []
        self.currently_downloading = False
        self.music_queue: asyncio.Queue[Song] = asyncio.Queue()
        self.music_downloader = MusicDownloader()

    async def add(self, query: str, ctx: commands.Context) -> None:
        self.downloading_queue.append(query)
        if not self.currently_downloading:
            await self._process_queue(ctx)

    async def _process_queue(self, ctx: commands.Context) -> None:
        while self.downloading_queue:
            self.currently_downloading = True
            query = self.downloading_queue.pop(0)
            song = await self.music_downloader.download(query)
            await self.music_queue.put(song)
        self.currently_downloading = False

    async def next(self) -> Song:
        if self.music_queue.empty() and not self.currently_downloading:
            raise MusicManager.EndOfPlaylistException
        return await self.music_queue.get()
