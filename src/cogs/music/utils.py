from _datetime import timedelta

from discord import Embed

from .music_downlaoder import Song

PLAY_DESCRIPTION = ("Play a song from youtube or add it to the queue.\n"
                    "Usage `!play <url or search query>`")
SKIP_DESCRIPTION = ("Skip the currently playing song and play the next one in the queue.\n"
                    "Usage `!skip`")
STOP_DESCRIPTION = ("Stop playback and clear the queue, the bot will leave the voice channel.\n"
                    "Usage `!stop`")
PAUSE_DESCRIPTION = ("Pause the currently playing song, use `!resume` to resume playback.\n"
                     "Usage `!pause`")
RESUME_DESCRIPTION = ("Resume playback of the paused song, needs to be paused first by `!pause`.\n"
                      "Usage `!resume`")
LOOP_DESCRIPTION = ("Toggle looping for the current playlist.\n"
                    "It prioritizes songs that are being added to the queue, over those that were already played.\n"
                    "Usage `!loop` to toggle looping on or off.")
QUEUE_DESCRIPTION = ("Show the current queue of songs.\n"
                     "Usage `!queue`")
CLEAR_DESCRIPTION = ("Clear all songs from the queue. Does not affect the currently playing song.\n"
                     "Usage `!clear`")


def added_to_queue(song: Song, queue_elements: int) -> Embed:
    message = Embed(title="Song Added to Queue 🎶",
                    description=f"[{song.title}]({song.url})\n",
                    color=0x00FF00)
    message.add_field(name="Duration", value=str(timedelta(seconds=song.duration)))
    message.add_field(name="Queue Length", value=queue_elements)
    message.set_thumbnail(url=song.thumbnail or song.url)
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


def queue(title_lst: list[str], loop: bool) -> Embed:  # TODO: improve
    message = Embed(title="Music Queue 🎵",
                    color=0x00FF00)
    if title_lst:
        message.add_field(name="Now Playing", value=title_lst[0])
        message.add_field(name="Up Next", value="\n".join(title_lst[1:]))
    else:
        message.add_field(name="Queue Empty", value="No songs in the queue")
    if loop:
        message.set_footer(text="Looping enabled")
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


def age_restricted(query: str) -> Embed:
    return Embed(title="Age Restricted Content 🔞",
                 description=f"The song: {query} is age restricted. "
                             "Please provide a `cookies.txt` file in the root directory to play the song\n\n"
                             "See `README.md` for details",
                 color=0xFF0000)
