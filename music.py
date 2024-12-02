import discord
from discord.ext import commands, tasks


class Music(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command()
    async def play(self, ctx):
        ...

    @commands.command()
    async def skip(self, ctx):
        ...

    @commands.command()
    async def stop(self, ctx):
        ...

    @commands.command()
    async def pause(self, ctx):
        ...

    @commands.command()
    async def resume(self, ctx):
        ...

    @commands.command()
    async def loop(self, ctx):
        ...

    @commands.command()
    async def join(self, ctx):
        ...

    @commands.command()
    async def queue(self, ctx):
        ...

    @tasks.loop()
    async def check_listeners(self):
        ...
