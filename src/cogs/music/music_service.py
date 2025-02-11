import asyncio
import logging
from typing import Optional

from .song import SongRequest
from discord import VoiceClient

from .messages import *
from .song_queue import SongQueue


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
        if self._now_playing:
            self._voice_client.stop()
        if self._processing_task:
            self._processing_task.cancel()
        await self._voice_client.disconnect()

    async def clear_queue(self) -> None:
        await self._song_queue.clear_queue()
        self._looped_songs.clear()
        self._clearing_queue = True

    async def get_queue_info(self) -> tuple[Optional[Song], list[str]]:  # (now_playing_song, [queries])
        waiting_in_queue = await self._song_queue.get_queue_info()
        looped_songs = [song.title for song in self._looped_songs] if self._loop else []
        return self._now_playing, waiting_in_queue + looped_songs

    async def queue_length(self) -> int:
        return await self._song_queue.queue_length() + (len(self._looped_songs) if self._loop else 0)

    async def play(self, song_request: SongRequest) -> None:
        await self._song_queue.add(song_request)
        if not self._processing_queue:
            self._processing_task = asyncio.create_task(self._process_song_queue())

    async def shuffle(self) -> None:
        await self._song_queue.shuffle()

    async def _process_song_queue(self) -> None:
        self._processing_queue = True
        try:
            while True:
                try:
                    self._now_playing = await self._song_queue.next()
                except SongQueue.EndOfPlaylistException:
                    if self.loop and self._looped_songs:
                        self._now_playing = self._looped_songs.pop(0)
                    else:
                        break
                source = await self._now_playing.get_source()
                finished = asyncio.Event()
                self._voice_client.play(source, after=lambda e: self._after_playing(e, finished))
                await finished.wait()
                self._now_playing = None
        except asyncio.CancelledError:
            pass
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
            logging.error(f"Error playing song: {error}", exc_info=True)
        finished.set()
