import asyncio
from traceback import format_exc

import discord
from discord.ext import commands
import logging
from utils import load_token, setup_logging
from cogs.music_cog import MusicCog
from help_message import HelpMessage
from config import *

intents = discord.Intents.default()
intents.message_content = True  # Required for commands to be able to read arguments

bot: commands.Bot = commands.Bot(
    command_prefix="!",
    description="Music bot for Discord, built with discord.py and youtube-dl",
    intents=intents,
    help_command=HelpMessage()
)


@bot.event
async def on_ready() -> None:
    message = f"Logged in as {bot.user} (ID: {bot.user.id})"
    logging.info(message)
    logging.info("-" * len(message))


@bot.event
async def on_command_error(ctx: commands.Context, error: Exception) -> None:
    """
    Discord event that is triggered when a command error occurs either
    through user input or through an error in the command itself.
    """
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(embed=discord.Embed(title="🤷‍ Command Not Found️",
                                           description="Type `!help` to see the list of available commands",
                                           color=ERROR_COLOR))
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(title=f"🤔 Oops! You’re missing something!",
                                           description=f"Type `!help {ctx.command.name}` for more information",
                                           color=ERROR_COLOR))
    else:  # error occurred in the command code
        logging.error(f"Error occurred in command: {ctx.command}")
        logging.error(error)
        logging.debug(format_exc() if format_exc() != "NoneType: None\n" else "No traceback available")


async def main() -> None:
    try:
        token = load_token()
        setup_logging(logging.DEBUG, enable_file_logging=True)  # TODO: Change to INFO for production
        async with bot:
            await bot.add_cog(MusicCog(bot))
            await bot.start(token)
    except discord.LoginFailure:
        logging.error("Failed to log in. Ensure the token is correct.")
    except Exception as e:
        logging.error(e)
        logging.debug(format_exc())


if __name__ == '__main__':
    asyncio.run(main())
