import re
import math
import typing
import random
import asyncio
import discord
import functools
import itertools
from discord.errors import ClientException
import youtube_dl

from discord.ext import commands, menus

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

#  Option base to avoid pull errors
FFMPEG_OPTION_BASE = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"

# YTDL options for creating sources
YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "extractaudio": True,
    "audioformat": "mp3",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "flatplaylist": False,
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

# YTDL info extractor class
YOUTUBE_DL = youtube_dl.YoutubeDL(YTDL_OPTIONS)


class AudioUtils:
    """
    Utility class that houses information
    and spotify-related helper functions.
    """

    def spotify(bot):
        """
        Create utiliites.spotify.Spotify() instance
        from credentials found in ./config.json
        """
        spotify_client_id = utils.config().get("spotify_client_id")
        spotify_client_secret = utils.config().get("spotify_client_secret")

        if spotify_client_id and spotify_client_secret:
            return spotify.Spotify(
                client_id=spotify_client_id,
                client_secret=spotify_client_secret,
                aiosession=bot.session,
                loop=bot.loop,
            )

    def parse_duration(duration: int):
        """
        Helper function to get visually pleasing
        timestamps from position of song in seconds.
        """
        if duration > 0:
            minutes, seconds = divmod(duration, 60)
            hours, minutes = divmod(minutes, 60)
            days, hours = divmod(hours, 24)

            duration = []
            if days > 0:
                duration.append("{}".format(str(days).zfill(2)))
            if hours > 0:
                duration.append("{}".format(str(hours).zfill(2)))
            if minutes > 0:
                duration.append("{}".format(str(minutes).zfill(2)))
            duration.append("{}".format(str(seconds).zfill(2)))

            value = ":".join(duration)

        elif duration == 0:
            value = "LIVE"

        return value

    async def create_embed(ctx, source):
        """
        Create an embed showing details of the current song
        Will change format depending on the channel perms.
        """
        MUSIC = ctx.bot.constants.emotes["music"]
        LIKE = ctx.bot.constants.emotes["like"]
        DISLIKE = ctx.bot.constants.emotes["dislike"]

        block = None
        embed = None
        file = None

        ytdl = source.ytdl

        if ctx.channel.permissions_for(ctx.me).embed_links:
            embed = discord.Embed(color=ctx.bot.constants.embed)
            embed.title = "Now Playing"
            embed.description = f"```fix\n{ytdl.title}\n```"

            embed.add_field(name="Duration", value=ytdl.duration)
            embed.add_field(name="Requester", value=ytdl.requester.mention)
            embed.add_field(
                name="Uploader", value=f"[{ytdl.uploader}]({ytdl.uploader_url})"
            )
            embed.add_field(name="Link", value=f"[Click]({ytdl.url})")
            embed.add_field(name="Likes", value=f"{LIKE} {ytdl.likes:,}")
            embed.add_field(name="Dislikes", value=f"{DISLIKE} {ytdl.dislikes:,}")
            embed.set_thumbnail(url=ytdl.thumbnail)

            if source.position > 1:  # Set a footer showing track position.
                percent = source.position / ytdl.raw_duration
                position = AudioUtils.parse_duration(int(source.position))

                embed.set_footer(
                    text=f"Current Position: {position} ({percent:.2%} completed)"
                )

                if ctx.channel.permissions_for(ctx.me).attach_files:
                    # Try to make a progress bar if bot has perms.
                    progress = await ctx.bot.loop.run_in_executor(
                        None, images.get_progress_bar, percent
                    )
                    embed.set_image(url=f"attachment://progress.png")
                    file = discord.File(progress, filename="progress.png")

        else:  # No embed perms, send as codeblock
            block = f"{MUSIC} **Now Playing**: *{ytdl.title}*```yaml\n"
            block += f"Duration : {ytdl.duration}\n"
            block += f"Requester: {ytdl.requester.display_name}\n"
            block += f"Uploader : {ytdl.uploader}\n"
            block += f"Link     : {ytdl.url}\n"
            block += f"Likes    : {ytdl.likes:,}\n"
            block += f"Dislikes : {ytdl.dislikes:,}\n```"

        return await ctx.send(content=block, embed=embed, file=file)

    async def read_url(url, session):
        """
        Read discord urls and return bytes
        if media type is playable and valid.
        """
        async with session.get(url) as r:
            if r.status != 200:
                raise commands.BadArgument("Unable to download discord media URL.")
            try:
                assert r.headers["content-type"] in ["video/mp4", "audio/mpeg"]
            except AssertionError:
                raise exceptions.InvalidMediaType

    def put_spotify_tracks(ctx, tracks):
        """
        Get a list of QueueEntry from spotify tracks. 
        """
        return [
            QueueEntry(
                ctx,
                track["name"],
                track["name"] + " " + track["artists"][0]["name"],
                uploader=track["artists"][0]["name"],
                link=track["external_urls"]["spotify"],
            )
            for track in tracks
        ]

    def put_spotify_playlist(ctx, playlist):
        """
        Get entries of the tracks
        from a spotify playlist.
        """
        return [
            QueueEntry(
                ctx,
                item["track"]["name"],
                item["track"]["name"] + " " + item["track"]["artists"][0]["name"],
                link=item["track"]["external_urls"]["spotify"],
            )
            for item in playlist
        ]

    def reformat_uri(search):
        linksRegex = "((http(s)*:[/][/]|www.)([a-z]|[A-Z]|[0-9]|[/.]|[~])*)"
        pattern = re.compile(linksRegex)
        matchUrl = pattern.match(search)
        song_url = search if matchUrl else search.replace("/", "%2F")

        playlist_regex = r"watch\?v=.+&(list=[^&]+)"
        matches = re.search(playlist_regex, song_url)
        groups = matches.groups() if matches is not None else []
        if len(groups) > 1:
            song_url = "https://www.youtube.com/playlist?" + groups[0]

        if "open.spotify.com" in song_url:
            sub_regex = r"(http[s]?:\/\/)?(open.spotify.com)\/"
            song_url = "spotify:" + re.sub(sub_regex, "", song_url)
            song_url = song_url.replace("/", ":")
            # remove session id (and other query stuff)
            song_url = re.sub("\?.*", "", song_url)

        return song_url

class AudioSource(discord.PCMVolumeTransformer):
    """
    Takes a ytdl source and player settings
    and returns a FFmpegPCMAudio source.
    """

    def __init__(self, ytdl, speed, pitch, volume, position=0):
        self.position = position  # Position of track
        self.ytdl = ytdl
        # Use two atempo filters in case speed/pitch < 0.5
        speed_filter = (
            f"atempo={math.sqrt(speed/pitch)},atempo={math.sqrt(speed/pitch)}"
        )
        pitch_filter = (
            f",asetrate={48000*pitch}" if pitch != 1 else ""
        )  # 48000hz normally.

        ffmpeg_options = {
            "before_options": FFMPEG_OPTION_BASE + f" -ss {position}",
            "options": f'-vn -filter:a "{speed_filter}{pitch_filter}"',
        }
        self.original = discord.FFmpegPCMAudio(ytdl.stream_url, **ffmpeg_options)
        super().__init__(self.original, volume=volume)


class QueueEntry:
    """
    QueueEntry object for enqueueing tracks.
    All TrackQueue objects are type QueueEntry
    """

    def __init__(self, ctx, title, url, *, data=None, uploader=None, link=None):
        self.ctx = ctx
        self.title = title
        self.url = url

        self.data = data
        self.uploader = uploader
        self.link = link

    def __str__(self):
        if self.uploader:
            return f"**{self.title}** by **{self.uploader}**"
        return f"**{self.title}**"

    @property
    def hyperlink(self):
        return f"**[{self.title}]({self.link or self.url})**"

    @property
    def has_data(self):
        if self.data:
            return True
        return False


class YTDLSource:
    """
    @classmethod functions create a YTDLSource object with video data
    @staticmethod functions return queueable QueueEntry objects
    """

    def __init__(self, ctx, data):
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
        self.duration = AudioUtils.parse_duration(int(data.get("duration")))
        self.tags = data.get("tags")
        self.url = data.get("webpage_url")
        self.views = data.get("view_count")
        self.likes = data.get("like_count")
        self.dislikes = data.get("dislike_count")
        self.stream_url = data.get("url")

    def __str__(self):
        return "**{0.title}** by **{0.uploader}**".format(self)

    @staticmethod
    async def get_song(ctx, search, *, loop=None):
        """
        Get the song url and title from a search query.
        If the search query is a youtube video url,
        Basic video data will be quickly returned.
        Otherwise, the webpage will be processed.
        A QueueEntry will be returned with the data
        parameter including the full webpage data.
        """
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(
            YOUTUBE_DL.extract_info, search, download=False, process=False
        )
        info = await loop.run_in_executor(None, partial)

        if info is None:
            raise exceptions.YTDLError(f"No matches found for `{search}`")

        data = None
        url = info.get("webpage_url")
        title = info.get("title")
        uploader = info.get("uploader")

        if not title:  # Was probably not a url
            partial = functools.partial(
                YOUTUBE_DL.extract_info, info["webpage_url"], download=False
            )
            info = await loop.run_in_executor(None, partial)

            if info is None:
                raise exceptions.YTDLError(f"Unable to fetch `{info['webpage_url']}`")

            if "entries" not in info:
                data = info
            else:
                data = None
                while data is None:
                    try:
                        data = info["entries"].pop(0)
                    except IndexError:
                        raise exceptions.YTDLError(
                            f"Unable to retrieve matches for `{info['webpage_url']}`"
                        )

            url = data.get("webpage_url")
            title = data.get("title")
            uploader = info.get("uploader")

            if title is None or url is None:
                raise exceptions.YTDLError(f"Unable to fetch `{search}`")

        return QueueEntry(ctx, title, url, data=data, uploader=uploader)

    @staticmethod
    async def get_playlist_tracks(ctx, search, *, loop=None):
        """
        Takes a youtube playlist url and returns a list of
        QueueEntry(track) for each track in the playlist.
        """
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(
            YOUTUBE_DL.extract_info, search, download=False, process=False
        )
        info = await loop.run_in_executor(None, partial)

        if info is None:
            raise exceptions.YTDLError(f"No matches found for `{search}`")

        if "entries" not in info:
            raise exceptions.YTDLError("Invalid youtube playlist.")

        title = info.get("title")
        uploader = info.get("uploader")

        playlist = f"**{title}** by **{uploader}**" if uploader else f"**{title}**"

        def pred(entry):
            if entry.get("title") and entry.get("url"):
                return True

        def format_url(url_code):
            return "https://www.youtube.com/watch?v=" + url_code

        return ([
            QueueEntry(
                ctx,
                entry["title"],
                format_url(entry["url"]),
                uploader=entry.get("uploader"),
            )
            for entry in info["entries"]
            if pred(entry) is True
        ], playlist)

    @classmethod
    async def get_source(cls, ctx, url, *, loop=None):
        """
        Takes a search query and returns the first result.
        """
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(YOUTUBE_DL.extract_info, url, download=False)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise exceptions.YTDLError(f"Unable to fetch `{url}`")

        if "entries" not in processed_info:
            data = processed_info
        else:
            data = None
            while data is None:
                try:
                    data = processed_info["entries"].pop(0)
                except IndexError:
                    raise exceptions.YTDLError(
                        f"Unable to retrieve matches for `{url}`"
                    )

        return cls(ctx, data)

    @staticmethod
    async def search_source(ctx, search: str, *, loop=None):
        """
        Takes a search query and returns a selection session
        with up to ten youtube videos to choose from.
        If a selection is made, QueueEntry is returned.
        """
        loop = loop or asyncio.get_event_loop()

        search_query = "%s%s:%s" % ("ytsearch", 10, "".join(search))

        partial = functools.partial(
            YOUTUBE_DL.extract_info, search_query, download=False, process=False
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
            color=ctx.bot.constants.embed,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(
            name=f"{ctx.author.name}",
            url=f"{ctx.author.avatar.url}",
            icon_url=f"{ctx.author.avatar.url}",
        )

        await ctx.send(embed=embed, delete_after=30.0)

        def check(msg):
            return (
                msg.content.isdigit() == True
                and msg.channel == ctx.channel
                or msg.content == "cancel"
                or msg.content == "Cancel"
            )

        try:
            m = await ctx.bot.wait_for("message", check=check, timeout=30.0)

        except asyncio.TimeoutError:
            rtrn = "timeout"

        else:
            if m.content.isdigit() == True:
                sel = int(m.content)
                if 0 < sel <= 10:
                    for key, value in info.items():
                        if key == "entries":
                            VId = e_list[sel - 1]["id"]
                            VUrl = "https://www.youtube.com/watch?v=%s" % (VId)
                            partial = functools.partial(
                                YOUTUBE_DL.extract_info, VUrl, download=False
                            )
                            data = await loop.run_in_executor(None, partial)

                    rtrn = QueueEntry(
                        ctx,
                        data["title"],
                        data["webpage_url"],
                        data=data,
                        uploader=data["uploader"],
                    )
                else:
                    rtrn = "sel_invalid"
            elif m.content == "cancel":
                rtrn = "cancel"
            else:
                rtrn = "sel_invalid"
        return rtrn


class TrackQueue(asyncio.Queue):
    """
    Queue for all tracks to be played.
    All items within the queue will be of type QueueEntry.
    Supports both asyncio.Queue and collections.deque operations.
    """

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
        if len(self) == 0:
            self.put_nowait(item)
        else:
            self._queue.insert(index, item)

    def append_left(self, item):
        if len(self) == 0:
            self.put_nowait(item)
        else:
            self._queue.appendleft(item)

    def extend(self, items):
        if len(self) == 0:
            self.put_nowait(items.pop(0))
            self._queue.extend(items)
        else:
            self._queue.extend(items)
        
    def extend_left(self, items):
        if len(self) == 0:
            last_item = items.pop()
            self._queue.extend(items)
            self.put_nowait(last_item)
        else:
            items.reverse()
            self._queue.extendleft(items)


class VoiceState:
    """
    Responsible for audio playing and manipulation.
    Guilds receive a cached instance in ctx.voice_state.
    """

    def __init__(self, bot, ctx):
        self.bot = bot
        self._ctx = ctx

        self.source = None  # Audio source.
        self.entry = None  # The QueueEntry track.
        self.current = None  # Current track.
        self.previous = None  # Previous track.
        self.voice = None  # Guild voice client.

        self._volume = 0.5  # Volume default.
        self._speed = 1  # Speed default.
        self._pitch = 1  # Pitch default.

        self.track_is_looped = False  # Single track is looped.
        self.queue_is_looped = False  # Entire queue is looped.

        self.skip_votes = set()  # Stored skip votes.

        self.tracks = TrackQueue()
        self.next = asyncio.Event()

        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def is_playing(self):
        return self.voice and self.current

    @property
    def validate(self):
        if self.is_playing:
            return self
        raise exceptions.InactivePlayer

    @property
    def pitch(self):
        return self._pitch

    @property
    def speed(self):
        return self._speed

    @property
    def volume(self):
        return self._volume

    @pitch.setter
    def pitch(self, value: float):
        if not 0.5 <= value <= 2.0:
            raise commands.BadArgument("Pitch must be between `0.5` and `2.0`")
        self._pitch = value
        self.alter_audio()

    @speed.setter
    def speed(self, value: float):
        if not 0.5 <= value <= 2.0:
            raise commands.BadArgument("Speed must be between `0.5` and `2.0`")
        self._speed = value
        self.alter_audio()

    @volume.setter
    def volume(self, value: float):
        if not 0.0 <= value <= 100.0:
            raise commands.BadArgument("Volume must be between `0.0` and `100.0`")
        self._volume = value
        self.source.volume = value

    async def connect(self, ctx, channel, *, timeout=60):
        try:
            self.voice = await channel.connect(timeout=timeout)
        except discord.ClientException:
            if hasattr(ctx.guild.me.voice, "channel"):
                if ctx.guild.me.voice.channel == channel:
                    raise commands.BadArgument(f"Already in channel {channel.mention}")
                else:
                    await ctx.guild.voice_client.disconnect(force=True)
                    self.voice = await channel.connect(timeout=timeout)
            else:
                await ctx.guild.voice_client.disconnect(force=True)
                self.voice = await channel.connect(timeout=timeout)

    async def reset_voice_client(self):
        if hasattr(self._ctx.guild.me.voice, "channel"):
            channel = self._ctx.guild.me.voice.channel
            await self._ctx.guild.voice_client.disconnect(force=True)
            self.voice = await channel.connect(timeout=60)

    async def play_from_file(self, file):
        await file.save("./track.mp3")
        await self.play_local_file()

    async def play_local_file(self, fname="track.mp3"):
        now = discord.FFmpegPCMAudio(fname)
        self.voice.play(now, after=self.play_next_track)

    def alter_audio(self, *, position=None, speed=None, pitch=None):
        position = position or self.source.position
        speed = speed or self.speed
        pitch = pitch or self.pitch

        self.voice.pause()  # Pause the audio before altering
        self.source = AudioSource(self.current, speed, pitch, self.volume, position)
        self.voice.play(self.source, after=self.play_next_track)

    async def get_next_track(self):
        self.entry = await self.tracks.get()
        if self.entry.has_data:
            current = YTDLSource(self.entry.ctx, self.entry.data)
        else:
            current = await YTDLSource.get_source(self.entry.ctx, self.entry.url)
        return current

    def requeue(self, source: YTDLSource):
        self.entry.data = source.data
        self.tracks.put_nowait(self.entry)

    def replay(self, source: YTDLSource):
        self.entry.data = source.data
        self.tracks.append_left(self.entry)

    async def audio_player_task(self):
        while True:
            self.next.clear()

            if self.voice is None:
                await self.reset_voice_client()

            if self.track_is_looped:  # Single song is looped.
                self.current = self.previous

            elif self.queue_is_looped:  # Entire queue is looped
                self.requeue(self.previous)  # Put old track back in the queue.
                self.current = (
                    await self.get_next_track()
                )  # Get the song from the queue

            else:  # Not looping track or queue.
                self.current = await self.get_next_track()

            self.source = AudioSource(self.current, self.speed, self.pitch, self.volume)
            self.voice.play(self.source, after=self.play_next_track)
            await AudioUtils.create_embed(self._ctx, self.source)

            self.bot.loop.create_task(self.increase_position())
            await self.next.wait()  # Wait until the track finishes
            self.previous = self.current  # Store previous track
            self.current = None
            self.source = None

    async def increase_position(self):
        """
        Helper function to increase the position
        of the song while it's being played.
        """
        while self.source:
            self.source.position += self.speed
            await asyncio.sleep(1)

    def play_next_track(self, error=None):
        if error:
            raise error

        self.next.set()

    def skip(self):
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.tracks.clear()

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
        self.spotify = AudioUtils.spotify(bot)

    def get_voice_state(self, ctx):
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

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

    async def ensure_voice_state(self, ctx):
        if not ctx.me.voice:
            if not hasattr(ctx.author.voice, "channel"):
                raise commands.BadArgument("You must be connected to a voice channel")

            channel = ctx.author.voice.channel
            await ctx.voice_state.connect(ctx, channel)
        return ctx.voice_state

    @decorators.command(
        name="connect",
        aliases=["join"],
        brief="Joins a voice or stage channel.",
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

        await ctx.voice_state.connect(ctx, channel)
        await ctx.success(f"Connected to {channel.mention}")

    @decorators.command(
        name="247",
        aliases=["24/7"],
        brief="Joins a channel indefinitely.",
    )
    async def _247(
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

        await ctx.voice_state.connect(ctx, channel, timeout=None)
        await ctx.success(f"Connected to {channel.mention} indefinitely.")

    @decorators.command(
        name="disconnect",
        aliases=["dc", "leave"],
        brief="Disconnect the bot from a channel.",
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
        aliases=["vol"],
        name="volume",
        brief="Set the volume of the player.",
    )
    async def _volume(self, ctx, volume: int = None):
        """
        Sets the volume of the player for the current song.
        """
        player = ctx.voice_state.validate
        emoji = self.bot.emote_dict["volume"]

        if volume is None:  # Output what we have
            await ctx.send_or_reply(
                f"{emoji} Volume of the player is currently {player.volume:.0%}"
            )
            return

        player.volume = volume / 100
        await ctx.send_or_reply(
            f"{emoji} Volume of the player set to {player.volume:.0%}"
        )

    @decorators.command(
        name="current",
        brief="Displays the currently playing song.",
        aliases=["now", "np", "nowplaying"],
    )
    @checks.cooldown()
    async def _current(self, ctx):
        """
        Usage: {0}now
        Aliases: {0}now {0}np
        Output: Displays the currently playing song.
        """
        player = ctx.voice_state.validate
        await AudioUtils.create_embed(ctx, player.source)

    @decorators.command(
        name="pause",
        brief="Pauses the current track.",
    )
    @checks.cooldown()
    async def _pause(self, ctx):
        """
        Usage: {0}pause
        Output: Pauses the currently playing song.
        """
        player = ctx.voice_state.validate

        if player.voice.is_paused():
            await ctx.fail("The player is already paused.")
            return

        player.voice.pause()
        await ctx.react(self.bot.emote_dict["pause"])

    @decorators.command(
        name="resume",
        brief="Resumes the current track.",
    )
    @checks.cooldown()
    async def _resume(self, ctx):
        """
        Usage: {0}resume
        Output:
            Resumes playback paused by the {0}pause command.
        """
        player = ctx.voice_state.validate

        if not player.voice.is_paused():
            await ctx.fail("The player is not paused.")
            return

        player.voice.resume()
        await ctx.react(self.bot.emote_dict["play"])

    @decorators.command(
        name="stop",
        brief="Stops track and clears the queue.",
    )
    @checks.cooldown()
    async def _stop(self, ctx):
        """
        {0}Usage: {0}stop
        Output:
            Stops playing song and clears the queue.
        """
        ctx.voice_state.tracks.clear()
        if ctx.voice_state.is_playing:
            ctx.voice_state.voice.stop()

        await ctx.react(self.bot.emote_dict["stop"])

    @decorators.command(
        name="skip",
        aliases=["s", "fs", "vs"],
        brief="Vote to skip the track.",
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
        player = ctx.voice_state.validate
        emoji = self.bot.emote_dict["skip"]

        voter = ctx.author
        if voter == player.current.requester:
            player.skip()  # Song requester can skip.
            await ctx.react(emoji)

        elif voter.guild_permissions.manage_guild:
            player.skip()  # Server mods can skip.
            await ctx.react(emoji)

        elif voter.id not in player.skip_votes:
            player.skip_votes.add(voter.id)
            total_votes = len(player.skip_votes)

            listeners = player.voice.channel.members
            valid_voters = [user for user in listeners if not user.bot]
            required_votes = valid_voters + 1 // 2  # Require majority

            if total_votes >= required_votes:
                player.skip()
                await ctx.react(emoji)
            else:
                await ctx.success(
                    f"Skip vote added, currently at `{total_votes}/{required_votes}`"
                )
        else:
            await ctx.fail("You have already voted to skip this track.")

    @decorators.command(
        aliases=["q"],
        name="queue",
        brief="Show the track queue.",
    )
    @checks.cooldown()
    @checks.bot_has_perms(add_reactions=True, external_emojis=True, embed_links=True)
    async def _queue(self, ctx):
        """
        Usage: {0}queue
        Alias: {0}q
        Output:
            Starts a pagination session showing
            all the tracks in the current queue.
        Notes:
            Each page contains 10 queue elements.
        """
        if len(ctx.voice_state.tracks) == 0:
            await ctx.fail("The queue is currently empty.")
            return

        entries = [track.hyperlink for track in ctx.voice_state.tracks]
        p = pagination.SimplePages(entries, per_page=10, index=True)
        p.embed.title = "Current Queue"

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    @decorators.command(
        name="clear",
        aliases=["c"],
        brief="Clear the queue.",
    )
    @checks.cooldown()
    async def _clear(self, ctx):
        """
        Usage: {0}clear
        Alias: {0}c
        Output:
            Removes all queued tracks
        """
        if len(ctx.voice_state.tracks) == 0:
            return await ctx.fail("The queue is already empty")
        ctx.voice_state.tracks.clear()
        await ctx.success("Cleared all tracks from the queue.")

    @decorators.command(
        name="shuffle",
        brief="Shuffle the queue.",
    )
    @checks.cooldown()
    async def _shuffle(self, ctx):
        """
        Usage: {0}shuffle
        Output: Shuffles the queue.
        """
        vs = ctx.voice_state

        if len(vs.tracks) == 0:
            await ctx.fail("The queue is currently empty.")
            return

        vs.tracks.shuffle()
        await ctx.send_or_reply(f"{self.bot.emote_dict['shuffle']} Shuffled the queue.")

    @decorators.command(
        aliases=["pop"],
        name="remove",
        brief="Remove a track from the queue.",
    )
    @checks.cooldown()
    async def _remove(self, ctx, index: int):
        """
        Usage: {0}remove [index]
        Alias: {0}pop
        Output:
            Removes a song from the queue at a given index.
        """
        vs = ctx.voice_state

        if len(vs.tracks) == 0:
            await ctx.fail("The queue is already empty")
            return

        try:
            vs.tracks.remove(index - 1)
        except Exception:
            await ctx.fail("Invalid index.")
            return

        await ctx.success(f"Removed item `{index}` from the queue.")

    @decorators.command(
        aliases=["deloop"],
        name="unloop",
        brief="Un-loop the track or queue.",
    )
    @checks.cooldown()
    async def _unloop(self, ctx):
        """
        Usage: {0}unloop
        Alias: {0}deloop
        Output:
            Stops looping the current song or queue
        """
        player = ctx.voice_state.validate

        player.track_is_looped = False
        player.queue_is_looped = False

        await ctx.react(self.bot.emote_dict["success"])

    @decorators.command(
        aliases=["repeat"],
        name="loop",
        brief="Loop the track or queue.",
    )
    @checks.cooldown()
    async def _loop(self, ctx, option: converters.SingleOrQueue = "single"):
        """
        Usage: {0}loop [option]
        Output: Loops the currently playing song.
        """
        player = ctx.voice_state.validate

        if option == "single":
            setting = "already" if player.track_is_looped else "now"
            player.track_is_looped = True
            await ctx.success(f"The current track is {setting} looped.")
        else:
            setting = "already" if player.queue_is_looped else "now"
            player.queue_is_looped = True
            player.track_is_looped = False  # In case we were looping a single track.
            await ctx.success(f"The current queue is {setting} looped.")
        await ctx.react(self.bot.emote_dict["loop"])

    @decorators.command(
        aliases=["jump"],
        name="seek",
        brief="Seek to a position in the track.",
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
        player = ctx.voice_state.validate

        if position < 0:
            await ctx.fail("Seek time cannot be negative.")
            return

        if position > player.current.raw_duration:
            track_dur = f"Track duration: `{player.current.raw_duration} seconds`"
            await ctx.fail(f"You cannot seek past the end of the track. {track_dur}")
            return

        player.alter_audio(position=position)
        await ctx.success(f"{ctx.invoked_with.capitalize()}ed to second `{position}`")

    @decorators.command(
        aliases=["ff", "ffw"],
        name="fastforward",
        brief="Fast forward the track.",
    )
    @checks.cooldown()
    async def _fastforward(self, ctx, seconds: int = 0):
        """
        Usage: {0}fastforward [seconds]
        Alias: {0}ff
        Output:
            Fast forward a certain number of seconds in a song.
        """
        player = ctx.voice_state.validate
        src = player.current
        current_position = player.source.position

        if seconds < 0:
            await ctx.invoke(self._rewind, abs(seconds))
            return

        position = seconds + current_position

        if position > src.raw_duration:
            current_pos = (
                f"`Current position: {current_position}/{src.raw_duration} seconds`"
            )
            await ctx.fail(
                f"You cannot fast forward past the end of the song. {current_pos}"
            )
            return

        player.alter_audio(position=position)
        await ctx.success(f"Fast forwarded to second `{position}`")

    @decorators.command(
        aliases=["rw"],
        name="rewind",
        brief="Rewind a number of seconds",
    )
    @checks.cooldown()
    async def _rewind(self, ctx, seconds: int = 0):
        """
        Usage: {0}rewind [seconds]
        Alias: {0}rw
        Output:
            Rewind a certain number of seconds in a song.
        """
        player = ctx.voice_state.validate
        current_position = player.source.position

        if seconds < 0:
            await ctx.invoke(self._fastforward, abs(seconds))
            return

        position = current_position - seconds

        if position < 0:
            ratio = f"{current_position}/{player.current.raw_duration}"
            current_pos = f"`Current position: {ratio} seconds`"
            await ctx.fail(
                f"You cannot rewind past the beginning of the track. {current_pos}"
            )
            return

        player.alter_audio(position=position)
        await ctx.success(f"Rewinded to second `{position}`")

    @decorators.command(
        aliases=["tempo"],
        name="speed",
        brief="Alter the speed of the track.",
    )
    @checks.cooldown()
    async def _speed(self, ctx, speed: float = None):
        """
        Usage: {0}speed [speed]
        Alias: {0}tempo
        Output:
            Speed up or slow down the current song.
        Notes:
            The speed must be between 0.5 and 2.0
        """
        player = ctx.voice_state.validate
        emoji = self.bot.emote_dict["music"]

        if speed is None:  # Output the current speed
            await ctx.send(f"{emoji} The audio speed is currently `{player.speed}x`")
            return

        player.speed = speed
        await ctx.send_or_reply(f"{emoji} Audio is now playing at `{speed}x`")

    @decorators.command(
        name="pitch",
        brief="Alter the pitch of the player.",
    )
    @checks.cooldown()
    async def _pitch(self, ctx, pitch: float = None):
        """
        Usage: {0}subtitles
        Alias: {0}lyrics
        Output:
            Attemps to generate subtitles for the current track.
            May not be available.
        """
        player = ctx.voice_state.validate
        emoji = self.bot.emote_dict["music"]

        if pitch is None:  # Output the current speed
            await ctx.send(f"{emoji} The audio pitch is currently `{player.pitch}`")
            return

        player.pitch = pitch
        await ctx.send_or_reply(f"{emoji} Audio pitch set to `{player.pitch}`")

    @decorators.command(
        aliases=["last", "back", "previous"],
        name="replay",
        brief="Play the previous track.",
    )
    @checks.cooldown()
    async def _replay(self, ctx):
        """
        Usage: {0}replay [seconds]
        Alias: {0}last, {0}back, {0}previous
        Output:
            Replay the last song to be played.
        """
        previous = ctx.voice_state.previous
        if not previous:
            await ctx.fail("No previous song to play.")
            return

        ctx.voice_state.replay(previous)

        emoji = self.bot.emote_dict["music"]
        await ctx.send_or_reply(f"{emoji} Requeued the previous song: {previous}")

    @decorators.command(
        aliases=["relocate", "switch"],
        name="move",
        brief="Move a song in the queue.",
    )
    @checks.cooldown()
    async def _move(self, ctx, index: int, position: int):
        """
        Usage: {0}move <index> <position>
        Alias: {0}switch, {0}relocate
        Output:
            Move a song to a new position in the queue.
        """
        total = len(ctx.voice_state.tracks)
        if total == 0:
            return await ctx.fail("The queue is currently empty.")
        elif index > total or index < 1:
            return await ctx.fail("Invalid index.")
        elif position > total or position < 1:
            return await ctx.fail("Invalid position.")
        elif index == position:
            await ctx.success("Song queue remains unchanged.")
            return

        song = ctx.voice_state.tracks.pop(index - 1)

        ctx.voice_state.tracks.insert(position - 1, song)

        await ctx.success(
            f"Moved song #{index} to the {utils.number_format(position)} position in the queue."
        )

    @decorators.command(
        aliases=["pos"],
        name="position",
        brief="Show the position of the song.",
    )
    @checks.cooldown()
    async def _position(self, ctx):
        """
        Usage: {0}position
        Alias: {0}pos
        Output:
            Shows the current position of the song
        """
        player = ctx.voice_state.validate

        if not player.is_playing:
            await ctx.fail("Nothing is currently being played.")
            return

        dur = player.current.duration
        raw = player.current.raw_duration
        pos = player.source.position
        await ctx.success(f"Current position: {dur} `({pos}/{raw}) seconds`")

    @decorators.command(
        name="youtube",
        aliases=["yt", "ytsearch"],
        brief="Search for a youtube video.",
    )
    @checks.bot_has_perms(embed_links=True)
    @checks.bot_has_guild_perms(connect=True, speak=True)
    @checks.cooldown()
    async def _youtube(self, ctx, *, search: str):
        """
        Usage: {0}youtube <search>
        Alias: {0}yt, {0}ytsearch
        Output:
            Searches youtube and returns an embed
            of the first 10 results collected.
        Notes:
            Choose one of the titles by typing a number
            or cancel by typing "cancel".
            Each title in the list can be clicked as a link.
        """
        await ctx.trigger_typing()
        player = await self.ensure_voice_state(ctx)
        try:
            source = await YTDLSource.search_source(
                ctx,
                search,
                loop=self.bot.loop,
            )
        except exceptions.YTDLError as e:
            await ctx.fail(f"Request failed: {e}")
        else:
            if source == "sel_invalid":
                await ctx.fail("Invalid selection")
            elif source == "cancel":
                await ctx.fail("Cancelled")
            elif source == "timeout":
                await ctx.fail("Timer expired")
            else:
                player.tracks.put_nowait(source)
                await ctx.send_or_reply(
                    f"{self.bot.emote_dict['music']} Queued {source}"
                )

    @decorators.command(
        name="playnext",
        brief="Add a song to the front of the queue.",
        aliases=["pn"],
    )
    @checks.bot_has_guild_perms(connect=True, speak=True)
    @checks.cooldown()
    async def _playnext(self, ctx, *, search: str = None):
        """
        Usage: {0}play <search>
        Alias: {0}p
        Output:
            Plays a song from your selection.
        Notes:
            If there are tracks in the queue,
            this will be queued before
            all other tracks in the queue.
        """
        await ctx.trigger_typing()
        player = await self.ensure_voice_state(ctx)
        MUSIC = self.bot.emote_dict['music']

        if search is None:
            # No search, check for resume command.

            if player.is_playing and player.voice.is_paused():
                # Player has likely been paused.
                ctx.voice_state.voice.resume()  # Resume playback,
                await ctx.message.add_reaction(self.bot.emote_dict["play"])
                await ctx.success("Resumed the player")
                return
            else:
                await ctx.usage()
                return

        song_url = AudioUtils.reformat_uri(search)

        if song_url.startswith("spotify:"):
            if not self.spotify:
                raise exceptions.FeatureNotSupported(
                    "Spotify support is currently unavailable."
                )
            parts = song_url.split(":")
            try:
                if "track" in parts:
                    res = await self.spotify.get_track(parts[-1])
                    song_url = res["artists"][0]["name"] + " " + res["name"]

                elif "album" in parts:
                    res = await self.spotify.get_album(parts[-1])
                    tracks = AudioUtils.put_spotify_tracks(
                        ctx, res["tracks"]["items"]
                    )
                    player.tracks.extend_left(tracks)
                    await ctx.send_or_reply(f"{MUSIC} Front Queued {len(tracks)} spotify tracks.")
                    return

                elif "artist" in parts:
                    res = await self.spotify.get_artist(parts[-1])
                    tracks = AudioUtils.put_spotify_tracks(ctx, res["tracks"])
                    player.tracks.extend_left(tracks)
                    await ctx.send_or_reply(f"{MUSIC} Front Queued {len(tracks)} spotify tracks.")
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

                    tracks = AudioUtils.put_spotify_playlist(ctx, res)
                    player.tracks.extend_left(tracks)
                    await ctx.send_or_reply(f"{MUSIC} Front Queued {len(tracks)} spotify tracks.")
                    return

                else:
                    await ctx.fail("Invalid Spotify URI.")
                    return
            except exceptions.SpotifyError as e:
                await ctx.fail("Invalid Spotify URI.")
                return

        if "youtube.com/playlist" in song_url:
            try:
                tracks, playlist = await YTDLSource.get_playlist_tracks(
                    ctx, song_url, loop=self.bot.loop
                )
            except exceptions.YTDLError as e:
                await ctx.fail(f"Request failed: {e}")
            else:
                player.tracks.extend_left(tracks)
                await ctx.send_or_reply(f"{MUSIC} Front Queued Playlist: {playlist} `({len(tracks)} tracks)`")

            return
        try:
            track = await YTDLSource.get_song(ctx, song_url, loop=self.bot.loop)
        except exceptions.YTDLError as e:
            await ctx.fail(f"Request failed: {e}")
        else:
            player.tracks.append_left(track)
            await ctx.send_or_reply(f"{MUSIC} Front Queued {track}")

    @decorators.command(
        name="play",
        brief="Play a song from a search or URL.",
        aliases=["p"],
    )
    @checks.bot_has_guild_perms(connect=True, speak=True)
    @checks.cooldown()
    async def _play(self, ctx, *, search: str = None):
        """
        Usage: {0}play <search>
        Alias: {0}p
        Output:
            Plays a song from your search.
        Notes:
            If there are tracks in the queue,
            this will be queued until the
            other tracks finished playing.
            This command automatically searches
            youtube if no url is provided.
            Accepts spotify and youtube urls.
        """
        await ctx.trigger_typing()
        player = await self.ensure_voice_state(ctx)
        MUSIC = self.bot.emote_dict['music']

        if search is None:
            # No search, check for resume command.

            if player.is_playing and player.voice.is_paused():
                # Player has likely been paused.
                ctx.voice_state.voice.resume()  # Resume playback,
                await ctx.message.add_reaction(self.bot.emote_dict["play"])
                await ctx.success("Resumed the player")
                return
            else:
                await ctx.usage()
                return

        song_url = AudioUtils.reformat_uri(search)

        if song_url.startswith("spotify:"):
            if not self.spotify:
                raise exceptions.FeatureNotSupported(
                    "Spotify support is currently unavailable."
                )
            parts = song_url.split(":")
            try:
                if "track" in parts:
                    res = await self.spotify.get_track(parts[-1])
                    song_url = res["artists"][0]["name"] + " " + res["name"]

                elif "album" in parts:
                    res = await self.spotify.get_album(parts[-1])
                    tracks = AudioUtils.put_spotify_tracks(
                        ctx, res["tracks"]["items"]
                    )
                    player.tracks.extend(tracks)
                    await ctx.send_or_reply(f"{MUSIC} Queued {len(tracks)} spotify tracks.")
                    return

                elif "artist" in parts:
                    res = await self.spotify.get_artist(parts[-1])
                    tracks = AudioUtils.put_spotify_tracks(ctx, res["tracks"])
                    player.tracks.extend(tracks)
                    await ctx.send_or_reply(f"{MUSIC} Queued {len(tracks)} spotify tracks.")
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

                    tracks = AudioUtils.put_spotify_playlist(ctx, res)
                    player.tracks.extend(tracks)
                    await ctx.send_or_reply(f"{MUSIC} Queued {len(tracks)} spotify tracks.")
                    return

                else:
                    await ctx.fail("Invalid Spotify URI.")
                    return
            except exceptions.SpotifyError as e:
                await ctx.fail("Invalid Spotify URI.")
                return

        if "youtube.com/playlist" in song_url:
            try:
                tracks, playlist = await YTDLSource.get_playlist_tracks(
                    ctx, song_url, loop=self.bot.loop
                )
            except exceptions.YTDLError as e:
                await ctx.fail(f"Request failed: {e}")
            else:
                player.tracks.extend(tracks)
                await ctx.send_or_reply(f"{MUSIC} Queued Playlist: {playlist} `({len(tracks)} tracks)`")

            return
        try:
            track = await YTDLSource.get_song(ctx, song_url, loop=self.bot.loop)
        except exceptions.YTDLError as e:
            await ctx.fail(f"Request failed: {e}")
        else:
            player.tracks.put_nowait(track)
            await ctx.send_or_reply(f"{MUSIC} Queued {track}")


    @decorators.command(
        brief="Play a discord file or url.",
        name="playfile",
        hidden=True
    )
    @checks.bot_has_guild_perms(connect=True, speak=True)
    async def _playfile(self, ctx, media_url = None):
        await ctx.trigger_typing()
        player = await self.ensure_voice_state(ctx)  # Initialize voice client.
        MUSIC = self.bot.emote_dict['music']  # Music emoji

        if len(ctx.message.attachments) > 0:  # User passed an attachment.
            file = ctx.message.attachments[0]
            if file.content_type not in ["audio/mpeg", "video/mp4"]:
                raise exceptions.InvalidMediaType  # Must be audio or video
            try:
                await player.play_from_file(file)
            except ClientException as e:
                raise commands.BadArgument(str(e))
            await ctx.send_or_reply(f"{MUSIC} Playing **{file.filename}**")

        else:  # Check for url regex
            regex = r"(https://|http://)?(cdn\.|media\.)discord(app)?\.(com|net)/attachments/[0-9]{17,19}/[0-9]{17,19}/(?P<filename>.{1,256})\.(?P<mime>[0-9a-zA-Z]{2,4})(\?size=[0-9]{1,4})?"
            pattern = re.compile(regex)
            match = pattern.match(media_url)
            if not match:  # We have a discord url.
                await ctx.fail(f"Invalid discord media url.")
                return

            await AudioUtils.read_url(match.group(0), self.bot.session)  # Get url bytes
            await player.play_local_file(match.group(0))
            await ctx.send_or_reply(f"{MUSIC} Playing `{match.group(0)}`")
