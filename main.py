import asyncio
import logging

import discord
from discord.ext import commands

from utils import load_token

intents: discord.Intents = discord.Intents.default()
intents.message_content = True

bot: commands.Bot = commands.Bot(
    command_prefix="!",
    description="Relatively simple music bot with some extra features for gaming",
    intents=intents,
    log_level=logging.DEBUG  # TODO: change this to logging.INFO after testing
)


@bot.event
async def on_ready() -> None:
    """
    Print a message to the console when the bot is ready

    :return: None
    """
    message = "Logged in as {bot.user} (ID: {bot.user.id})"
    print(message)
    print("-" * len(message))


async def main():
    TOKEN = load_token()
    async with bot:
        ...
        await bot.start(TOKEN)


if __name__ == '__main__':
    asyncio.run(main())
