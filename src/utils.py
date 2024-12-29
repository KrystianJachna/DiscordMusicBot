import logging
from os import getenv
from sys import stdout

from dotenv import load_dotenv


def load_token() -> str:
    token = getenv("DISCORD_TOKEN")  # Check if the token is set in the Docker environment

    if not token:  # If the token is not set in the Docker environment, check the .env file
        load_dotenv()
        token = getenv("DISCORD_TOKEN")

    if not token:
        raise Exception("Failed to load token. "
                        "Ensure DISCORD_TOKEN is set in Docker environment or in the .env file.")
    return token


def setup_logging(level: int = logging.INFO, enable_file_logging: bool = False) -> None:
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
