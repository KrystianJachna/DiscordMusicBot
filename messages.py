
from discord import Embed

def command_not_found() -> Embed:
    return Embed(title="Command Not Found",
                 color=0xFF6900)