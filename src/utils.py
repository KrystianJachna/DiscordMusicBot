
import logging
from os import getenv
from sys import stdout

from dotenv import load_dotenv


def load_token() -> str:
    """
    Load the discord token either from the environment variables (e.g., in Docker)
    or from the .env file (e.g., locally).

    :raises Exception: If neither environment variable nor .env file provides the token
    :return: The discord token
    """
    token = getenv("DISCORD_TOKEN")

    if not token:
        load_dotenv()
        token = getenv("DISCORD_TOKEN")

    if not token:
        raise Exception(
            "Failed to load token. Ensure DISCORD_TOKEN is set in Docker environment or in the .env file."
        )
    return token


def setup_logging(level: int = logging.INFO, enable_file_logging: bool = False) -> None:
    """
    Setup logging for the bot. The logs will be written to stdout and optionally to a file.

    :param level: The logging level to use
    :param enable_file_logging: If the logs should be written to a file
    :return: None
    """
    logger = logging.getLogger()
    logger.setLevel(level)
    formatter = logging.Formatter("%(asctime)-15s - %(name)-25s - %(levelname)-5s - %(message)s")

    console_handler = logging.StreamHandler(stream=stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    logger.addHandler(console_handler)

    if enable_file_logging:
        file_handler = logging.FileHandler("bot.log", mode="w")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)
