
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
    # Try to get the token directly from environment variables (Docker scenario)
    token = getenv("DISCORD_TOKEN")

    # If not found, fallback to loading .env file for local development
    if not token:
        load_dotenv()  # Attempt to load .env file
        token = getenv("DISCORD_TOKEN")

    # Raise an exception if the token is still not found
    if not token:
        raise Exception(
            "Failed to load token. Ensure DISCORD_TOKEN is set in Docker environment or in the .env file."
        )
    return token


def setup_logging(level: int = logging.INFO) -> None:
    """
    Setup logging for the bot

    :param level: The logging level to use
    :return: None
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)-15s - %(name)-25s - %(levelname)-5s - %(message)s",
        stream=stdout
    )
