from typing import Optional
from dataclasses import dataclass
from discord import FFmpegPCMAudio


@dataclass
class Song:
    title: str
    url: str
    duration: int
    thumbnail: Optional[str]
    _stream_url: Optional[str]

    _ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    async def get_source(self) -> FFmpegPCMAudio:
        # every time get_source is called, the FFPCMAudio object is created
        # it has to be created every time because it is not reusable
        return FFmpegPCMAudio(self._stream_url, **self._ffmpeg_options)
