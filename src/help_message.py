from discord import Embed
from discord.ext import commands
from config import INFO_COLOR


class HelpMessage(commands.HelpCommand):

    def __init__(self):
        super().__init__()

    async def send_bot_help(self, mapping: dict) -> None:
        desc = """
        **Welcome to the help menu!** 
         
        Here you can find a list of all available commands and cogs.

        - You can also use `!help <command>` to get more information about a specific command.  
          *e.g.* `!help play`

        - In order to get more information about a specific Cog, use `!help <cog>`.  
          *e.g.* `!help MusicCog`

        **The available commands are:**
        """

        embed = Embed(description=desc, color=INFO_COLOR)
        for cog, _commands in mapping.items():
            command_list = [command.name for command in _commands]
            if command_list:
                embed.add_field(name=cog.qualified_name if cog else "No Category",
                                value="- !" + "\n - !".join(command_list),
                                inline=True)
        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_command_help(self, command: commands.Command) -> None:
        embed = Embed(title="!" + command.name, description=command.description or "No description",
                      color=INFO_COLOR)
        if command.aliases:
            embed.add_field(name="Aliases", value=", ".join(command.aliases), inline=False)
        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_cog_help(self, cog: commands.Cog) -> None:
        embed = Embed(title=cog.qualified_name,
                      color=INFO_COLOR)
        for command in cog.get_commands():
            embed.add_field(name="!" + command.name, value=command.description or "No description", inline=False)
        channel = self.get_destination()
        await channel.send(embed=embed)

    async def command_not_found(self, string: str, /) -> str:
        channel = self.get_destination()
        await channel.send(
            embed=Embed(title=f"Command: `{string}` not found", color=INFO_COLOR))
        return ""
