import re
import json
import pytz
import time
import discord

from datetime import datetime, timedelta
from discord.ext import commands, menus
from geopy import geocoders

from utilities import utils, pagination, converters, checks
from utilities import decorators


def setup(bot):
    bot.add_cog(Time(bot))


class Time(commands.Cog):
    """
    Module for time functions.
    """

    def __init__(self, bot):
        self.bot = bot
        self.stopwatches = {}
        self.geo = geocoders.Nominatim(user_agent="Snowbot")

    @decorators.command(
        brief="Remove your timezone.",
        aliases=["rmtz", "removetz", "removetimzone", "rmtimezone", "remtimezone"],
    )
    async def remtz(self, ctx):
        """Remove your timezone"""

        await self.bot.cxn.execute(
            "DELETE FROM usertime WHERE user_id = $1;", ctx.author.id
        )
        await ctx.send_or_reply(
            f"{self.bot.emote_dict['success']} Your timezone has been removed."
        )

    @decorators.command(brief="List all available timezones.")
    async def listtz(self, ctx):
        """
        Usage: -listtz
        Output:
            A pagination session that shows
            all available timezones.
        """
        await ctx.invoke(self.settz, tz_search=None)

    @decorators.command(brief="Set your timezone.", aliases=["settimezone", "settime"])
    async def settz(self, ctx, *, tz_search=None):
        """
        Usage: -settz <timezone>
        Aliases: -settimezone, -settime
        Output: Sets your timezone
        Notes:
            Will provide you with the 5 closest
            timezone matches if the supplied timezone
            is invalid. Invoke with no arguments to
            show all available timezones.
        """

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
                await ctx.send_or_reply(e)
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
                await ctx.send_or_reply(msg)

    @decorators.command(
        brief="Show times for all users.", aliases=["alltime", "alltimes"]
    )
    async def usertimes(self, ctx):
        """
        Usage: -usertimes
        Aliases: -alltime, -alltimes
        Output:
            Shows the current time for all
            users who set their timezone
        """
        query = """
                SELECT *
                FROM usertime;
                """
        message = await ctx.send_or_reply(
            content=f"{self.bot.emote_dict['loading']} **Loading user timezones...**",
        )
        result = await self.bot.cxn.fetch(query)
        users = []
        for x in result:
            member = ctx.guild.get_member(x[0])
            if member:
                users.append((member, x[1]))

        if users:
            width = []
            for user in users:
                width.append(len(str(user[0])))
            msg = ""
            for user in users:
                t = self.getTimeFromTZ(user[1])
                if t is None:
                    continue
                t["time"] = utils.getClockForTime(t["time"])
                msg += f"{str(user[0]).ljust(max(*width))}| {t['time']} ({user[1]})\n"
            await message.edit(
                content=f"{self.bot.emote_dict['announce']} **Usertimes:**"
            )
            p = pagination.MainMenu(
                pagination.TextPageSource(text=msg, prefix="```prolog")
            )
            try:
                await p.start(ctx)
            except menus.MenuError as e:
                await ctx.send_or_reply(e)
        else:
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['failed']} No users have set their timezones.",
            )

    @decorators.command(brief="See a member's timezone.", aliases=["tz"])
    async def timezone(self, ctx, *, member: converters.DiscordUser = None):
        """
        Usage: -timezone <user>
        Aliases: -tz
        Output:
            Shows you the passed member's timezone, if applicable
        """

        if member is None:
            member = ctx.author

        query = """
                SELECT timezone
                FROM usertime
                WHERE user_id = $1;
                """
        timezone = await self.bot.cxn.fetchval(query, member.id) or None
        if timezone is None:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['warn']} `{member}` has not set their timezone. "
                f"Use the `{ctx.prefix}settz [Region/City]` command.",
            )

        await ctx.send_or_reply(
            content=f"{self.bot.emote_dict['announce']} `{member}'s timezone is {timezone}`",
        )

    @decorators.command(brief="Show a user's current time.", aliases=["time"])
    async def usertime(self, ctx, *, member: discord.Member = None):
        """
        Usage: -usertime [member]
        Alias: -time
        Output: Time for the passed user, if set.
        Notes: Will default to you if no user is specified
        """
        timenow = utils.getClockForTime(datetime.utcnow().strftime("%a %I:%M %p"))
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
                f"{self.bot.emote_dict['warn']} "
                f"`{member}` hasn't set their timezone yet. "
                f"They can do so with `{ctx.prefix}settz [Region/City]` command.\n"
                f"The current UTC time is **{timenow}**."
            )
            await ctx.send_or_reply(msg)
            return

        t = self.getTimeFromTZ(tz)
        if t is None:
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['failed']} I couldn't find that timezone.",
            )
            return
        t["time"] = utils.getClockForTime(t["time"])
        if member:
            msg = f"{self.bot.emote_dict['announce']} `It's currently {t['time']} where {member.display_name} is.`"
        else:
            msg = f"{self.bot.emote_dict['announce']} `It's {t['time']} currently where you are.`"

        await ctx.send_or_reply(msg)

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
        return {"zone": tz_list[0]["result"], "time": zone_now.strftime("%a %I:%M %p")}

    @decorators.command(
        brief="Get the time of any location", aliases=["worldclock", "worldtime"]
    )
    async def clock(self, ctx, *, place=None):
        """
        Usage: -clock <location>
        Aliases: -worldclock, -worldtime
        Examples:
            -clock Los Angeles
            -clock Netherlands
        Output:
            The current time in the specified location
        Notes:
            Can accept cities, states, provinces,
            and countries as valid locations
        """
        if place is None:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}clock <location>`",
            )
        try:
            if place.lower() == "la":
                city_name = "Los Angeles"
            else:
                city_name = re.sub(r"([^\s\w]|_)+", "", place)
            location = self.geo.geocode(city_name)
            if location is None:
                return await ctx.send_or_reply(
                    content=f"{self.bot.emote_dict['failed']} Invalid location.",
                )

            r = await self.bot.get(
                "http://api.timezonedb.com/v2.1/get-time-zone?key={}&format=json&by=position&lat={}&lng={}".format(
                    self.bot.constants.timezonedb, location.latitude, location.longitude
                )
            )
            request = json.loads(r)

            if request["status"] != "OK":
                await ctx.send_or_reply(
                    content=f"{self.bot.emote_dict['failed']} An API error occurred. Please try again later.",
                )
            else:
                zone = pytz.timezone(request["zoneName"])
                time = datetime.now(zone)
                time_fmt = time.strftime("%a %I:%M %p")
                clock = utils.getClockForTime(time_fmt)
                msg = f"{self.bot.emote_dict['announce']} `It is {clock} in {city_name.title()} ({request['zoneName']})`"
                await ctx.send_or_reply(content=msg)
        except Exception as e:
            await ctx.send_or_reply(e)

    @decorators.command(aliases=["sw"], brief="Start or stop a stopwatch.")
    async def stopwatch(self, ctx):
        """
        Usage: -stopwatch
        Alias: -sw
        Output: Starts or ends a stopwatch
        Notes:
             One stopwatch is available per user.
             Your stopwatch will not be interrupted
             if another user executes the command.
        """
        author = ctx.author
        if author.id not in self.stopwatches:
            self.stopwatches[author.id] = int(time.perf_counter())
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['stopwatch']} Stopwatch started!",
            )
        else:
            tmp = abs(self.stopwatches[author.id] - int(time.perf_counter()))
            tmp = str(timedelta(seconds=tmp))
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['stopwatch']} Stopwatch stopped! Time: **{tmp}**",
            )
            self.stopwatches.pop(author.id, None)


    @decorators.command(
        aliases=["utctime", "utc"],
        brief="Show the current utc time.",
        implemented="2021-05-05 02:04:35.619602",
        updated="2021-05-05 19:17:21.775487",
    )
    async def utcnow(self, ctx):
        """
        Usage: {0}utcnow
        Aliases: {0}utctime, {0}utc
        Output:
            datetime.datetime.utcnow()
            time format.
        """
        await ctx.send_or_reply(
            f"{self.bot.emote_dict['clock']} `{datetime.utcnow()}`"
        )
