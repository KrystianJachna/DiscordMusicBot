# Discord bot

This is a simple discord bot that can be mainly used to play music in a voice channel. 
It uses the discord.py library and the youtube-dl library to play downloaded music from youtube.

## Features

- Play music in a voice channel
- Control the music with commands like play, pause, resume, skip, stop, queue, loop, etc.
- TODO: Add more features e.g. team management, etc.

## How to use

1. Clone the repository
2. Change directory to the repository
3. Install the required libraries using `pip install -r requirements.txt`
4. Visit the [Discord Developer Portal](https://discord.com/developers/applications) and create a new application,
    then create a bot for the application and copy the bot token. For more information, visit the [Discord Developer Portal](https://discord.com/developers/docs/intro)
5. Create a `.env` file in the root directory of the repository and add the following:
```
DISCORD_TOKEN='<your-discord-bot-token>'
```
6. Run the bot using `python main.py`

## Requirements

- Python 3.8 or higher
- FFmpeg
- rest of the requirements are in the `requirements.txt` file

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

TODO: Add more information, info about cookies, etc.

```