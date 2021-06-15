import math
import random
import typing
import asyncio
import discord
import functools
import itertools
import youtube_dl

from datetime import datetime
from discord.ext import commands, menus

from settings import constants
from utilities import checks
from utilities import decorators
from utilities import pagination

# Silence useless bug reports messages
youtube_dl.utils.bug_reports_message = lambda: ""


class VoiceError(Exception):
    pass


class YTDLError(Exception):
    pass


class YTDLSource(discord.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        "format": "bestaudio/best",
        "extractaudio": True,
        "audioformat": "mp3",
        "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
        "restrictfilenames": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "ignoreerrors": False,
        "logtostderr": False,
        "quiet": True,
        "no_warnings": True,
        "default_search": "ytsearch",
        "source_address": "0.0.0.0",
    }
    FFMPEG_OPTIONS = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": f"-vn",
    }

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(
        self, ctx, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 0.5
    ):
        super().__init__(source, volume)

        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data

        self.uploader = data.get("uploader")
        self.uploader_url = data.get("uploader_url")
        date = data.get("upload_date")
        self.upload_date = date[6:8] + "." + date[4:6] + "." + date[0:4]
        self.title = data.get("title")
        self.thumbnail = data.get("thumbnail")
        self.description = data.get("description")
        self.raw_duration = data.get("duration")
        self.duration = self.parse_duration(int(data.get("duration")))
        self.tags = data.get("tags")
        self.url = data.get("webpage_url")
        self.views = data.get("view_count")
        self.likes = data.get("like_count")
        self.dislikes = data.get("dislike_count")
        self.stream_url = data.get("url")

    def __str__(self):
        return "**{0.title}** by **{0.uploader}**".format(self)

    @classmethod
    async def create_source(
        cls, ctx, search: str, *, loop: asyncio.BaseEventLoop = None
    ):
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(
            cls.ytdl.extract_info, search, download=False, process=False
        )
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError("Couldn't find anything that matches `{}`".format(search))

        if "entries" not in data:
            process_info = data
        else:
            process_info = None
            for entry in data["entries"]:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError(
                    "Couldn't find anything that matches `{}`".format(search)
                )

        webpage_url = process_info["webpage_url"]
        partial = functools.partial(cls.ytdl.extract_info, webpage_url, download=False)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError("Couldn't fetch `{}`".format(webpage_url))

        if "entries" not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info["entries"].pop(0)
                except IndexError:
                    raise YTDLError(
                        "Couldn't retrieve any matches for `{}`".format(webpage_url)
                    )

        return cls(
            ctx, discord.FFmpegPCMAudio(info["url"], **cls.FFMPEG_OPTIONS), data=info
        )

    @classmethod
    async def search_source(
        self, ctx, search: str, *, loop: asyncio.BaseEventLoop = None, bot
    ):
        robot = ctx.guild.me
        self.bot = bot
        channel = ctx.channel
        loop = loop or asyncio.get_event_loop()

        self.search_query = "%s%s:%s" % ("ytsearch", 10, "".join(search))

        partial = functools.partial(
            self.ytdl.extract_info, self.search_query, download=False, process=False
        )
        info = await loop.run_in_executor(None, partial)

        # self.search = {}
        # self.search["title"] = f'Search results for:\n**{search}**'
        # self.search["type"] = 'rich'
        # self.search["color"] = int(str(robot.color).replace("#",""))
        # self.search["author"] = {'name': f'{ctx.author.name}', 'url': f'{ctx.author.avatar_url}',
        #                         'icon_url': f'{ctx.author.avatar_url}'}

        lst = []
        count = 0
        e_list = []
        for e in info["entries"]:
            # lst.append(f'`{info["entries"].index(e) + 1}.` {e.get("title")} **[{YTDLSource.parse_duration(int(e.get("duration")))}]**\n')
            VId = e.get("id")
            VUrl = "https://www.youtube.com/watch?v=%s" % (VId)
            lst.append(f'`{count + 1}.` [{e.get("title")}]({VUrl})\n')
            count += 1
            e_list.append(e)

        lst.append("\n**Type a number to make a choice, Type `cancel` to exit**")
        # self.search["description"] = "\n".join(lst)

        embed = discord.Embed(
            title=f"Search results for:\n**{search}**",
            description="\n".join(lst),
            color=robot.color,
            timestamp=datetime.utcnow(),
        )
        embed.set_author(
            name=f"{ctx.author.name}",
            url=f"{ctx.author.avatar_url}",
            icon_url=f"{ctx.author.avatar_url}",
        )

        # em = discord.Embed.from_dict(self.search)
        await ctx.send(embed=embed, delete_after=45.0)

        def check(msg):
            return (
                msg.content.isdigit() == True
                and msg.channel == channel
                or msg.content == "cancel"
                or msg.content == "Cancel"
            )

        try:
            m = await self.bot.wait_for("message", check=check, timeout=45.0)

        except asyncio.TimeoutError:
            rtrn = "timeout"

        else:
            if m.content.isdigit() == True:
                sel = int(m.content)
                if 0 < sel <= 10:
                    for key, value in info.items():
                        if key == "entries":
                            """data = value[sel - 1]"""
                            VId = e_list[sel - 1]["id"]
                            VUrl = "https://www.youtube.com/watch?v=%s" % (VId)
                            partial = functools.partial(
                                self.ytdl.extract_info, VUrl, download=False
                            )
                            data = await loop.run_in_executor(None, partial)
                    rtrn = self(
                        ctx,
                        discord.FFmpegPCMAudio(data["url"], **self.FFMPEG_OPTIONS),
                        data=data,
                    )
                else:
                    rtrn = "sel_invalid"
            elif m.content == "cancel":
                rtrn = "cancel"
            else:
                rtrn = "sel_invalid"

        return rtrn

    @staticmethod
    def parse_duration(duration: int):
        if duration > 0:
            minutes, seconds = divmod(duration, 60)
            hours, minutes = divmod(minutes, 60)
            days, hours = divmod(hours, 24)

            duration = []
            if days > 0:
                duration.append("{}".format(days))
            if hours > 0:
                duration.append("{}".format(hours))
            if minutes > 0:
                duration.append("{}".format(minutes))
            if seconds > 0:
                duration.append("{}".format(seconds))

            value = ":".join(duration)

        elif duration == 0:
            value = "LIVE"

        return value


class Song:
    __slots__ = ("source", "requester")

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    def create_embed(self):
        embed = (
            discord.Embed(
                title="Now playing",
                description=f"```fix\n{self.source.title}\n```",
                color=constants.embed,
            )
            .add_field(name="Duration", value=self.source.duration)
            .add_field(name="Requested by", value=self.requester.mention)
            .add_field(
                name="Uploader",
                value=f"[{self.source.uploader}]({self.source.uploader_url})",
            )
            .add_field(name="URL", value=f"[Click]({self.source.url})")
            .add_field(
                name="Likes", value=f'{constants.emotes["like"]} {self.source.likes:,}'
            )
            .add_field(
                name="Dislikes",
                value=f'{constants.emotes["dislike"]} {self.source.dislikes:,}',
            )
            .set_thumbnail(url=self.source.thumbnail)
            .set_author(name=self.requester.name, icon_url=self.requester.avatar_url)
        )
        return embed


class SongQueue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]


class VoiceState:
    def __init__(self, bot, ctx):
        self.bot = bot
        self._ctx = ctx

        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()
        self.exists = True

        self._loop = False
        self._volume = 0.5
        self.skip_votes = set()

        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def is_playing(self):
        return self.voice and self.current

    async def audio_player_task(self):
        while True:
            self.next.clear()
            self.now = None

            if self.voice is None:
                await Music(self.bot).get_voice_client(self._ctx)

            if self.loop is False:
                # Try to get the next song within 3 minutes.
                # If no song will be added to the queue in time,
                # the player will disconnect due to performance
                # reasons.
                try:
                    self.current = await self.songs.get()
                except Exception as e:
                    raise e
                # except asyncio.TimeoutError:
                #     self.bot.loop.create_task(self.stop())
                #     self.exists = False
                #     return

                self.current.source.volume = self._volume

                self.voice.play(self.current.source, after=self.play_next_song)
                await self.current.source.channel.send(
                    embed=self.current.create_embed()
                )

            # If the song is looped
            elif self.loop == True:
                self.now = discord.FFmpegPCMAudio(
                    self.current.source.stream_url, **YTDLSource.FFMPEG_OPTIONS
                )
                self.voice.play(self.now, after=self.play_next_song)

            await self.next.wait()

    def play_next_song(self, error=None):
        if error:
            raise error

        self.next.set()

    def skip(self):
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.songs.clear()

        if self.voice:
            await self.voice.disconnect()
            self.voice = None


def setup(bot):
    bot.add_cog(Music(bot))


class Music(commands.Cog):
    """
    Module for playing music
    """

    def __init__(self, bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, ctx):
        state = self.voice_states.get(ctx.guild.id)
        if not state or not state.exists:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    async def get_voice_client(self, ctx):
        if hasattr(ctx.guild.me.voice, "channel"):
            channel = ctx.guild.me.voice.channel
            await ctx.guild.voice_client.disconnect(force=True)
            ctx.voice_state.voice = await channel.connect()

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    async def cog_check(self, ctx):
        if not ctx.guild:
            return
        if ctx.guild.id in self.bot.home_guilds:
            return True

    async def cog_before_invoke(self, ctx):
        ctx.voice_state = self.get_voice_state(ctx)

    @decorators.command(
        name="connect",
        aliases=["join"],
        brief="Joins a voice or stage channel.",
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    async def _connect(
        self,
        ctx,
        *,
        channel: typing.Union[discord.VoiceChannel, discord.StageChannel] = None,
    ):
        """
        Usage: {0}connect [channel]
        Alias: {0}join
        Output:
            Joins a specified channel
        Notes:
            If you do not specify a channel,
            the bot will join your current
            channel. (If possible)
        """
        if channel is None:
            if not hasattr(ctx.author.voice, "channel"):
                return await ctx.usage()
            else:
                channel = ctx.author.voice.channel
        try:
            ctx.voice_state.voice = await channel.connect(timeout=None)
        except discord.ClientException:
            if hasattr(ctx.guild.me.voice, "channel"):
                if ctx.guild.me.voice.channel == channel:
                    return await ctx.fail(f"Already in channel {channel.mention}")
                else:
                    await ctx.guild.voice_client.disconnect(force=True)
                    ctx.voice_state.voice = await channel.connect(timeout=None)
            else:
                await ctx.guild.voice_client.disconnect(force=True)
                ctx.voice_state.voice = await channel.connect(timeout=None)
        await ctx.success(f"Connected to {channel.mention}")

    @decorators.command(
        name="disconnect",
        aliases=["dc"],
        brief="Disconnects from the voice or stage channel.",
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    async def _disconnect(self, ctx):
        """
        Usage: {0}disconnect
        Alias: {0}dc
        Output:
            Clears the queue and leaves the voice channel.
        """
        if hasattr(ctx.guild.me.voice, "channel"):
            channel = ctx.guild.me.voice.channel
            await ctx.guild.voice_client.disconnect(force=True)
            await ctx.message.add_reaction(self.bot.emote_dict["wave"])
            await ctx.success(f"Disconnected from {channel.mention}")
        else:
            if not ctx.voice_state.voice:
                return await ctx.fail("Not connected to any voice channel.")
        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]

    @decorators.command(
        name="volume",
        brief="Set the volume of the player.",
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    @checks.has_perms(manage_guild=True)
    async def _volume(self, ctx, volume: int):
        """Sets the volume of the player for the current song."""
        if not ctx.voice_state.is_playing:
            return await ctx.fail("Nothing is currently being played.")

        if volume < 0 or volume > 100:
            return await ctx.fail("Volume percentage must be between 0 and 100")

        ctx.voice_state.current.source.volume = volume / 100
        await ctx.send_or_reply(
            f"{self.bot.emote_dict['volume']} Volume of the player set to {volume}%"
        )

    @decorators.command(
        name="current",
        brief="Displays the currently playing song.",
        aliases=["now", "np"],
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    async def _current(self, ctx):
        """
        Usage: {0}now
        Aliases: {0}now {0}np
        Output: Displays the currently playing song.
        """
        if not ctx.voice_state.is_playing:
            return await ctx.fail("Nothing is currently being played.")
        embed = ctx.voice_state.current.create_embed()
        await ctx.send(embed=embed)

    @decorators.command(
        name="pause",
        brief="Pauses the currently playing song.",
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    async def _pause(self, ctx):
        """
        Usage: {0}pause
        Output: Pauses the currently playing song.
        """
        if not ctx.voice_state.is_playing:
            return await ctx.fail("Nothing is currently being played.")

        if ctx.voice_state.voice.is_paused():
            return await ctx.fail("The player is already paused.")

        ctx.voice_state.voice.pause()
        await ctx.message.add_reaction(self.bot.emote_dict["pause"])

    @decorators.command(
        name="resume",
        brief="Resumes a currently paused song.",
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    async def _resume(self, ctx):
        """
        Usage: {0}resume
        Output:
            Resumes a currently paused song.
        """
        if not ctx.voice_state.is_playing:
            return await ctx.fail("Nothing is currently being played.")

        if ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            await ctx.message.add_reaction(self.bot.emote_dict["play"])

        else:
            return await ctx.fail("The player is not paused.")

    @decorators.command(
        name="stop",
        brief="Stops playing song and clears the queue.",
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    async def _stop(self, ctx):
        """
        {0}Usage: {0}stop
        Output:
            Stops playing song and clears the queue.
        """

        ctx.voice_state.songs.clear()

        if ctx.voice_state.is_playing:
            ctx.voice_state.voice.stop()
            await ctx.message.add_reaction(self.bot.emote_dict["stop"])

    @decorators.command(
        name="skip",
        aliases=["s", "fs", "vs"],
        brief="Vote to skip the current song.",
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    async def _skip(self, ctx):
        """
        Usage: {0}skip
        Aliases: {0}s, {0}fs, {0}vs
        Output: Vote to skip a song.
        Notes:
            The song requester and those with the
            Manage Server permission can automatically skip
            Otherwise half the listeners neet to vote skip
            for the song to be skipped.
        """
        if not ctx.voice_state.is_playing:
            return await ctx.fail("Nothing is currently being played.")

        required_voters = (len(ctx.voice_state.voice.channel.members) - 1) // 2
        voter = ctx.author
        if voter == ctx.voice_state.current.requester:
            await ctx.message.add_reaction(self.bot.emote_dict["skip"])
            ctx.voice_state.skip()

        elif checks.is_admin(voter) or voter.guild_permissions.manage_guild:
            await ctx.message.add_reaction(self.bot.emote_dict["skip"])
            ctx.voice_state.skip()

        elif voter.id not in ctx.voice_state.skip_votes:
            ctx.voice_state.skip_votes.add(voter.id)
            total_votes = len(ctx.voice_state.skip_votes)

            if total_votes >= required_voters:
                await ctx.message.add_reaction(self.bot.emote_dict["skip"])
                ctx.voice_state.skip()
            else:
                await ctx.success(
                    "Skip vote added, currently at `{}/{}`".format(
                        total_votes, required_voters
                    )
                )
        else:
            await ctx.fail("You have already voted to skip this song.")

    @decorators.command(
        name="queue",
        brief="Display the queue.",
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    @checks.bot_has_perms(add_reactions=True, external_emojis=True)
    async def _queue(self, ctx):
        """
        Usage: {0}queue
        Output:
            Starts a pagination session showing
            all the songs in the current queue.
        Notes:
            Each page contains 10 queue elements.
        """

        if len(ctx.voice_state.songs) == 0:
            return await ctx.fail("The queue is currently empty.")

        entries = [
            f"[**{song.source.title}**]({song.source.url})"
            for song in ctx.voice_state.songs
        ]
        p = pagination.SimplePages(entries, per_page=10, index=True)
        p.embed.title = "Current Queue"

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    @decorators.command(
        name="clear",
        aliases=["c"],
        brief="Remove all queued songs.",
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    async def _clear(self, ctx):
        """
        Usage: {0}clear
        Alias: {0}c
        Output:
            Removes all queued songs
        """
        if len(ctx.voice_state.songs) == 0:
            return await ctx.fail("The queue is already empty")
        ctx.voice_state.songs.clear()
        await ctx.success("Cleared all songs from the queue.")

    @decorators.command(
        name="shuffle",
        brief="Shuffle the queue.",
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    async def _shuffle(self, ctx):
        """
        Usage: {0}shuffle
        Output: Shuffles the queue.
        """

        if len(ctx.voice_state.songs) == 0:
            return await ctx.fail("The queue is currently empty.")

        ctx.voice_state.songs.shuffle()
        await ctx.success("Shuffled the queue.")

    @decorators.command(
        name="pop",
        brief="Remove a song from the queue.",
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    async def _pop(self, ctx, index: int):
        """Removes a song from the queue at a given index."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send("The queue is already empty")
        try:
            ctx.voice_state.songs.remove(index - 1)
        except Exception:
            return await ctx.fail("Invalid index.")
        await ctx.success(f"Removed item {index} from the queue.")

    @decorators.command(
        name="loop",
        brief="Loop the current song.",
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    async def _loop(self, ctx):
        """
        Usage: {0}loop
        Output: Loops the currently playing song.
        """
        if not ctx.voice_state.is_playing:
            return await ctx.fail("Nothing is currently being played.")

        if ctx.voice_state.loop:
            return await ctx.fail("Already looping this song.")

        ctx.voice_state.loop = True
        await ctx.message.add_reaction(self.bot.emote_dict["loop"])

    @decorators.command(
        name="unloop",
        aliases=["deloop"],
        brief="Un-loop the current song.",
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    async def _unloop(self, ctx):
        """
        Usage: {0}unloop
        Alias: {0}deloop
        Output:
            Stops looping the current song
        """

        if not ctx.voice_state.is_playing:
            return await ctx.fail("Nothing is currently being played.")

        if not ctx.voice_state.loop:
            return await ctx.fail("Not currently looping this song.")

        ctx.voice_state.loop = False
        await ctx.message.add_reaction(self.bot.emote_dict["success"])

    @decorators.command(
        name="seek",
        brief="Seek to a position in a song.",
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    async def _seek(self, ctx, time: int = 0):
        song = ctx.voice_state.current
        if time < 0:
            return await ctx.fail("Seek time cannot be negative.")
        if time > song.source.raw_duration:
            return await ctx.fail(
                f"Seek time must be less than the length of the song. `{song.source.raw_duration} seconds`"
            )
        ffmpeg_options = f"-vn -ss {time}"  # This seeks to the specified timestamp
        ctx.voice_state.voice.pause()  # Pause the audio before seeking
        now = discord.FFmpegPCMAudio(
            song.source.stream_url, before_options=ffmpeg_options
        )
        ctx.voice_state.voice.play(now, after=ctx.voice_state.play_next_song)

        await ctx.success(f"Seeked to second `{time}`")

    @decorators.command(
        name="play",
        brief="Play a song",
        aliases=["p"],
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    async def _play(self, ctx, *, search: str = None):
        """
        Usage: {0}play <search>
        Alias: {0}p
        Output:
            Plays a song from your selection.
        Notes:
            If there are songs in the queue,
            this will be queued until the
            other songs finished playing.
            This command automatically searches from
            various sites if no URL is provided.
            A list of these sites can be found here:
            https://rg3.github.io/youtube-dl/supportedsites.html
        """
        await ctx.trigger_typing()
        await self.ensure_voice_state(ctx)

        if search is None:
            if ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
                ctx.voice_state.voice.resume()
                await ctx.message.add_reaction(self.bot.emote_dict["play"])
                await ctx.success("Resumed the player")
            else:
                return await ctx.usage()

        else:
            try:
                source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop)
            except YTDLError as e:
                await ctx.fail(f"Request failed: {e}")
            else:
                song = Song(source)
                ctx.voice_state.songs.put_nowait(song)
                await ctx.send_or_reply(
                    f"{self.bot.emote_dict['music']} Queued {source}"
                )

    @decorators.command(
        name="youtube",
        aliases=["yt"],
        brief="Search for anything on youtube.",
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    async def _youtube(self, ctx, *, search: str):
        """
        Usage: {0}youtube <search>
        Alias: {0}yt
        Output:
            Searches youtube and returns an embed
            of the first 10 results collected.
        Notes:
            Choose one of the titles by typing a number
            or cancel by typing "cancel".
            Each title in the list can be clicked as a link.
        """
        await ctx.trigger_typing()
        await self.ensure_voice_state(ctx)
        try:
            source = await YTDLSource.search_source(
                ctx, search, loop=self.bot.loop, bot=self.bot
            )
        except YTDLError as e:
            await ctx.send(f"Request failed: {e}")
        else:
            if source == "sel_invalid":
                await ctx.fail("Invalid selection")
            elif source == "cancel":
                await ctx.fail("Cancelled")
            elif source == "timeout":
                await ctx.fail("Timer expired")
            else:
                song = Song(source)
                await ctx.voice_state.songs.put(song)
                await ctx.send_or_reply(
                    f"{self.bot.emote_dict['music']} Queued {source}"
                )

    async def ensure_voice_state(self, ctx):
        if not ctx.voice_state.voice:
            if not hasattr(ctx.author.voice, "channel"):
                raise commands.BadArgument("You must be connected to a voice channel")

            channel = ctx.author.voice.channel
            try:
                ctx.voice_state.voice = await channel.connect(timeout=None)
            except discord.ClientException:
                if hasattr(ctx.guild.me.voice, "channel"):
                    if ctx.guild.me.voice.channel == channel:
                        raise commands.BadArgument(
                            f"Already in channel {channel.mention}"
                        )
                    else:
                        await ctx.guild.voice_client.disconnect(force=True)
                        ctx.voice_state.voice = await channel.connect(timeout=None)
                else:
                    await ctx.guild.voice_client.disconnect(force=True)
                    ctx.voice_state.voice = await channel.connect(timeout=None)
