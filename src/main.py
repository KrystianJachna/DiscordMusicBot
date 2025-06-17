import asyncio

import discord
from discord.ext import commands
import logging

from utils import load_token, setup_logging
from cogs.music.music_cog import MusicCog
from help_message import HelpMessage
from config import DAEMON_INTERVAL, ERROR_COLOR, DEFAULT_BUCKET_NAME, mongo_client, minio_client
from cogs.music.music_database import DatabaseDaemon, FileStorageManager

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
        await ctx.send(embed=discord.Embed(title="🤔 Oops! You’re missing something!",
                                           description=f"Type `!help {ctx.command.name}` for more information",
                                           color=ERROR_COLOR))
    else:
        logging.error(f"Error occurred in command: {ctx.command}", exc_info=True)


async def create_file_storage_manager(bucket_name=DEFAULT_BUCKET_NAME, create_bucket=True) -> FileStorageManager | None:
    if mongo_client is None or minio_client is None:
        logging.error("Cannot create FileStorageManager: MongoDB or MinIO client is not available")
        return None

    try:
        storage_manager = await FileStorageManager.create_async(
            mongo_db_client=mongo_client,
            minio_client=minio_client,
            bucket_name=bucket_name,
            create_bucket=create_bucket
        )
        logging.info(f"FileStorageManager created successfully with bucket: {bucket_name}")
        return storage_manager
    except Exception as e:
        logging.error(f"Failed to create FileStorageManager: {str(e)}")
        return None


async def main() -> None:
    try:
        storage_manager = await create_file_storage_manager()
        daemon = DatabaseDaemon(storage_manager, DAEMON_INTERVAL)
        await daemon.start()
        token = load_token()
        setup_logging(logging.INFO, enable_file_logging=True)
        async with bot:
            await bot.add_cog(MusicCog(bot, storage_manager))
            await bot.start(token)
    except discord.LoginFailure:
        logging.error("Failed to log in. Ensure the token is correct.")
    except Exception as e:
        logging.error(e, exc_info=True)


if __name__ == '__main__':
    asyncio.run(main())
