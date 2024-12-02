from os import getenv

from dotenv import load_dotenv


def load_token() -> str:
    """
    Load the discord token from the .env file

    :raises Exception: If the .env file does not exist
    :raises Exception: If the token is not specified in the .env file
    :return: The discord token
    """
    if not load_dotenv():
        raise Exception(
            "Failed to load .env file, please ensure it exists in the root directory of the project."
        )
    token = getenv("DISCORD_TOKEN")
    if not token:
        raise Exception(
            "Failed to load token from .env file, please specify the token in the .env file. as DISCORD_TOKEN"
        )
    return token