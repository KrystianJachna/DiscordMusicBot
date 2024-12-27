from _datetime import timedelta

from discord import Embed

from .music_downlaoder import Song

def added_to_queue(song: Song, queue_elements: int, loop_enabled: bool) -> Embed:
    message = Embed(title="Song Added to Queue 🎶",
                    description=f"[{song.title}]({song.url})\n",
                    color=0x00FF00)
    message.add_field(name="Duration", value=str(timedelta(seconds=song.duration)))
    message.add_field(name="Queue Length", value=queue_elements)
    message.set_thumbnail(url=song.thumbnail or song.url)
    if loop_enabled:
        message.set_footer(text="Looping is enabled")
    return message


def download_error(query: str) -> Embed:
    return Embed(title="Download Error ⛔",
                 description=f"An error occurred while downloading the song: {query}",
                 color=0xFF0000)


def no_results(query: str) -> Embed:
    return Embed(title="No Results 👎",
                 description=f"No results found for: \n*{query}*\nPlease try a different search query",
                 color=0xFF0000)


def live_stream(query: str) -> Embed:
    return Embed(title="Live Stream 🎥",
                 description=f"Live stream found for: \n*{query}*\nPlease try a different search query",
                 color=0xFF0000)


def skip_error() -> Embed:
    return Embed(title="Skip Error ⛔",
                 description="There is no song currently playing",
                 color=0xFF6900)


def skipped(queue_length: int) -> Embed:
    message = Embed(title="Song Skipped ⏭️",
                    description=f"**Queue Length:** {queue_length}",
                    color=0x00FF00)
    return message


def not_in_voice_channel() -> Embed:
    return Embed(title="Not in Voice Channel 🔇",
                 description="You need to be in a voice channel to use this command",
                 color=0xFF0000)


def not_playing() -> Embed:
    return Embed(title="Not Playing 🔇",
                 description="There is no song currently playing",
                 color=0xFF6900)


def not_connected() -> Embed:
    return Embed(title="Not Connected 🔇 ",
                 description="Bot needs to be connected to a voice channel to use this command",
                 color=0xFF6900)


def stopped() -> Embed:
    return Embed(title="Stopped 🛑",
                 description="The music player has been stopped",
                 color=0x00FF00)


def queue(queue_songs: str, now_playing: str, looping_enabled: bool) -> Embed:
    if queue_songs or now_playing:
        message = Embed(title="Music Queue 🎶",
                        description="**Now Playing:** " + (now_playing if now_playing else "*waiting...*"),
                        color=0x00FF00)
        message.add_field(name="Queue:", value=queue_songs if queue_songs else "*The queue is empty*")
    else:
        message = Embed(title="Music Queue 🎶",
                        description="The music queue is empty",
                        color=0xFF6900)
    if looping_enabled:
        message.set_footer(text="Looping is enabled")
    return message


def clear() -> Embed:
    return Embed(title="Queue Cleared 🧹",
                 description="The music queue has been cleared",
                 color=0x00FF00)


def paused(song_title: str) -> Embed:
    return Embed(title="Paused ⏸️",
                 description=f"The song **{song_title}** has been paused",
                 color=0x00FF00)


def resumed(song_title: str) -> Embed:
    return Embed(title="Resumed ▶️",
                 description=f"The song **{song_title}** has been resumed",
                 color=0x00FF00)


def looping(loop: bool) -> Embed:
    description = f"**Status**: {'enabled' if loop else 'disabled'}"
    return Embed(title=f"Looping ⟳",
                 description=description,
                 color=0x00FF00)
