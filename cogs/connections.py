import discord
from discord.ext import commands

from utilities import checks
from utilities import converters
from utilities import decorators
from utilities import pagination

from utilities import spotify
from utilities.discord import oauth as discord_oauth


def setup(bot):
    bot.add_cog(Connections(bot))

class Connections(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def truncate(self, string, max_chars=20):
        return (string[: max_chars - 3] + "...") if len(string) > max_chars else string

    def hyperlink(self, name, url, max_chars=20):
        return f"**[{self.truncate(name, max_chars)}]({url})**"
    
    def format_track(self, track):
        return self.hyperlink(track['name'], track['external_urls']['spotify'])

    def format_artists(self, artists):
        artists = artists[:3] # more than 3 artists looks bad on embed
        max_chars = 40 // len(artists)
        return ', '.join(self.hyperlink(artist['name'], artist['external_urls']['spotify'], max_chars) for artist in artists)

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
        pass

    @_sp.command(brief="Get top spotify tracks.", aliases=["tt"])
    async def top_tracks(self, ctx, user: converters.DiscordMember = None):
        user = user or ctx.author
        sp_user = await self.get_spotify_user(ctx, user)
        if not sp_user:
            return

        top_tracks = await sp_user.get_top_tracks()
        if not top_tracks:
            await ctx.send_or_reply(f"error")
            return
        if not top_tracks.get("items"):
            await ctx.send_or_reply(f"no top tracks")
            return

        entries = [
            f"{self.format_track(track)} by {self.format_artists(track['artists'])}"
            for track in top_tracks["items"]
        ]

        p = pagination.SimplePages(
            entries=entries,
            per_page=10,
        )
        p.embed.title = f"{user.display_name}'s Spotify Top Tracks"
        p.embed.set_thumbnail(url=spotify.CONSTANTS.WHITE_ICON)
        await p.start(ctx)

    @_sp.command(brief="Get top spotify artists.", aliases=["ta"])
    async def top_artists(self, ctx, user: converters.DiscordMember = None):
        user = user or ctx.author
        sp_user = await self.get_spotify_user(ctx, user)
        if not sp_user:
            return

        top_artists = await sp_user.get_top_artists()
        if not top_artists:
            await ctx.send_or_reply(f"error")
            return
        if not top_artists.get("items"):
            await ctx.send_or_reply(f"no top artists")
            return

        entries = [
            self.hyperlink(artist['name'], artist['external_urls']['spotify'], max_chars=50)
            for artist in top_artists["items"]
        ]

        p = pagination.SimplePages(
            entries=entries,
            per_page=10,
        )
        p.embed.title = f"{user.display_name}'s Spotify Top Artists"
        p.embed.set_thumbnail(url=spotify.CONSTANTS.WHITE_ICON)
        await p.start(ctx)

    @_sp.command(brief="Disconnect your spotify account.")
    async def disconnect(self, ctx):
        query = """
                DELETE FROM spotify_auth
                WHERE user_id = $1;
                """
        status = await self.bot.cxn.execute(query, ctx.author.id)
        if status != "DELETE 0":
            await ctx.success("Successfully disconnected your spotify account.")
        else:
            await ctx.fail(
                "You have not connected your Spotify account yet."
            )
