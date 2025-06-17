import discord
from discord.ext import commands, tasks

from cogs.music.messages import *
from cogs.music.music_service import MusicPlayer
from cogs.music.song_queue import BgDownloadSongQueue
from cogs.music.song_cache import LRUSongsCache
from cogs.music.music_downloader import YouTubeSongInfoProvider, DownloaderException
from .music_database import FileStorageManager, PlaylistQuery, PlaylistDBError, PlaylistStorageManager
from config import *
from .song import SongRequest


class MusicCog(commands.Cog):

    def __init__(
        self,
        bot: commands.Bot,
        storage_manager: FileStorageManager,
        playlist_storage_manager: PlaylistStorageManager,
    ) -> None:
        self._bot = bot
        self._servers_music_players: dict[int, MusicPlayer] = (
            {}
        )  # guild_id: MusicPlayer
        self._song_downloader = YouTubeSongInfoProvider(
            LRUSongsCache(CACHE_SIZE, QUERIES_CACHE_SIZE), storage_manager
        )
        self.storage_manager = storage_manager
        self.playlist_storage_manager = playlist_storage_manager

        self.monitor_music_player_status.start()
        self.check_listeners.start()

    @commands.command(description=PLAY_DESCRIPTION)
    async def play(self, ctx: commands.Context, *, search: str) -> None:
        music_player = self._servers_music_players[ctx.guild.id]
        song_request = SongRequest(search, ctx)
        await music_player.play(song_request)

    @commands.command(description=CREATE_PLAYLIST_DESCRIPTION)
    async def create_playlist(self, ctx: commands.Context, *, name: str) -> None:
        music_player = self._servers_music_players[ctx.guild.id]
        now_playing, queries = await music_player.get_queue_info()

        urls, invalid_queries = [now_playing.url] if now_playing else [], []

        for query in queries:
            try:
                url = await self._song_downloader.get_url(query)
                urls.append(url)
            except DownloaderException:
                invalid_queries.append(query)
        logging.info(
            f"Creating playlist '{name}' for user {ctx.author.id} in guild {ctx.guild.id}. Valid URLs: {urls}, Invalid queries: {invalid_queries}"
        )

        try:
            await self.playlist_storage_manager.add_playlist(
                PlaylistQuery(ctx.author.id, name, urls)
            )
        except PlaylistDBError as e:
            await ctx.send(embed=e.embed())
        await ctx.send(embed=playlist_created(name, urls, invalid_queries))

    @commands.command(description="...")  # TODO: Add description
    async def playlist(self, ctx: commands.Context, *, name: str) -> None:
        print("kurwy")
        logging.info(
            f"Loading playlist '{name}' for user {ctx.author.id} in guild {ctx.guild.id}."
        )
        music_player = self._servers_music_players[ctx.guild.id]
        try:
            playlist = await self.storage_manager.get_playlist(str(ctx.author.id), name)
        except PlaylistDBError as e:
            await ctx.send(embed=e.embed(name))
            return
        except Exception as e:
            import traceback

            logging.error(
                f"Unexpected error in playlist command: {e}\n{traceback.format_exc()}"
            )
            await ctx.send("An unexpected error occurred while loading the playlist.")
            return
        for url in playlist.song_urls:
            song_request = SongRequest(url, ctx, quiet=True)
            await music_player.play(song_request)
        await ctx.send(embed=playlist_loaded(playlist.name, len(playlist.song_urls)))

    @commands.command(description=SKIP_DESCRIPTION)
    async def skip(self, ctx: commands.Context) -> None:
        music_player = self._servers_music_players[ctx.guild.id]
        try:
            await music_player.skip()
            await ctx.send(
                embed=skipped(await music_player.queue_length(), music_player.loop)
            )
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
            await ctx.send(
                embed=paused(
                    music_player.now_playing.title, music_player.now_playing.url
                )
            )
        except MusicPlayer.NotPlayingException:
            await ctx.send(embed=not_playing())

    @commands.command(description=RESUME_DESCRIPTION)
    async def resume(self, ctx: commands.Context) -> None:
        music_player = self._servers_music_players[ctx.guild.id]
        try:
            await music_player.resume()
            await ctx.send(
                embed=resumed(
                    music_player.now_playing.title, music_player.now_playing.url
                )
            )
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

    async def _stop_music_player(self, guild_id: int) -> None:
        try:
            music_player = self._servers_music_players[guild_id]
        except KeyError:  # called by on_voice_state_update while executing this command
            return
        await music_player.stop()
        self._servers_music_players.pop(guild_id, None)

    @staticmethod
    async def _is_on_same_channel(ctx: commands.Context) -> None:
        if ctx.author.voice.channel != ctx.voice_client.channel:
            await ctx.send(
                embed=not_in_same_voice_channel(ctx.author.voice.channel.name)
            )
            raise commands.CommandError("User not in the same channel as the bot.")

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if member == self._bot.user and after.channel is None:
            await self._stop_music_player(before.channel.guild.id)

    @tasks.loop(seconds=NO_USERS_DISCONNECT_TIMEOUT)
    async def check_listeners(self) -> None:
        for guild_id, music_player in self._servers_music_players.copy().items():
            if not music_player.voice_client.channel.members:
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
            voice_client = await ctx.author.voice.channel.connect()
            self._servers_music_players[ctx.guild.id] = MusicPlayer(
                voice_client, BgDownloadSongQueue(self._song_downloader)
            )
        await self._is_on_same_channel(ctx)

    @skip.before_invoke
    @stop.before_invoke
    @pause.before_invoke
    @resume.before_invoke
    @loop.before_invoke
    @clear.before_invoke
    @queue.before_invoke
    @shuffle.before_invoke
    @create_playlist.before_invoke
    @playlist.before_invoke
    async def ensure_bot_on_voice(self, ctx: commands.Context) -> None:
        if ctx.guild.id not in self._servers_music_players:
            await ctx.send(embed=not_connected())
            raise commands.CommandError("Bot not connected to a voice channel.")
        await self._is_on_same_channel(ctx)
