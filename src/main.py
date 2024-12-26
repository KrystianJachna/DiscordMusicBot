
import asyncio
import logging
from traceback import format_exc

import discord

from cogs.music_cog import MusicCog
from utils import load_token, setup_logging
from messages import *

intents = discord.Intents.default()
intents.message_content = True

bot: commands.Bot = commands.Bot(
    command_prefix="!",
    description="Relatively simple music bot with some extra features for gaming",
    intents=intents,
    help_command=HelpMessage()
)

@bot.event
async def on_ready() -> None:
    """
    Print a message to the console when the bot is ready

    :return: None
    """
    message = f"Logged in as {bot.user} (ID: {bot.user.id})"
    logging.info(message)
    logging.info("-" * len(message))


@bot.event
async def on_command_error(ctx: commands.Context, error: Exception) -> None:
    """
    Discord event that is triggered when a command error occurs either
    through user input or through an error in the command itself.

    :param ctx: Discord context
    :param error: The error that occurred
    :return:    None
    """
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(embed=command_not_found())
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=missing_argument(error.param.name, ctx.command.name))
    else: # error occurred in the command code
        logging.error(error)
        logging.debug(format_exc())

async def main() -> None:
    """
    Main function to start the bot

    :return: None
    """
    try:
        token = load_token()
        setup_logging(logging.DEBUG, enable_file_logging=True) # TODO: Change to INFO for production
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
