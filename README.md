# Discord Music Bot

This is a simple discord bot that can be mainly used to play music in a voice channel.
It uses the discord.py library and the youtube-dl library to stream music from youtube.

## Features

- Play music in a voice channel
- Control the music flow (pause, resume, skip, stop, loop)
- Display/clear the queue of songs
- Send embed messages to the text channel while interacting with the bot

## How to use

The bot can be easily run using Docker.
Follow the instructions below to set up and start the bot in a container.

## Requirements

- [Docker](https://docs.docker.com/get-docker/)
- [Discord Account](https://discord.com/)
- [Discord Bot Token](https://discord.com/developers/applications)

## Setting up the Token

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Provide a name for the application
4. Bring your bot to life with Icon and Description
5. Retrieve the token from the Bot section

For more information on how to create a bot and get the token, check
the [Discord Developer Documentation](https://discord.com/developers/docs/intro)
or follow this [tutorial](https://realpython.com/how-to-make-a-discord-bot-python/).

## Installation

1. Clone the repository

```bash
git clone <repo-url>
```

2. Navigate to the project directory

```bash
cd DiscordMusicBot
```

3. Build the docker image

```bash
docker build -t discord-music-bot .
```

4. Run the docker container with the token of your discord bot

```bash
docker run -e DISCORD_TOKEN=<your-token> discord-music-bot
```

## Usage

Once the bot is running, you can invite it to your server by using link generated in
the [Discord Developer Portal](https://discord.com/developers/applications).

1. Go to the OAuth2 section
2. Select the bot scope and permissions (in this case you need to select the `bot` scope and the `Administrator`
   permission)
3. Copy the generated link and paste it in your browser
4. Select the server where you want to invite the bot
5. Start using the bot in the server

## Commands

The bot has the following commands:

- `!help`: Display the list of commands and instructions on how to use them
- `!play <song>`: Play a song in the voice channel (you can use the name of the song or the youtube link)
- `!pause`: Pause the current song
- `!resume`: Resume the current song
- `!skip`: Skip the current song
- `!stop`: Stop the music and leave the voice channel
- `!queue`: Display the queue of songs
- `!clear`: Clear the queue of songs
- `!loop`: Toggle the loop mode on/off for whole queue

## Handling Age-Restricted Content on YouTube

To allow the bot to play age-restricted content from YouTube, follow these steps:

1. **Install a browser extension for generating a `cookies.txt` file**  
   For example, you can use [cookies.txt](https://addons.mozilla.org/pl/firefox/addon/cookies-txt/) (available for
   Google Chrome or other Chromium-based browsers).

2. **Log in to your YouTube account** in the browser.

3. **Generate the `cookies.txt` file**:
    - Open YouTube in your browser.
    - Use the installed extension to generate a `cookies.txt` file and save it locally on your system.

4. **Add the `cookies.txt` file to the bot's working directory**.
5.
5. **Restart the bot**

After following these steps, the bot will be able to play YouTube videos with age restrictions.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
