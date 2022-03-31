import typing
import discord
from discord.ext import commands, tasks

from utilities import checks
from utilities import converters
from utilities import decorators
from utilities import pagination

from utilities import spotify
from utilities.discord import oauth as discord_oauth


async def setup(bot):
    await bot.add_cog(Spotify(bot))


class Spotify(commands.Cog):
    """
    Spotify account statistics.
    """

    def __init__(self, bot):
        self.bot = bot
        self.time_map = {
            "short_term": "month",
            "medium_term": "semester",
            "long_term": "year",
        }
        self.live_stats.start()

    @tasks.loop(seconds=1)
    async def live_stats(self):

        r = await self.bot.http_utils.post(
            "http://localhost:3000/stats",
            data={
                "members": len(self.bot.users),
                "servers": len(self.bot.guilds),
                "messages": sum(self.bot.message_stats.values()),
            },
            headers={"Content-Type": "application/json"},
            res_method="json",
        )

    def truncate(self, string, max_chars=20):
        return (string[: max_chars - 3] + "...") if len(string) > max_chars else string

    def hyperlink(self, name, url, max_chars=20):
        return f"**[{self.truncate(name, max_chars)}]({url})**"

    def format_track(self, track):
        return self.hyperlink(track["name"], track["external_urls"]["spotify"])

    def format_artists(self, artists):
        artists = artists[:3]  # more than 3 artists looks bad on embed
        max_chars = 40 // len(artists)
        return ", ".join(
            self.hyperlink(
                artist["name"], artist["external_urls"]["spotify"], max_chars
            )
            for artist in artists
        )

    async def get_spotify_user(self, ctx, user):
        sp_user = await spotify.User.load(user.id)
        if not sp_user:
            if user == ctx.author:
                view = discord.ui.View()
                button = discord.ui.Button(
                    label="Click here to connect your Spotify account!",
                    url=discord_oauth.get_auth_url(),
                )
                view.add_item(button)
                await ctx.fail(
                    "You have not connected your Spotify account yet.", view=view
                )

            else:
                await ctx.fail(
                    f"User **{user}** `{user.id}` has not connected their Spotify account yet."
                )
        return sp_user

    @decorators.group(
        name="spotify",
        aliases=["sp", "sf"],
        brief="Manage spotify stats and playlists",
    )
    @checks.cooldown()
    async def _sp(self, ctx):
        if not ctx.invoked_subcommand:
            sp_user = await self.get_spotify_user(ctx, ctx.author)
            if sp_user:
                await ctx.success("You have already connected your spotify account.")

    @_sp.command(brief="Get top spotify tracks.", aliases=["tt"])
    async def top_tracks(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember],
        time_frame: converters.SpotifyTimeFrame = "short_term",
    ):
        user = user or ctx.author
        sp_user = await self.get_spotify_user(ctx, user)
        if not sp_user:
            return

        top_tracks = await sp_user.get_top_tracks(time_range=time_frame)
        print(top_tracks)

        if not top_tracks.get("items"):
            await ctx.fail(
                f"{f'User **{user}** `{user.id}` has' if user != ctx.author else 'You have'} no top tracks."
            )
            return

        entries = [
            f"{self.format_track(track)} by {self.format_artists(track['artists'])}"
            for track in top_tracks["items"]
        ]

        p = pagination.SimplePages(
            entries=entries,
            per_page=10,
        )
        p.embed.title = f"{user.display_name}'s top Spotify tracks in the past {self.time_map[time_frame]}."
        p.embed.set_thumbnail(url=spotify.CONSTANTS.WHITE_ICON)
        await p.start(ctx)

    @_sp.command(brief="Get top spotify artists.", aliases=["ta"])
    async def top_artists(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember],
        time_frame: converters.SpotifyTimeFrame = "short_term",
    ):
        user = user or ctx.author
        sp_user = await self.get_spotify_user(ctx, user)
        if not sp_user:
            return

        top_artists = await sp_user.get_top_artists()

        if not top_artists.get("items"):
            await ctx.fail(
                f"{f'User **{user}** `{user.id}` has' if user != ctx.author else 'You have'} no top artists."
            )
            return

        entries = [
            self.hyperlink(
                artist["name"], artist["external_urls"]["spotify"], max_chars=50
            )
            for artist in top_artists["items"]
        ]

        p = pagination.SimplePages(
            entries=entries,
            per_page=10,
        )
        p.embed.title = f"{user.display_name}'s top Spotify artists in the past {self.time_map[time_frame]}."
        p.embed.set_thumbnail(url=spotify.CONSTANTS.WHITE_ICON)
        await p.start(ctx)

    @_sp.command(brief="Get recent Spotify listens", aliases=["r"])
    async def recent(self, ctx, *, user: converters.DiscordMember = None):
        user = user or ctx.author
        sp_user = await self.get_spotify_user(ctx, user)
        if not sp_user:
            return

        recent = await sp_user.get_recently_played()
        print(recent)
        if not recent.get("items"):
            await ctx.fail(
                f"{f'User **{user}** `{user.id}` has' if user != ctx.author else 'You have'} no recent tracks."
            )
            return

        entries = [
            f"{self.format_track(item['track'])} by {self.format_artists(item['track']['artists'])}"
            for item in recent["items"]
        ]

        p = pagination.SimplePages(
            entries=entries,
            per_page=10,
        )
        p.embed.title = f"{user.display_name}'s recently played Spotify tracks."
        p.embed.set_thumbnail(url=spotify.CONSTANTS.WHITE_ICON)
        await p.start(ctx)

    @_sp.command(brief="Get current song data")
    async def plst(self, ctx, *, user: converters.DiscordMember = None):
        sp_user = await self.get_spotify_user(ctx, ctx.author)
        url = "https://open.spotify.com/playlist/490Su62TmufWRkdxmggDnY?si=37542cff68fb4899"
        url = "https://open.spotify.com/playlist/6K9uHsMwuRGRWvHLNK4rT2?si=f7be2003e315494b"
        uri = spotify.url_to_uri(url)
        data = await spotify.get_playlist(uri)
        del data["tracks"]
        print(data)

    @_sp.command(brief="Get user playlists")
    async def playlists(self, ctx, *, user: converters.DiscordMember = None):
        user = user or ctx.author
        sp_user = await self.get_spotify_user(ctx, ctx.author)
        data = await sp_user.get_playlists()
        if not data.get("items"):
            await ctx.fail(
                f"{f'User **{user}** `{user.id}` has' if user != ctx.author else 'You have'} no recent tracks."
            )
            return

        entries = [
            f"{self.format_track(playlist)} ID: `{playlist['id']}`"
            for playlist in data["items"]
        ]

        p = pagination.SimplePages(
            entries=entries,
            per_page=10,
        )
        p.embed.title = f"{user.display_name}'s Spotify playlists."
        p.embed.set_thumbnail(url=spotify.CONSTANTS.WHITE_ICON)
        await p.start(ctx)

    @_sp.command(brief="Get user playlists")
    async def user_playlists(self, ctx, username):
        data = await spotify.get_user_playlists(username)
        if not data.get("items"):
            await ctx.fail(f"No user found with username: `{username}`")
            return

        entries = [
            f"{self.format_track(playlist)} ID: `{playlist['id']}`"
            for playlist in data["items"]
        ]

        p = pagination.SimplePages(
            entries=entries,
            per_page=10,
        )
        p.embed.title = f"{username}'s Spotify playlists."
        p.embed.set_thumbnail(url=spotify.CONSTANTS.WHITE_ICON)
        await p.start(ctx)

    @_sp.command(brief="Disconnect your Spotify account.")
    async def disconnect(self, ctx):
        query = """
                DELETE FROM spotify_auth
                WHERE user_id = $1;
                """
        status = await self.bot.cxn.execute(query, ctx.author.id)
        if status != "DELETE 0":
            await ctx.success("Successfully disconnected your spotify account.")
        else:
            await ctx.fail("You have not connected your Spotify account yet.")
