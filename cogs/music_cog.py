# music.py
from random import random

import discord
from discord.ext import commands, tasks
import asyncio
import random
from cogs.music.music_downlaoder import MusicDownloader


class MusicCog(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.q = []
        self.currently_downloading = False
        self.music_queue = []

    @commands.command()
    async def play(self, ctx: commands.Context):
        m = MusicDownloader()
        await m.download('https://www.youtube.com/watch?v=Vu1YERh2vnM')
        download_time = random.choice([2, 10])
        self.q.append(download_time)
        await ctx.send(f"Added to queue. Estimated download time: {download_time} seconds")
        if not self.currently_downloading:
            await self._process_queue(ctx)

    async def _process_queue(self, ctx: commands.Context):
        while self.q:
            self.currently_downloading = True
            download_time = self.q.pop(0)
            await asyncio.sleep(download_time)
            self.music_queue.append(download_time)
            await ctx.send(f"Downloaded a song in {download_time} seconds")
        self.currently_downloading = False


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
