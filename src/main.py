import asyncio

import discord
from discord.ext import commands
import logging
try:
    from src.utils import load_token, setup_logging
    from src.cogs.music.music_cog import MusicCog
    from src.help_message import HelpMessage
    from src.config import *
except ModuleNotFoundError:  # supports `python src/main.py` as well
    from utils import load_token, setup_logging
    from cogs.music.music_cog import MusicCog
    from help_message import HelpMessage
    from config import *

intents = discord.Intents.default()
intents.message_content = True  # Required for commands to be able to read arguments

class MusicBot(commands.Bot):
    async def setup_hook(self) -> None:
        await self.add_cog(MusicCog(self))
        # setup_hook runs after login, so application_id is available here.
        synced_commands = await self.tree.sync()
        logging.info("Synchronized %d application commands", len(synced_commands))


bot: commands.Bot = MusicBot(
    command_prefix="!",
    description="Music bot for Discord, built with discord.py and yt-dlp",
    intents=intents,
    help_command=HelpMessage(),
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
    else:
        logging.error(f"Error occurred in command: {ctx.command}", exc_info=True)


async def main() -> None:
    try:
        token = load_token()
        setup_logging(logging.INFO, enable_file_logging=True)
        async with bot:
            await bot.start(token)
    except discord.LoginFailure:
        logging.error("Failed to log in. Ensure the token is correct.")
    except Exception as e:
        logging.error(e, exc_info=True)


if __name__ == '__main__':
    asyncio.run(main())
