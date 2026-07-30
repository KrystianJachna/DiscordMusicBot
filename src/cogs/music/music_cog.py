import asyncio
import logging

import discord
from discord.ext import commands, tasks

try:
    from src.cogs.music.messages import *
    from src.cogs.music.music_service import MusicPlayer
    from src.cogs.music.song_queue import BgDownloadSongQueue
    from src.cogs.music.song_cache import LRUSongsCache
    from src.cogs.music.music_downloader import SongDownloader
    from src.config import *
except ModuleNotFoundError:
    from cogs.music.messages import *
    from cogs.music.music_service import MusicPlayer
    from cogs.music.song_queue import BgDownloadSongQueue
    from cogs.music.song_cache import LRUSongsCache
    from cogs.music.music_downloader import SongDownloader
    from config import *
from .song import SongRequest

class MusicCog(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self._bot = bot
        self._servers_music_players: dict[int, MusicPlayer] = {}  # guild_id: MusicPlayer
        self._song_downloader = SongDownloader(LRUSongsCache(CACHE_SIZE, QUERIES_CACHE_SIZE))

        self.monitor_music_player_status.start()
        self.check_listeners.start()

    @commands.command(description=PLAY_DESCRIPTION)
    async def play(self, ctx: commands.Context, *, search: str) -> None:
        music_player = self._servers_music_players[ctx.guild.id]
        song_request = SongRequest(search, ctx)
        await music_player.play(song_request)

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

    @commands.command(description=SHUFFLE_DESCRIPTION)
    async def shuffle(self, ctx: commands.Context) -> None:
        music_player = self._servers_music_players[ctx.guild.id]
        await music_player.shuffle()
        await ctx.send(embed=shuffled())

    @commands.command(description="Pokaż aktualnie odtwarzany utwór.\n**Użycie**: `!nowplaying`")
    async def nowplaying(self, ctx: commands.Context) -> None:
        music_player = self._servers_music_players[ctx.guild.id]
        if not music_player.now_playing:
            await ctx.send(embed=not_playing())
            return
        await ctx.send(embed=now_playing(music_player.now_playing, music_player.volume))

    @commands.command(description="Usuń utwór z kolejki po numerze.\n**Użycie**: `!remove <numer>`")
    async def remove(self, ctx: commands.Context, position: int) -> None:
        music_player = self._servers_music_players[ctx.guild.id]
        try:
            title = await music_player.remove(position)
        except (IndexError, ValueError):
            await ctx.send(embed=invalid_queue_position())
            return
        await ctx.send(embed=removed_from_queue(title))

    @commands.command(description="Ustaw głośność od 0 do 200 procent.\n**Użycie**: `!volume <0-200>`")
    async def volume(self, ctx: commands.Context, value: int) -> None:
        if not 0 <= value <= 200:
            await ctx.send(embed=invalid_volume())
            return
        music_player = self._servers_music_players[ctx.guild.id]
        await music_player.set_volume(value / 100)
        await ctx.send(embed=volume_changed(value))

    async def _stop_music_player(self, guild_id: int) -> None:
        music_player = self._servers_music_players.pop(guild_id, None)
        if music_player is None:  # also called by on_voice_state_update during disconnect
            return
        await music_player.stop()

    @staticmethod
    async def _is_on_same_channel(ctx: commands.Context) -> None:
        if not ctx.author.voice or not ctx.voice_client or ctx.author.voice.channel != ctx.voice_client.channel:
            channel_name = getattr(getattr(ctx.voice_client, "channel", None), "name", "kanałem bota")
            await ctx.send(embed=not_in_same_voice_channel(channel_name))
            raise commands.CommandError("User not in the same channel as the bot.")

    @commands.Cog.listener()
    async def on_voice_state_update(self,
                                    member: discord.Member,
                                    before: discord.VoiceState,
                                    after: discord.VoiceState) -> None:
        if member == self._bot.user and after.channel is None and before.channel:
            await self._stop_music_player(before.channel.guild.id)

    @tasks.loop(seconds=NO_USERS_DISCONNECT_TIMEOUT)
    async def check_listeners(self) -> None:
        for guild_id, music_player in self._servers_music_players.copy().items():
            if not any(not member.bot for member in music_player.voice_client.channel.members):
                await self._stop_music_player(guild_id)

    @tasks.loop(seconds=NO_MUSIC_DISCONNECT_TIMEOUT)
    async def monitor_music_player_status(self) -> None:
        for guild_id, music_player in self._servers_music_players.copy().items():
            if not music_player.now_playing and not await music_player.queue_length():
                await self._stop_music_player(guild_id)

    @play.before_invoke
    async def connect_on_command(self, ctx: commands.Context) -> None:
        if ctx.author.voice is None:
            await ctx.send(embed=not_in_voice_channel())
            raise commands.CommandError("User not connected to a voice channel.")
        if ctx.voice_client is None:
            voice_client = None
            last_error = None
            for attempt in range(1, 4):
                try:
                    if ctx.voice_client:
                        await ctx.voice_client.disconnect(force=True)
                    voice_client = await ctx.author.voice.channel.connect(reconnect=False)
                    break
                except (discord.ClientException, asyncio.TimeoutError, discord.ConnectionClosed) as error:
                    last_error = error
                    logging.warning(
                        "Voice connection attempt %d/3 failed: %s", attempt, error
                    )
                    if ctx.voice_client:
                        await ctx.voice_client.disconnect(force=True)
                    if attempt < 3:
                        await asyncio.sleep(attempt)

            if voice_client is None:
                logging.error("Voice connection failed after 3 attempts", exc_info=last_error)
                error_embed = (
                    voice_e2ee_error()
                    if getattr(last_error, "code", None) == 4017
                    else voice_connection_error()
                )
                await ctx.send(embed=error_embed)
                raise commands.CommandError("Voice connection failed") from last_error
            self._servers_music_players[ctx.guild.id] = MusicPlayer(voice_client,
                                                                    BgDownloadSongQueue(self._song_downloader))
        await self._is_on_same_channel(ctx)

    @skip.before_invoke
    @stop.before_invoke
    @pause.before_invoke
    @resume.before_invoke
    @loop.before_invoke
    @clear.before_invoke
    @queue.before_invoke
    @nowplaying.before_invoke
    @remove.before_invoke
    @volume.before_invoke
    async def ensure_bot_on_voice(self, ctx: commands.Context) -> None:
        if ctx.guild.id not in self._servers_music_players:
            await ctx.send(embed=not_connected())
            raise commands.CommandError("Bot not connected to a voice channel.")
        await self._is_on_same_channel(ctx)
