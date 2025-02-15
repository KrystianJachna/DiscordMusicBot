
# Discord Music Bot

A simple Discord bot for playing music in a voice channel using the `discord.py` and `youtube-dl` libraries.

---

## Features

- Play music in a voice channel
- Control the music flow (pause, resume, skip, stop, loop)
- Display/clear the queue of songs
- Send embed messages to the text channel while interacting with the bot

## How to use

The bot can be easily run using Docker. Follow the instructions below to set up and start the bot in a container.

---

## Requirements

- [Docker](https://docs.docker.com/get-docker/)
- [Discord Account](https://discord.com/)
- [Discord Bot Token](https://discord.com/developers/applications)

---

## Setting up the Discord Bot Token

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Provide a name for the application
4. Bring your bot to life with Icon and Description
5. Retrieve the token from the Bot section

For more information on how to create a bot and get the token, check
the [Discord Developer Documentation](https://discord.com/developers/docs/intro)
or follow this [tutorial](https://realpython.com/how-to-make-a-discord-bot-python/).

---

## Installation

### Steps:

1. Clone the repository

```bash
git clone <repo-url>
```

2. Navigate to the downloaded project directory:

```bash
cd DiscordMusicBot
```

3. Build the Docker image:

```bash
docker build -t discord-music-bot .
```

4. Run the Docker container. Provide your Discord bot token as an environment variable:

```bash
docker run -e DISCORD_TOKEN=<your token> discord-music-bot
```

* Optionally, you can mount the `bot.log` file to the host system to keep track of the bot's activity:

```bash
docker run -e DISCORD_TOKEN=<your token> -v $(pwd)/bot.log:/app/bot.log discord-music-bot
```

---

## Usage

Once the bot is running, invite it to your server using the link generated in the
[Discord Developer Portal](https://discord.com/developers/applications):

1. Open the **OAuth2** section.
2. Select the `bot` scope and set the required permissions (e.g., `Administrator`).
3. Copy the generated link and open it in your browser.
4. Choose the server to which you want to add the bot.
5. Start interacting with the bot in your server!

---

## Commands

Here are the available commands:

- **General Commands**:
    - `!help`: Display the list of commands and instructions on how to use them.

- **Music Playback**:
    - `!play <song>`: Play a song in the voice channel (use the name or YouTube link).
    - `!pause`: Pause the current song.
    - `!resume`: Resume the current song.
    - `!skip`: Skip the current song.
    - `!stop`: Stop the music and leave the voice channel.

- **Queue Management**:
    - `!queue`: Display the current queue of songs.
    - `!clear`: Clear the queue of songs.

- **Other**:
    - `!loop`: Toggle the loop mode for the entire queue (on/off).

---

## Handling Age-Restricted YouTube Content

To allow the bot to play age-restricted YouTube content, follow these steps:

1. **Install a browser extension for generating a `cookies.txt` file**  
   For example, you can use [cookies.txt](https://addons.mozilla.org/pl/firefox/addon/cookies-txt/) (available for
   Google Chrome or other Chromium-based browsers).

2. **Log in to your YouTube account** in the browser.

3. **Generate the `cookies.txt` file**:
    - Open YouTube in your browser.
    - Use the installed extension to generate a `cookies.txt` file and save it locally on your system.

4. **Place the `cookies.txt` file in the bot's working directory**.

5. **Restart the bot**.

After following these steps, the bot will be able to play YouTube videos with age restrictions.

---

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for more details.
