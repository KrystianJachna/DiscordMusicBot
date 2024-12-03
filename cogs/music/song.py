from dataclasses import dataclass
from pathlib import Path
from discord import FFmpegPCMAudio


@dataclass
class Song:
    title: str
    file: Path
    source: FFmpegPCMAudio
    url: str
