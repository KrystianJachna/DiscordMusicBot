from discord import Embed
from discord.ext.commands import HelpCommand, Command, Cog


class HelpMessage(HelpCommand):

    def __init__(self, color: int = 0x89CFF0):
        super().__init__()
        self.color = color

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

        embed = Embed(description=desc, color=self.color)
        for cog, commands in mapping.items():
            command_list = [command.name for command in commands]
            if command_list:
                embed.add_field(name=cog.qualified_name if cog else "No Category",
                                value="- !" + "\n - !".join(command_list),
                                inline=True)
        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_command_help(self, command: Command) -> None:
        embed = Embed(title="!" + command.name, description=command.description or "No description",
                      color=self.color)
        if command.aliases:
            embed.add_field(name="Aliases", value=", ".join(command.aliases), inline=False)
        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_cog_help(self, cog: Cog) -> None:
        embed = Embed(title=cog.qualified_name,
                      color=self.color)
        for command in cog.get_commands():
            embed.add_field(name="!" + command.name, value=command.description or "No description", inline=False)
        channel = self.get_destination()
        await channel.send(embed=embed)

    async def command_not_found(self, string: str, /) -> str:
        channel = self.get_destination()
        await channel.send(
            embed=Embed(title=f"Command: `{string}` not found", color=self.color))
        return ""
