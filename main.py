
from discord.ext import commands
from dotenv import load_dotenv
from os import getenv
import asyncio




async def main():
    TOKEN = getenv("DISCORD_TOKEN")
    print(TOKEN)

asyncio.run(main())
