import discord
import pytz

from discord.ext import commands, menus
from datetime import datetime
from utilities import utils, pagination, converters


def setup(bot):
    bot.add_cog(Timezones(bot))


class Timezones(commands.Cog):
    """
    Module for all timezone data
    """

    def __init__(self, bot):
        self.bot = bot

    async def get_datetime(self, member):
        a = None
        tzerror = False
        query = """SELECT timezone FROM usertime WHERE user_id = $1"""
        timezone = await self.bot.cxn.fetchval(query, member.id) or None
        try:
            if timezone:
                tz = timezone
                a = pytz.timezone(tz)
        except pytz.exceptions.UnknownTimeZoneError:
            tzerror = True
        return datetime.now(a), tzerror

    @commands.command(brief="Show the current time.")
    async def timenow(self, ctx, twenty_four_hour_time=True):
        """Date time module."""

        dandt, tzerror = await self.get_datetime(ctx.author)
        em = discord.Embed(color=self.bot.constants.embed)
        if twenty_four_hour_time is True:
            em.add_field(
                name="\u23F0 Time", value="{:%H:%M:%S}".format(dandt), inline=True
            )
        else:
            em.add_field(
                name="\u23F0 Time", value="{:%I:%M:%S %p}".format(dandt), inline=True
            )
        em.add_field(
            name="\U0001F4C5 Date", value="{:%d %B %Y}".format(dandt), inline=True
        )
        if tzerror:
            em.add_field(
                name="\u26A0 Warning",
                value="Invalid timezone specified, system timezone was used instead.",
                inline=True,
            )

        await ctx.send(content=None, embed=em)
        msg = "**Local Date and Time:** ```{:Time: %H:%M:%S\nDate: %Y-%m-%d```}".format(
            dandt
        )
        await ctx.send(msg)

    @commands.command(
        brief="Remove your timezone.",
        aliases=["rmtz", "removetz", "removetimzone", "rmtimezone", "remtimezone"],
    )
    async def remtz(self, ctx):
        """Remove your timezone"""

        await self.bot.cxn.execute(
            "DELETE FROM usertime WHERE user_id = $1;", ctx.author.id
        )
        await ctx.send(
            f"{self.bot.emote_dict['success']} Your timezone has been removed."
        )

    @commands.command(brief="Set your timezone.", aliases=["settimezone", "settime"])
    async def settz(self, ctx, *, tz_search=None):
        """List all the supported timezones."""

        msg = ""
        if tz_search is None:
            title = "Available Timezones"
            entry = [x for x in pytz.all_timezones]
            p = pagination.SimplePages(
                entry,
                per_page=20,
                index=False,
                desc_head="```prolog\n",
                desc_foot="```",
            )
            p.embed.title = title
            try:
                await p.start(ctx)
            except menus.MenuError as e:
                await ctx.send(e)
        else:
            tz_list = utils.disambiguate(tz_search, pytz.all_timezones, None, 5)
            if not tz_list[0]["ratio"] == 1:
                edit = True
                tz_list = [x["result"] for x in tz_list]
                index, message = await pagination.Picker(
                    embed_title="Select one of the 5 closest matches.",
                    list=tz_list,
                    ctx=ctx,
                ).pick(embed=True, syntax="prolog")

                if index < 0:
                    return await message.edit(
                        content=f"{self.bot.emote_dict['info']} Timezone selection cancelled.",
                        embed=None,
                    )

                selection = tz_list[index]
            else:
                edit = False
                selection = tz_list[0]["result"]

            query = """
                    INSERT INTO usertime
                    VALUES ($1, $2)
                    ON CONFLICT (user_id)
                    DO UPDATE SET timezone = $2
                    WHERE usertime.user_id = $1;
                    """
            await self.bot.cxn.execute(query, ctx.author.id, selection)
            msg = f"{self.bot.emote_dict['success']} Timezone set to `{selection}`"
            if edit:
                await message.edit(content=msg, embed=None)
            else:
                await ctx.send(msg)

    @commands.command(brief="See a member's timezone.", aliases=["tz"])
    async def timezone(self, ctx, *, member: converters.DiscordUser = None):
        """See a member's timezone."""

        if member is None:
            member = ctx.author

        query = """
                SELECT timezone
                FROM usertime
                WHERE user_id = $1;
                """
        timezone = await self.bot.cxn.fetchval(query, member.id) or None
        if timezone is None:
            return await ctx.send(
                f"{self.bot.emote_dict['error']} `{member}` has not set their timezone. "
                f"Use the `{ctx.prefix}settz [Region/City]` command."
            )

        await ctx.send(f"`{member}'` timezone is *{timezone}*")

    @commands.command(brief="Show a user's current time.")
    async def time(self, ctx, *, member: discord.Member = None):
        """
        Usage: -time [member]
        Output: Time for the passed user, if set.
        Notes: Will default to you if no user is specified
        """
        timenow = utils.getClockForTime(datetime.utcnow().strftime("%I:%M %p"))
        if member is None:
            member = ctx.author

        query = """
                SELECT timezone
                FROM usertime
                WHERE user_id = $1;
                """
        tz = await self.bot.cxn.fetchval(query, member.id) or None
        if tz is None:
            msg = (
                f"`{member}` hasn't set their timezone yet. "
                f"They can do so with `{ctx.prefix}settz [Region/City]` command.\n"
                f"The current UTC time is **{timenow}**."
            )
            await ctx.send(msg)
            return

        t = self.getTimeFromTZ(tz)
        if t is None:
            await ctx.send(
                f"{self.bot.emote_dict['failed']} I couldn't find that timezone."
            )
            return
        t["time"] = utils.getClockForTime(t["time"])
        if member:
            msg = f'It\'s currently **{t["time"]}** where {member.display_name} is.'
        else:
            msg = "{} is currently **{}**".format(t["zone"], t["time"])

        await ctx.send(msg)

    def getTimeFromTZ(self, tz, t=None):
        # Assume sanitized zones - as they're pulled from pytz
        # Let's get the timezone list
        tz_list = utils.disambiguate(tz, pytz.all_timezones, None, 3)
        if not tz_list[0]["ratio"] == 1:
            # We didn't find a complete match
            return None
        zone = pytz.timezone(tz_list[0]["result"])
        if t is None:
            zone_now = datetime.now(zone)
        else:
            zone_now = t.astimezone(zone)
        return {"zone": tz_list[0]["result"], "time": zone_now.strftime("%I:%M %p")}
