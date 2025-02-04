from typing import Optional
from dataclasses import dataclass
from discord import FFmpegPCMAudio
from discord.ext import commands


@dataclass
class Song:
    title: str
    url: str
    duration: int
    thumbnail: Optional[str]
    expires_at: Optional[int]
    _stream_url: Optional[str]

    _ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    async def get_source(self) -> FFmpegPCMAudio:
        # every time get_source is called, the FFPCMAudio object is created
        # it has to be created every time because it is not reusable
        return FFmpegPCMAudio(self._stream_url, **self._ffmpeg_options)


@dataclass
class SongRequest:
    query: str
    ctx: commands.Context
    playlist_elem: bool = False  # whether to send a message after adding the song to the queue
    _title: Optional[str] = None

    @property
    def title(self) -> str:
        return self._title or self.query

    @title.setter
    def title(self, value: str) -> None:
        self._title = value
