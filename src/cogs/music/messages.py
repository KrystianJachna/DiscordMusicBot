# This file contains the messages that are sent to the user when they use the music commands for simplicity.

from _datetime import timedelta

from discord import Embed
from .song import PlaylistRequest
from .music_downloader import Song

from config import *

PLAY_DESCRIPTION = (
    "Play a song directly from YouTube or add it to the queue. You can provide a direct video link, a playlist link, or even a search query. "
    "If a playlist is provided, all songs in the playlist will be added to the queue.\n"
    "**Usage**: `!play <YouTube URL or search query>`"
)

SKIP_DESCRIPTION = (
    "Skip the currently playing song and move to the next one in the queue.\n"
    "**Usage**: `!skip`"
)

STOP_DESCRIPTION = (
    "Stop playback entirely, clear the queue, and disconnect the bot from the voice channel.\n"
    "**Usage**: `!stop`"
)

PAUSE_DESCRIPTION = (
    "Pause the currently playing song. Use `!resume` to continue playback.\n"
    "**Usage**: `!pause`"
)

RESUME_DESCRIPTION = (
    "Resume playback of the paused song. If no song is paused, this command will do nothing.\n"
    "**Usage**: `!resume`"
)

LOOP_DESCRIPTION = (
    "Toggle looping for the current playlist. When enabled, the bot will prioritize newly added songs over previously played ones.\n"
    "**Usage**: `!loop` to turn looping on or off."
)

QUEUE_DESCRIPTION = (
    "Display the current list of songs in the queue.\n"
    "**Usage**: `!queue`"
)

CLEAR_DESCRIPTION = (
    "Clear all songs from the queue. This does not affect the currently playing song.\n"
    "**Usage**: `!clear`"
)

SHUFFLE_DESCRIPTION = (
    "Shuffle the songs in the queue.\n"
    "**Usage**: `!shuffle`"
)

def added_to_queue(song: Song, queue_elements: int) -> Embed:
    message = Embed(title=" 🎶 Song Added to Queue",
                    description=f"🔗 [{song.title}]({song.url})\n",
                    color=SUCCESS_COLOR)
    message.add_field(name="Duration", value=str(timedelta(seconds=song.duration)))
    message.add_field(name="Queue Length", value=queue_elements)
    message.set_thumbnail(url=song.thumbnail or song.url)
    return message


def added_playlist_to_queue(playlist: PlaylistRequest) -> Embed:
    message = Embed(title="📋 Songs from Playlist Added to Queue",
                    description=f"🔗 [{playlist.title}]({playlist.playlist_url})\n",
                    color=SUCCESS_COLOR)
    message.add_field(name="Total Duration", value=str(timedelta(seconds=playlist.total_duration)))
    message.add_field(name="Number of Songs", value=playlist.length)
    message.set_thumbnail(url=playlist.thumbnail)
    message.set_footer(
        text=f"Some songs may be unavailable, therefore the total duration and number of songs may differ")
    return message


def download_error(query: str) -> Embed:
    return Embed(title="⛔ Download Error",
                 description=f"An error occurred while downloading the song: {query}.",
                 color=ERROR_COLOR)


def skip_error() -> Embed:
    return Embed(title="⛔ Skip Error",
                 description="There is no song currently playing",
                 color=ERROR_COLOR)


def skipped(queue_length: int, looping_enabled: bool) -> Embed:
    message = Embed(title="⏭️ Song skipped",
                    description=f"**Queue Length**: {queue_length}",
                    color=SUCCESS_COLOR)
    if looping_enabled:
        message.set_footer(text="🔄 Looping is enabled")
    return message


def not_in_voice_channel() -> Embed:
    return Embed(
        title="🔇 Not in Voice Channel",
        description="You must be in a voice channel to use this command!\n"
                    "Please join a voice channel and try again.",
        color=ERROR_COLOR
    )


def not_playing() -> Embed:
    return Embed(title="⏯️ Not Playing",
                 description="There is no song currently playing",
                 color=ERROR_COLOR)


def not_connected() -> Embed:
    message = Embed(title="🔇 Not Connected",
                    description="Bot needs to be connected to a voice channel to use this command",
                    color=ERROR_COLOR)
    message.set_footer(text="💡Tip: Play a song first to connect the bot to a voice channel")
    return message


def stopped() -> Embed:
    return Embed(title="🛑️ Stopped",
                 description="The music player has been stopped",
                 color=SUCCESS_COLOR)


def queue(now_playing: Song, coming_next: list[str], looping_enabled: bool) -> Embed:
    if now_playing or coming_next:
        now_playing = f"**Now Playing**: [{now_playing.title}]({now_playing.url})" if now_playing else "waiting..."
        message = Embed(title="🎵 Music Queue",
                        description=now_playing,
                        color=SUCCESS_COLOR)
        waiting_in_queue = "- " + "\n- ".join(coming_next[:10]) if coming_next else "No songs in queue"
        waiting_in_queue += f"\n**{len(coming_next)} more songs in queue**" if len(coming_next) > 10 else ""
        message.add_field(name="Coming Next:", value=waiting_in_queue)
    else:
        message = Embed(title="🎵 Music Queue",
                        description="No songs in queue",
                        color=SUCCESS_COLOR)
    if looping_enabled:
        message.set_footer(text="🔄 Looping is enabled")
    return message


def clear() -> Embed:
    return Embed(title="🧹 Queue Cleared",
                 description="The music queue has been cleared",
                 color=SUCCESS_COLOR)


def paused(song_title: str, url: str) -> Embed:
    return Embed(title="⏸️ Paused",
                 description=f"Song: [{song_title}]({url})",
                 color=SUCCESS_COLOR)


def resumed(song_title: str, url: str) -> Embed:
    return Embed(title="▶️ Resumed",
                 description=f"Song: [{song_title}]({url})",
                 color=SUCCESS_COLOR)


def looping(looping_enabled: bool) -> Embed:
    description = f"**Status**: {'enabled' if looping_enabled else 'disabled'}"
    return Embed(title=f"🔄 Looping",
                 description=description,
                 color=SUCCESS_COLOR)


def not_in_same_voice_channel(bot_channel: str) -> Embed:
    return Embed(title="⛔ Not in the Same Voice Channel",
                 description=f"You must be in the same voice channel as the bot: **{bot_channel}**",
                 color=ERROR_COLOR)


def shuffled() -> Embed:
    return Embed(title="🔀 Queue Shuffled",
                 description="The queue has been shuffled",
                 color=SUCCESS_COLOR)
