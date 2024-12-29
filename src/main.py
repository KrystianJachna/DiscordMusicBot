import asyncio
import logging
from traceback import format_exc

import discord
from discord import Embed
from cogs.music_cog import MusicCog
from utils import load_token, setup_logging
from discord.ext import commands
from help_message import HelpMessage

intents = discord.Intents.default()
intents.message_content = True  # Required for commands to be able to read arguments

bot: commands.Bot = commands.Bot(
    command_prefix="!",
    description="Relatively simple music bot with some extra features for gaming",
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
        await ctx.send(embed=Embed(title="🤷‍ Command Not Found️",
                                   description="Type `!help` to see the list of available commands",
                                   color=0xFF6900))
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=Embed(title=f"🤔 Oops! You’re missing something!",
                                   description=f"Type `!help {ctx.command.name}` for more information",
                                   color=0xFF0000))
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
        logging.debug(format_exc())
    except Exception as e:
        logging.error(e)
        logging.debug(format_exc())


if __name__ == '__main__':
    asyncio.run(main())
