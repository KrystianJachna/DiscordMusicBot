# music.py
import asyncio
import random
from random import random

from discord.ext import commands, tasks

from cogs.music.music_downlaoder import MusicDownloader
from cogs.music.music_queue import MusicQueue


class MusicCog(commands.Cog):
    """
    Music commands for the bot

    :param bot: The bot instance
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # self.q = []
        # self.currently_downloading = False
        # self.music_queue = []
        # self.mdow = MusicDownloader()
        self.music_queue = MusicQueue(bot)

    @commands.command()
    async def play(self, ctx: commands.Context, *, arg: str):
        await self.music_queue.add(arg, ctx)


    @commands.command()
    async def skip(self, ctx: commands.Context):
        ...

    @commands.command()
    async def stop(self, ctx: commands.Context):
        # await ctx.send(f"queue now has {self.q.qsize()} items")
        await ctx.send(f"Queue items: {self.music_queue}")
        #

    @commands.command()
    async def pause(self, ctx: commands.Context):
        ...

    @commands.command()
    async def resume(self, ctx: commands.Context):
        ...

    @commands.command()
    async def loop(self, ctx: commands.Context):
        ...

    @commands.command()
    async def join(self, ctx: commands.Context):
        ...

    @commands.command()
    async def queue(self, ctx: commands.Context):
        ...

    @commands.command()
    async def clear(self, ctx: commands.Context):
        ...

    @tasks.loop()
    async def check_listeners(self):
        ...

    @play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
