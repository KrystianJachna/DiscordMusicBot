import asyncio
import logging
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
        self.music_manager = music_manager
        self.voice_client = voice_client
        self.singing: asyncio.Condition = asyncio.Condition()
        self.event_loop = asyncio.get_event_loop()

    async def play_loop(self):
        self._is_playing = True
        while True:
            try:
                song = await self.music_manager.next()
            except MusicManager.EndOfPlaylistException:
                break
            async with self.singing:
                self.voice_client.play(
                    song.source,
                    after=lambda _: asyncio.run_coroutine_threadsafe(
                        self._notify_singing(), self.event_loop
                    )
                )
                await self.singing.wait()
        self._is_playing = False

    async def _notify_singing(self):
        async with self.singing:
            self.singing.notify_all()

    @property
    def is_playing(self) -> bool:
        return self._is_playing


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
            try:
                song = await self.music_downloader.download(query)
            except Exception as e:
                await ctx.send(f"An error occurred while downloading the song: {query}")
                logging.error(e)
                continue
            await self.music_queue.put(song)
            await ctx.send(f"Added `{song.title}` to the queue.")
            await ctx.send(f"{song.url}")
        self.currently_downloading = False

    async def next(self) -> Song:
        if self.music_queue.empty() and not self.currently_downloading:
            raise MusicManager.EndOfPlaylistException
        return await self.music_queue.get()
