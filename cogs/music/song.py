from dataclasses import dataclass
from pathlib import Path


@dataclass
class Song:
    title: str
    file: Path
