import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, Tuple

from discord import VoiceClient
from discord.ext import commands

from .messages import *
from .music_downlaoder import MusicDownloader


class MusicManager(ABC):
    """
    Abstract class to manage the music queue

    :param EndOfPlaylistException: Exception to raise when the end of the playlist is reached
    """

    class EndOfPlaylistException(Exception):
        def __init__(self):
            super().__init__("End of playlist reached.")

    @abstractmethod
    async def next(self) -> Song:
        """
        Get the next song from the queue

        :return: The next song
        """
        pass

    @abstractmethod
    async def clear_queue(self) -> None:
        """
        Clear the queue

        :return: None
        :return:
        """
        pass


class MusicPlayer:
    """
    Class to play the songs in the queue

    :param music_manager: The music manager
    :param voice_client: The voice client (think of it as the voice channel)
    """

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

    async def pause(self) -> None:
        """
        Pause the current song

        :return: None
        """
        if not self._is_playing:
            raise MusicPlayer.NotPlayingException
        self.voice_client.pause()

    async def resume(self):
        """"
        Resume the current song

        :return: None
        """
        if not self._is_playing:
            raise MusicPlayer.NotPlayingException
        self.voice_client.resume()

    async def skip(self) -> None:
        """
        Skip the current song

        :return: None
        """
        self.voice_client.stop()

    async def play_loop(self) -> None:
        """
        Play the songs in the queue

        Try to play the next song in the queue until the end of the playlist is reached
        :return: None
        """
        self._is_playing = True
        while self.keep_playing:
            try:
                self._now_playing = await self.music_manager.next()
            except MusicManager.EndOfPlaylistException:
                break
            async with self._singing:
                self.voice_client.play(
                    self._now_playing.source,
                    after=lambda _: asyncio.run_coroutine_threadsafe(
                        self._notify_singing(), self.event_loop
                    )
                )
                await self._singing.wait()
        self._is_playing = False

    def get_now_playing(self) -> Optional[str]:
        """
        Get the song name that is currently playing

        :return: The song name that is currently playing or an empty string if no song is playing
        """
        return f"[{self._now_playing.title}]({self._now_playing.url})" if self._now_playing else ""

    async def _notify_singing(self) -> None:
        """
        Notify the player that the song has finished playing

        :return: None
        """
        async with self._singing:
            self._singing.notify_all()

    async def stop(self) -> None:
        """
        Stop the player

        :return: None
        """
        self.keep_playing = False
        self.voice_client.stop()
        await self.music_manager.clear_queue()
        await self.voice_client.disconnect()

    @property
    def is_playing(self) -> bool:
        """
        Check if the player is currently playing a song

        :return: True if the player is playing a song, False otherwise
        """
        return self._is_playing

    @property
    def voice_client(self) -> VoiceClient:
        """
        Get the voice client

        :return: The voice client
        """
        return self._voice_client


class MusicQueue(MusicManager):
    """
    Class to manage the music queue, and download the songs

    :param downloading_queue: The queue of songs to download
    :param currently_downloading: If any song is currently downloading
    :param music_queue: The queue of songs to play
    :param music_downloader: The music downloader
    """

    def __init__(self) -> None:
        self.downloading_queue: list[Tuple[str, bool]] = [] # list of tuples containing the url/silent flag
        self.currently_downloading = False
        self.music_queue: asyncio.Queue[Song] = asyncio.Queue()
        self.downloaded_songs: list[str] = []
        self.music_downloader = MusicDownloader(quiet=False) # TODO: Change to True for production
        self.download_task: Optional[asyncio.Task] = None
        self.song_currently_downloading: Optional[str] = None
        self._loop_music = False

    @property
    def loop_music(self) -> bool:
        return self._loop_music

    @loop_music.setter
    def loop_music(self, value: bool) -> None:
        self._loop_music = value

    async def add(self, query: str, ctx: Optional[commands.Context], *, silent: bool = False) -> None:
        """
        Add a song to the queue, and start downloading it if there are no songs currently downloading

        :param query: url or search query
        :param ctx: The discord context
        :return: None
        """
        self.downloading_queue.append((query, silent))
        if not self.currently_downloading:
            await self._download(ctx)

    async def _download(self, ctx: Optional[commands.Context]) -> None:
        """
        Process the downloading queue

        This method will download the songs in the queue if there are any
        url/query waiting to be downloaded

        :param ctx: The discord context
        :return: None
        """
        while self.downloading_queue:
            message: Optional[Embed] = None
            self.currently_downloading = True
            self.song_currently_downloading, silent = self.downloading_queue.pop(0)
            try:
                self.download_task = asyncio.create_task(
                    self.music_downloader.download(self.song_currently_downloading))
                song = await self.download_task
            except asyncio.CancelledError:
                continue
            except MusicDownloader.NoResultsFound as e:
                message = no_results(self.song_currently_downloading)
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
        """
        Get the next song from the queue

        :return: The next song
        """
        if self.music_queue.empty() and not self.currently_downloading:
            raise MusicManager.EndOfPlaylistException
        song = await self.music_queue.get()
        logging.info(f"Playing song: {song.title}")
        if self.loop_music:
            await self.add(song.url, None, silent=True)
            logging.info(f"Looping song: {song.title}")
        else:
            self.downloaded_songs.remove(song.title)
        return song

    @property
    def queue_length(self) -> int:
        """
        Get the length of the queue

        :return: The length of the queue
        """
        return self.music_queue.qsize()

    async def clear_queue(self) -> None:
        """
        Clear the queue

        :return: None
        """
        self.downloading_queue.clear()

        if self.currently_downloading:
            self.download_task.cancel()

        self.music_queue = asyncio.Queue()
        self.downloaded_songs.clear()

    def get_queue_info(self) -> Tuple[str, str, str]:
        """
        Show the songs in the queue

        Each song is separated by a new line and a dash

        :return: A tuple containing the downloaded songs, the song currently downloading, and the songs to download
        """
        downloaded = "- " + "\n- ".join('`' + title + '`' for title in self.downloaded_songs) if self.downloaded_songs else ""
        now_downloading = "- `" + self.song_currently_downloading + '`' if self.currently_downloading else ""
        to_download = "- " + "\n- ".join(
            '`' + query + '`' for query, _ in self.downloading_queue) if self.downloading_queue else ""

        return downloaded, now_downloading, to_download
