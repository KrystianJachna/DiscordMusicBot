# This file contains the messages that are sent to the user when they use the music commands for simplicity.

from _datetime import timedelta

from discord import Embed

from .music_downlaoder import Song

from config import *

PLAY_DESCRIPTION = ("Play a song from youtube or add it to the queue.\n"
                    "Usage: `!play <url or search yt query>`")
SKIP_DESCRIPTION = ("Skip the currently playing song and play the next one in the queue.\n"
                    "Usage: `!skip`")
STOP_DESCRIPTION = ("Stop playback and clear the queue, the bot will leave the voice channel.\n"
                    "Usage: `!stop`")
PAUSE_DESCRIPTION = ("Pause the currently playing song, use `!resume` to resume playback.\n"
                     "Usage: `!pause`")
RESUME_DESCRIPTION = ("Resume playback of the paused song, if not paused, does nothing.\n"
                      "Usage: `!resume`")
LOOP_DESCRIPTION = ("Toggle looping for the current playlist. "
                    "It prioritizes songs that are being added to the queue, over those that were already played.\n"
                    "Usage: `!loop` to toggle looping on or off.")
QUEUE_DESCRIPTION = ("Show the current queue of songs.\n"
                     "Usage `!queue`")
CLEAR_DESCRIPTION = ("Clear all songs from the queue. Does not affect the currently playing song.\n"
                     "Usage: `!clear`")


def added_to_queue(song: Song, queue_elements: int) -> Embed:
    message = Embed(title=" 🎶 Song Added to Queue",
                    description=f"🔗 [{song.title}]({song.url})\n",
                    color=SUCCESS_COLOR)
    message.add_field(name="Duration", value=str(timedelta(seconds=song.duration)))
    message.add_field(name="Queue Length", value=queue_elements)
    message.set_thumbnail(url=song.thumbnail or song.url)
    return message


def download_error(query: str) -> Embed:
    return Embed(title="⛔ Download Error",
                 description=f"An error occurred while downloading the song: {query}.",
                 color=ERROR_COLOR)


def no_results(query: str) -> Embed:
    message = Embed(title="🔍 No Results Found",
                    description=f"We couldn't find any results for: *{query}*\n\n",
                    color=ERROR_COLOR)
    message.set_footer(text="💡Tip: Try using different keywords or check your spelling")
    return message


def live_stream(query: str) -> Embed:
    message = Embed(title="🎥 Live Stream",
                    description=f"Found a live stream for: *{query}*\n"
                                f"We currently do not support live streams",
                    color=ERROR_COLOR)
    message.set_footer(text="💡Tip: Try using different keywords or search for a different song")
    return message


def age_restricted(query: str) -> Embed:
    message = Embed(title=" 🔞 Age Restricted Content",
                    description=f"The song: {query} is age restricted. "
                                "Please provide a `cookies.txt` file in the root directory to play the song\n\n"
                                "See `README.md` for details",
                    color=ERROR_COLOR)
    message.set_footer(text="💡Tip: Search for a different song")
    return message


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
        waiting_in_queue = "- " + "\n- ".join(coming_next) if coming_next else "No songs in queue"
        message.add_field(name="Coming Next:", value=waiting_in_queue)
    else:
        message = Embed(title="🎵Music Queue",
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
