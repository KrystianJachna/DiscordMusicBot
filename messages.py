from discord import Embed, Color
from discord.ext import commands


def command_not_found() -> Embed:
    return Embed(title="Command Not Found 🤷‍♂️",
                 color=0xFF6900)


def missing_argument(arg: str, command: str) -> Embed:
    return Embed(title=f"Missing Argument 🤷‍♂️",
                 description=f"Usage: `!{command} {arg}`\nType `!help {command}` for more information",
                 color=0xFF0000)


class HelpMessage(commands.HelpCommand):
    """
    Custom help command for the bot
    """

    def __init__(self):
        super().__init__()

    async def send_bot_help(self, mapping: dict) -> None:
        """
        Send the help message for the bot

        :param mapping: The mapping of commands
        :return: None
        """
        desc = """
        This bot is a relatively simple music bot with some extra features for gaming.
        
        To get started, use the `!help` command to see the list of available commands.
        You can also use `!help <command>` to get more information about a specific command. E.g. `!help play`
        In order to get more information about a specific Cog, use `!help <cog>`. E.g. `!help MusicCog`
        
        The available commands are:
        """
        embed = Embed(title="Help 🆘", description=desc, color=Color.blue())
        for cog, commands in mapping.items():
            command_list = [command.name for command in commands]
            if command_list:
                embed.add_field(name=cog.qualified_name if cog else "No Category",
                                value="- !" + "\n - !".join(command_list),
                                inline=False)
        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_command_help(self, command: commands.Command) -> None:
        """
        Send the help message for a specific command

        :param command: The command to send the help message for
        :return: None
        """
        embed = Embed(title="!" + command.name, description=command.description or "No description",
                      color=Color.blue())
        if command.aliases:
            embed.add_field(name="Aliases", value=", ".join(command.aliases), inline=False)
        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_cog_help(self, cog: commands.Cog) -> None:
        """
        Send the help message for a specific cog

        :param cog: The cog to send the help message for
        :return: None
        """
        embed = Embed(title=cog.qualified_name,
                      color=Color.blue())
        for command in cog.get_commands():
            embed.add_field(name="!" + command.name, value=command.description or "No description", inline=False)
        channel = self.get_destination()
        await channel.send(embed=embed)
