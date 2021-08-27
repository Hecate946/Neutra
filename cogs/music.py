import io
import random
import re
import typing
import asyncio
import discord
import functools
import itertools
import youtube_dl

from discord.ext import commands, menus

from settings import constants
from utilities import utils
from utilities import checks
from utilities import images
from utilities import spotify
from utilities import converters
from utilities import decorators
from utilities import exceptions
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
        "ignoreerrors": True,
        "logtostderr": False,
        "quiet": True,
        "no_warnings": True,
        "default_search": "ytsearch",
        "source_address": "0.0.0.0",
        "subtitleslangs": ["en"],
        "writesubtitles": True,
        "writeautomaticsub": True,
    }
    FFMPEG_OPTIONS = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn",
    }

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(
        self, ctx, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 0.5
    ):
        super().__init__(source, volume)
        self.ctx = ctx

        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data

        self.id = data.get("id")
        self.uploader = data.get("uploader")
        self.uploader_url = data.get("uploader_url")
        date = data.get("upload_date")
        self.upload_date = date[6:8] + "." + date[4:6] + "." + date[0:4]
        self.title = data.get("title")
        self.thumbnail = data.get("thumbnail")
        self.description = data.get("description")
        self.raw_duration = data.get("duration")
        self.duration = utils.parse_duration(int(data.get("duration")))
        self.tags = data.get("tags")
        self.url = data.get("webpage_url")
        self.views = data.get("view_count")
        self.likes = data.get("like_count")
        self.dislikes = data.get("dislike_count")
        self.stream_url = data.get("url")

        ctx.bot.loop.create_task(self.get_subtitles())

        self.subtitles = None

    def __str__(self):
        return "**{0.title}** by **{0.uploader}**".format(self)

    async def get_subtitles(self):
        data = self.data.get("subtitles")
        if not data:
            data = self.data.get("requested_subtitles")

        if data:
            url = "https://www.youtube.com/api/timedtext?lang=en&v=" + self.id
            text = await self.ctx.bot.get(url, res_method="read")
            clean_text = re.sub(r"(?=<).*?(?<=>)", "", string=text.decode("utf-8"))
            self.subtitles = clean_text.strip("\n").replace("♪♪", "♪\n♪")

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
        self.bot = bot
        channel = ctx.channel
        loop = loop or asyncio.get_event_loop()

        self.search_query = "%s%s:%s" % ("ytsearch", 10, "".join(search))

        partial = functools.partial(
            self.ytdl.extract_info, self.search_query, download=False, process=False
        )
        info = await loop.run_in_executor(None, partial)

        lst = []
        count = 0
        e_list = []
        for e in info["entries"]:
            VId = e.get("id")
            VUrl = "https://www.youtube.com/watch?v=%s" % (VId)
            lst.append(f'`{count + 1}.` [{e.get("title")}]({VUrl})\n')
            count += 1
            e_list.append(e)

        lst.append("\n**Type a number to make a choice, Type `cancel` to exit**")

        embed = discord.Embed(
            title=f"Search results for:\n**{search}**",
            description="\n".join(lst),
            color=self.bot.constants.embed,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(
            name=f"{ctx.author.name}",
            url=f"{ctx.author.avatar.url}",
            icon_url=f"{ctx.author.avatar.url}",
        )

        # em = discord.Embed.from_dict(self.search)
        await ctx.send_or_reply(embed=embed, delete_after=45.0)

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


class Song:
    __slots__ = ("source", "requester")

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester
        if not hasattr(self.source, "position"):
            self.source.position = 0

    def create_embed(self):
        embed = discord.Embed(
            title="Now playing",
            description=f"```fix\n{self.source.title}\n```",
            color=constants.embed,
        )
        embed.add_field(name="Duration", value=self.source.duration)
        embed.add_field(name="Requested by", value=self.requester.mention)
        embed.add_field(
            name="Uploader",
            value=f"[{self.source.uploader}]({self.source.uploader_url})",
        )
        embed.add_field(name="URL", value=f"[Click]({self.source.url})")
        embed.add_field(
            name="Likes", value=f'{constants.emotes["like"]} {self.source.likes:,}'
        )
        embed.add_field(
            name="Dislikes",
            value=f'{constants.emotes["dislike"]} {self.source.dislikes:,}',
        )
        embed.set_thumbnail(url=self.source.thumbnail)

        return embed

    def truncate(self, string, max_chars=2000):
        if len(string) > max_chars:
            return string[: max_chars - 3] + "..."
        return string

    def current_embed(self):
        embed = discord.Embed(
            title="Now playing",
            description=f"```fix\n{self.source.title}\n```\n",
            color=constants.embed,
        )
        # embed.description += self.truncate("\n" + self.source.description)
        embed.add_field(name="Duration", value=self.source.duration)
        embed.add_field(name="Requested by", value=self.requester.mention)
        embed.add_field(
            name="Uploader",
            value=f"[{self.source.uploader}]({self.source.uploader_url})",
        )
        embed.add_field(name="URL", value=f"[Click]({self.source.url})")
        embed.add_field(
            name="Likes", value=f'{constants.emotes["like"]} {self.source.likes:,}'
        )
        embed.add_field(
            name="Dislikes",
            value=f'{constants.emotes["dislike"]} {self.source.dislikes:,}',
        )
        embed.set_thumbnail(url=self.source.thumbnail)

        percent = self.source.position / self.source.raw_duration
        embed.set_footer(
            text=f"Current Position: {utils.parse_duration(int(self.source.position))} ({percent:.2%} completed)"
        )
        dfile, fname = images.get_progress_bar(percent)
        embed.set_image(url=f"attachment://{fname}")

        return (embed, dfile)


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

    def pop(self, index: int):
        song = self._queue[index]
        del self._queue[index]
        return song

    def insert(self, index: int, item):
        self._queue.insert(index, item)

    def append_left(self, item):
        self._queue.appendleft(item)


class VoiceState:
    def __init__(self, bot, ctx):
        self.bot = bot
        self._ctx = ctx

        self.current = None  # Current song
        self.previous = None  # Previous song
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()
        self.exists = True

        self._loop = False
        self._queue_loop = False
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
    def queue_loop(self):
        return self._queue_loop

    @queue_loop.setter
    def queue_loop(self, value: bool):
        self._queue_loop = value

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

            if not self.loop and not self.queue_loop:
                # we're not looping a single song
                self.current = await self.songs.get()
                self.current.source.volume = self._volume

                self.voice.play(self.current.source, after=self.play_next_song)
                await self.current.source.channel.send(
                    embed=self.current.create_embed()
                )
                await self.bot.loop.create_task(self.increase_position())

            elif self.loop:  # Single song is looped.
                self.now = discord.FFmpegPCMAudio(
                    self.current.source.stream_url, **YTDLSource.FFMPEG_OPTIONS
                )
                self.voice.play(self.now, after=self.play_next_song)

                await self.current.source.channel.send(
                    embed=self.current.create_embed()
                )
                await self.bot.loop.create_task(self.increase_position())

            elif self.queue_loop:  # Entire queue is looped
                self.current = await self.songs.get()  # Get the song from the queue
                self.current.source.volume = self._volume  # Establish the volume
                self.songs.put_nowait(
                    self.current
                )  #  Put the song back into the end of the queue.
                self.now = discord.FFmpegPCMAudio(  # Play the song
                    self.current.source.stream_url, **YTDLSource.FFMPEG_OPTIONS
                )
                self.voice.play(self.now, after=self.play_next_song)

            await self.next.wait()
            self.previous = self.current

    async def increase_position(self):
        """
        Helper function to increase the position
        of the song while it's being played.
        """
        while self.voice.is_playing():
            self.current.source.position += 1
            await asyncio.sleep(1)

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

        self.spotify_client_id = utils.config().get("spotify_client_id")
        self.spotify_client_secret = utils.config().get("spotify_client_secret")
        self.spotify = None

        if self.spotify_client_id and self.spotify_client_secret:
            self.spotify = spotify.Spotify(
                self.spotify_client_id,
                self.spotify_client_secret,
                aiosession=self.bot.session,
                loop=self.bot.loop,
            )

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
        aliases=["dc", "leave"],
        brief="Disconnect the bot from a channel.",
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    async def _disconnect(self, ctx):
        """
        Usage: {0}disconnect
        Alias: {0}dc, {0}leave
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
    async def _volume(self, ctx, volume: int = None):
        """Sets the volume of the player for the current song."""
        if not ctx.voice_state.is_playing:
            return await ctx.fail("Nothing is currently being played.")

        if volume is None:  # Output what we have
            v = ctx.voice_state.current.source.volume
            return await ctx.send_or_reply(
                f"{self.bot.emote_dict['volume']} Volume of the player is currently {v * 100}%"
            )

        if volume < 0 or volume > 100:
            return await ctx.fail("Volume percentage must be between 0 and 100")

        ctx.voice_state.current.source.volume = volume / 100
        await ctx.send_or_reply(
            f"{self.bot.emote_dict['volume']} Volume of the player set to {volume}%"
        )

    @decorators.command(
        name="current",
        brief="Displays the currently playing song.",
        aliases=["now", "np", "nowplaying"],
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    @checks.bot_has_perms(embed_links=True, attach_files=True)
    @checks.cooldown()
    async def _current(self, ctx):
        """
        Usage: {0}now
        Aliases: {0}now {0}np
        Output: Displays the currently playing song.
        """
        if not ctx.voice_state.is_playing:
            return await ctx.fail("Nothing is currently being played.")
        embed, file = ctx.voice_state.current.current_embed()
        await ctx.send_or_reply(embed=embed, file=file)

    @decorators.command(
        name="pause",
        brief="Pauses the currently playing song.",
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    @checks.cooldown()
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
    @checks.cooldown()
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
    @checks.cooldown()
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
    @checks.cooldown()
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

        elif checks.is_admin(ctx) or voter.guild_permissions.manage_guild:
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
        aliases=["q"],
        name="queue",
        brief="Show the song queue.",
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    @checks.cooldown()
    @checks.bot_has_perms(add_reactions=True, external_emojis=True, embed_links=True)
    async def _queue(self, ctx):
        """
        Usage: {0}queue
        Alias: {0}q
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
        brief="Clear all queued songs.",
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    @checks.cooldown()
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
        brief="Shuffle the song queue.",
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    @checks.cooldown()
    async def _shuffle(self, ctx):
        """
        Usage: {0}shuffle
        Output: Shuffles the queue.
        """
        if len(ctx.voice_state.songs) == 0:
            return await ctx.fail("The queue is currently empty.")

        ctx.voice_state.songs.shuffle()
        await ctx.send_or_reply(f"{self.bot.emote_dict['shuffle']} Shuffled the queue.")

    @decorators.command(
        aliases=["pop"],
        name="remove",
        brief="Remove a song from the queue.",
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    @checks.cooldown()
    async def _remove(self, ctx, index: int):
        """
        Usage: {0}remove [index]
        Alias: {0}pop
        Output:
            Removes a song from the queue at a given index.
        """

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send_or_reply("The queue is already empty")
        try:
            ctx.voice_state.songs.remove(index - 1)
        except Exception:
            return await ctx.fail("Invalid index.")
        await ctx.success(f"Removed item {index} from the queue.")

    @decorators.command(
        aliases=["deloop"],
        name="unloop",
        brief="Un-loop the current song or queue.",
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-22 17:48:57.021225",
    )
    @checks.cooldown()
    async def _unloop(self, ctx):
        """
        Usage: {0}unloop
        Alias: {0}deloop
        Output:
            Stops looping the current song or queue
        """
        if not ctx.voice_state.is_playing:
            return await ctx.fail("Nothing is currently being played.")

        ctx.voice_state.loop = False
        ctx.voice_state.queue_loop = False
        await ctx.message.add_reaction(self.bot.emote_dict["success"])

    @decorators.command(
        name="loop",
        brief="Loop the current song or queue.",
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    @checks.cooldown()
    async def _loop(self, ctx, option: converters.SingleOrQueue = "single"):
        """
        Usage: {0}loop [option]
        Output: Loops the currently playing song.
        """
        if not ctx.voice_state.is_playing:
            return await ctx.fail("Nothing is currently being played.")

        if option == "single":
            if ctx.voice_state.loop:
                return await ctx.fail("Already looping this song.")

            ctx.voice_state.loop = True
            await ctx.message.add_reaction(self.bot.emote_dict["loop"])
            await ctx.success("The current song is now looped.")
        else:
            if ctx.voice_state.queue_loop:
                return await ctx.fail("Already looping this queue.")

            ctx.voice_state.queue_loop = True
            ctx.voice_state.loop = False  # In case we were looping a single song.
            ctx.voice_state.songs.put_nowait(
                ctx.voice_state.current
            )  # Put back the current song.
            await ctx.message.add_reaction(self.bot.emote_dict["loop"])
            await ctx.success("The current queue is now looped.")

    @decorators.command(
        aliases=["jump"],
        name="seek",
        brief="Seek to a position in the song.",
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    @checks.cooldown()
    async def _seek(self, ctx, position: int = 0):
        """
        Usage: {0}seek [time]
        Alias: {0}jump
        Output:
            Seeks to a certain position in the track
        Notes:
            The position must be given in seconds.
        """
        if not ctx.voice_state.is_playing:
            return await ctx.fail("Nothing is currently being played.")
        song = ctx.voice_state.current
        if position < 0:
            return await ctx.fail("Seek time cannot be negative.")
        if position > song.source.raw_duration:
            return await ctx.fail(
                f"Seek time must be less than the length of the song. `{song.source.raw_duration} seconds`"
            )

        ffmpeg_options = {
            "before_options": f"-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -ss {position}",
            "options": "-vn",  # This seeks to the specified timestamp
        }
        ctx.voice_state.voice.pause()  # Pause the audio before seeking
        now = discord.FFmpegPCMAudio(song.source.stream_url, **ffmpeg_options)
        ctx.voice_state.voice.play(now, after=ctx.voice_state.play_next_song)
        ctx.voice_state.current.source.position = position

        await ctx.success(f"{ctx.invoked_with.capitalize()}ed to second `{position}`")

    @decorators.command(
        aliases=["ff", "ffw"],
        name="fastforward",
        brief="Fast forward the song.",
        implemented="2021-06-22 01:55:36.152071",
        updated="2021-06-22 01:55:36.152071",
    )
    @checks.cooldown()
    async def _fastforward(self, ctx, seconds: int = 0):
        """
        Usage: {0}fastforward [seconds]
        Alias: {0}ff
        Output:
            Fast forward a certain number of seconds in a song.
        """
        if not ctx.voice_state.is_playing:
            return await ctx.fail("Nothing is currently being played.")
        song = ctx.voice_state.current
        if seconds < 0:
            return await ctx.invoke(self._rewind, seconds)
        position = seconds + song.source.position
        if position > song.source.raw_duration:
            return await ctx.fail(
                f"You cannot fast forward past the end of the song. `Current position: {song.source.position}/{song.source.raw_duration} seconds`"
            )
        ffmpeg_options = {
            "before_options": f"-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -ss {position}",
            "options": "-vn",  # This seeks to the specified timestamp
        }
        ctx.voice_state.voice.pause()  # Pause the audio before seeking
        now = discord.FFmpegPCMAudio(song.source.stream_url, **ffmpeg_options)
        ctx.voice_state.voice.play(now, after=ctx.voice_state.play_next_song)
        ctx.voice_state.current.source.position = position
        await ctx.success(f"Fast forwarded to second `{position}`")

    @decorators.command(
        aliases=["fb", "fbw", "rw", "fastback", "fastbackwards"],
        name="rewind",
        brief="Rewind a number of seconds",
        implemented="2021-06-22 01:55:36.152071",
        updated="2021-06-22 01:55:36.152071",
    )
    @checks.cooldown()
    async def _rewind(self, ctx, seconds: int = 0):
        """
        Usage: {0}rewind [seconds]
        Alias: {0}rw
        Output:
            Rewind a certain number of seconds in a song.
        """
        if not ctx.voice_state.is_playing:
            return await ctx.fail("Nothing is currently being played.")
        song = ctx.voice_state.current
        if seconds < 0:
            seconds = abs(seconds)
        position = song.source.position - seconds
        if position < 0:
            return await ctx.fail(
                f"You cannot rewind past the beginning of the song. `Current position: {song.source.position}/{song.source.raw_duration} seconds`"
            )
        ffmpeg_options = {
            "before_options": f"-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -ss {position}",
            "options": "-vn",  # This seeks to the specified timestamp
        }
        ctx.voice_state.voice.pause()  # Pause the audio before seeking
        now = discord.FFmpegPCMAudio(song.source.stream_url, **ffmpeg_options)
        ctx.voice_state.voice.play(now, after=ctx.voice_state.play_next_song)
        ctx.voice_state.current.source.position = position

        await ctx.success(f"Rewinded to second `{position}`")

    @decorators.command(
        aliases=["last", "back", "previous"],
        name="replay",
        brief="Play the previous song.",
        implemented="2021-06-22 19:55:33.279989",
        updated="2021-06-22 19:55:33.279989",
    )
    @checks.cooldown()
    async def _replay(self, ctx):
        """
        Usage: {0}replay [seconds]
        Alias: {0}last, {0}back, {0}previous
        Output:
            Replay the last song to be played.
        """
        if not ctx.voice_state.previous:
            return await ctx.fail("No previous song to play.")
        song = ctx.voice_state.previous
        ytdlsrc = await YTDLSource.create_source(
            ctx, str(song.source.url), loop=self.bot.loop
        )
        song = Song(ytdlsrc)
        ctx.voice_state.songs.put_nowait(song)
        ctx.voice_state.voice.pause()
        ctx.voice_state.voice.resume()
        await ctx.send_or_reply(
            f"{self.bot.emote_dict['music']} Requeued the previous song: {song.source}"
        )

    @decorators.command(
        aliases=["relocate", "switch"],
        name="move",
        brief="Move a song in the queue.",
        implemented="2021-07-01 04:12:22.192236",
        updated="2021-07-01 04:12:22.192236",
    )
    @checks.cooldown()
    async def _move(self, ctx, index: int, position: int):
        """
        Usage: {0}move <index> <position>
        Alias: {0}switch, {0}relocate
        Output:
            Move a song to a new position in the queue.
        """
        total = len(ctx.voice_state.songs)
        if total == 0:
            return await ctx.fail("The queue is currently empty.")
        elif index > total or index < 1:
            return await ctx.fail("Invalid index.")
        elif position > total or position < 1:
            return await ctx.fail("Invalid position.")
        elif index == position:
            await ctx.success("Song queue remains unchanged.")
            return

        song = ctx.voice_state.songs.pop(index - 1)

        ctx.voice_state.songs.insert(position - 1, song)

        await ctx.success(
            f"Moved song #{index} to the {utils.number_format(position)} position in the queue."
        )

    @decorators.command(
        aliases=["pos"],
        name="position",
        brief="Show the position of the song.",
        implemented="2021-06-21 23:09:55.015228",
        updated="2021-06-21 23:09:55.015228",
    )
    @checks.cooldown()
    async def _position(self, ctx):
        """
        Usage: {0}position
        Alias: {0}pos
        Output:
            Shows the current position of the song
        """
        if not ctx.voice_state.is_playing:
            return await ctx.fail("Nothing is currently being played.")
        dur = ctx.voice_state.current.source.duration
        pos = ctx.voice_state.current.source.position
        raw = ctx.voice_state.current.source.raw_duration
        await ctx.success(f"Current position: {dur} `({pos}/{raw}) seconds`")

    @decorators.command(
        name="play",
        brief="Play a song from a search or URL.",
        aliases=["p"],
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    @checks.bot_has_perms(embed_links=True)
    @checks.bot_has_guild_perms(connect=True, speak=True)
    @checks.cooldown()
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
            linksRegex = "((http(s)*:[/][/]|www.)([a-z]|[A-Z]|[0-9]|[/.]|[~])*)"
            pattern = re.compile(linksRegex)
            matchUrl = pattern.match(search)
            song_url = search.replace("/", "%2F") if matchUrl is None else search

            # Rewrite YouTube playlist URLs if the wrong URL type is given
            playlistRegex = r"watch\?v=.+&(list=[^&]+)"
            matches = re.search(playlistRegex, song_url)
            groups = matches.groups() if matches is not None else []
            song_url = (
                "https://www.youtube.com/playlist?" + groups[0]
                if len(groups) > 0
                else song_url
            )

            if self.spotify:
                if "open.spotify.com" in song_url:
                    song_url = "spotify:" + re.sub(
                        "(http[s]?:\/\/)?(open.spotify.com)\/", "", song_url
                    ).replace("/", ":")
                    # remove session id (and other query stuff)
                    song_url = re.sub("\?.*", "", song_url)
                if song_url.startswith("spotify:"):
                    parts = song_url.split(":")
                    try:
                        if "track" in parts:
                            res = await self.spotify.get_track(parts[-1])
                            song_url = res["artists"][0]["name"] + " " + res["name"]

                        elif "album" in parts:
                            res = await self.spotify.get_album(parts[-1])
                            song_urls = [
                                i["name"] + " " + i["artists"][0]["name"]
                                for i in res["tracks"]["items"]
                            ]
                            await self.enqueue_songs(ctx, song_urls)
                            return

                        elif "artist" in parts:
                            res = await self.spotify.get_artist(parts[-1])
                            song_urls = [
                                i["name"] + " " + i["artists"][0]["name"]
                                for i in res["tracks"]
                            ]
                            await self.enqueue_songs(ctx, song_urls)
                            return

                        elif "playlist" in parts:
                            res = []
                            r = await self.spotify.get_playlist_tracks(parts[-1])
                            while True:
                                res.extend(r["items"])
                                if r["next"] is not None:
                                    r = await self.spotify.make_spotify_req(r["next"])
                                    continue
                                else:
                                    break

                            song_urls = [
                                i["track"]["name"]
                                + " "
                                + i["track"]["artists"][0]["name"]
                                for i in res
                            ]
                            await self.enqueue_songs(ctx, song_urls)
                            return

                        else:
                            return await ctx.fail("Invalid Spotify URI.")
                    except exceptions.SpotifyError as e:
                        return await ctx.fail("Invalid Spotify URI.")
                try:
                    source = await YTDLSource.create_source(
                        ctx, song_url, loop=self.bot.loop
                    )
                except YTDLError as e:
                    await ctx.fail(f"Request failed: {e}")
                else:
                    song = Song(source)
                    ctx.voice_state.songs.put_nowait(song)
                    await ctx.send_or_reply(
                        f"{self.bot.emote_dict['music']} Queued {source}"
                    )

    async def enqueue_songs(self, ctx, songs):
        msg = await ctx.load(f"Enqueueing {len(songs)} tracks...")
        queued = 0
        for song in songs:
            try:
                source = await YTDLSource.create_source(ctx, song, loop=self.bot.loop)
            except YTDLError:
                continue
            else:
                song = Song(source)
                ctx.voice_state.songs.put_nowait(song)
                queued += 1

        await msg.edit(
            content=f"**{self.bot.emote_dict['music']} Queued {queued} tracks.**"
        )

    @decorators.command(
        name="playnext",
        brief="Add a song to the front of the queue.",
        aliases=["pn"],
        implemented="2021-06-21 23:09:55.015228",
        updated="2021-06-21 23:09:55.015228",
    )
    @checks.bot_has_perms(embed_links=True)
    @checks.bot_has_guild_perms(connect=True, speak=True)
    @checks.cooldown()
    async def _playnext(self, ctx, *, search: str = None):
        """
        Usage: {0}play <search>
        Alias: {0}p
        Output:
            Plays a song from your selection.
        Notes:
            If there are songs in the queue,
            this will be queued before
            all other songs in the queue.
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
                if len(ctx.voice_state.songs) > 0:
                    ctx.voice_state.songs.append_left(song)
                else:
                    ctx.voice_state.songs.put_nowait(song)
                await ctx.send_or_reply(
                    f"{self.bot.emote_dict['music']} Front Queued {source}"
                )

    @decorators.command(
        name="youtube",
        aliases=["yt"],
        brief="Search for a youtube video.",
        implemented="2021-06-15 06:50:53.661786",
        updated="2021-06-15 06:50:53.661786",
    )
    @checks.bot_has_perms(embed_links=True)
    @checks.bot_has_guild_perms(connect=True, speak=True)
    @checks.cooldown()
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
            await ctx.fail(f"Request failed: {e}")
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

    @decorators.command(
        name="subtitles",
        aliases=["lyrics"],
        brief="Request subtitles for the song.",
        implemented="2021-06-23 06:48:27.194755",
        updated="2021-06-23 06:48:27.194755",
    )
    @checks.cooldown()
    async def _subtitle(self, ctx):
        """
        Usage: {0}subtitles
        Alias: {0}lyrics
        Output:
            Attemps to generate subtitles for the current track.
            May not be available.
        """
        if not ctx.voice_state.current:
            return await ctx.fail("No song is currently being played.")
        if not ctx.voice_state.is_playing:
            return await ctx.fail("No song is currently being played.")

        subtitles = ctx.voice_state.current.source.subtitles
        if subtitles:
            print(subtitles)
            if len(subtitles) > 2048:
                data = io.BytesIO(subtitles.encode("utf-8"))
                file = discord.File(data, filename="subtitles.txt")
                await ctx.send_or_reply(file=file)
            else:
                embed = discord.Embed(title="Subtitles", color=self.bot.constants.embed)
                embed.description = subtitles
                await ctx.send_or_reply(embed=embed)
        else:
            return await ctx.fail("Subtitles not available.")

    async def ensure_voice_state(self, ctx):
        if not ctx.me.voice:
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
