"""
Hello! This is the heart and soul of the Neutra's music module.
It contains four total cogs, the first for the player, the second
for the queue, third for voice management, and last for effects.
Also included are custom music checks, audio-specific utilities,
custom exceptions, a spotify api getter class, a guild-specific
VoiceState class, a custom TrackQueue that contains QueueEntry's,
Two audio source classes, YTDLSource, for creating a playable audio
source from youtube, and AudioSource, that plays the audio and is
responsible for managing volume and other effects. Finally, a group
Views class for managing the user interface for the effects command.
This module is entirely separate from the remainder of the client,
and can be removed with relative ease merely by deleting this file.
"""

from operator import is_
import re
import io
import json
import math
import time
import base64
import typing
import random
import aiohttp
import asyncio
import asyncpg
import discord
import logging
import functools
import itertools
import traceback
import youtube_dl

from datetime import datetime
from discord.ext import commands, tasks
from logging.handlers import RotatingFileHandler
from collections import deque, defaultdict
from PIL import Image

from settings import constants

from utilities import views
from utilities import checks
from utilities import helpers
from utilities import converters
from utilities import decorators

# Set up our music-specific logger.
log = logging.getLogger("MUSIC_LOGGER")
log.setLevel(logging.INFO)
if not log.handlers:
    handler = RotatingFileHandler(
        filename="./data/logs/music.log",
        encoding="utf-8",
        mode="w",
        maxBytes=30 * 1024 * 1024,
        backupCount=5,
    )
    log.addHandler(handler)
    formatter = logging.Formatter(
        fmt="{asctime}: [{levelname}] {name} || {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
        style="{",
    )
    handler.setFormatter(formatter)

# Silence useless bug reports messages
youtube_dl.utils.bug_reports_message = lambda: ""

#  Option base to avoid pull errors
FFMPEG_OPTION_BASE = (
    "-loglevel panic -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
)

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
    "ignoreerrors": False,  # TODO change to false and handle download errors
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


class exceptions:
    class InactivePlayer(commands.BadArgument):
        """
        Custom exception to raise when
        the music player is not active.
        """

        def __init__(self, *args):
            msg = "No track is currently being played."
            super().__init__(message=msg, *args)

    class FeatureNotSupported(commands.BadArgument):
        """
        Custom exception to raise when the user
        uses on a not yet implemented music feature.
        """

        def __init__(self, message=None, *args):
            msg = "Feature is currently not supported."
            super().__init__(message=message or msg, *args)

    class InvalidMediaType(commands.BadArgument):
        """
        Custom exception to raise when the
        file media type cannot be played.
        """

        def __init__(self, message=None, *args):
            msg = "Invalid media type. Media type must be either audio or video."
            super().__init__(message=message or msg, *args)

    class IsBound(commands.BadArgument):
        """
        Custom exception to raise when the
        bot is bound to a specific text channel.
        """

        def __init__(self, channel, *args):
            msg = f"Music commands cannot be used outside of {channel.mention}."
            super().__init__(message=msg, *args)

    class SpotifyError(Exception):
        pass

    class VoiceError(Exception):
        pass

    class YTDLError(Exception):
        pass

    class InvalidPosition(Exception):
        pass


class Spotify:
    # https://github.com/Just-Some-Bots/MusicBot
    OAUTH_TOKEN_URL = "https://accounts.spotify.com/api/token"
    API_BASE = "https://api.spotify.com/v1/"

    def __init__(self, client_id, client_secret, aiosession=None, loop=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.aiosession = aiosession if aiosession else aiohttp.ClientSession()
        self.loop = loop if loop else asyncio.get_event_loop()

        self.token = None

        self.loop.create_task(self.get_token())  # validate token

    def _make_token_auth(self, client_id, client_secret):
        auth_header = base64.b64encode(
            (client_id + ":" + client_secret).encode("ascii")
        )
        return {"Authorization": "Basic %s" % auth_header.decode("ascii")}

    async def get_tracks(self, track_ids):
        return [await self.get_track(track_id) for track_id in track_ids]

    async def get_track(self, uri):
        """Get a track's info from its URI"""
        return await self.make_spotify_req(self.API_BASE + "tracks/{0}".format(uri))

    async def get_album(self, uri):
        """Get an album's info from its URI"""
        return await self.make_spotify_req(self.API_BASE + "albums/{0}".format(uri))

    async def get_artist(self, uri):
        """Get an artist's info from its URI"""
        return await self.make_spotify_req(
            self.API_BASE + "artists/{0}/top-tracks?market=US".format(uri)
        )

    async def get_playlist(self, user, uri):
        """Get a playlist's info from its URI"""
        return await self.make_spotify_req(
            self.API_BASE + "users/{0}/playlists/{1}{2}".format(user, uri)
        )

    async def get_playlist_tracks(self, uri):
        """Get a list of a playlist's tracks"""
        return await self.make_spotify_req(
            self.API_BASE + "playlists/{0}/tracks".format(uri)
        )

    async def make_spotify_req(self, url):
        """Proxy method for making a Spotify req using the correct Auth headers"""
        token = await self.get_token()
        return await self.make_get(
            url, headers={"Authorization": "Bearer {0}".format(token)}
        )

    async def make_get(self, url, headers=None):
        """Makes a GET request and returns the results"""
        async with self.aiosession.get(url, headers=headers) as r:
            if r.status != 200:
                raise exceptions.SpotifyError(
                    "Issue making GET request to {0}: [{1.status}] {2}".format(
                        url, r, await r.json(content_type=None)
                    )
                )
            return await r.json()

    async def make_post(self, url, payload, headers=None):
        """Makes a POST request and returns the results"""
        async with self.aiosession.post(url, data=payload, headers=headers) as r:
            if r.status != 200:
                raise exceptions.SpotifyError(
                    "Issue making POST request to {0}: [{1.status}] {2}".format(
                        url, r, await r.json()
                    )
                )
            return await r.json()

    async def get_token(self):
        """Gets the token or creates a new one if expired"""
        if self.token and not await self.check_token(self.token):
            return self.token["access_token"]

        token = await self.request_token()
        if token is None:
            raise exceptions.SpotifyError(
                "Requested a token from Spotify, did not end up getting one"
            )
        token["expires_at"] = int(time.time()) + token["expires_in"]
        self.token = token
        return self.token["access_token"]

    async def check_token(self, token):
        """Checks a token is valid"""
        now = int(time.time())
        return token["expires_at"] - now < 60

    async def request_token(self):
        """Obtains a token from Spotify and returns it"""
        payload = {"grant_type": "client_credentials"}
        headers = self._make_token_auth(self.client_id, self.client_secret)
        r = await self.make_post(self.OAUTH_TOKEN_URL, payload=payload, headers=headers)
        return r


class MusicUtils:
    """
    Utility class that houses information
    and spotify-related helper functions.
    """

    def get_key(key: str = ""):
        """ Fetch a key from the config file """
        with open("config.json", encoding="utf8") as data:
            config = json.load(data)
        return config.get(key)

    def spotify(bot):
        """
        Create utiliites.spotify.Spotify() instance
        from credentials found in ./config.json
        """
        client_id = MusicUtils.get_key("spotify_client_id")
        client_secret = MusicUtils.get_key("spotify_client_secret")

        if client_id and client_secret:
            return Spotify(
                client_id=client_id,
                client_secret=client_secret,
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

    def number_format(number):
        if str(number).endswith("1") and number != 11:
            fmt = str(number) + "st"
        elif str(number).endswith("2") and number != 12:
            fmt = str(number) + "nd"
        elif str(number).endswith("3") and number != 13:
            fmt = str(number) + "rd"
        else:
            fmt = str(number) + "th"
        return fmt

    def get_image_progress_bar(ctx, ratio, length=800, width=80):
        GRAY = ctx.bot.constants.Colors.GRAY
        BLUE = ctx.bot.constants.Colors.BLUE
        bar_length = ratio * length
        a = 0
        b = -1
        c = width / 2
        w = (width / 2) + 1

        shell = Image.new("RGB", (length, width), color=GRAY)
        imgsize = (int(bar_length), width)  # The size of the image
        image = Image.new("RGB", imgsize, color=GRAY)  # Create the image

        innerColor = BLUE  # Color at the center
        outerColor = [0, 0, 0]  # Color at the edge

        for y in range(imgsize[1]):
            for x in range(imgsize[0]):

                dist = (a * x + b * y + c) / math.sqrt(a * a + b * b)
                color_coef = abs(dist) / w

                if abs(dist) < w:
                    red = outerColor[0] * color_coef + innerColor[0] * (1 - color_coef)
                    green = outerColor[1] * color_coef + innerColor[1] * (
                        1 - color_coef
                    )
                    blue = outerColor[2] * color_coef + innerColor[2] * (1 - color_coef)

                    image.putpixel((x, y), (int(red), int(green), int(blue)))

        shell.paste(image)
        buffer = io.BytesIO()
        shell.save(buffer, "png")  # 'save' function for PIL
        buffer.seek(0)
        return buffer

    def make_embed(ctx, source):
        MUSIC = ctx.bot.constants.emotes["music"]
        LIKE = ctx.bot.constants.emotes["like"]
        DISLIKE = ctx.bot.constants.emotes["dislike"]

        block = None
        embed = None
        ytdl = source.ytdl
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
            if ytdl.is_live:
                footer = "LIVE"
                percent = 1
            else:
                percent = source.position / ytdl.raw_duration
                position = MusicUtils.parse_duration(int(source.position))
                if percent > 1:
                    percent = 1
                footer = f"{position} ({percent:.2%} completed)"

            embed.set_footer(text=f"Current Position: {footer}")

            # if ctx.channel.permissions_for(ctx.me).attach_files:
            #     # Try to make a nice image progress bar if bot has perms.
            #     progress = await ctx.bot.loop.run_in_executor(
            #         None, MusicUtils.get_image_progress_bar, ctx, percent
            #     )
            #     embed.set_image(url=f"attachment://progress.png")
            #     file = discord.File(progress, filename="progress.png")
            # else:
            #     embed.add_field(
            #         name="Progress", value=MusicUtils.get_progress_bar(percent)
            #     )
            embed.set_image(url=ctx.bot.constants.progress_bars[round(percent * 100)])
        return embed

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
        ytdl = source.ytdl

        if ctx.channel.permissions_for(ctx.me).embed_links:
            embed = MusicUtils.make_embed(ctx, source)

        else:  # No embed perms, send as codeblock
            block = f"{MUSIC} **Now Playing**: *{ytdl.title}*```yaml\n"
            block += f"Duration : {ytdl.duration}\n"
            block += f"Requester: {ytdl.requester.display_name}\n"
            block += f"Uploader : {ytdl.uploader}\n"
            block += f"Link     : {ytdl.url}\n"
            block += f"Likes    : {ytdl.likes:,}\n"
            block += f"Dislikes : {ytdl.dislikes:,}\n```"

        return await ctx.send(content=block, embed=embed)

    def get_progress_bar(percent, decimals=2, length=50, fill="█"):
        length = length / 2
        portion = length * percent
        percent_str = ("{0:." + str(decimals) + "f}").format(percent * 100)
        bar = fill * int(portion) + "—" * (int((length - portion)))
        return f"\r│{bar}│{percent_str}%"

    async def save_embed(ctx, ytdl):
        MUSIC = ctx.bot.constants.emotes["music"]
        LIKE = ctx.bot.constants.emotes["like"]
        DISLIKE = ctx.bot.constants.emotes["dislike"]
        embed = discord.Embed(color=ctx.bot.constants.embed)
        embed.title = "Track Information"
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
        try:
            await ctx.author.send(f"Saved {str(ytdl)} to your liked songs", embed=embed)
        except Exception:
            if ctx.channel.permissions_for(ctx.me).embed_links:
                await ctx.send(f"Saved {str(ytdl)} to your liked songs", embed=embed)
            else:
                block = f"Saved **{ytdl}** to your liked songs```yaml\n"
                block += f"Duration : {ytdl.duration}\n"
                block += f"Requester: {ytdl.requester.display_name}\n"
                block += f"Uploader : {ytdl.uploader}\n"
                block += f"Link     : {ytdl.url}\n"
                block += f"Likes    : {ytdl.likes:,}\n"
                block += f"Dislikes : {ytdl.dislikes:,}\n```"
                await ctx.send(block)
        else:
            await ctx.success(f"Saved the current track to your liked songs.")

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
                track["artists"][0]["name"] + " " + track["name"],
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
                link=item["track"]["external_urls"].get("spotify"),
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


class Checks:
    def is_active(ctx):
        voice = ctx.voice_state.voice
        if voice:
            if voice.channel:
                if len([m for m in voice.channel.members if not m.bot]) != 0:
                    return True

    def assert_is_dormant(ctx):
        if Checks.is_active(ctx):
            raise commands.BadArgument(
                f"Bot is currently active in {ctx.voice_state.voice.channel}."
            )

    def is_alone(ctx):
        """Checks if the user is alone with the bot in a voice channel"""
        voice = ctx.voice_state.voice
        if not voice:
            return True
        if not voice.channel:
            return True
        channel_members = [m for m in voice.channel.members if not m.bot]
        if len(channel_members) == 1 and ctx.author in channel_members:
            return True
        return False

    def is_dj(ctx):
        djrole = ctx.voice_state.djrole
        if djrole and djrole in ctx.author.roles:
            return True
        if Checks.is_alone(ctx):
            return True
        if ctx.author.guild_permissions.deafen_members:
            return True
        if ctx.author.guild_permissions.move_members:
            return True
        if ctx.author.guild_permissions.mute_members:
            return True
        return False

    def is_requester(ctx):
        player = ctx.voice_state.validate
        requester = player.current.requester
        return requester == ctx.author

    def assert_is_dj(ctx):
        if not Checks.is_dj(ctx):
            raise commands.BadArgument(
                "You must have the `Manage Channels` permission, have a DJ role, or be alone in the voice channel to use this command."
            )

    def raise_if_bound(ctx):
        bind = ctx.voice_state.bind
        if bind:
            if ctx.channel != bind:
                raise commands.BadArgument(
                    f"Music commands cannot be used outside of {bind.mention}."
                )

    def raise_if_locked(ctx):
        lock = ctx.voice_state.djlock
        if lock:
            if not Checks.is_dj(ctx):
                raise commands.BadArgument(
                    "The music module has been locked to DJs only."
                )

    def is_manager(ctx):
        if ctx.author.guild_permissions.manage_roles:
            return True
        if ctx.author.guild_permissions.manage_guild:
            return True
        return False

    def assert_is_manager(ctx):
        if not Checks.is_manager(ctx):
            raise commands.BadArgument(
                "You must have the `Manage Roles` or the `Manage Guild` permission to use this command."
            )


class QueueEntry:
    """
    QueueEntry object for enqueueing tracks.
    All TrackQueue objects are type QueueEntry
    """

    def __init__(self, ctx, title, search, *, data=None, uploader=None, link=None):
        self.ctx = ctx
        self.requester = ctx.author
        self.title = title
        self.search = search

        self.data = data
        self.uploader = uploader
        self.link = link

    def __str__(self):
        if self.uploader:
            return f"**{self.title}** by **{self.uploader}**"
        return f"**{self.title}**"

    def __eq__(self, other):
        if isinstance(other, QueueEntry):
            return self.search == other.search and self.title == other.title
        else:
            return self is other

    def __hash__(self):
        return hash((self.search, self.title))

    @property
    def hyperlink(self):
        return f"**[{self.title}]({self.link or self.search})**"

    @property
    def has_data(self):
        if self.data:
            return True
        return False

    @property
    def json(self):
        """ Returns a json representation of QueueEntry. """
        json_entry = {
            "title": self.title,
            "search": self.search,
            "uploader": self.uploader,
            "link": self.link,
        }
        return json_entry


class Playlist:
    """
    QueueEntry object for enqueueing tracks.
    All TrackQueue objects are type QueueEntry
    """

    def __init__(self, ctx, record):
        self.ctx = ctx
        self.bot = ctx.bot
        self.record = record
        self.queue = json.loads(record.get("queue"))
        self.entries = [
            QueueEntry(
                ctx,
                track.get("title"),
                track.get("search"),
                uploader=track.get("uploader"),
                link=track.get("link"),
            )
            for track in self.queue
        ]
        self.tracks = len(self.queue)
        self.id = record.get("id")
        self.likes = record.get("likes")
        self.owner = self.bot.get_user(record.get("owner_id"))
        self.name = record.get("name")
        self.uses = record.get("uses", 0)
        self.created_at = record.get("insertion")

    def is_owner(self, user):
        return user.id == self.owner.id

    @classmethod
    async def initialize(cls, ctx, owner, name: str):
        query = """
                SELECT * FROM playlists
                WHERE owner_id = $1
                AND name = $2
                """
        record = await ctx.bot.cxn.fetchrow(query, owner.id, name.lower())
        if not record:
            raise commands.BadArgument(
                f"You do not have a playlist with name: **{name}**"
            )
        return cls(ctx, record)

    @classmethod
    async def get_playlists(cls, ctx, owner):
        query = """
                SELECT * FROM playlists
                WHERE owner_id = $1
                """
        records = await ctx.bot.cxn.fetch(query, owner.id)
        if not records:
            raise commands.BadArgument(
                f"**{owner}** `{owner.id}` has no saved playlists."
            )
        return [cls(ctx, record) for record in records]

    async def finalize(self):
        query = """
                UPDATE playlists
                SET queue = $1
                WHERE owner_id = $2
                AND name = $3
                """
        return await self.bot.cxn.execute(
            query, json.dumps(self.queue), self.owner.id, self.name.lower()
        )

    async def delete(self):
        query = """
                DELETE FROM playlists
                WHERE owner_id = $1
                AND name = $2;
                """
        return await self.bot.cxn.execute(query, self.owner.id, self.name.lower())

    def pop(self, index: int):
        try:
            return self.queue.pop(index - 1)
        except IndexError:
            raise IndexError(
                "Invalid index. Please specify a valid track index to remove."
            )

    async def like(self):
        query = """
                UPDATE playlists
                SET likes = likes + 1
                WHERE owner_id = $1
                AND name = $2
                """
        await self.bot.cxn.execute(query, self.owner.id, self.name.lower())


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
        self.duration = MusicUtils.parse_duration(int(data.get("duration")))
        self.tags = data.get("tags")
        self.url = data.get("webpage_url")
        self.views = data.get("view_count", 0)
        self.likes = data.get("like_count", 0)
        self.dislikes = data.get("dislike_count", 0)
        self.stream_url = data.get("url")

    @property
    def hyperlink(self):
        return f"**[{self.title}]({self.url})**"

    @property
    def is_live(self):
        if self.raw_duration == 0:
            return True
        return False

    def __str__(self):
        return "**{0.title}** by **{0.uploader}**".format(self)

    @classmethod
    async def get_source(cls, ctx, url, *, loop=None):
        """
        Takes a search query and returns the first result.
        """
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(YOUTUBE_DL.extract_info, url, download=False)
        processed_info = None  # TODO fix this system
        try:
            processed_info = await loop.run_in_executor(None, partial)
        except youtube_dl.DownloadError as e:
            if "urlopen error unknown url type" in str(e):
                log.warning("Suspected error caused by colon in search query.")
                try:
                    partial = functools.partial(
                        YOUTUBE_DL.extract_info,
                        url.replace(":", ""),
                        download=False,
                        process=False,
                    )
                    processed_info = await loop.run_in_executor(None, partial)
                    log.info("Attempting re-searching with altered url.")
                except Exception as e:
                    log.error(f"Re-searching failed: {e}")
            else:
                log.error(traceback.format_exc())

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
            YOUTUBE_DL.extract_info,
            search,
            download=False,
            process=False,
        )
        info = None  # TODO fix this system
        try:
            info = await loop.run_in_executor(None, partial)
        except youtube_dl.DownloadError as e:
            if "urlopen error unknown url type" in str(e):
                log.warning("Suspected error caused by colon in search query.")
                try:
                    partial = functools.partial(
                        YOUTUBE_DL.extract_info,
                        search.replace(":", ""),
                        download=False,
                        process=False,
                    )
                    info = await loop.run_in_executor(None, partial)
                    log.info("Attempting re-searching with altered url.")
                except Exception as e:
                    log.error(f"Re-searching failed: {e}")
            else:
                log.error(traceback.format_exc())

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
            try:
                processed_info = await loop.run_in_executor(None, partial)
            except youtube_dl.DownloadError as e:
                if "This video may be inappropriate for some users." in str(e):
                    raise exceptions.YTDLError("Unable to play age restricted videos.")
                else:
                    raise exceptions.YTDLError(
                        f"Unable to download `{info['webpage_url']}`"
                    )

            if processed_info is None:
                raise exceptions.YTDLError(f"Unable to fetch `{info['webpage_url']}`")

            if "entries" not in processed_info:
                data = processed_info
            else:
                data = None
                while data is None:
                    try:
                        data = processed_info["entries"].pop(0)
                    except IndexError as e:
                        raise exceptions.YTDLError(
                            f"Unable to retrieve matches for `{processed_info['webpage_url']}`"
                        )

            url = data.get("webpage_url")
            title = data.get("title")
            uploader = data.get("uploader")

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

        return (
            [
                QueueEntry(
                    ctx,
                    entry["title"],
                    format_url(entry["url"]),
                    uploader=entry.get("uploader"),
                )
                for entry in info["entries"]
                if pred(entry) is True
            ],
            playlist,
        )

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
            url=f"{ctx.author.display_avatar.url}",
            icon_url=f"{ctx.author.display_avatar.url}",
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
            return deque(
                itertools.islice(self._queue, item.start, item.stop, item.step)
            )
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

    def reverse(self):
        self._queue.reverse()

    def skipto(self, place):
        entry = self._queue[place]
        self._queue = self[place + 1 :]
        return entry

    def deduplicate(self):
        self._queue = deque(set(self))

    def leave_cleanup(self, users):
        for entry in list(self._queue):
            if entry.requester not in users:
                self._queue.remove(entry)

    def dequeue(self, user):
        for entry in list(self._queue):
            if entry.requester == user:
                self._queue.remove(entry)

    def clear_range(self, start, end):
        queue = list(self._queue)
        del queue[start - 1 : end]
        self._queue = deque(queue)

    def shuffle_range(self, start, end):
        queue = list(self._queue)
        to_shuffle = queue[start - 1 : end]
        random.shuffle(to_shuffle)
        queue[start - 1 : end] = to_shuffle
        self._queue = deque(queue)

    def reverse_range(self, start, end):
        queue = list(self._queue)
        to_reverse = queue[start - 1 : end]
        to_reverse.reverse()
        queue[start - 1 : end] = to_reverse
        self._queue = deque(queue)


class VoiceClient(discord.VoiceClient):
    def __init__(self, client, channel):
        super().__init__(client, channel)

    async def on_voice_state_update(self, data) -> None:
        self.session_id = data["session_id"]
        channel_id = data["channel_id"]

        if not self._handshaking or self._potentially_reconnecting:
            # If we're done handshaking then we just need to update ourselves
            # If we're potentially reconnecting due to a 4014, then we need to differentiate
            # a channel move and an actual force disconnect
            if channel_id is None:
                # We're being disconnected so cleanup
                await VOICE_STATES[self.guild.id].stop()
            else:
                guild = self.guild
                self.channel = channel_id and guild and guild.get_channel(int(channel_id))  # type: ignore
        else:
            self._voice_state_complete.set()


class AudioSource(discord.PCMVolumeTransformer):
    """
    Takes a ytdl source and player settings
    and returns a FFmpegPCMAudio source.
    """

    def __init__(self, ytdl, volume, position: float = 0.0, **kwargs):
        self.ytdl = ytdl
        self.position = position
        self.rate = speed = kwargs.get("speed", 1)
        pitch = kwargs.get("pitch", 1)

        s_filter = f"atempo=sqrt({speed}/{pitch}),atempo=sqrt({speed}/{pitch})"
        p_filter = f",asetrate=48000*{pitch}" if pitch != 1 else ""

        base = s_filter + p_filter

        filters = {  # Mapping of filters to their names
            "nightcore": ",asetrate=48000*1.1",
            "earrape": ",acrusher=.1:1:64:0:log",
            "echo": ",aecho=0.5:0.5:500|50000:1.0|1.0",
            "muffle": ",lowpass=f=300",
            "treble": ",treble=g=15",
            "bass": ",bass=g=15",
            # "backwards": ",areverse",
            "phaser": ",aphaser=type=t:speed=2:decay=0.6",
            "robot": ",afftfilt=real='hypot(re,im)*sin(0)':imag='hypot(re,im)*cos(0)':win_size=512:overlap=0.75",
            "tremolo": ",apulsator=mode=sine:hz=3:width=0.1:offset_r=0",
            "vibrato": ",vibrato=f=10:d=1",
            "whisper": ",afftfilt=real='hypot(re,im)*cos((random(0)*2-1)*2*3.14)':imag='hypot(re,im)*sin((random(1)*2-1)*2*3.14)':win_size=128:overlap=0.8",
        }

        effects = "".join([y for x, y in filters.items() if kwargs.get(x)])
        ffmpeg_options = {
            "before_options": FFMPEG_OPTION_BASE + f" -ss {position}",
            "options": f'-vn -af:a "{base + effects}"',
        }

        self.original = discord.FFmpegPCMAudio(ytdl.stream_url, **ffmpeg_options)
        super().__init__(self.original, volume=volume)

    @staticmethod
    async def save(ytdl, volume, position=0, **kwargs):
        """Returns a class instance and saves track."""
        cxn = ytdl.ctx.bot.cxn
        if cxn:
            query = """
                    INSERT INTO tracks (requester_id, title, url, uploader)
                    VALUES ($1, $2, $3, $4)
                    """
            await cxn.execute(
                query, ytdl.requester.id, ytdl.title, ytdl.url, ytdl.uploader
            )
        return await AudioSource.check_source(ytdl, volume, position, **kwargs)

    @classmethod
    async def check_source(cls, ytdl, volume, position, **kwargs):
        asession = ytdl.ctx.bot.session
        async with asession.get(str(ytdl.stream_url)) as r:
            if r.status == 403:  # Forbidden stream url.
                log.info("Forbidden Stream URL. Redownloading...")

                ctx = ytdl.ctx
                url = ytdl.url
                loop = ytdl.ctx.bot.loop
                try:
                    ytdl = await YTDLSource.get_source(ctx, url, loop=loop)
                except exceptions.YTDLError as e:
                    log.error(f"Redownload failed: {e}")
                    return
                else:
                    log.info("Redownload successful")
        return cls(ytdl, volume, position, **kwargs)


class VoiceState:
    """
    Responsible for audio playing and manipulation.
    Guilds receive a cached instance in ctx.voice_state.
    """

    def __init__(self, bot, ctx, *, bind=None, djrole=None, djlock=False):
        self.bot = bot
        self._ctx = ctx

        self.source = None  # Audio source.
        self.entry = None  # The QueueEntry track.
        self.current = None  # Current track.
        self.previous = None  # Previous track.
        self.voice = None  # Guild voice client.

        self._volume = 0.5  # Volume default.
        self.effects = {}

        self.track_is_looped = False  # Single track is looped.
        self.queue_is_looped = False  # Entire queue is looped.

        self.skip_votes = set()  # Stored skip votes.

        self.tracks = TrackQueue()
        self.next = asyncio.Event()

        self.bind = bind
        self.djrole = djrole
        self.djlock = djlock

        self.audio_player = bot.loop.create_task(self.audio_player_task())
        self.incrementer = bot.loop.create_task(self.increment_position())

    def __del__(self):
        self.audio_player.cancel()
        self.incrementer.cancel()

    def __setitem__(self, key, value):
        if key == "speed":  # Assert valid speed range
            if not 0.5 <= value <= 2.0:
                raise commands.BadArgument("Speed must be between `0.5` and `2.0`")
        if key == "pitch":  # Assert valid pitch range
            if not 0.5 <= value <= 2.0:
                raise commands.BadArgument("Pitch must be between `0.5` and `2.0`")

        self.effects.__setitem__(key, value)
        self.alter_audio()

    def __getitem__(self, key):  # Return false by default
        if key == "speed":  # Speed = 1 by default
            return self.effects.get(key, 1)
        if key == "pitch":  # Pitch = 1 by default
            return self.effects.get(key, 1)

        # Other effects are False by default
        return self.effects.get(key, False)

    async def stop(self):
        self.tracks.clear()

        if self.voice:
            await self.voice.disconnect(force=True)

        self.audio_player.cancel()
        self.incrementer.cancel()

        del VOICE_STATES[self._ctx.guild.id]

    def clear_effects(self):
        self.effects.clear()
        self.alter_audio()

    @classmethod
    async def create(cls, bot, ctx):
        bind = None
        djrole = None
        djlock = False
        query = """
                SELECT bind, djrole, djlock
                FROM musicconf
                WHERE server_id = $1
                """
        record = await bot.cxn.fetchrow(query, ctx.guild.id)
        if record:
            bind = bot.get_channel(record["bind"])
            djrole = ctx.guild.get_role(record["djrole"])
            djlock = ctx.guild.get_role(record["djlock"])

        return cls(bot, ctx, bind=bind, djrole=djrole, djlock=djlock)

    @property
    def is_playing(self):
        return self.source and self.voice

    @property
    def validate(self):
        if self.is_playing:
            return self
        raise exceptions.InactivePlayer

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        if not 0.0 <= value <= 100.0:
            raise commands.BadArgument("Volume must be between `0.0` and `100.0`")
        self._volume = value
        self.source.volume = value

    async def connect(self, channel, *, timeout=None):
        try:
            self.voice = await channel.connect(timeout=timeout, cls=VoiceClient)
        except discord.ClientException:
            await channel.guild.voice_client.disconnect(force=True)
            self.voice = await channel.connect(timeout=timeout, cls=VoiceClient)

        return self.voice

    async def ensure_voice_state(self, ctx):
        if not ctx.me.voice:
            if not hasattr(ctx.author.voice, "channel"):
                raise commands.BadArgument("You must be connected to a voice channel")
            channel = ctx.author.voice.channel
        else:
            channel = ctx.me.voice.channel
        self.voice = await self.get_voice_client(channel)
        return self

    async def get_voice_client(self, channel, *, timeout=None):
        voice = channel.guild.me.voice
        voice_client = channel.guild.voice_client
        if hasattr(voice, "channel"):
            if voice_client:  # Already have everything
                return voice_client
            else:  # Create voice client
                return await self.connect(channel, timeout=timeout)
        else:
            return await self.connect(channel, timeout=timeout)

    async def check_voice_client(self):
        voice = self._ctx.me.guild.me.voice
        voice_client = self._ctx.me.guild.voice_client
        if hasattr(voice, "channel"):
            if voice_client:  # Already have everything
                return voice_client

        await self.stop()

    async def play_from_file(self, file):
        await file.save("./track.mp3")
        await self.play_local_file()

    async def play_local_file(self, fname="track.mp3"):
        now = discord.FFmpegPCMAudio(fname)
        self.voice.play(now, after=self.play_next_track)

    def alter_audio(self, *, position=None):
        if position is None:
            position = self.source.position

        self.voice.pause()  # Pause the audio before altering
        self.source = AudioSource(self.current, self.volume, position, **self.effects)
        self.voice.play(self.source, after=self.play_next_track)

    async def get_next_track(self):
        self.entry = await self.tracks.get()
        if self.entry.has_data:
            current = YTDLSource(self.entry.ctx, self.entry.data)
        else:
            while True:
                try:
                    current = await YTDLSource.get_source(
                        self.entry.ctx, self.entry.search
                    )
                except exceptions.YTDLError:
                    self.entry = await self.tracks.get()
                else:
                    break
        return current

    def requeue(self, source: YTDLSource):
        self.entry.data = source.data
        self.tracks.put_nowait(self.entry)

    def replay(self, source: YTDLSource):
        self.entry.data = source.data
        self.tracks.append_left(self.entry)

    async def audio_player_task(self):
        run = True
        while run is True:
            try:
                self.next.clear()

                if self.track_is_looped:  # Single song is looped.
                    self.current = self.previous

                elif self.queue_is_looped:  # Entire queue is looped
                    self.requeue(self.previous)  # Put old track back in the queue.
                    self.current = await self.get_next_track()  # Get song from queue

                else:  # Not looping track or queue.
                    self.current = await self.get_next_track()
                self.source = await AudioSource.save(
                    self.current,
                    self.volume,
                    **self.effects,
                )
                if self.source:
                    self.voice = await self.check_voice_client()
                    self.voice.play(self.source, after=self.play_next_track)
                    await MusicUtils.create_embed(self.current.ctx, self.source)
                    await self.next.wait()  # Wait until the track finishes
                else:  # Something went wrong, get next track
                    self.next.set()

                self.previous = self.current  # Store previous track
                self.current = None
                self.source = None
            except Exception:
                tb = traceback.format_exc()
                log.fatal(tb)
                self.bot.dispatch("error", "MUSIC_ERROR", tb=tb)
                # run = False

    async def increment_position(self):
        """Keeps track of the position in the song"""

        def condition():
            if not self.voice:
                return False
            if not self.voice.is_playing():
                return False
            if not self.source:
                return False
            return True

        while True:
            if condition():
                self.source.position += self.source.rate
            await asyncio.sleep(1.0)

    def play_next_track(self, error=None):
        if error:
            log.warning(error)
        self.next.set()

    def skip(self):
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    def track_loop(self):
        self.track_is_looped = True

    def queue_loop(self):
        self.queue_is_looped = True
        self.track_is_looped = False

    def unloop(self):
        self.queue_is_looped = False
        self.track_is_looped = False


class VoiceStates(dict):
    def __init__(self):
        pass

    async def get_state(self, ctx):
        state = self.get(ctx.guild.id)
        if not state:
            state = await VoiceState.create(ctx.bot, ctx)
            self[ctx.guild.id] = state
        return state

    def destroy(self, loop=None):
        loop = loop or asyncio.get_event_loop()
        for state in self.values():
            loop.create_task(state.stop())


VOICE_STATES = VoiceStates()


class Player(commands.Cog):
    """
    Module for playing audio.
    """

    def __init__(self, bot):
        self.bot = bot
        self.spotify = MusicUtils.spotify(bot)

    def cog_unload(self):
        VOICE_STATES.destroy(loop=self.bot.loop)

    async def cog_check(self, ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage()
        return True

    async def cog_before_invoke(self, ctx):
        ctx.voice_state = await VOICE_STATES.get_state(ctx)
        Checks.raise_if_bound(ctx)
        Checks.raise_if_locked(ctx)

    @decorators.command(
        name="connect",
        aliases=["join"],
        brief="Connect to a channel.",
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
            Connects to a specified voice
            or stage channel.
        Notes:
            If you do not specify a channel,
            the bot will join your current channel.
            (If it exists)
            If the bot is currently active in another
            channel, you must have DJ perms for the
            command to function properly.
        """
        if channel is None:
            if not hasattr(ctx.author.voice, "channel"):
                return await ctx.usage()
            else:
                channel = ctx.author.voice.channel

        if not Checks.is_dj(ctx):
            Checks.assert_is_dormant(ctx)
        await ctx.voice_state.connect(channel)
        await ctx.success(f"Connected to {channel.mention}")

    @decorators.command(
        name="disconnect",
        aliases=["dc", "leave"],
        brief="Disconnects from a channel.",
    )
    async def _disconnect(self, ctx):
        """
        Usage: {0}leave
        Alias: {0}dc, {0}disconnect
        Output:
            Clears the queue and leaves
            the voice or stage channel.
        """
        if not Checks.is_dj(ctx):
            Checks.assert_is_dormant(ctx)
        if hasattr(ctx.guild.me.voice, "channel"):
            channel = ctx.guild.me.voice.channel
            await ctx.voice_state.stop()
            await ctx.message.add_reaction(self.bot.emote_dict["wave"])
            await ctx.success(f"Disconnected from {channel.mention}")
        else:
            await ctx.fail("Not connected to any voice channel.")
            await ctx.voice_state.stop()

    @decorators.command(
        name="pause",
        aliases=["halt"],
        brief="Pause the track.",
    )
    @checks.cooldown()
    async def _pause(self, ctx):
        """
        Usage: {0}pause
        Alias: {0}halt
        Output: Pauses the current track.
        Notes:
            To resume playback, use the {0}resume command
            or invoke the {0}play command with no arguments.
        """
        player = ctx.voice_state.validate
        Checks.assert_is_dj(ctx)

        if player.voice.is_paused():
            await ctx.fail("The player is already paused.")
            return

        player.voice.pause()
        await ctx.react(self.bot.emote_dict["pause"])

    @decorators.command(
        name="resume",
        aliases=["unpause"],
        brief="Resume the track.",
    )
    @checks.cooldown()
    async def _resume(self, ctx):
        """
        Usage: {0}resume
        Alias: {0}unpause
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
        brief="Stop track and clear the queue.",
    )
    @checks.cooldown()
    async def _stop(self, ctx):
        """
        {0}Usage: {0}stop
        Output:
            Stops playing song and clears the queue.
        """
        Checks.assert_is_dj(ctx)
        ctx.voice_state.tracks.clear()
        if ctx.voice_state.is_playing:
            ctx.voice_state.voice.stop()

        await ctx.react(self.bot.emote_dict["stop"])

    @decorators.command(
        name="skip",
        aliases=["s", "fs", "vs", "voteskip", "forceskip", "next"],
        brief="Skip the track.",
    )
    @checks.cooldown()
    async def _skip(self, ctx):
        """
        Usage: {0}skip
        Aliases:
            {0}s, {0}fs, {0}vs, {0}next
            {0}voteskip, {0}forceskip
        Output: Vote to skip a song.
        Notes:
            The song requester and those with the
            Manage Server permission can automatically skip
            Otherwise half the listeners neet to vote skip
            for the song to be skipped.
        """
        player = ctx.voice_state.validate
        emoji = self.bot.emote_dict["skip"]

        if Checks.is_requester(ctx):
            player.skip()  # Song requester can skip.
            await ctx.react(emoji)

        elif Checks.is_dj(ctx):
            player.skip()  # Server Djs can skip.
            await ctx.react(emoji)

        elif ctx.author.id not in player.skip_votes:
            player.skip_votes.add(ctx.author.id)
            total_votes = len(player.skip_votes)

            listeners = player.voice.channel.members
            valid_voters = [user for user in listeners if not user.bot]
            required_votes = len(valid_voters) + 1 // 2  # Require majority

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
        name="seek",
        brief="Seek to a position in the track.",
    )
    @checks.cooldown()
    async def _seek(self, ctx, position: int = 0):
        """
        Usage: {0}seek [time]
        Output:
            Seeks to a certain position in the track
        Notes:
            The position must be given in seconds.
        """
        player = ctx.voice_state.validate
        if player.current.is_live:
            await ctx.fail("Unable to seek livestream tracks.")
            return

        if not Checks.is_requester(ctx):
            Checks.assert_is_dj(ctx)

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
        if player.current.is_live:
            await ctx.fail("Unable to seek livestream tracks.")

        if not Checks.is_requester(ctx):
            Checks.assert_is_dj(ctx)

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
        brief="Rewind the track.",
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
        if player.current.is_live:
            await ctx.fail("Unable to seek livestream tracks.")

        if not Checks.is_requester(ctx):
            Checks.assert_is_dj(ctx)

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
        name="current",
        brief="Show track info.",
        aliases=["now", "np", "nowplaying"],
    )
    @checks.bot_has_perms(embed_links=True)
    @checks.cooldown()
    async def _current(self, ctx):
        """
        Usage: {0}current
        Aliases: {0}now, {0}np, {0}current, {0}nowplaying
        Output: Displays the currently playing song.
        Notes:
            Will fall back to sending a codeblock
            if the bot does not have the Embed Links
            permission. A progress bar will be included
            if the bot has the Attach Files permission.
        """
        player = ctx.voice_state.validate
        await Views.TrackView(ctx).start()

    @decorators.command(
        name="trackinfo",
        brief="Show track info.",
    )
    @checks.bot_has_perms(embed_links=True)
    @checks.cooldown()
    async def _trackinfo(self, ctx):
        """
        Usage: {0}trackinfo
        Aliases: {0}now, {0}np, {0}current, {0}nowplaying
        Output: Displays the currently playing song.
        Notes:
            Will fall back to sending a codeblock
            if the bot does not have the Embed Links
            permission. A progress bar will be included
            if the bot has the Attach Files permission.
        """
        player = ctx.voice_state.validate
        await MusicUtils.create_embed(ctx, player.source)

    @decorators.command(
        name="save",
        brief="Save a song to your liked songs.",
        aliases=["like"],
    )
    @checks.cooldown()
    async def _save(self, ctx):
        """
        Usage: {0}save
        Aliases: {0}like
        Output: Sends info and saves the current track
        Notes:
            Will attempt to DM you the info and fall
            back to sending track information to the
            current channel. Saving songs with this
            command will add songs to your "Liked Songs"
            which can be played using the playliked command.
        """
        player = ctx.voice_state.validate
        query = """
                INSERT INTO saved (requester_id, title, url, uploader)
                VALUES ($1, $2, $3, $4)
                """
        await self.bot.cxn.execute(
            query,
            player.current.requester.id,
            player.current.title,
            player.current.url,
            player.current.uploader,
        )
        await MusicUtils.save_embed(ctx, player.current)

    @decorators.command(
        aliases=["again"],
        name="replay",
        brief="Play the previous track.",
    )
    @checks.cooldown()
    async def _replay(self, ctx):
        """
        Usage: {0}replay
        Alias: {0}again
        Output:
            Add the previous song to the
            beginning of the track queue.
        """
        previous = ctx.voice_state.previous
        Checks.assert_is_dj(ctx)
        if not previous:
            await ctx.fail("No previous song to play.")
            return

        ctx.voice_state.replay(previous)
        await ctx.music(f"Front queued the previous song: {previous}")

    @decorators.command(
        aliases=["pos"],
        name="position",
        brief="Show the track position.",
    )
    @checks.cooldown()
    async def _position(self, ctx):
        """
        Usage: {0}position
        Alias: {0}pos
        Output:
            Shows the current position of the song.
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
        brief="Get results from a search.",
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
        player = await ctx.voice_state.ensure_voice_state(ctx)
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
                await ctx.music(f"Queued {source}")

    @decorators.command(
        name="playnext",
        brief="Front queue a track.",
        aliases=["pn", "frontqueue"],
    )
    @checks.bot_has_guild_perms(connect=True, speak=True)
    @checks.cooldown()
    async def _playnext(self, ctx, *, search: str = None):
        """
        Usage: {0}playnext <search>
        Alias: {0}frontqueue, {0}pn
        Output:
            Plays a track from your selection.
        Notes:
            If there are tracks in the queue,
            this will be queued before
            all other tracks in the queue.
            If the track you select is a playlist,
            all tracks in the playlist will be placed
            ahead of the previously queued tracks.
        """
        await ctx.trigger_typing()
        player = await ctx.voice_state.ensure_voice_state(ctx)
        Checks.assert_is_dj(ctx)

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

        song_url = MusicUtils.reformat_uri(search)

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
                    tracks = MusicUtils.put_spotify_tracks(ctx, res["tracks"]["items"])
                    player.tracks.extend_left(tracks)
                    await ctx.music(
                        f"Front Queued {len(res['tracks']['items'])} spotify tracks."
                    )
                    return

                elif "artist" in parts:
                    res = await self.spotify.get_artist(parts[-1])
                    tracks = MusicUtils.put_spotify_tracks(ctx, res["tracks"])
                    player.tracks.extend_left(tracks)
                    await ctx.music(
                        f"Front Queued {len(res['tracks'])} spotify tracks."
                    )
                    return

                elif "playlist" in parts:
                    res = []
                    r = await self.spotify.get_playlist_tracks(parts[-1])
                    iterations = 0
                    while iterations < 5:  # Max playlist length 500
                        res.extend(r["items"])
                        if r["next"] is not None:
                            r = await self.spotify.make_spotify_req(r["next"])
                            iterations += 1
                            continue
                        else:
                            break

                    tracks = MusicUtils.put_spotify_playlist(ctx, res)
                    player.tracks.extend_left(tracks)
                    await ctx.music(f"Front Queued {len(res)} spotify tracks.")
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
                await ctx.music(
                    f"Front Queued Playlist: {playlist} `({len(tracks) + 1} tracks)`"
                )

            return
        try:
            track = await YTDLSource.get_song(ctx, song_url, loop=self.bot.loop)
        except exceptions.YTDLError as e:
            await ctx.fail(f"Request failed: {e}")
        else:
            player.tracks.append_left(track)
            await ctx.music(f"Front Queued {track}")

    @decorators.command(
        name="play",
        brief="Play a track from a search.",
        aliases=["p", "enqueue"],
    )
    @checks.bot_has_guild_perms(connect=True, speak=True)
    @checks.cooldown()
    async def _play(self, ctx, *, search: str = None):
        """
        Usage: {0}play <search>
        Alias: {0}p, {0}enqueue
        Output:
            Plays a track from your search.
        Notes:
            If there are tracks in the queue,
            this will be queued until the
            other tracks finished playing.
            This command automatically searches
            youtube if no url is provided.
            Accepts spotify and youtube urls.
        """
        await ctx.trigger_typing()
        player = await ctx.voice_state.ensure_voice_state(ctx)
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

        song_url = MusicUtils.reformat_uri(search)

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
                    tracks = MusicUtils.put_spotify_tracks(ctx, res["tracks"]["items"])
                    player.tracks.extend(tracks)
                    await ctx.music(
                        f"Queued {len(res['tracks']['items'])} spotify tracks."
                    )
                    return

                elif "artist" in parts:
                    res = await self.spotify.get_artist(parts[-1])
                    tracks = MusicUtils.put_spotify_tracks(ctx, res["tracks"])
                    player.tracks.extend(tracks)
                    await ctx.music(f"Queued {len(res['tracks'])} spotify tracks.")
                    return

                elif "playlist" in parts:
                    res = []
                    r = await self.spotify.get_playlist_tracks(parts[-1])
                    iterations = 0
                    while iterations < 5:  # Max playlist length 500
                        res.extend(r["items"])
                        if r["next"] is not None:
                            r = await self.spotify.make_spotify_req(r["next"])
                            iterations += 1
                            continue
                        else:
                            break

                    tracks = MusicUtils.put_spotify_playlist(ctx, res)
                    player.tracks.extend(tracks)
                    await ctx.music(f"Queued {len(res)} spotify tracks.")
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
                await ctx.music(
                    f"Queued Playlist: {playlist} `({len(tracks) + 1} tracks)`"
                )

            return
        try:
            track = await YTDLSource.get_song(ctx, song_url, loop=self.bot.loop)
        except exceptions.YTDLError as e:
            await ctx.fail(f"Request failed: {e}")
        else:
            player.tracks.put_nowait(track)
            await ctx.music(f"Queued {track}")

    @decorators.command(
        brief="Play a discord file or url.", name="playfile", hidden=True
    )
    @checks.bot_has_guild_perms(connect=True, speak=True)
    async def _playfile(self, ctx, media_url=None):
        await ctx.trigger_typing()
        player = await ctx.voice_state.ensure_voice_state(ctx)

        if len(ctx.message.attachments) > 0:  # User passed an attachment.
            file = ctx.message.attachments[0]
            if file.content_type not in ["audio/mpeg", "video/mp4"]:
                raise exceptions.InvalidMediaType  # Must be audio or video
            try:
                await player.play_from_file(file)
            except discord.ClientException as e:
                raise commands.BadArgument(str(e))
            await ctx.music(f"Playing **{file.filename}**")

        else:  # Check for url regex
            regex = r"(https://|http://)?(cdn\.|media\.)discord(app)?\.(com|net)/attachments/[0-9]{17,19}/[0-9]{17,19}/(?P<filename>.{1,256})\.(?P<mime>[0-9a-zA-Z]{2,4})(\?size=[0-9]{1,4})?"
            pattern = re.compile(regex)
            match = pattern.match(media_url)
            if not match:  # We have a discord url.
                await ctx.fail(f"Invalid discord media url.")
                return

            await MusicUtils.read_url(match.group(0), self.bot.session)  # Get url bytes
            await player.play_local_file(match.group(0))
            await ctx.music(f"Playing `{match.group(0)}`")


class Queue(commands.Cog):
    """
    Module for managing the queue.
    """

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage()
        return True

    async def cog_before_invoke(self, ctx):
        ctx.voice_state = await VOICE_STATES.get_state(ctx)
        Checks.raise_if_bound(ctx)
        Checks.raise_if_locked(ctx)

    @decorators.command(
        aliases=["last", "back", "previous"],
        name="requeue",
        brief="Queue the previous track.",
    )
    @checks.cooldown()
    async def _requeue(self, ctx):
        """
        Usage: {0}requeue
        Alias: {0}last, {0}back, {0}previous
        Output:
            Add the previous song to the
            end of the track queue.
        """
        previous = ctx.voice_state.previous
        if not previous:
            await ctx.fail("No previous song to play.")
            return

        ctx.voice_state.requeue(previous)
        await ctx.music(f"Requeued the previous song: {previous}")

    @decorators.command(
        name="skipto",
        brief="Skip to a track in the queue.",
    )
    @checks.cooldown()
    async def _skipto(self, ctx, index: int):
        """
        Usage: {0}skipto [index]
        Output:
            Skips the current track and plays
            the selected track in the queue.
        Notes:
            Tracks before the selected song
            will be removed from the queue.
        """
        player = ctx.voice_state.validate
        queue = player.tracks
        Checks.assert_is_dj(ctx)

        if len(queue) == 0:
            await ctx.fail("The queue is currently empty.")

        try:
            selection = queue.skipto(index - 1)
        except IndexError:
            await ctx.fail("Invalid track index provided.")
            return

        queue.append_left(selection)
        player.skip()
        await ctx.success(f"Skipped to track #{index}: {selection}")

    @decorators.command(
        name="jump",
        brief="Jump to a track in the queue.",
    )
    @checks.has_guild_permissions(move_members=True)
    @checks.cooldown()
    async def _jump(self, ctx, index: int):
        """
        Usage: {0}jump [index]
        Output:
            Skips the current track and plays
            the selected track in the queue.
        Notes:
            All other tracks in the queue will
            remain in their respective positions.
        """
        player = ctx.voice_state.validate
        queue = player.tracks
        if not Checks.is_requester(ctx):
            Checks.assert_is_dj(ctx)

        if len(queue) == 0:
            await ctx.fail("The queue is currently empty.")

        try:
            selection = queue.pop(index - 1)
        except IndexError:
            await ctx.fail("Invalid track index provided.")
            return
        queue.append_left(selection)  # Server DJs can jump
        player.skip()
        await ctx.success(f"Jumped to track #{index}: {selection}")

    @decorators.command(
        aliases=["repeat"],
        name="loop",
        brief="Loop the track or queue.",
    )
    @checks.cooldown()
    async def _loop(self, ctx, option: converters.TrackOrQueue = "track"):
        """
        Usage: {0}loop [option]
        Output: Loops the currently playing song.
        Notes:
            Use {0}loop queue to loop the entire queue.
            Use {0}loop track to loop only the current track.
            Use {0}loop off to stop looping the track or queue.
            Will loop the current track if neither is specified.
            Use {0}unloop can also be used to stop looping settings.
        """
        player = ctx.voice_state.validate
        Checks.assert_is_dj(ctx)

        if option == "track":
            setting = "already" if player.track_is_looped else "now"
            player.track_is_looped = True
            await ctx.success(f"The current track is {setting} looped.")
        elif option == "queue":
            setting = "already" if player.queue_is_looped else "now"
            player.queue_is_looped = True
            player.track_is_looped = False  # In case we were looping a track.
            await ctx.success(f"The current queue is {setting} looped.")
        elif option == "off":
            return await ctx.invoke(self._unloop)
        await ctx.react(self.bot.emote_dict["loop"])

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
        Checks.assert_is_dj(ctx)
        player.track_is_looped = False
        player.queue_is_looped = False

        await ctx.react(self.bot.emote_dict["success"])

    ######################
    ## Queue Management ##
    ######################

    @decorators.command(
        name="tracks", aliases=["q", "queue"], brief="Show the track queue."
    )
    @checks.bot_has_perms(embed_links=True)
    @checks.cooldown()
    async def _tracks(self, ctx, *, search=None):
        """
        Usage: {0}tracks
        Alias: {0}q, {0}queue
        Output:
            Starts a pagination session showing
            all the tracks in the current queue.
        Notes:
            Each page contains 10 queue elements.
            Will invoke the play command if a search
            is specified.
        """
        if search:
            audio = self.bot.get_cog("Player")
            return await ctx.invoke(audio._play, search=search)

        if len(ctx.voice_state.tracks) == 0:
            await ctx.fail("The queue is currently empty.")
            return

        entries = [track.hyperlink for track in ctx.voice_state.tracks]

        p = Views.QueueView(ctx, entries, per_page=10, index=True)
        p.embed.title = "Current Queue"
        if ctx.voice_state.current:
            p.embed.add_field(
                name="Current Track", value=ctx.voice_state.current.hyperlink
            )
        await p.start()

    @decorators.group(name="clear", aliases=["c"], brief="Clear the queue.")
    @checks.cooldown()
    async def _clear(self, ctx):
        """
        Usage: {0}clear
        Alias: {0}c
        Output:
            Removes all queued tracks.
        Notes:
            Specify a range, e.g. {0}clear 3 10
            to remove only the tracks between
            position 3 and 10 in the queue.
        """
        if ctx.invoked_subcommand is None:
            queue = ctx.voice_state.tracks
            Checks.assert_is_dj(ctx)
            if len(queue) == 0:
                await ctx.fail("The queue is already empty")
                return
            queue.clear()
            await ctx.success("Cleared all tracks from the queue.")

    @_clear.command(name="range", brief="Ckear a range from the queue.")
    async def _clear_range(self, ctx, start: int, end: int):
        Checks.assert_is_dj(ctx)
        queue = ctx.voice_state.tracks

        if len(queue) == 0:
            await ctx.fail("The queue is currently empty.")
            return
        if not 1 <= start <= len(queue) - 1:
            await ctx.fail("Invalid range start.")
            return
        if not start < end <= len(queue):
            await ctx.fail("Invalid range end.")
            return

        queue.clear_range(start, end)
        await ctx.success(f"Cleared tracks in range from {start} to {end}")

    @decorators.group(name="shuffle", brief="Shuffle the queue.")
    @checks.cooldown()
    async def _shuffle(self, ctx):
        """
        Usage: {0}shuffle
        Output: Shuffles the queue.
        Notes:
            Specify a range, e.g. {0}shuffle 3 10
            to shuffle only the tracks between
            position 3 and 10 in the queue.
        """
        if ctx.invoked_subcommand is None:
            Checks.assert_is_dj(ctx)
            queue = ctx.voice_state.tracks

            if len(queue) == 0:
                await ctx.fail("The queue is currently empty.")
                return

            queue.shuffle()
            await ctx.send_or_reply(
                f"{self.bot.emote_dict['shuffle']} Shuffled the queue."
            )

    @_shuffle.command(name="range", brief="Shuffle a range of the queue.")
    async def _shuffle_range(self, ctx, start: int, end: int):
        Checks.assert_is_dj(ctx)
        queue = ctx.voice_state.tracks

        if len(queue) == 0:
            await ctx.fail("The queue is currently empty.")
            return
        if not 1 <= start <= len(queue) - 1:
            await ctx.fail("Invalid range start.")
            return
        if not start < end <= len(queue):
            await ctx.fail("Invalid range end.")
            return

        queue.shuffle_range(start, end)
        await ctx.send_or_reply(
            f"{self.bot.emote_dict['shuffle']} Shuffled tracks in range from {start} to {end}"
        )

    @decorators.group(name="reverse", brief="Reverse the queue.")
    @checks.cooldown()
    async def _reverse(self, ctx):
        """
        Usage: {0}reverse
        Output: Reverses the queue.
        """
        if ctx.invoked_subcommand is None:
            queue = ctx.voice_state.tracks

            if len(queue) == 0:
                await ctx.fail("The queue is currently empty.")
                return

            queue.reverse()
            await ctx.send_or_reply(
                f"{self.bot.emote_dict['redo']} Reversed the queue."
            )

    @_reverse.command(name="range", brief="Reverse a range from the queue.")
    async def _reverse_range(self, ctx, start: int, end: int):
        Checks.assert_is_dj(ctx)
        queue = ctx.voice_state.tracks

        if len(queue) == 0:
            await ctx.fail("The queue is currently empty.")
            return
        if not 1 <= start <= len(queue) - 1:
            await ctx.fail("Invalid range start.")
            return
        if not start < end <= len(queue):
            await ctx.fail("Invalid range end.")
            return

        queue.reverse_range(start, end)
        await ctx.success(f"Reversed tracks in range from {start} to {end}")

    @decorators.group(
        name="remove", aliases=["pop"], brief="Remove a track from the queue."
    )
    @checks.cooldown()
    async def _remove(self, ctx, index: int):
        """
        Usage: {0}remove [index]
        Alias: {0}pop
        Output:
            Removes a song from the queue at a given index.
        """
        if ctx.invoked_subcommand is None:
            queue = ctx.voice_state.tracks

            if len(queue) == 0:
                await ctx.fail("The queue is already empty")
                return

            try:
                queue.remove(index - 1)
            except Exception:
                await ctx.fail("Invalid index.")
                return

            await ctx.success(f"Removed item `{index}` from the queue.")

    @_remove.command(name="range", brief="Remove a range from the queue.")
    async def _remove_range(self, ctx, start: int, end: int):
        Checks.assert_is_dj(ctx)
        queue = ctx.voice_state.tracks

        if len(queue) == 0:
            await ctx.fail("The queue is currently empty.")
            return
        if not 1 <= start <= len(queue) - 1:
            await ctx.fail("Invalid range start.")
            return
        if not start < end <= len(queue):
            await ctx.fail("Invalid range end.")
            return

        queue.clear_range(start, end)
        await ctx.success(f"Removed tracks in range from {start} to {end}")

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
        Checks.assert_is_dj(ctx)
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
            f"Moved song #{index} to the {MusicUtils.number_format(position)} position in the queue."
        )

    @decorators.command(
        aliases=["uniquify", "dd", "deduplicate"],
        name="dedupe",
        brief="Remove duplicate tracks.",
    )
    @checks.cooldown()
    async def _dedupe(self, ctx):
        """
        Usage: {0}dedupe
        Alias: {0}dd, {0}uniquify, {deduplicate}
        Output:
            Remove all duplicate tracks in the queue.
        """
        Checks.assert_is_dj(ctx)
        queue = ctx.voice_state.tracks
        if len(queue) == 0:
            await ctx.fail("The queue is currently empty.")
            return

        queue.deduplicate()
        await ctx.success("Removed all duplicate tracks from the queue")

    @decorators.command(
        aliases=["lc", "leavecleanup", "cull"],
        name="weed",
        brief="Clear absent user enqueues.",
    )
    @checks.cooldown()
    async def _weed(self, ctx):
        """
        Usage: {0}weed
        Alias: {0}lc, {0}leavechannel, {0}cull
        Output:
            Remove all tracks enqueued by users
            who have left the music channel.
        """
        Checks.assert_is_dj(ctx)
        channel = ctx.voice_state.voice.channel
        queue = ctx.voice_state.tracks
        if not channel:
            await ctx.fail("Not currently playing music.")
            return
        if len(queue) == 0:
            await ctx.fail("The queue is currently empty.")
            return

        queue.leave_cleanup(channel.members)
        await ctx.success(
            f"Removed all tracks enqueued by users no longer in {channel.mention}"
        )

    @decorators.command(
        aliases=["dq", "detrack"],
        name="dequeue",
        brief="Clear a user's enqueues.",
    )
    @checks.cooldown()
    async def _dequeue(self, ctx, *, user: converters.DiscordMember):
        """
        Usage: {0}dequeue [user]
        Alias: {0}detrack, {0}dq
        Output:
            Remove all tracks queued by a specific user.
        """
        Checks.assert_is_dj(ctx)
        queue = ctx.voice_state.tracks
        if len(queue) == 0:
            await ctx.fail("The queue is currently empty.")
            return

        queue.dequeue(user)
        await ctx.success(f"Removed all tracks enqueued by **{user}** `{user.id}`")


class Audio(commands.Cog):
    """
    Module for managing the queue.
    """

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage()
        return True

    async def cog_before_invoke(self, ctx):
        ctx.voice_state = await VOICE_STATES.get_state(ctx)
        Checks.raise_if_bound(ctx)
        Checks.raise_if_locked(ctx)

    async def set_effect(self, ctx):
        player = ctx.voice_state.validate
        Checks.assert_is_dj(ctx)

        name = ctx.command.name
        ternery = not player[name]
        player[name] = ternery

        fmt = lambda t: "" if t else "de"
        await ctx.music(f"{name.title()} effect {fmt(ternery)}activated.")

    @decorators.command(
        aliases=["tempo"],
        name="speed",
        brief="Alter the speed of the player.",
    )
    @checks.cooldown()
    async def _speed(self, ctx, speed: float = None):
        """
        Usage: {0}speed [speed]
        Alias: {0}tempo
        Output:
            Speed up or slow down the player.
        Notes:
            The speed must be between 0.5 and 2.0.
            Will output the current speed if no
            new speed is explicitly specified.
        """
        player = ctx.voice_state.validate
        Checks.assert_is_dj(ctx)

        if speed is None:  # Output the current speed
            await ctx.music(f"The audio speed is currently `{player['speed']}x`")
            return

        player["speed"] = speed
        await ctx.music(f"Audio speed is now `{speed}x`")

    @decorators.command(
        name="pitch",
        brief="Alter the pitch of the player.",
    )
    @checks.cooldown()
    async def _pitch(self, ctx, pitch: float = None):
        """
        Usage: {0}pitch [pitch]
        Output:
            Alter the pitch of the player.
        Notes:
            The pitch must be between 0.5 and 2.0.
            Will output the current pitch if no
            new pitch is explicitly specified.
        """
        player = ctx.voice_state.validate
        Checks.assert_is_dj(ctx)

        if pitch is None:  # Output the current pitch
            await ctx.music(f"The audio pitch is currently `{player['pitch']}`")
            return

        player["pitch"] = pitch
        await ctx.music(f"Audio pitch is now `{pitch}`")

    @decorators.command(
        name="nightcore",
        brief="Toggle the nightcore effect.",
    )
    @checks.cooldown()
    async def _nightcore(self, ctx):
        """
        Usage: {0}nightcore
        Output:
            Enables the nightcore audio effect.
        """
        await self.set_effect(ctx)

    @decorators.command(
        aliases=["blowout"],
        name="earrape",
        brief="Toggle the earrape effect.",
    )
    @checks.cooldown()
    async def _earrape(self, ctx):
        """
        Usage: {0}earrape
        Output:
            Enables the earrape audio effect.
        """
        await self.set_effect(ctx)

    @decorators.command(
        name="vibrato",
        brief="Toggle the vibrato effect.",
    )
    @checks.cooldown()
    async def _vibrato(self, ctx):
        """
        Usage: {0}vibrato
        Output:
            Enables the vibrato audio effect.
        """
        await self.set_effect(ctx)

    @decorators.command(
        name="echo",
        brief="Toggle the echo effect.",
    )
    @checks.cooldown()
    async def _echo(self, ctx):
        """
        Usage: {0}echo
        Output:
            Enables the echo audio effect.
        """
        await self.set_effect(ctx)

    @decorators.command(
        name="tremolo",
        brief="Toggle the tremolo effect.",
    )
    @checks.cooldown()
    async def _tremolo(self, ctx):
        """
        Usage: {0}tremolo
        Output:
            Enables the tremolo audio effect.
        """
        await self.set_effect(ctx)

    @decorators.command(
        name="muffle",
        brief="Toggle the muffle effect.",
    )
    @checks.cooldown()
    async def _muffle(self, ctx):
        """
        Usage: {0}muffle
        Output:
            Toggles the muffle audio effect.
        """
        await self.set_effect(ctx)

    @decorators.command(
        name="treble",
        brief="Toggle the treble effect.",
    )
    @checks.cooldown()
    async def _treble(self, ctx):
        """
        Usage: {0}treble
        Output:
            Toggles the treble audio effect.
        """
        await self.set_effect(ctx)

    @decorators.command(
        name="bass",
        brief="Toggle the bass effect.",
    )
    @checks.cooldown()
    async def _bass(self, ctx):
        """
        Usage: {0}bass
        Output:
            Toggles the bass audio effect.
        """
        await self.set_effect(ctx)

    # @decorators.command(
    #     name="backwards",
    #     brief="Toggle the backwards effect.",
    #     disabled=True
    # )
    # @checks.cooldown()
    # async def _backwards(self, ctx):
    #     """
    #     Usage: {0}backwards
    #     Output:
    #         Toggles the backwards audio effect.
    #     """
    #     await self.set_effect(ctx)

    @decorators.command(
        name="robot",
        brief="Toggle the robot effect.",
    )
    @checks.cooldown()
    async def _robot(self, ctx):
        """
        Usage: {0}robot
        Output:
            Toggles the robot audio effect.
        """
        await self.set_effect(ctx)

    @decorators.command(
        name="phaser",
        brief="Toggle the phaser effect.",
    )
    @checks.cooldown()
    async def _phaser(self, ctx):
        """
        Usage: {0}phaser
        Output:
            Toggles the phaser audio effect.
        """
        await self.set_effect(ctx)

    @decorators.command(
        name="whisper",
        brief="Toggle the whisper effect.",
    )
    @checks.cooldown()
    async def _whisper(self, ctx):
        """
        Usage: {0}whisper
        Output:
            Toggles the whisper audio effect.
        """
        await self.set_effect(ctx)

    @decorators.group(
        name="effects",
        brief="Show audio effects.",
    )
    @checks.cooldown()
    async def _effects(self, ctx):
        """
        Usage: {0}effects
        Output: Shows all available effects
        """
        player = ctx.voice_state.validate
        Checks.assert_is_dj(ctx)

        view = Views.Effects(ctx, player)
        msg = await ctx.send(
            "Select an audio effect from the dropdown below.", view=view
        )
        view.message = msg

    @_effects.command(
        aliases=["clear"],
        name="reset",
        brief="Reset audio effects.",
    )
    @checks.cooldown()
    async def reset_effects(self, ctx):
        """
        Usage: {0}effects reset
        Alias: {0}effects clear
        Output: Resets all effects to default.
        """
        player = ctx.voice_state.validate
        Checks.assert_is_dj(ctx)
        player.clear_effects()
        await ctx.success("Reset all audio effects.")

    @decorators.command(
        aliases=["vol", "sound"],
        name="volume",
        brief="Alter the volume.",
    )
    async def _volume(self, ctx, volume: int = None):
        """
        Usage: {0}volume [volume]
        Alias: {0}vol, {0}sound
        Output: Changes the volume of the player.
        Notes:
            Will show current volume if
            no new volume is specified.
        """
        player = ctx.voice_state.validate
        Checks.assert_is_dj(ctx)
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


class Playlists(commands.Cog):
    """
    Module for managing playlists.
    """

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage()
        return True

    async def cog_before_invoke(self, ctx):
        ctx.voice_state = await VOICE_STATES.get_state(ctx)
        Checks.raise_if_bound(ctx)
        Checks.raise_if_locked(ctx)

    @decorators.group(name="playlist", brief="Manage playlists.")
    async def _playlist(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))

    @_playlist.command(name="save", brief="Save the queue to a new playlist.")
    async def playlist_save(self, ctx, *, name: str):
        """
        Usage: {0}playlist save [playlist name]
        Output:
            Saves the current queue to a playlist with a given name.
        Notes:
            This command will attach the current queue
            and the provided name to your ID. You will
            be the only person able to playback this queue
            at a later time.
        """
        player = ctx.voice_state.validate
        queue = list(ctx.voice_state.tracks)
        if player.entry:
            queue.insert(0, player.entry)
        if len(queue) == 0:
            await ctx.fail("The queue is currently empty.")
            return

        queue = json.dumps([entry.json for entry in queue])
        query = """
                INSERT INTO playlists (owner_id, name, queue)
                VALUES ($1, $2, $3::JSONB)
                """
        try:
            await self.bot.cxn.execute(query, ctx.author.id, name.lower(), queue)
        except asyncpg.exceptions.UniqueViolationError:
            await ctx.fail(
                "You already have a saved playlist with that name. Please try again with a different name"
            )
            return
        await ctx.success(f"Saved the current queue to playlist: **{name}**")

    @_playlist.command(name="delete", brief="Delete one of your saved playlists.")
    async def playlist_delete(self, ctx, *, name: str):
        """
        Usage: {0}playlist delete [playlist name]
        Output:
            Deletes a saved playlist by name.
        """
        query = """
                DELETE FROM playlists
                WHERE owner_id = $1
                AND name = $2
                """
        r = await self.bot.cxn.execute(query, ctx.author.id, name.lower())
        if r == "DELETE 0":
            await ctx.fail(f"You have no saved playlist with name: **{name}**")
            return
        await ctx.success(f"Successfully deleted playlist: **{name}**")

    @_playlist.command(name="append", aliases=["add"], brief="Add to a saved playlist.")
    async def playlist_append(self, ctx, *, name: str):
        """
        Usage: {0}playlist append [playlist name]
        Output:
            Appends the current song to the end of a saved playlist.
        """
        await ctx.trigger_typing()
        player = ctx.voice_state.validate
        if not player.entry:
            await ctx.fail("No current track to append to the playlist.")
            return

        query = """
                SELECT queue
                FROM playlists
                WHERE owner_id = $1
                AND name = $2;
                """
        playlist = await self.bot.cxn.fetchval(query, ctx.author.id, name.lower())
        if not playlist:
            await ctx.fail(f"You do not have a playlist with name: **{name}**")
            return

        playlist = json.loads(playlist)
        playlist.append(player.entry.json)
        playlist = json.dumps(playlist)

        query = """
                UPDATE queues
                SET queue = $1
                WHERE owner_id = $2
                AND name = $3;
                """
        await self.bot.cxn.execute(query, playlist, ctx.author.id, name.lower())
        await ctx.success(f"Appended the current track to playlist: **{name}**")

    @_playlist.command(
        name="extend", brief="Extend a saved playlist with the current queue."
    )
    async def playlist_extend(self, ctx, *, name: str):
        """
        Usage: {0}playlist save [playlist name]
        Output:
            Saves the current queue to a playlist with a given name.
        Notes:
            This command will attach the current queue
            and the provided name to your ID. You will
            be the only person able to playback this queue
            at a later time.
        """
        await ctx.trigger_typing()
        player = ctx.voice_state.validate
        queue = list(ctx.voice_state.tracks)
        if player.entry:
            queue.insert(0, player.entry)
        if len(queue) == 0:
            await ctx.fail("The queue is currently empty.")
            return

        query = """
                SELECT queue
                FROM playlists
                WHERE owner_id = $1
                AND name = $2;
                """
        playlist = await self.bot.cxn.fetchval(query, ctx.author.id, name.lower())
        if not playlist:
            await ctx.fail(f"You do not have a playlist with name: **{name}**")
            return

        playlist = json.loads(playlist)
        playlist.extend([entry.json for entry in queue])
        playlist = json.dumps(playlist)

        query = """
                UPDATE queues
                SET queue = $1
                WHERE owner_id = $2
                AND name = $3;
                """
        await self.bot.cxn.execute(query, playlist, ctx.author.id, name.lower())
        await ctx.success(f"Extended playlist: **{name}** with the current queue.")

    @_playlist.command(
        name="enqueue",
        aliases=["play", "start", "queue", "load"],
        brief="Enqueue a saved playlist.",
    )
    async def playlist_enqueue(self, ctx, *, name: str):
        """
        Usage: {0}playlist enqueue [playlist name]
        Aliases:
            {0}playlist play, {0}playlist start,
            0}playlist queue, 0}playlist load
        Output:
            Enqueues all tracks in the saved queue by
            adding them to the end of the current queue.
        Notes:
            Save playable queues by using
            the {0}playlist save command.
        """
        await ctx.trigger_typing()
        player = await ctx.voice_state.ensure_voice_state(ctx)
        query = """
                SELECT queue
                FROM playlists
                WHERE owner_id = $1
                AND name = $2
                """
        saved_queue = await self.bot.cxn.fetchrow(query, ctx.author.id, name.lower())
        if not saved_queue:
            await ctx.fail("You do not have a saved playlist with that name")
            return

        queue = json.loads(saved_queue["queue"])

        player.tracks.extend(
            [
                QueueEntry(
                    ctx,
                    track.get("title"),
                    track.get("search"),
                    uploader=track.get("uploader"),
                    link=track.get("link"),
                )
                for track in queue
            ]
        )

        await ctx.music(f"Enqueued saved playlist: {name} `({len(queue)} tracks)`")
        query = """
                UPDATE playlists
                SET uses = uses + 1
                WHERE owner_id = $1
                AND name = $2
                """
        await self.bot.cxn.execute(query, ctx.author.id, name.lower())

    @_playlist.command(name="view", aliases=["info"], brief="Show info on a playlist.")
    async def playlist_view(
        self, ctx, user: typing.Optional[converters.DiscordMember], *, name: str
    ):
        """
        Usage: {0}playlist view [playlist owner] [playlist name]
        Alias: {0}playlist info
        Output:
            Show some statistics on a saved playlist
        """
        await ctx.trigger_typing()
        user = user or ctx.author
        playlist = await Playlist.initialize(ctx, user, name)

        view = Views.QueueView(
            ctx, [entry.hyperlink for entry in playlist.entries], playlist=playlist
        )
        view.embed.set_thumbnail(url=playlist.owner.display_avatar)
        view.embed.title = "Playlist Viewing Session"
        view.embed.add_field(name="Playlist Name", value=name.title())
        view.embed.add_field(name="Playlist Owner", value=str(playlist.owner))
        view.embed.add_field(
            name="Created on", value=playlist.created_at.__format__("%m/%d/%Y")
        )
        view.embed.add_field(name="Total Tracks", value=playlist.tracks)
        view.embed.add_field(name="Total Likes", value=playlist.likes)
        view.embed.add_field(name="Total Uses", value=playlist.uses)
        await view.start()

    @decorators.command(
        brief="Show queues saved by a user.",
        name="playlists",
        aliases=["queues"],
    )
    @checks.bot_has_perms(embed_links=True)
    @checks.cooldown()
    async def _playlists(self, ctx, *, user: converters.DiscordMember = None):
        """
        Usage: {0}queues [user]
        Aliases: {0}myqueues, {0}savedqueues, {0}userqueues
        Output:
            Shows all saved queues of a user
            in a pagination session.
        Notes:
            Save playable queues by using
            the {0}savequeue command.
        """
        user = user or ctx.author
        playlists = await Playlist.get_playlists(ctx, user)
        p = views.SimpleView(
            ctx,
            entries=[
                f"**{playlist.name.title()}**: `{playlist.tracks} tracks`"
                for playlist in playlists
            ],
            per_page=10,
            index=True,
        )
        p.embed.title = f"{user.display_name}'s Saved Playlists"
        await p.start()

    @decorators.command(
        name="playliked", aliases=["playsaved"], brief="Enqueue saved songs."
    )
    async def _playliked(self, ctx):
        """
        Usage: {0}playliked
        Alias: {0}playsaved
        Output:
            Enqueues all tracks in the your liked songs
            by adding them to the end of the current queue.
        Notes:
            Add to your saved songs by using the {0}save command
        """
        await ctx.trigger_typing()
        player = await ctx.voice_state.ensure_voice_state(ctx)
        query = """
                SELECT title, url, uploader
                FROM saved
                WHERE requester_id = $1
                ORDER BY insertion DESC;
                """
        records = await self.bot.cxn.fetch(query, ctx.author.id)
        if not records:
            await ctx.fail("You have no liked tracks")
            return

        for record in records:
            player.tracks.put_nowait(
                QueueEntry(
                    ctx, record["title"], record["url"], uploader=record["uploader"]
                )
            )

        await ctx.send(f"Enqueued your liked songs `({len(records)} tracks)`")

    @decorators.command(
        name="playtop",
        aliases=["playpop"],
        brief="Enqueue the top 10 most frequently queued tracks.",
    )
    async def _playtop(self, ctx, limit: int = 10):
        """
        Usage: {0}playliked
        Alias: {0}playsaved
        Output:
            Enqueues all tracks in the your liked songs
            by adding them to the end of the current queue.
        Notes:
            Add to your saved songs by using the {0}save command
        """
        await ctx.trigger_typing()
        if not 0 < limit < 100:
            await ctx.fail(
                f"the `limit` argument must be an integer between `0` and `100`."
            )
            return
        player = await ctx.voice_state.ensure_voice_state(ctx)
        query = f"""
                SELECT title, url, uploader, count(url) as c
                FROM tracks
                WHERE requester_id = $1
                GROUP BY title, url, uploader
                ORDER BY c DESC
                LIMIT {limit};
                """
        records = await self.bot.cxn.fetch(query, ctx.author.id)
        if not records:
            await ctx.fail("You have no recorded tracks")
            return

        for record in records:
            player.tracks.put_nowait(
                QueueEntry(
                    ctx, record["title"], record["url"], uploader=record["uploader"]
                )
            )

        await ctx.send(f"Enqueued your top tracks `({len(records)} tracks)`")


class Voice(commands.Cog):
    """
    Module for voice permissions.
    """

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage()
        return True

    async def cog_before_invoke(self, ctx):
        ctx.voice_state = await VOICE_STATES.get_state(ctx)


    @decorators.group(
        brief="Manage the DJ role.",
        name="djrole",
    )
    @checks.cooldown()
    async def _djrole(self, ctx):
        """
        Usage: {0}djrole [option]
        Alias: {0}dj
        Output: Manages the server DJ role
        Options:
            - create # Creates the server DJ role
            - delete # Deletes the server DJ role
        Notes:
            This role, when added to users,
            gives users full control over
            the music module. Note that all
            users with the Move Members,
            Mute Members, and Deafen Members
            permission will always be DJs.
        """
        if ctx.invoked_subcommand is None:
            djrole = ctx.voice_state.djrole
            if djrole:
                await ctx.send(
                    f"{self.bot.emote_dict['dj']} The current DJ role is `@{djrole.name}`"
                )
            else:
                await ctx.fail("This server currently has no DJ role.")

    @_djrole.command(
        aliases=["make"],
        brief="Create a DJ role.",
        name="create",
    )
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(manage_roles=True)
    async def djrole_create(self, ctx, *, role: converters.UniqueRole = None):
        """
        Usage: {0}djrole create [role]
        Alias: {0}djrole make
        Output: Creates a DJ role
        Notes:
            If no role is specified,
            a new role named DJ will be
            automatically created by the bot.
        """
        if role is None:
            role_color = discord.Color.from_rgb(*self.bot.constants.Colors.PINK)
            role = await ctx.guild.create_role(
                name="DJ", color=role_color, reason="For music permission management."
            )

        query = """
                INSERT INTO musicconf (server_id, djrole)
                VALUES ($1, $2)
                ON CONFLICT (server_id)
                DO UPDATE SET djrole = $2
                WHERE musicconf.server_id = $1;
                """
        await self.bot.cxn.execute(query, ctx.guild.id, role.id)
        ctx.voice_state.djrole = role
        await ctx.success(f"Saved `@{role.name}` as this server's DJ role.")

    @_djrole.command(
        aliases=["remove"],
        brief="Delete the DJ role.",
        name="delete",
    )
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(manage_roles=True)
    async def djrole_delete(self, ctx):
        """
        Usage: {0}djrole delete
        Alias: {0}djrole remove
        Output:
            Deletes the server DJ role
        """
        query = """
                UPDATE musicconf 
                SET djrole = NULL
                WHERE server_id = $1;
                """
        await self.bot.cxn.execute(query, ctx.guild.id)
        ctx.voice_state.djrole = None
        await ctx.success("Deleted this server's DJ role.")

    @decorators.command(
        brief="Show the server djs.",
        name="djs",
        examples="""
                {0}djs
                """,
    )
    @checks.cooldown()
    async def _djs(self, ctx):
        """
        Usage: {0}djs
        Output:
            Show all the server music djs
            and their respective statuses.
        """
        message = ""
        all_status = {
            "online": {"users": [], "emoji": self.bot.emote_dict["online"]},
            "idle": {"users": [], "emoji": self.bot.emote_dict["idle"]},
            "dnd": {"users": [], "emoji": self.bot.emote_dict["dnd"]},
            "offline": {"users": [], "emoji": self.bot.emote_dict["offline"]},
        }

        def is_dj(user):
            djrole = ctx.voice_state.djrole
            if djrole in user.roles:
                return True
            if user.guild_permissions.move_members:
                return True
            if user.guild_permissions.mute_members:
                return True
            if user.guild_permissions.deafen_members:
                return True
            return False

        for user in ctx.guild.members:
            if not user.bot:
                if is_dj(user):
                    all_status[str(user.status)]["users"].append(f"{user}")

        for g in all_status:
            if all_status[g]["users"]:
                message += (
                    f"{all_status[g]['emoji']} `{', '.join(all_status[g]['users'])}`\n"
                )

        await ctx.send_or_reply(
            f"{self.bot.emote_dict['dj']} DJs in **{ctx.guild.name}:**\n\n{message}",
        )

    @decorators.command(
        aliases=["musicchannel"],
        brief="Bind music commands to a channel.",
        name="bind",
    )
    @checks.has_perms(manage_channels=True)
    async def _bind(self, ctx, *, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        c = await ctx.confirm(
            f"This action will prevent all music commands in all channels except {channel.mention}."
        )
        if c:
            query = """
                    INSERT INTO musicconf (server_id, bind)
                    VALUES ($1, $2)
                    ON CONFLICT (server_id)
                    DO UPDATE SET bind = $2
                    WHERE musicconf.server_id = $1;
                    """
            await self.bot.cxn.execute(query, ctx.guild.id, channel.id)
            ctx.voice_state.bind = channel
            await ctx.success(f"Successfully bound to {channel.mention}.")

    @decorators.command(
        brief="Unbind music commands to a channel.",
        name="unbind",
    )
    @checks.has_perms(manage_channels=True)
    async def _unbind(self, ctx):
        query = """
                UPDATE musicconf
                SET bind = NULL
                WHERE server_id = $1
                """
        await self.bot.cxn.execute(query, ctx.guild.id)
        ctx.voice_state.bind = None
        await ctx.success(f"No longer bound to any channel.")

    @decorators.command(
        aliases=["musiclock"],
        brief="Lock the music module to DJs.",
        name="djlock",
    )
    @checks.has_perms(manage_channels=True)
    async def _djlock(self, ctx):
        """
        Usage: {0}djlock
        Alias: {0}musiclock
        Output: Locks the music module to DJs
        """
        c = await ctx.confirm(
            "This will disallow all non-DJs from using the music module."
        )
        if c:
            query = """
                    INSERT INTO musicconf (server_id, djlock)
                    VALUES ($1, True)
                    ON CONFLICT (server_id)
                    DO UPDATE SET djlock = True
                    WHERE musicconf.server_id = $1;
                    """
            await self.bot.cxn.execute(query, ctx.guild.id)
            ctx.voice_state.djlock = True
            await ctx.success(f"Successfully djlocked the music module.")

    @decorators.command(
        aliases=["musicunlock"],
        brief="Unlock the music module.",
        name="djunlock",
    )
    @checks.has_perms(manage_channels=True)
    async def _djunlock(self, ctx):
        """
        Usage: {0}djunlock
        Alias: {0}musicunlock
        Output: Unlocks the music module to all
        """
        query = """
                UPDATE musicconf
                SET djlock = False
                WHERE server_id = $1
                """
        await self.bot.cxn.execute(query, ctx.guild.id)
        ctx.voice_state.djlock = False
        await ctx.success(f"Successfully djunlocked the music module.")

    ####################
    ## VOICE COMMANDS ##
    ####################

    @decorators.command(
        brief="Move a user from a voice channel.",
        examples="""
                {0}vcmove Hecate Neutra #music
                """,
    )
    @checks.guild_only()
    @checks.bot_has_guild_perms(move_members=True)
    @checks.has_perms(move_members=True)
    @checks.cooldown()
    async def vcmove(
        self,
        ctx,
        targets: commands.Greedy[converters.DiscordMember(False)],
        *,  # Do not disambiguate when accepting multiple members.
        channel: typing.Union[discord.VoiceChannel, discord.StageChannel],
    ):
        """
        Usage: {0}vcmove <targets>... <channel>
        Output: Moves members into a new voice channel
        Permission: Move Members
        """
        if not len(targets):
            return await ctx.usage()

        vcmoved = []
        failed = []
        for target in targets:
            try:
                await target.move_to(channel)
            except discord.HTTPException:
                failed.append((str(target), e))
                continue
            except Exception as e:
                failed.append((str(target, e)))
            vcmoved.append(str(target))
        if vcmoved:
            await ctx.success(f"VC Moved `{', '.join(vcmoved)}`")
        if failed:
            await helpers.error_info(ctx, failed)

    @decorators.command(
        brief="Kick users from a voice channel.",
        implemented="2021-04-22 01:13:53.346822",
        updated="2021-07-04 17:59:53.792869",
        examples="""
                {0}vckick Neutra Hecate#3523
                """,
    )
    @checks.guild_only()
    @checks.has_perms(move_members=True)
    @checks.bot_has_guild_perms(move_members=True)
    @checks.cooldown()
    async def vckick(self, ctx, *targets: converters.DiscordMember(False)):
        """
        Usage: {0}vckick <targets>...
        Output: Kicks passed members from their channel
        Permission: Move Members
        """
        vckicked = []
        failed = []
        for target in targets:
            try:
                await target.move_to(None)
            except discord.HTTPException:
                failed.append((str(target), e))
                continue
            except Exception as e:
                failed.append((str(target, e)))
            vckicked.append(str(target))
        if vckicked:
            await ctx.success(f"VC Kicked `{', '.join(vckicked)}`")
        if failed:
            await helpers.error_info(ctx, failed)

    @decorators.command(
        brief="Kick all users from a voice channel.",
        implemented="2021-04-22 01:13:53.346822",
        updated="2021-07-04 17:59:53.792869",
        examples="""
                {0}vcpurge #music
                """,
    )
    @checks.guild_only()
    @checks.bot_has_guild_perms(move_members=True)
    @checks.has_perms(move_members=True)
    @checks.cooldown()
    async def vcpurge(
        self, ctx, *, channel: typing.Union[discord.VoiceChannel, discord.StageChannel]
    ):
        """
        Usage: {0}vcpurge <voice channel>
        Output: Kicks all members from the channel
        Permission: Move Members
        """
        if len(channel.members) == 0:
            return await ctx.fail(f"No users in voice channel {channel.mention}.")
        failed = []
        for member in channel.members:
            try:
                await member.move_to(None)
            except Exception as e:
                failed.append((str(member), e))
                continue
        await ctx.success(f"Purged {channel.mention}.")
        if failed:
            await helpers.error_info(ctx, failed)

    @decorators.command(
        brief="Transfer users into a new channel.",
        examples="""
                {0}vctransfer #music
                """,
    )
    @checks.bot_has_guild_perms(move_members=True)
    @checks.has_perms(move_members=True)
    @checks.cooldown()
    async def vctransfer(
        self,
        ctx,
        from_channel: typing.Union[discord.VoiceChannel, discord.StageChannel],
        *,
        to_channel: typing.Union[discord.VoiceChannel, discord.StageChannel],
    ):
        """
        Usage: {0}vctransfer <voice channel> <voice channel>
        Output: Transfers all members from one channel to another
        Permission: Move Members
        """
        if len(from_channel.members) == 0:
            return await ctx.fail(f"No users in voice channel {from_channel.mention}.")
        failed = []
        for member in from_channel.members:
            try:
                await member.move_to(to_channel)
            except Exception as e:
                failed.append((str(member), e))
                continue
        await ctx.success(f"Transferred {from_channel.mention}to {to_channel.mention}.")
        if failed:
            await helpers.error_info(ctx, failed)


class SpotifyTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.batch_lock = asyncio.Lock(loop=bot.loop)
        self.spotify = MusicUtils.spotify(bot)

        self.spotify_data = defaultdict(dict)
        self.inserter.start()

    @tasks.loop(seconds=30.0)
    async def inserter(self):
        if self.spotify_data:
            async with self.batch_lock:
                query = """
                        INSERT INTO spotify (user_id, album_id, artist_id, track_id, insertion)
                        SELECT x.user_id, x.album_id, x.artist_id, x.track_id, x.insertion
                        FROM JSONB_TO_RECORDSET($1::JSONB)
                        AS x(user_id BIGINT, album_id TEXT, artist_id TEXT, track_id TEXT, insertion TIMESTAMP);
                        """

                data = json.dumps(
                    [
                        {
                            "user_id": user_id,
                            "album_id": info["album_id"],
                            "artist_id": info["artist_id"],
                            "track_id": info["track_id"],
                            "insertion": info["updated"],
                        }
                        for user_id, info in self.spotify_data.items()
                    ]
                )
                self.spotify_data.clear()
            await self.bot.cxn.execute(query, data)

    # @commands.Cog.listener()
    # @decorators.event_check(lambda s, b, a: a.activities)
    # async def on_presence_update(self, before, after):
    #     for activity in after.activities:
    #         if type(activity) is discord.activity.Spotify:
    #             if activity not in before.activities:
    #                 async with self.batch_lock:
    #                     try:
    #                         track = await self.spotify.get_track(activity.track_id)
    #                     except Exception:
    #                         return
    #                     self.spotify_data[after.id].update({
    #                         "album_id": track["album"]["id"],
    #                         "artist_id": track["artists"][0]["id"],
    #                         "track_id": activity.track_id,
    #                         "updated": str(datetime.utcnow())
    #                     })

    @decorators.group(name="spotify", hidden=True)
    @checks.cooldown()
    async def _spotify(self, ctx):
        if ctx.invoked_subcommand is None:
            return await ctx.invoke(self.spotify_status)

    @_spotify.command()
    async def spotify_status(self, ctx, *, user: converters.DiscordMember = None):
        user = user or ctx.author
        status = None
        for activity in user.activities:
            if type(activity) is discord.activity.Spotify:
                status = activity
                break

        if not status:
            await ctx.fail("No current spotify status found.")
            return

        e = discord.Embed(color=self.bot.constants.embed)
        e.title = f"{user.display_name}'s Spotify Track Information"
        e.description = f"```fix\n{status.title}```"
        e.add_field(name="Artist", value=status.artist)
        e.add_field(name="Album", value=status.album)
        e.add_field(
            name="Duration",
            value=MusicUtils.parse_duration(int(status.duration.total_seconds())),
        )
        e.add_field(name="Song URL", value=status.track_url, inline=False)
        e.set_thumbnail(url=status.album_cover_url)
        track = await self.spotify.get_track(status.track_id)
        artist_id = track["artists"][0]["id"]
        album_id = track["album"]["id"]
        await ctx.send_or_reply(embed=e)

    # @decorators.command()
    # async def _track(self, ctx, *, user: converters.DiscordUser = None):
    #     user = user or ctx.author
    #     # query = """
    #     #         SELECT ARRAY(
    #     #             SELECT track_id
    #     #             FROM spotify
    #     #             WHERE user_id = $1
    #     #             ORDER BY COUNT(track_id) DESC
    #     #             ORDER BY insertion DESC
    #     #             LIMIT 10;

    #     #         );
    #     #         """
    #     query = """
    #             select track_id, count(*) as c
    #             FROM spotify
    #             where user_id = $1
    #             group by track_id
    #             order by c DESC
    #             limit 10;
    #             """

    #     records = await self.bot.cxn.fetch(query, user.id)

    #     async def format_track(track_id, count):
    #         track = await self.spotify.get_track(track_id)
    #         title = f"{track['name']} `{count} listening session{'' if count == 1 else 's'}`"
    #         field = f"**Track URL:** {track['external_urls']['spotify']}\n**Album:** [{track['album']['name']}]({track['album']['external_urls']['spotify']})\n**Artist**: [{track['artists'][0]['name']}]({track['artists'][0]['external_urls']['spotify']})"
    #         return (title, field)

    #     entries = []
    #     for record in records:
    #         entries.append(await format_track(*record))

    #     p = pagination.MainMenu(pagination.FieldPageSource(entries=entries, per_page=5, title=f"{user.display_name}'s Top 10 Spotify Tracks"))
    #     try:
    #         await p.start(ctx)
    #     except menus.MenuError as e:
    #         await ctx.send(e)


def setup(bot):
    bot.music_cogs = ["PLAYER", "PLAYLISTS", "AUDIO", "QUEUE", "VOICE"]
    bot.add_cog(Player(bot))
    bot.add_cog(Playlists(bot))
    bot.add_cog(Queue(bot))
    bot.add_cog(Audio(bot))
    bot.add_cog(Voice(bot))
    bot.add_cog(SpotifyTracker(bot))


class Views:
    class Confirmation(discord.ui.View):
        def __init__(self, interaction: discord.Interaction, message="", **kwargs):
            super().__init__(timeout=30.0)
            self.interaction = interaction
            self.message = message
            self.kwargs = kwargs
            self.result = None

        async def prompt(self):
            if self.interaction.response.is_done():
                await self.interaction.followup.send(
                    self.message, **self.kwargs, ephemeral=True, view=self
                )
            else:
                await self.interaction.response.send_message(
                    self.message, **self.kwargs, ephemeral=True, view=self
                )
            await self.wait()
            return self.result

        async def on_timeout(self):
            await self.interaction.edit_original_message(
                content="**Confirmation Cancelled.**", view=None
            )

        async def interaction_check(self, interaction):
            if self.interaction.user.id == interaction.user.id:
                return True
            else:
                await interaction.response.send_message(
                    "Only the command invoker can use this button.", ephemeral=True
                )

        @discord.ui.button(
            emoji=constants.emotes["success"], style=discord.ButtonStyle.gray
        )
        async def _confirm(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            self.result = self.interaction
            self.stop()

        @discord.ui.button(
            emoji=constants.emotes["failed"], style=discord.ButtonStyle.gray
        )
        async def _deny(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            await self.interaction.edit_original_message(
                content="**Confirmation Cancelled.**", view=None
            )
            self.stop()

    class TrackView(discord.ui.View):
        def __init__(self, ctx):
            super().__init__(timeout=120)
            self.ctx = ctx
            self.voice_client = ctx.voice_state.voice
            self.player = ctx.voice_state
            self.input_lock = asyncio.Lock()

            self.clear_items()
            self.fill_items()

        async def start(self):
            embed = MusicUtils.make_embed(self.ctx, self.ctx.voice_state.source)
            self.message = await self.ctx.send(embed=embed, view=self)

        def fill_items(self, _help=None):
            if _help:
                self.add_item(self._return)
                self.add_item(self._delete)
                return

            self.add_item(self._help)
            self.add_item(self._rewind)
            if self.voice_client.is_paused():
                self.add_item(self._resume)
            else:
                self.add_item(self._pause)
            self.add_item(self._forward)
            self.add_item(self._trash)
            if Checks.is_dj(self.ctx):
                self.add_item(Views.EffectSelect(self.ctx))

        async def interaction_check(self, interaction):
            if self.ctx.author.id == interaction.user.id:
                return True
            else:
                await interaction.response.send_message(
                    "Only the command invoker can use this button.", ephemeral=True
                )

        async def on_timeout(self):
            try:
                await self.message.edit(view=None)
            except Exception:
                pass

        async def on_error(
            self,
            error: Exception,
            item: discord.ui.Item,
            interaction: discord.Interaction,
        ):
            if interaction.response.is_done():
                await interaction.followup.send(str(error), ephemeral=True)
            else:
                await interaction.response.send_message(str(error), ephemeral=True)

        @discord.ui.button(
            emoji=constants.emotes["fastforward"], style=discord.ButtonStyle.gray
        )
        async def _forward(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            try:
                Checks.assert_is_dj(self.ctx)
            except commands.BadArgument as e:
                await interaction.response.send_message(str(e), ephemeral=True)
            position = self.ctx.voice_state.source.position
            to_seek = position + 10
            if to_seek >= self.ctx.voice_state.source.ytdl.raw_duration:
                to_seek = self.ctx.voice_state.source.ytdl.raw_duration

            self.player.alter_audio(position=to_seek)
            embed = MusicUtils.make_embed(self.ctx, self.ctx.voice_state.source)
            await interaction.message.edit(embed=embed)
            await interaction.response.send_message(
                "Fast forwarded 10 seconds.", ephemeral=True
            )

        @discord.ui.button(
            emoji=constants.emotes["rewind"], style=discord.ButtonStyle.gray
        )
        async def _rewind(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            try:
                Checks.assert_is_dj(self.ctx)
            except commands.BadArgument as e:
                await interaction.response.send_message(str(e), ephemeral=True)
            position = self.ctx.voice_state.source.position
            to_seek = position - 10
            if to_seek <= 0:
                to_seek = 0

            embed = MusicUtils.make_embed(self.ctx, self.ctx.voice_state.source)
            await interaction.message.edit(embed=embed)
            self.player.alter_audio(position=to_seek)
            await interaction.response.send_message(
                "Rewinded 10 seconds.", ephemeral=True
            )

        @discord.ui.button(
            emoji=constants.emotes["pause"], style=discord.ButtonStyle.gray
        )
        async def _pause(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            try:
                Checks.assert_is_dj(self.ctx)
            except commands.BadArgument as e:
                await interaction.response.send_message(str(e), ephemeral=True)

            self.voice_client.pause()
            self.clear_items()
            self.fill_items()
            await interaction.message.edit(view=self)
            await interaction.response.send_message(
                "Paused the player.", ephemeral=True
            )

        @discord.ui.button(
            emoji=constants.emotes["play"], style=discord.ButtonStyle.gray
        )
        async def _resume(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            try:
                Checks.assert_is_dj(self.ctx)
            except commands.BadArgument as e:
                await interaction.response.send_message(str(e), ephemeral=True)

            self.voice_client.resume()
            self.clear_items()
            self.fill_items()
            await interaction.message.edit(view=self)
            await interaction.response.send_message(
                "Resumed the player.", ephemeral=True
            )

        @discord.ui.button(
            emoji=constants.emotes["skip"], style=discord.ButtonStyle.gray
        )
        async def _skip(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            if Checks.is_requester(self.ctx):
                self.ctx.voice_state.skip()  # Song requester can skip.

            elif Checks.is_dj(self.ctx):
                self.ctx.voice_state.skip()  # Server Djs can skip.

            elif self.ctx.author.id not in self.ctx.voice_state.skip_votes:
                self.ctx.voice_state.skip_votes.add(self.ctx.author.id)
                total_votes = len(self.ctx.voice_state.skip_votes)

                listeners = self.ctx.voice_state.voice.channel.members
                valid_voters = [user for user in listeners if not user.bot]
                required_votes = len(valid_voters) + 1 // 2  # Require majority

                if total_votes >= required_votes:
                    self.ctx.voice_state.skip()
                else:
                    await interaction.response.send_message(
                        f"{constants.emotes['success']} Skip vote added, currently at `{total_votes}/{required_votes}`"
                    )
                    return
            else:
                await interaction.response.send_message(
                    "You have already voted to skip this track.", ephemeral=True
                )
                return
            await interaction.response.send_message(
                f"{constants.emotes['success']} Skipped the current track."
            )

        @discord.ui.button(
            emoji=constants.emotes["previous"], style=discord.ButtonStyle.gray
        )
        async def _prev(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            try:
                Checks.assert_is_dj(self.ctx)
            except commands.BadArgument as e:
                await interaction.response.send_message(str(e), ephemeral=True)
            else:
                prev = self.ctx.voice_state.previous
                if not prev:
                    await interaction.response.send_message(
                        "No previous song to play.", ephemeral=True
                    )
                    return

                self.ctx.voice_state.replay(prev)
                self.ctx.voice_state.skip()

                await interaction.response.send_message(
                    f"{constants.emotes['success']} Replaying the previous song."
                )

        @discord.ui.button(
            emoji=constants.emotes["help"], style=discord.ButtonStyle.gray
        )
        async def _help(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            self.clear_items()
            self.fill_items(_help=True)
            embed = discord.Embed(color=constants.embed)
            embed.set_author(
                name="Pagination Help Page",
                icon_url=self.ctx.bot.user.display_avatar.url,
            )
            embed.description = (
                "Read below for a description of each button and it's function."
            )
            embed.add_field(
                name=constants.emotes["backward2"] + "  Jump to the first page",
                value="This button shows the first page of the pagination session.",
                inline=False,
            )
            embed.add_field(
                name=constants.emotes["backward"] + "  Show the previous page",
                value="This button shows the previous page of the pagination session.",
                inline=False,
            )
            embed.add_field(
                name=constants.emotes["1234button"] + "  Input a page number",
                value="This button shows a page after you input a page number.",
                inline=False,
            )
            embed.add_field(
                name=constants.emotes["forward"] + "  Show the next page",
                value="This button shows the next page of the pagination session",
                inline=False,
            )
            embed.add_field(
                name=constants.emotes["forward2"] + "  Jump to the last page.",
                value="This button shows the last page of the pagination session",
                inline=False,
            )
            embed.add_field(
                name=constants.emotes["help"] + "  Show the help page.",
                value="This button shows this help page.",
                inline=False,
            )
            embed.add_field(
                name=constants.emotes["previous"] + "  Play the previous track.",
                value="This button skips the current track and replays the previous track. (if it exists)",
                inline=False,
            )
            embed.add_field(
                name=constants.emotes["download"] + "  Save the current queue.",
                value="This button saves the current queue under a name so that you can listen to it later.",
                inline=False,
            )
            embed.add_field(
                name=constants.emotes["skip"] + "  Play the next track.",
                value="This button skips the current track and plays the next track. (If it exists)",
                inline=False,
            )
            embed.add_field(
                name=constants.emotes["trash"] + "  Delete session.",
                value="This button deletes the message and ends the session.",
                inline=False,
            )
            await interaction.message.edit(embed=embed, view=self)

        @discord.ui.button(
            emoji=constants.emotes["trash"], style=discord.ButtonStyle.gray
        )
        async def _trash(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            await interaction.message.delete()
            self.stop()

        @discord.ui.button(label="Delete session", style=discord.ButtonStyle.red)
        async def _delete(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            await interaction.message.delete()
            self.stop()

        @discord.ui.button(
            label="Return to main page", style=discord.ButtonStyle.blurple
        )
        async def _return(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            self.clear_items()
            self.fill_items()
            page = MusicUtils.make_embed(self.ctx, self.ctx.voice_state.source)
            if isinstance(page, discord.Embed):
                await interaction.message.edit(embed=page, view=self)
            else:
                await interaction.message.edit(content=page, view=self)

    class ButtonPages(discord.ui.View):
        async def __init__(self, ctx, pages, *, content=""):
            super().__init__(timeout=120)
            self.ctx = ctx
            self.pages = pages
            self.content = content
            self.page_number = 1
            self.max_pages = len(self.pages)
            self.current_page = pages[0]
            self.input_lock = asyncio.Lock()

            self.clear_items()
            self.fill_items()

            self.message = await self.send_message()

        def fill_items(self, _help=None):
            if _help:
                self.add_item(self._return)
                self.add_item(self._delete)
                return

            self.add_item(self._first)
            self.add_item(self._back)
            self.add_item(self._select)
            self.add_item(self._next)
            self.add_item(self._last)

        async def send_message(self):
            self.update_view(1)
            if isinstance(self.pages[0], discord.Embed):
                message = await self.ctx.send(
                    self.content, embed=self.pages[0], view=self
                )
            else:
                message = await self.ctx.send(self.content + self.pages[0], view=self)
            return message

        async def interaction_check(self, interaction):
            if self.ctx.author.id == interaction.user.id:
                return True
            else:
                await interaction.response.send_message(
                    "Only the command invoker can use this button.", ephemeral=True
                )

        async def on_timeout(self):
            try:
                await self.message.edit(view=None)
            except Exception:
                pass

        async def on_error(
            self,
            error: Exception,
            item: discord.ui.Item,
            interaction: discord.Interaction,
        ):
            if interaction.response.is_done():
                await interaction.followup.send(str(error), ephemeral=True)
            else:
                await interaction.response.send_message(str(error), ephemeral=True)

        def update_view(self, page_number):
            self.page_number = page_number
            self._first.disabled = page_number == 1
            self._back.disabled = page_number == 1
            self._next.disabled = page_number == self.max_pages
            self._last.disabled = page_number == self.max_pages
            self._select.disabled = self.max_pages == 1

        async def show_page(self, interaction):
            page = self.current_page = self.pages[self.page_number - 1]
            if isinstance(page, discord.Embed):
                await interaction.message.edit(embed=page, view=self)
            else:
                await interaction.message.edit(content=page, view=self)

        @discord.ui.button(
            emoji=constants.emotes["backward2"], style=discord.ButtonStyle.gray
        )
        async def _first(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            self.update_view(1)
            await self.show_page(interaction)

        @discord.ui.button(
            emoji=constants.emotes["backward"], style=discord.ButtonStyle.gray
        )
        async def _back(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            self.update_view(self.page_number - 1)
            await self.show_page(interaction)

        @discord.ui.button(
            emoji=constants.emotes["forward"], style=discord.ButtonStyle.gray
        )
        async def _next(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            self.update_view(self.page_number + 1)
            await self.show_page(interaction)

        @discord.ui.button(
            emoji=constants.emotes["forward2"], style=discord.ButtonStyle.gray
        )
        async def _last(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            self.update_view(self.max_pages)
            await self.show_page(interaction)

        @discord.ui.button(
            emoji=constants.emotes["1234button"], style=discord.ButtonStyle.grey
        )
        async def _select(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            """lets you type a page number to go to"""
            if self.input_lock.locked():
                await interaction.response.send_message(
                    "Already waiting for your response...", ephemeral=True
                )
                return

            if self.message is None:
                return

            async with self.input_lock:
                channel = self.message.channel
                author_id = interaction.user and interaction.user.id
                await interaction.response.send_message(
                    "What page do you want to go to?", ephemeral=True
                )

                def message_check(m):
                    if not m.author.id == author_id:
                        return False
                    if not channel == m.channel:
                        return False
                    if not m.content.isdigit():
                        return False
                    if not 1 <= int(m.content) <= self.max_pages:
                        raise IndexError(
                            f"Page number must be between 1 and {self.max_pages}"
                        )
                    return True

                try:
                    msg = await self.ctx.bot.wait_for(
                        "message", check=message_check, timeout=30.0
                    )
                except asyncio.TimeoutError:
                    await interaction.followup.send(
                        "Selection expired.", ephemeral=True
                    )
                    await asyncio.sleep(5)
                else:
                    page = int(msg.content)
                    try:
                        await msg.delete()
                    except:
                        pass
                    self.update_view(page)
                    await self.show_page(interaction)

    class QueueSource(ButtonPages):
        async def __init__(self, ctx, pages, *, playlist=None, content=""):
            self.ctx = ctx
            self.content = content
            self.playlist = playlist
            self.input_lock = asyncio.Lock()

            await super().__init__(ctx, pages, content=content)

        def fill_items(self, _help=None):
            if _help:
                self.add_item(self._return)
                self.add_item(self._delete)
                return

            if self.playlist:
                self.add_item(self._first)
                self.add_item(self._back)
                self.add_item(self._select)
                self.add_item(self._next)
                self.add_item(self._last)
                self.add_item(self._help)
                if self.playlist.is_owner(self.ctx.author):
                    self.add_item(self._subtract)
                else:
                    self.add_item(self._download)
                self.add_item(self._enqueue)
                if self.playlist.is_owner(self.ctx.author):
                    self.add_item(self._drop)
                else:
                    self.add_item(self._like)
                self.add_item(self._trash)
                return

            self.add_item(self._first)
            self.add_item(self._back)
            self.add_item(self._select)
            self.add_item(self._next)
            self.add_item(self._last)
            self.add_item(self._help)
            self.add_item(self._prev)
            self.add_item(self._download)
            self.add_item(self._skip)
            self.add_item(self._trash)
            if Checks.is_dj(self.ctx):
                self.add_item(Views.QueueSelect(self.ctx))

        @discord.ui.button(
            emoji=constants.emotes["minus"], style=discord.ButtonStyle.gray
        )
        async def _subtract(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            """Remove a track from a saved playlist."""
            if self.input_lock.locked():
                await interaction.response.send_message(
                    "Already waiting for your response...", ephemeral=True
                )
                return

            if self.message is None:
                return

            async with self.input_lock:
                channel = self.message.channel
                author_id = interaction.user and interaction.user.id
                await interaction.response.send_message(
                    "Please enter the track index to be removed from this playlist.",
                    ephemeral=True,
                )

                def message_check(m):
                    if not m.author.id == author_id:
                        return False
                    if not channel == m.channel:
                        return False
                    if not m.content.isdigit():
                        return False
                    if int(m.content) < 1:
                        raise IndexError(
                            "Invalid index. Please specify a valid track index to remove."
                        )
                    return True

                try:
                    msg = await self.ctx.bot.wait_for(
                        "message", check=message_check, timeout=30.0
                    )
                except asyncio.TimeoutError:
                    await interaction.followup.send(
                        "Playlist editing expired.", ephemeral=True
                    )
                    await asyncio.sleep(5)
                else:
                    track = self.playlist.pop(int(msg.content))
                    res = await Views.Confirmation(
                        interaction,
                        message=f"**This action will remove track: `{track['title']}` from this playlist. Do you wish to continue?**",
                    ).prompt()
                    if res:
                        await self.playlist.finalize()
                        await res.edit_original_message(
                            content="Saved this playlist to your liked songs.",
                            view=None,
                        )
                    try:
                        await msg.delete()
                    except:
                        pass

        @discord.ui.button(
            emoji=constants.emotes["delete"], style=discord.ButtonStyle.gray
        )
        async def _drop(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            res = await Views.Confirmation(
                interaction,
                message="**This will permanently delete this playlist. Do you wish to continue?**",
            ).prompt()
            if res:
                name = self.playlist.name.title()
                await self.playlist.delete()
                await res.edit_original_message(
                    content=f"Deleted playlist: **{name}**", view=None
                )

        @discord.ui.button(
            emoji=constants.emotes["heart"], style=discord.ButtonStyle.gray
        )
        async def _like(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            await self.playlist.like()
            await interaction.response.send_message(
                content="Added a like to the playlist.", ephemeral=True
            )

        @discord.ui.button(
            emoji=constants.emotes["music"], style=discord.ButtonStyle.gray
        )
        async def _enqueue(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            player = await self.ctx.voice_state.ensure_voice_state(self.ctx)
            player.tracks.extend(self.playlist.entries)
            await interaction.response.send_message(
                f"Enqueued playlist: **{self.playlist.name.title()}** `({self.playlist.tracks} tracks)`"
            )

        @discord.ui.button(
            emoji=constants.emotes["download"], style=discord.ButtonStyle.gray
        )
        async def _download(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            """Saves the current playlist"""
            if self.input_lock.locked():
                await interaction.response.send_message(
                    "Already waiting for your response...", ephemeral=True
                )
                return

            if self.message is None:
                return

            async with self.input_lock:
                channel = self.message.channel
                author_id = interaction.user and interaction.user.id
                await interaction.response.send_message(
                    "Enter a name to save this playlist under.", ephemeral=True
                )

                def message_check(m):
                    if not m.author.id == author_id:
                        return False
                    if not channel == m.channel:
                        return False
                    return True

                try:
                    msg = await self.ctx.bot.wait_for(
                        "message", check=message_check, timeout=30.0
                    )
                except asyncio.TimeoutError:
                    await interaction.followup.send(
                        "Playlist saving expired.", ephemeral=True
                    )
                    await asyncio.sleep(5)
                else:
                    name = msg.content.lower()
                    queue = [self.ctx.voice_state.entry] + list(
                        self.ctx.voice_state.tracks
                    )
                    queue = json.dumps([entry.json for entry in queue])
                    query = """
                            INSERT INTO playlists (owner_id, name, queue)
                            VALUES ($1, $2, $3::JSONB)
                            """
                    try:
                        await self.ctx.bot.cxn.execute(
                            query, author_id, name.lower(), queue
                        )
                    except asyncpg.exceptions.UniqueViolationError:
                        await interaction.followup.send(
                            "You already have a saved playlist with that name. Please try again with a different name",
                            ephemeral=True,
                        )
                        return
                    await interaction.followup.send(
                        f"{constants.emotes['success']} Saved the current queue with name: **{name}**"
                    )
                    try:
                        await msg.delete()
                    except:
                        pass

        @discord.ui.button(
            emoji=constants.emotes["skip"], style=discord.ButtonStyle.gray
        )
        async def _skip(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            if Checks.is_requester(self.ctx):
                self.ctx.voice_state.skip()  # Song requester can skip.

            elif Checks.is_dj(self.ctx):
                self.ctx.voice_state.skip()  # Server Djs can skip.

            elif self.ctx.author.id not in self.ctx.voice_state.skip_votes:
                self.ctx.voice_state.skip_votes.add(self.ctx.author.id)
                total_votes = len(self.ctx.voice_state.skip_votes)

                listeners = self.ctx.voice_state.voice.channel.members
                valid_voters = [user for user in listeners if not user.bot]
                required_votes = len(valid_voters) + 1 // 2  # Require majority

                if total_votes >= required_votes:
                    self.ctx.voice_state.skip()
                else:
                    await interaction.response.send_message(
                        f"{constants.emotes['success']} Skip vote added, currently at `{total_votes}/{required_votes}`"
                    )
                    return
            else:
                await interaction.response.send_message(
                    "You have already voted to skip this track.", ephemeral=True
                )
                return
            await interaction.response.send_message(
                f"{constants.emotes['success']} Skipped the current track."
            )

        @discord.ui.button(
            emoji=constants.emotes["previous"], style=discord.ButtonStyle.gray
        )
        async def _prev(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            try:
                Checks.assert_is_dj(self.ctx)
            except commands.BadArgument as e:
                await interaction.response.send_message(str(e), ephemeral=True)
            else:
                prev = self.ctx.voice_state.previous
                if not prev:
                    await interaction.response.send_message(
                        "No previous song to play.", ephemeral=True
                    )
                    return

                self.ctx.voice_state.replay(prev)
                self.ctx.voice_state.skip()

                await interaction.response.send_message(
                    f"{constants.emotes['success']} Replaying the previous song."
                )

        @discord.ui.button(
            emoji=constants.emotes["help"], style=discord.ButtonStyle.gray
        )
        async def _help(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            self.clear_items()
            self.fill_items(_help=True)
            embed = discord.Embed(color=constants.embed)
            embed.set_author(
                name="Pagination Help Page",
                icon_url=self.ctx.bot.user.display_avatar.url,
            )
            embed.description = (
                "Read below for a description of each button and it's function."
            )
            embed.add_field(
                name=constants.emotes["backward2"] + "  Jump to the first page",
                value="This button shows the first page of the pagination session.",
                inline=False,
            )
            embed.add_field(
                name=constants.emotes["backward"] + "  Show the previous page",
                value="This button shows the previous page of the pagination session.",
                inline=False,
            )
            embed.add_field(
                name=constants.emotes["1234button"] + "  Input a page number",
                value="This button shows a page after you input a page number.",
                inline=False,
            )
            embed.add_field(
                name=constants.emotes["forward"] + "  Show the next page",
                value="This button shows the next page of the pagination session",
                inline=False,
            )
            embed.add_field(
                name=constants.emotes["forward2"] + "  Jump to the last page.",
                value="This button shows the last page of the pagination session",
                inline=False,
            )
            embed.add_field(
                name=constants.emotes["help"] + "  Show the help page.",
                value="This button shows this help page.",
                inline=False,
            )
            embed.add_field(
                name=constants.emotes["previous"] + "  Play the previous track.",
                value="This button skips the current track and replays the previous track. (if it exists)",
                inline=False,
            )
            embed.add_field(
                name=constants.emotes["download"] + "  Save the current queue.",
                value="This button saves the current queue under a name so that you can listen to it later.",
                inline=False,
            )
            embed.add_field(
                name=constants.emotes["skip"] + "  Play the next track.",
                value="This button skips the current track and plays the next track. (If it exists)",
                inline=False,
            )
            embed.add_field(
                name=constants.emotes["trash"] + "  Delete session.",
                value="This button deletes the message and ends the session.",
                inline=False,
            )
            embed.set_footer(
                text=f"Previously viewing page {self.page_number} of {self.max_pages}"
            )
            await interaction.message.edit(embed=embed, view=self)

        @discord.ui.button(
            emoji=constants.emotes["trash"], style=discord.ButtonStyle.gray
        )
        async def _trash(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            await interaction.message.delete()
            self.stop()

        @discord.ui.button(label="Delete session", style=discord.ButtonStyle.red)
        async def _delete(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            await interaction.message.delete()
            self.stop()

        @discord.ui.button(
            label="Return to main page", style=discord.ButtonStyle.blurple
        )
        async def _return(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            self.clear_items()
            self.fill_items()
            if isinstance(self.current_page, discord.Embed):
                await interaction.message.edit(embed=self.current_page, view=self)
            else:
                await interaction.message.edit(content=self.current_page, view=self)

    class QueueView(QueueSource):
        """
        Simple button page session that turns
        a list of strings into a pagination session
        by splitting them up and adding them to the
        description of an embed.
        Parameters:
            ctx: The context of a command
            entries: The list of strings
            per_page: How many entries per embed
            index: Whether or not to prepend numbers to each entry
            desc_head: Prefix the description with a string
            desc_foot: Suffix the description with a string
        """

        def __init__(
            self,
            ctx,
            entries,
            *,
            per_page: int = 10,
            index: bool = True,
            desc_head: str = "",
            desc_foot: str = "",
            playlist=None,
            content="",
        ):
            self.ctx = ctx
            self.entries = entries
            self.playlist = playlist
            self.per_page = per_page
            self.index = index
            self.desc_head = desc_head
            self.desc_foot = desc_foot
            self.content = content

            self.embed = discord.Embed(color=ctx.bot.constants.embed)

        async def start(self):
            self.pages = self.create_pages(self.entries, self.per_page)
            await super().__init__(
                self.ctx, self.pages, playlist=self.playlist, content=self.content
            )

        def create_pages(self, entries, per_page):
            embeds = []
            index = 0
            while entries:
                embed = self.embed.copy()
                embed.description = self.desc_head
                if self.index:
                    for entry in entries[:per_page]:
                        index += 1
                        embed.description += f"{index}. {entry}\n"
                else:
                    embed.description += "\n".join(entries[:per_page])
                embed.description += self.desc_foot
                del entries[:per_page]

                embeds.append(embed)

            for count, embed in enumerate(embeds, start=1):
                embed.set_footer(text=f"Page {count} of {len(embeds)}")
            return embeds

    class SimpleView(ButtonPages):
        """
        Simple button page session that turns
        a list of strings into a pagination session
        by splitting them up and adding them to the
        description of an embed.
        Parameters:
            ctx: The context of a command
            entries: The list of strings
            per_page: How many entries per embed
            index: Whether or not to prepend numbers to each entry
            desc_head: Prefix the description with a string
            desc_foot: Suffix the description with a string
        """

        def __init__(
            self,
            ctx,
            entries,
            *,
            per_page: int = 10,
            index: bool = True,
            desc_head: str = "",
            desc_foot: str = "",
            content="",
        ):
            self.ctx = ctx
            self.entries = entries

            self.per_page = per_page
            self.index = index
            self.desc_head = desc_head
            self.desc_foot = desc_foot
            self.content = content

            self.embed = discord.Embed(color=ctx.bot.constants.embed)

        async def start(self):
            self.pages = self.create_pages(self.entries, self.per_page)
            await super().__init__(self.ctx, self.pages, content=self.content)

        def create_pages(self, entries, per_page):
            embeds = []
            index = 0
            while entries:
                embed = self.embed.copy()
                embed.description = self.desc_head
                if self.index:
                    for entry in entries[:per_page]:
                        index += 1
                        embed.description += f"{index}. {entry}\n"
                else:
                    embed.description += "\n".join(entries[:per_page])
                embed.description += self.desc_foot
                del entries[:per_page]

                embeds.append(embed)

            for count, embed in enumerate(embeds, start=1):
                embed.set_footer(text=f"Page {count} of {len(embeds)}")
            return embeds

    class QueueSelect(discord.ui.Select):
        def __init__(self, ctx):
            self.ctx = ctx
            self.queue = queue = ctx.voice_state.tracks
            self.opts = (
                {  # Mapping of labels, descriptions, functions, and success messages
                    "Shuffle": (
                        "Shuffle the queue.",
                        queue.shuffle,
                        "Shuffled the queue.",
                    ),
                    "Queue Loop": (
                        "Loop the entire queue.",
                        ctx.voice_state.queue_loop,
                        "Looped the queue.",
                    ),
                    "Track Loop": (
                        "Loop the current track.",
                        ctx.voice_state.track_loop,
                        "Looped the current track.",
                    ),
                    "Unloop": (
                        "Unloop the queue and/or track.",
                        ctx.voice_state.unloop,
                        "Unlooped the track and queue.",
                    ),
                    "Reverse": (
                        "Reverse the queue.",
                        queue.reverse,
                        "Reversed the queue.",
                    ),
                    "Clear": (
                        "Remove all tracks from the queue.",
                        queue.clear,
                        "Cleared the queue.",
                    ),
                    "Dedupe": (
                        "Remove track duplicates from the queue.",
                        queue.deduplicate,
                        "Removed duplicate tracks from the queue.",
                    ),
                    "Cleanup": (
                        "Remove tracks queued by users who left the channel.",
                        queue.leave_cleanup,
                        "Removed absent user enqueues.",
                    ),
                }
            )
            super().__init__(placeholder="Queue Management", options=self.get_options())

        def get_options(self):
            """Creates a list of SelectOption"""
            return [
                discord.SelectOption(label=label, description=items[0])
                for label, items in sorted(self.opts.items())
            ]

        async def callback(self, interaction: discord.Interaction):
            selection = interaction.data["values"][0]
            if selection == "Cleanup":
                self.opts[selection][1](self.ctx.voice_state.voice.channel.members)
            else:
                self.opts[selection][1]()
            await interaction.response.send_message(
                f"{self.ctx.bot.emote_dict['success']} {self.opts[selection][2]}",
                ephemeral=True,
            )
            await interaction.message.edit(view=self.view)

    class EffectSelect(discord.ui.Select):
        def __init__(self, ctx):
            self.ctx = ctx
            self.player = ctx.voice_state
            self.input_lock = asyncio.Lock()
            self.effects = [
                # "backwards",
                "bass",
                "earrape",
                "echo",
                "muffle",
                "nightcore",
                "phaser",
                "robot",
                "tremolo",
                "treble",
                "vibrato",
                "whisper",
            ]
            super().__init__(placeholder="Audio Effects", options=self.get_options())

        def get_options(self):
            """Creates a list of SelectOption"""
            PASS = self.player._ctx.bot.emote_dict["success"]
            FAIL = self.player._ctx.bot.emote_dict["failed"]
            get_emoji = lambda e: PASS if self.player[e] else FAIL
            get_desc = (
                lambda e: f"Toggle the {e} audio effect. (Currently {'en' if self.player[e] else 'dis'}abled)"
            )

            speed_pitch_reset = [
                discord.SelectOption(
                    label="Speed",
                    description=f"Alter the speed of the player. (Current speed: {self.player['speed']})",
                    emoji=constants.emotes["speed"],
                ),
                discord.SelectOption(
                    label="Pitch",
                    description=f"Alter the pitch of the player. (Current pitch: {self.player['pitch']})",
                    emoji=constants.emotes["music"],
                ),
                discord.SelectOption(
                    label="Reset",
                    description="Reset all effects to default.",
                    emoji=constants.emotes["trash"],
                ),
            ]
            return [
                discord.SelectOption(
                    label=effect, description=get_desc(effect), emoji=get_emoji(effect)
                )
                for effect in self.effects
            ] + speed_pitch_reset

        async def callback(self, interaction: discord.Interaction):
            selection = interaction.data["values"][0]
            if selection == "Reset":
                self.player.clear_effects()
                await interaction.response.send_message(
                    "All audio effects have been restored to default.", ephemeral=True
                )
            elif selection in ["Speed", "Pitch"]:
                if self.input_lock.locked():
                    await interaction.response.send_message(
                        "Already waiting for your response...", ephemeral=True
                    )
                    return

                async with self.input_lock:
                    channel = self.ctx.channel
                    author_id = interaction.user and interaction.user.id
                    await interaction.response.send_message(
                        f"Enter a {selection.lower()} value between `0.25` and `2`.",
                        ephemeral=True,
                    )

                    def message_check(m):
                        if not m.author.id == author_id:
                            return False
                        if not channel == m.channel:
                            return False
                        try:
                            float(m.content)
                        except ValueError:
                            return False
                        else:
                            return True

                    try:
                        msg = await self.ctx.bot.wait_for(
                            "message", check=message_check, timeout=30.0
                        )
                    except asyncio.TimeoutError:
                        await interaction.followup.send(
                            f"{selection} input expired.", ephemeral=True
                        )
                        await asyncio.sleep(5)
                    else:
                        value = float(msg.content)
                        if not 0.25 <= value <= 2:
                            await interaction.followup.send(
                                f"Audio {selection.lower()} must be between `0.25` and `2`.",
                                ephemeral=True,
                            )
                        else:
                            self.player[selection.lower()] = value
                            await interaction.followup.send(
                                f"Audio {selection.lower()} set to `{value}`.",
                                ephemeral=True,
                            )
                        try:
                            await msg.delete()
                        except:
                            pass
            else:
                self.player[selection] = not self.player[selection]
                await interaction.response.send_message(
                    f"{selection.capitalize()} effect {'en' if self.player[selection] else 'dis'}abled.",
                    ephemeral=True,
                )
            self.options.clear()
            self.options.extend(self.get_options())
            await interaction.message.edit(view=self.view)

    class Effects(discord.ui.View):
        def __init__(self, ctx, player):
            self.ctx = ctx
            self.player = player
            self.message = None
            super().__init__(timeout=120)

            self.add_item(Views.EffectSelect(ctx))

        async def interaction_check(self, interaction):
            if self.ctx.author.id == interaction.user.id:
                return True
            else:
                await interaction.response.send_message(
                    "Only the command invoker can use this menu.", ephemeral=True
                )

        async def on_error(
            self,
            error: Exception,
            item: discord.ui.Item,
            interaction: discord.Interaction,
        ):
            if interaction.response.is_done():
                await interaction.followup.send(str(error), ephemeral=True)
            else:
                await interaction.response.send_message(str(error), ephemeral=True)

        async def on_timeout(self):
            if self.message:
                await self.message.delete()
            self.stop()

        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, row=2)
        async def cancel_button(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            await interaction.message.delete()
            self.stop()

        @discord.ui.button(label="Save", style=discord.ButtonStyle.green, row=2)
        async def save_button(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            await interaction.message.edit(
                "Successfully saved audio effect settings.", view=None
            )
            self.stop()

        @discord.ui.button(label="Reset", style=discord.ButtonStyle.blurple, row=2)
        async def reset_button(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            self.player.clear_effects()
            await interaction.message.edit(
                "Successfully reset effect settings.", view=None
            )
            self.stop()

        @discord.ui.button(label="Help", style=discord.ButtonStyle.gray, row=2)
        async def help_button(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            embed = discord.Embed(color=self.ctx.bot.constants.embed)
            embed.set_author(
                name="Welcome to the audio effects help page.",
                icon_url=self.ctx.bot.user.display_avatar.url,
            )
            embed.description = f"Below are comprehensive instructions on how to use the `{self.ctx.clean_prefix}effects` dropdown menu command. Each effect in the dropdown menu is a toggle switch. This means that if an effect is disabled, it will be enabled when clicked, and vice-versa. The **Main Menu** category below shows how to work the main page, while the **Help Menu** category shows instructions for this page."
            embed.add_field(
                name="Main Menu",
                value="`Cancel` simply deletes the menu.\n`Reset` resets all effects to default.\n`Save` saves the effect settings and stops the menu.\n`Help` shows this help page.",
            )
            embed.add_field(
                name="Help Menu",
                value="`Cancel` simply deletes the menu.\n`Effects` shows all effect outputs.\n`Return` will return to the main menu.",
            )
            embed.set_footer(
                text="This menu will expire after 2 minutes of inactivity."
            )
            help_view = Views.HelpMenu(self.ctx, self.player)
            await interaction.message.edit(content=None, embed=embed, view=help_view)
            help_view.message = self.message
            self.stop()

    class HelpMenu(discord.ui.View):
        def __init__(self, ctx, player):
            self.ctx = ctx
            self.player = player
            self.message = None
            self.effects = {
                # "backwards": "This effect plays the song from the end.",
                "bass": "This effect boosts the bass clef audio.",
                "earrape": "This effect makes audio sound scratchy.",
                "echo": "This effect makes audio sound with an echo.",
                "muffle": "This effect makes the audio sound muffled.",
                "nightcore": "This effect plays audio with a higher pitch and speed.",
                "phaser": "This effect makes audio sound synthetically generated.",
                "robot": "This effect makes audio sound like a robot is speaking.",
                "treble": "This effect boosts the treble clef audio.",
                "tremolo": "This effect creates minature breaks in the audio.",
                "vibrato": "This effect makes the audio dilate for vibrato.",
                "whisper": "This effect makes audio sound as if it were being whispered.",
            }
            super().__init__(timeout=120)

        async def interaction_check(self, interaction):
            if self.ctx.author.id == interaction.user.id:
                return True
            else:
                await interaction.response.send_message(
                    "Only the command invoker can use this button.", ephemeral=True
                )

        async def on_error(
            self,
            error: Exception,
            item: discord.ui.Item,
            interaction: discord.Interaction,
        ):
            if interaction.response.is_done():
                await interaction.followup.send(str(error), ephemeral=True)
            else:
                await interaction.response.send_message(str(error), ephemeral=True)

        async def on_timeout(self):
            if self.message:
                await self.message.delete()
            self.stop()

        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
        async def cancel_button(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            await interaction.message.delete()
            self.stop()

        @discord.ui.button(label="Effects", style=discord.ButtonStyle.green)
        async def effects_button(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            embed = discord.Embed(color=self.ctx.bot.constants.embed)
            embed.title = "Audio Effects"
            embed.description = "Press the `Cancel` button to delete this message.\nPress the `Return` button to return to the main menu.\nPress the `Help` button for the help menu."
            embed.set_footer(
                text="This menu will expire after 2 minutes of inactivity."
            )
            for name, description in self.effects.items():
                embed.add_field(name=name, value=description)

            return_view = Views.Return(self.ctx, self.player)
            await interaction.message.edit(content=None, embed=embed, view=return_view)
            return_view.message = self.message
            self.stop()

        @discord.ui.button(label="Return", style=discord.ButtonStyle.blurple)
        async def main_button(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            effects_view = Views.Effects(self.ctx, self.player)
            await interaction.message.edit(content=None, embed=None, view=effects_view)
            effects_view.message = self.message
            self.stop()

    class Return(discord.ui.View):
        def __init__(self, ctx, player):
            self.ctx = ctx
            self.player = player
            self.message = None
            self.effects = {
                # "backwards": "This effect plays the song from the end.",
                "bass": "This effect boosts the bass clef audio.",
                "earrape": "This effect makes audio sound scratchy.",
                "echo": "This effect makes audio sound with an echo.",
                "muffle": "This effect makes the audio sound muffled.",
                "nightcore": "This effect plays audio with a higher pitch and speed.",
                "phaser": "This effect makes audio sound synthetically generated.",
                "robot": "This effect makes audio sound like a robot is speaking.",
                "treble": "This effect boosts the treble clef audio.",
                "tremolo": "This effect creates minature breaks in the audio.",
                "vibrato": "This effect makes the audio dilate for vibrato.",
                "whisper": "This effect makes audio sound as if it were being whispered.",
            }
            super().__init__(timeout=120)

        async def interaction_check(self, interaction):
            if self.ctx.author.id == interaction.user.id:
                return True
            else:
                await interaction.response.send_message(
                    "Only the command invoker can use this button.", ephemeral=True
                )

        async def on_error(
            self,
            error: Exception,
            item: discord.ui.Item,
            interaction: discord.Interaction,
        ):
            if interaction.response.is_done():
                await interaction.followup.send(str(error), ephemeral=True)
            else:
                await interaction.response.send_message(str(error), ephemeral=True)

        async def on_timeout(self):
            if self.message:
                await self.message.delete()
            self.stop()

        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
        async def cancel_button(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            await interaction.message.delete()
            self.stop()

        @discord.ui.button(label="Return", style=discord.ButtonStyle.blurple)
        async def main_button(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            effect_view = Views.Effects(self.ctx, self.player)
            await interaction.message.edit(
                content="Select an audio effect from the dropdown below.",
                embed=None,
                view=effect_view,
            )
            effect_view.message = self.message
            self.stop()

        @discord.ui.button(label="Help", style=discord.ButtonStyle.gray)
        async def help_button(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ):
            embed = discord.Embed(color=self.ctx.bot.constants.embed)
            embed.set_author(
                name="Welcome to the audio effects help page.",
                icon_url=self.ctx.bot.user.display_avatar.url,
            )
            embed.description = f"Below are comprehensive instructions on how to use the `{self.ctx.clean_prefix}effects` dropdown menu command. Each effect in the dropdown menu is a toggle switch. This means that if an effect is disabled, it will be enabled when clicked, and vice-versa. The **Main Menu** category below shows how to work the main page, while the **Help Menu** category shows instructions for this page."
            embed.add_field(
                name="Main Menu",
                value="`Cancel` simply deletes the menu.\n`Reset` resets all effects to default.\n`Save` saves the effect settings and stops the menu.\n`Help` shows this help page.",
            )
            embed.add_field(
                name="Help Menu",
                value="`Cancel` simply deletes the menu.\n`Effects` shows all effect outputs.\n`Return` will return to the main menu.",
            )
            embed.set_footer(
                text="This menu will expire after 2 minutes of inactivity."
            )
            help_view = Views.HelpMenu(self.ctx, self.player)
            await interaction.message.edit(content=None, embed=embed, view=help_view)
            help_view.message = self.message
            self.stop()
