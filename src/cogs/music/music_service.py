import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, Tuple

from discord import VoiceClient
from discord.ext import commands

from .messages import *
from .music_downlaoder import SongFactory
from .song_cache import LRUSongsCache


class MusicManager(ABC):

    class EndOfPlaylistException(Exception):
        def __init__(self):
            super().__init__("End of playlist reached.")

    @abstractmethod
    async def next(self) -> Song:
        pass

    @abstractmethod
    async def clear_queue(self) -> None:
        pass


class MusicPlayer:

    class NotPlayingException(Exception):
        def __init__(self):
            super().__init__("Player is not playing")

    def __init__(self, music_manager: MusicManager, voice_client: VoiceClient):
        self._is_playing = False
        self.music_manager = music_manager
        self._voice_client = voice_client
        self._singing: asyncio.Condition = asyncio.Condition()
        self.event_loop = asyncio.get_event_loop()
        self.keep_playing = True
        self._now_playing: Optional[Song] = None

    @property
    def now_playing(self) -> Optional[Song]:
        return self._now_playing

    async def pause(self) -> None:
        if not self._is_playing:
            raise MusicPlayer.NotPlayingException
        self.voice_client.pause()

    async def resume(self):
        if not self._is_playing:
            raise MusicPlayer.NotPlayingException
        self.voice_client.resume()

    async def skip(self) -> None:
        self.voice_client.stop()

    async def play_loop(self) -> None:
        self._is_playing = True
        while self.keep_playing:
            try:
                self._now_playing = await self.music_manager.next()
                # TODO: add timeout to the play method
            except MusicManager.EndOfPlaylistException:
                break
            async with self._singing:
                source = await self._now_playing.get_source()
                self.voice_client.play(
                    source,
                    after=lambda _: asyncio.run_coroutine_threadsafe(
                        self._notify_singing(), self.event_loop
                    )
                )
                await self._singing.wait()
        self._is_playing = False

    def get_now_playing(self) -> Optional[str]:
        return f"[{self._now_playing.title}]({self._now_playing.url})" if self._now_playing else ""

    async def _notify_singing(self) -> None:
        self._now_playing = None
        async with self._singing:
            self._singing.notify_all()

    async def stop(self) -> None:
        self.keep_playing = False
        self.voice_client.stop()
        await self.music_manager.clear_queue()
        await self.voice_client.disconnect()

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def voice_client(self) -> VoiceClient:
        return self._voice_client


class MusicQueue(MusicManager):

    def __init__(self) -> None:
        self.music_downloader = SongFactory(LRUSongsCache())
        self.music_queue: asyncio.Queue[Song] = asyncio.Queue()
        self.downloading_queue: list[Tuple[str, str, bool]] = []  # (query, url, silent)
        self.downloaded_songs: list[str] = []
        self.currently_downloading = False
        self.download_task: Optional[asyncio.Task] = None
        self.song_currently_downloading: Optional[str] = None
        self._loop_music = False

    @property
    def loop_music(self) -> bool:
        return self._loop_music

    @loop_music.setter
    def loop_music(self, value: bool) -> None:
        self._loop_music = value

    async def add(self, query: str, ctx: Optional[commands.Context], *, silent: bool = False,
                  url: Optional[str] = None) -> None:
        self.downloading_queue.append((query, url, silent))
        if not self.currently_downloading:
            await self._download(ctx)

    async def _download(self, ctx: Optional[commands.Context]) -> None:
        while self.downloading_queue:
            message: Optional[Embed] = None
            self.currently_downloading = True
            self.song_currently_downloading, url, silent = self.downloading_queue.pop(0)
            try:
                search = url or self.song_currently_downloading
                self.download_task = asyncio.create_task(
                    self.music_downloader.prepare_song(search))
                song = await self.download_task
            except asyncio.CancelledError:
                continue
            except SongFactory.NoResultsFoundException as e:
                message = no_results(self.song_currently_downloading)
                continue
            except SongFactory.LiveFoundException as e:
                message = live_stream(self.song_currently_downloading)
                continue
            except SongFactory.AgeRestrictedException as e:
                message = age_restricted(self.song_currently_downloading)
                continue
            except Exception as e:
                message = download_error(self.song_currently_downloading)
                logging.error(e)
                continue
            finally:
                if ctx and message and not silent:
                    await ctx.send(embed=message)
            await self.music_queue.put(song)
            self.downloaded_songs.append(song.title)
            message = added_to_queue(song, self.queue_length, self.loop_music)
            if ctx and not silent and message:
                await ctx.send(embed=message)
        self.currently_downloading = False

    async def next(self) -> Song:
        if self.music_queue.empty() and not self.currently_downloading:
            raise MusicManager.EndOfPlaylistException
        song = await self.music_queue.get()
        if self.loop_music:
            await self.add(song.title, None, silent=True, url=song.url)
        self.downloaded_songs.remove(song.title)
        return song

    @property
    def queue_length(self) -> int:
        return self.music_queue.qsize()

    async def clear_queue(self) -> None:
        self.downloading_queue.clear()

        if self.currently_downloading:
            self.download_task.cancel()

        self.music_queue = asyncio.Queue()
        self.downloaded_songs.clear()

    def get_queue_info(self) -> str:
        downloaded = "- " + "\n- ".join(
            '`' + title + '`' for title in self.downloaded_songs) + "\n" if self.downloaded_songs else ""
        now_downloading = "- `" + self.song_currently_downloading + '`\n' if self.currently_downloading else ""
        to_download = "- " + "\n- ".join(
            '`' + query + '`' for query, _, _ in self.downloading_queue) + "\n" if self.downloading_queue else ""
        return downloaded + now_downloading + to_download
