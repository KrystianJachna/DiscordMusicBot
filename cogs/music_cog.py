# music.py
from typing import Optional

import discord
from discord.ext import commands, tasks

from .music.messages import *
from .music.music_service import MusicQueue, MusicPlayer


class MusicCog(commands.Cog):
    """
    Music commands for the bot

    :param bot: The bot instance
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.music_queue = MusicQueue()
        self.music_player: Optional[MusicPlayer] = None

    @commands.command(description="Play a song or add it to the queue, use !play <url or search query>")
    async def play(self, ctx: commands.Context, *, arg) -> None:
        """
        Play a song in the voice channel

        :param ctx: The discord context
        :param arg: The song to play passed as a url or search query by the user
        :return:
        """
        await self.music_queue.add(arg, ctx)
        if not self.music_player.is_playing:
            await self.music_player.play_loop()

    @commands.command(description="Skip the currently playing song")
    async def skip(self, ctx: commands.Context) -> None:
        """
        Skip the current song

        :param ctx: The discord context
        :return: None
        """
        if not self.music_player.is_playing:
            await ctx.send(embed=skip_error())
            return
        await self.music_player.skip()
        await ctx.send(embed=skipped(self.music_queue.queue_length))

    @commands.command()
    async def create_playlist(self, ctx: commands.Context) -> None:
        pass

    @commands.command(description="Stop playback and clear the music player")
    async def stop(self, ctx: commands.Context) -> None:
        """
        Stop the music player

        :param ctx: The discord context
        :return: None
        """
        if not self.music_player:
            await ctx.send(embed=not_connected())
            return
        await self.music_player.stop()
        self.music_player = None
        await ctx.send(embed=stopped())

    @commands.command(description="Pause the currently playing song")
    async def pause(self, ctx: commands.Context) -> None:
        """
        Pause the current song

        :param ctx: The discord context
        :return: None
        """
        try:
            await self.music_player.pause()
        except MusicPlayer.NotPlayingException:
            await ctx.send(embed=not_playing())

    @commands.command(description="Resume playback of the paused song")
    async def resume(self, ctx: commands.Context) -> None:
        """
        Resume the current song

        :param ctx: The discord context
        :return: None
        """
        try:
            await self.music_player.resume()
        except MusicPlayer.NotPlayingException:
            await ctx.send(embed=not_playing())

    @commands.command(description="Toggle looping for the current song")
    async def loop(self, ctx: commands.Context) -> None:
        ...

    @commands.command(description="View the current music queue")
    async def queue(self, ctx: commands.Context) -> None:
        """
        Get information about the music queue

        :param ctx: The discord context
        :return: None
        """
        downloaded, now_downloading, to_download = self.music_queue.get_queue_info()
        now_playing = self.music_player.get_now_playing() if self.music_player else "-"
        await ctx.send(embed=queue(downloaded, now_downloading, to_download, now_playing))

    @commands.command(description="Clear all songs from the queue")
    async def clear(self, ctx: commands.Context) -> None:
        """
        Clear the music queue

        :param ctx: The discord context
        :return: None
        """
        await self.music_queue.clear_queue()
        await ctx.send(embed=clear())

    @tasks.loop()
    async def check_listeners(self):
        pass

    @play.before_invoke
    async def ensure_voice(self, ctx):
        """
        Ensure the bot is in a voice channel before playing a song

        :param ctx: The discord context
        :return: None
        """
        if ctx.voice_client is None:
            if ctx.author.voice:
                voice_client = await ctx.author.voice.channel.connect()
                self.music_player = MusicPlayer(self.music_queue, voice_client)
            else:
                await ctx.send(embed=not_in_voice_channel())
