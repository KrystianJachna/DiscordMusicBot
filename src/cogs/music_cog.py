import discord
from discord.ext import commands, tasks

from .music.messages import *
from .music.music_service import MusicPlayer
from .music.song_queue import BgDownloadSongQueue
from .music.song_cache import LRUSongsCache
from .music.music_downlaoder import SongDownloader
from config import *

class MusicCog(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self._bot = bot
        self._servers_music_players: dict[int, MusicPlayer] = {}  # guild_id: MusicPlayer
        song_cache = LRUSongsCache(songs_size=CACHE_SIZE)
        self._song_downloader = SongDownloader(song_cache, COOKIES_PATH)
        self.check_music.start()
        self.check_listeners.start()

    @commands.command(description=PLAY_DESCRIPTION)
    async def play(self, ctx: commands.Context, *, search: str) -> None:
        music_player = self._servers_music_players[ctx.guild.id]
        await music_player.play(search, ctx)

    @commands.command(description=SKIP_DESCRIPTION)
    async def skip(self, ctx: commands.Context) -> None:
        music_player = self._servers_music_players[ctx.guild.id]
        try:
            await music_player.skip()
            await ctx.send(embed=skipped(await music_player.queue_length(), music_player.loop))
        except MusicPlayer.NotPlayingException:
            await ctx.send(embed=skip_error())

    @commands.command(description=STOP_DESCRIPTION)
    async def stop(self, ctx: commands.Context) -> None:
        await ctx.send(embed=stopped())
        await self._stop_music_player(ctx.guild.id)

    @commands.command(description=PAUSE_DESCRIPTION)
    async def pause(self, ctx: commands.Context) -> None:
        music_player = self._servers_music_players[ctx.guild.id]
        try:
            await music_player.pause()
            await ctx.send(embed=paused(music_player.now_playing.title, music_player.now_playing.url))
        except MusicPlayer.NotPlayingException:
            await ctx.send(embed=not_playing())

    @commands.command(description=RESUME_DESCRIPTION)
    async def resume(self, ctx: commands.Context) -> None:
        music_player = self._servers_music_players[ctx.guild.id]
        try:
            await music_player.resume()
            await ctx.send(embed=resumed(music_player.now_playing.title, music_player.now_playing.url))
        except MusicPlayer.NotPlayingException:
            await ctx.send(embed=not_playing())

    @commands.command(description=LOOP_DESCRIPTION)
    async def loop(self, ctx: commands.Context) -> None:
        music_player = self._servers_music_players[ctx.guild.id]
        music_player.loop = not music_player.loop
        await ctx.send(embed=looping(music_player.loop))

    @commands.command(description=QUEUE_DESCRIPTION)
    async def queue(self, ctx: commands.Context) -> None:
        music_player = self._servers_music_players[ctx.guild.id]
        now_playing, waiting = await music_player.get_queue_info()
        await ctx.send(embed=queue(now_playing, waiting, music_player.loop))

    @commands.command(description=CLEAR_DESCRIPTION)
    async def clear(self, ctx: commands.Context) -> None:
        music_player = self._servers_music_players[ctx.guild.id]
        await music_player.clear_queue()
        await ctx.send(embed=clear())

    async def _stop_music_player(self, guild_id: int) -> None:
        try:
            music_player = self._servers_music_players[guild_id]
        except KeyError:  # called by on_voice_state_update while executing this command
            return
        await music_player.stop()
        self._servers_music_players.pop(guild_id, None)

    @tasks.loop(seconds=NO_USERS_DISCONNECT_TIMEOUT)
    async def check_listeners(self) -> None:
        for guild_id, music_player in self._servers_music_players.copy().items():
            if not music_player.voice_client.channel.members:
                await self._stop_music_player(guild_id)

    @tasks.loop(seconds=NO_MUSIC_DISCONNECT_TIMEOUT)
    async def check_music(self) -> None:
        for guild_id, music_player in self._servers_music_players.copy().items():
            if not music_player.now_playing and not await music_player.queue_length():
                await self._stop_music_player(guild_id)


    @play.before_invoke
    async def connect_on_command(self, ctx: commands.Context) -> None:
        if ctx.author.voice is None:
            await ctx.send(embed=not_in_voice_channel())
            raise commands.CommandError("User not connected to a voice channel.")
        if ctx.voice_client is None:
            voice_client = await ctx.author.voice.channel.connect()
            self._servers_music_players[ctx.guild.id] = MusicPlayer(voice_client,
                                                                    BgDownloadSongQueue(self._song_downloader))

    @commands.Cog.listener()
    async def on_voice_state_update(self,
                                    member: discord.Member,
                                    before: discord.VoiceState,
                                    after: discord.VoiceState) -> None:
        if member == self._bot.user and after.channel is None:
            await self._stop_music_player(before.channel.guild.id)

    @skip.before_invoke
    @stop.before_invoke
    @pause.before_invoke
    @resume.before_invoke
    @loop.before_invoke
    @clear.before_invoke
    @queue.before_invoke
    async def ensure_bot_on_voice(self, ctx: commands.Context) -> None:
        if ctx.guild.id not in self._servers_music_players:
            await ctx.send(embed=not_connected())
            raise commands.CommandError("Bot not connected to a voice channel.")
