from abc import ABC, abstractmethod
import asyncio

from discord.ext import commands
from discord import VoiceProtocol

from cogs.music.music_downlaoder import MusicDownloader
from cogs.music.song import Song


class MusicManager(ABC):

    class EndOfPlaylist(Exception):
        ...

    @abstractmethod
    async def next(self) -> Song:
        pass


class MusicPlayer:

    def __init__(self, music_manager: MusicManager):
        self._is_playing = False
        self._loop: None | asyncio.Task = None
        self.music_manager = music_manager

    async def play_loop(self, ctx: commands.Context):
        self._is_playing = True
        while True:
            try:
                song = await self.music_manager.next()
            except MusicManager.EndOfPlaylist:
                break
            voice_cli = ctx.voice_client
            assert isinstance(voice_cli, VoiceProtocol)
            await asyncio.to_thread(voice_cli.play, song.source)
        self._is_playing = False

    def is_running(self) -> bool:
        return self._is_playing

    def start_loop(self, ctx: commands.Context):
        if self._is_playing:
            raise RuntimeError("The player is already running.")
        self._loop = asyncio.create_task(self.play_loop(ctx), name=f'{self.__class__.__name__}::f{id(self)}')

    def stop_loop(self):
        if self._loop:
            self._loop.cancel()


class MusicQueue(MusicManager):
    """
    TODO: add docstring
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.downloading_queue: list[str] = []
        self.currently_downloading = False
        self.music_queue: list[Song] = []
        self.music_downloader = MusicDownloader()
        self.playing = False

    async def add(self, query: str, ctx: commands.Context) -> None:
        self.downloading_queue.append(query)
        if not self.currently_downloading:
            await self._process_queue(ctx)

    async def next(self) -> Song:
        ...

    async def _process_queue(self, ctx: commands.Context) -> None:
        while self.downloading_queue:
            self.currently_downloading = True
            query = self.downloading_queue.pop(0)
            song = await self.music_downloader.download(query)
            self.music_queue.append(song)
            self._play_next(ctx)
        self.currently_downloading = False

    def _play(self, ctx: commands.Context) -> None:
        song = self.music_queue.pop(0)
        print(f"Playing: {song.title}")
        self.playing = True
        ctx.voice_client.play(song.source,
                              after=lambda e: self._play_next(ctx) if not e else print(f"Player error: {e}")
                              )
        print(f'end of _play')

    def _play_next(self, ctx: commands.Context) -> None:
        if not self.music_queue:
            self.playing = False
            return
        self._play(ctx)
