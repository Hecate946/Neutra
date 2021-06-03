import io
import re
import json
import pytz
import time as t
import typing
import discord
import collections

from datetime import datetime
from datetime import timedelta
from discord.ext import commands
from discord.ext import menus
from geopy import geocoders

from utilities import utils
from utilities import checks
from utilities import humantime
from utilities import converters
from utilities import decorators
from utilities import formatting
from utilities import pagination


def setup(bot):
    bot.add_cog(Times(bot))


class Times(commands.Cog):
    """
    Module for time functions.
    """

    def __init__(self, bot):
        self.bot = bot
        self.stopwatches = {}
        self.geo = geocoders.Nominatim(user_agent="Snowbot")

    @decorators.command(
        aliases=["rmtz", "remtz", "remtimezone", "removetimzone", "rmtimezone"],
        brief="Remove your timezone.",
        implemented="2021-04-05 18:24:17.716638",
        updated="2021-05-06 21:01:36.198294",
        examples="""
                {0}rmtz
                {0}remtz
                {0}removetz
                {0}rmtimezone
                {0}remtimezone
                {0}removetimzone
                """,
    )
    async def removetz(self, ctx):
        """
        Usage: {0}removetz
        Aliases:
            {0}rmtz,
            {0}remtz,
            {0}removetz,
            {0}rmtimezone,
            {0}remtimezone,
            {0}removetimzone
        Output:
            Removes your set timezone
            from the bot's timezone list.
        Notes:
            Will not inform you if you did
            not previously set your timezone.
        """
        await self.bot.cxn.execute(
            "DELETE FROM usertime WHERE user_id = $1;", ctx.author.id
        )
        await ctx.send_or_reply(
            f"{self.bot.emote_dict['success']} Your timezone has been removed."
        )

    @decorators.command(
        aliases=["listtzs", "listtimezone"],
        brief="List all available timezones.",
        implemented="2021-04-01 14:40:28.719199",
        updated="2021-05-06 21:07:24.328765",
        examples="""
                {0}listtz
                {0}listtzs
                {0}listtimezone
                """,
    )
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    async def listtz(self, ctx):
        """
        Usage: {0}listtz
        Aliases:
            {0}listtzs
            {0}listtimezone
        Output:
            A pagination session that
            shows all valid timezones.
        """
        await ctx.invoke(self.settz)

    @decorators.command(
        aliases=["settimezone", "settime"],
        brief="Set your timezone.",
        implemented="2021-04-01 14:40:01.850145",
        updated="2021-05-06 21:10:01.049494",
        examples="""
                {0}settz los angeles
                {0}settz America/Los_Angeles
                {0}settime new york
                {0}settime America/New_York
                {0}settimezone arctic
                {0}settimezone Arctic/Longyearbyen
                """,
    )
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    async def settz(self, ctx, *, timezone=None):
        """
        Usage: {0}settz [timezone]
        Aliases: {0}settimezone, {0}settime
        Output:
            Sets your timezone to a valid
            timezone based off of your input.
        Notes:
            Will provide you with the 5 closest
            timezone matches if the supplied timezone
            is invalid. Invoke with no arguments to
            show all available timezones.
        """
        msg = ""
        if timezone is None:
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
            tz_list = utils.disambiguate(timezone, pytz.all_timezones, None, 5)
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
        aliases=["alltime", "alltimes"],
        brief="Show times for all users.",
        implemented="2021-04-21 19:11:27.501917",
        updated="2021-05-06 21:16:29.417030",
        examples="""
                {0}alltime
                {0}alltimes
                {0}usertimes
                """,
    )
    @checks.bot_has_perms(add_reactions=True, external_emojis=True)
    async def usertimes(self, ctx):
        """
        Usage: {0}usertimes
        Aliases: {0}alltime, {0}alltimes
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

    @decorators.command(
        aliases=["tz", "showtz", "showtimezone"],
        brief="See a member's timezone.",
        implemented="2021-04-05 19:16:57.722357",
        updated="2021-05-06 21:20:23.225596",
        examples="""
                {0}tz
                {0}tz Hecate
                {0}tz @Hecate
                {0}tz Hecate#3523
                {0}tz 708584008065351681
                {0}showtz
                {0}showtz Hecate
                {0}showtz @Hecate
                {0}showtz Hecate#3523
                {0}showtz 708584008065351681
                {0}timezone
                {0}timezone Hecate
                {0}timezone @Hecate
                {0}timezone Hecate#3523
                {0}timezone 708584008065351681
                {0}showtimezone
                {0}showtimezone Hecate
                {0}showtimezone @Hecate
                {0}showtimezone Hecate#3523
                {0}showtimezone 708584008065351681
                """,
    )
    async def timezone(self, ctx, *, user: converters.DiscordUser = None):
        """
        Usage: {0}timezone [user]
        Aliases:
            {0}tz, {0}showtz, {0}showtimezone
        Output:
            Shows you the passed user's timezone, if applicable
        Notes:
            Will default to yourself if no user is passed
        """
        if user is None:
            user = ctx.author

        query = """
                SELECT timezone
                FROM usertime
                WHERE user_id = $1;
                """
        timezone = await self.bot.cxn.fetchval(query, user.id) or None
        if timezone is None:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['warn']} `{user}` has not set their timezone. "
                f"Use the `{ctx.prefix}settz [Region/City]` command.",
            )

        await ctx.send_or_reply(
            content=f"{self.bot.emote_dict['announce']} `{user}'s timezone is {timezone}`",
        )

    @decorators.command(
        aliases=["time"],
        brief="Show a user's current time.",
        implemented="2021-04-24 08:58:32.644191",
        updated="2021-05-06 21:24:58.166767",
        examples="""
                {0}time
                {0}time Hecate
                {0}time @Hecate
                {0}time Hecate#3523
                {0}time 708584008065351681
                {0}usertime
                {0}usertime Hecate
                {0}usertime @Hecate
                {0}usertime Hecate#3523
                {0}usertime 708584008065351681
                """,
    )
    async def usertime(self, ctx, *, member: converters.DiscordMember = None):
        """
        Usage: {0}usertime [user]
        Alias: {0}time
        Output:
            Show's the current time for the passed user,
            if they previously set their timezone.
        Notes:
            Will default to you if no user is specified
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
            await ctx.fail("I couldn't find that timezone.")
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
        aliases=["worldclock", "worldtime"],
        brief="Get the time of any location",
        implemented="2021-04-15 06:20:17.433895",
        updated="2021-05-06 21:28:57.052612",
        examples="""
                {0}clock Los Angeles
                {0}clock Netherlands
                {0}worldtime Los Angeles
                {0}worldtime Netherlands
                {0}worldclock Los Angeles
                {0}worldclock Netherlands
                """,
    )
    async def clock(self, ctx, *, place):
        """
        Usage: {0}clock <place>
        Aliases: {0}worldclock, {0}worldtime
        Output:
            Shows the current time of day
            it is in the specified location.
        Notes:
            Can accept cities, states, provinces,
            and countries as valid locations.
        """
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

    @decorators.command(
        aliases=["sw"],
        brief="Start or stop a stopwatch.",
        implemented="2021-04-28 02:38:06.104546",
        updated="2021-05-06 21:32:55.642104",
        examples="""
                {0}stopwatch
                {0}sw
                """,
    )
    async def stopwatch(self, ctx):
        """
        Usage: {0}stopwatch
        Alias: {0}sw
        Output:
            Starts a stopwatch unique to you.
            If you have a current stopwatch,
            the bot will end that stopwatch
            and calculate the time passed.
        Notes:
            One stopwatch is available per user.
            Your stopwatch will not be interrupted
            if another user executes the command.
            If not stopped by the user, stopwatches
            will automatically be stopped after 12 hours.
        """
        author = ctx.author
        if author.id not in self.stopwatches:
            self.stopwatches[author.id] = int(t.perf_counter())
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['stopwatch']} Stopwatch started!",
            )
        else:
            tmp = abs(self.stopwatches[author.id] - int(t.perf_counter()))
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
        examples="""
                {0}utc
                {0}utcnow
                {0}utctime
                """,
    )
    async def utcnow(self, ctx):
        """
        Usage: {0}utcnow
        Aliases: {0}utctime, {0}utc
        Output:
            datetime.datetime.utcnow()
            python time format.
        """
        await ctx.send_or_reply(f"{self.bot.emote_dict['clock']} `{datetime.utcnow()}`")

    @decorators.command(
        hidden=True,
        brief="Show the days a user was active.",
        implemented="2021-05-12 07:46:53.635661",
        updated="2021-05-12 15:25:00.152528",
        examples="""
                {0}clocker
                {0}clocker Hecate
                {0}clocker @Hecate 3 days ago
                {0}clocker 708584008065351681 2m
                {0}clocker Hecate#3523 one month ago
                """,
    )
    @checks.has_perms(view_audit_log=True)
    async def clocker(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember] = None,
        *,
        time: humantime.PastTime = None,
    ):
        """
        Usage: {0}clocker [user] [time]
        Output:
            Counts the days that
            a user has sent a message
            in the specified time period.
        Notes:
            If no time frame is specified,
            will default to 1 week.
        """
        if user is None:
            user = ctx.author
        await ctx.trigger_typing()
        if time:
            actual_time = (datetime.utcnow() - time.dt).total_seconds()
            the_datetime = time.dt
        else:
            actual_time = 604800  # 1 week
            the_datetime = datetime.utcfromtimestamp(t.time() - actual_time)
        query = """
                SELECT DISTINCT (
                    SELECT EXTRACT(
                        DAY FROM (
                            TO_TIMESTAMP(unix)
                        )
                    ) WHERE author_id = $1
                    AND unix > ((SELECT EXTRACT(EPOCH FROM NOW()) - $2))
                ) FROM messages;
                """
        row = await self.bot.cxn.fetch(query, user.id, (actual_time - 86400))
        results = len([x[0] for x in row if x[0] is not None])
        emote = self.bot.emote_dict["graph"]
        pluralize = "" if results == 1 else "s"
        timefmt = humantime.human_timedelta(the_datetime, accuracy=1)
        msg = f"{emote} User `{user}` has logged into discord **{results} day{pluralize} since {timefmt}.**"
        await ctx.send_or_reply(msg)

    @decorators.command(
        hidden=True,
        brief="Show all active users.",
        implemented="2021-05-12 15:25:00.152528",
        updated="2021-05-12 15:25:00.152528",
        examples="""
                {0}clocking
                {0}clocking 2m
                {0}clocking 1 month ago
                {0}clocking 3 weeks ago
                """,
    )
    @checks.bot_has_perms(attach_files=True)
    @checks.has_perms(manage_guild=True)
    async def clocking(self, ctx, *, timeframe: humantime.PastTime = None):
        """
        Usage: {0}clocking [time]
        Output:
            Shows all users who have
            sent a message in the server
            in the specified time frame
        Notes:
            If no time frame is specified,
            will default to 1 week.
        """
        await ctx.trigger_typing()
        if timeframe:
            actual_time = (datetime.utcnow() - timeframe.dt).total_seconds()
            the_datetime = timeframe.dt
        else:
            actual_time = 604800  # 1 week
            the_datetime = datetime.utcfromtimestamp(t.time() - actual_time)
        query = """
                SELECT DISTINCT author_id, (SELECT EXTRACT(DAY FROM (TO_TIMESTAMP(unix))))
                FROM messages
                WHERE server_id = $1
                AND unix > (SELECT EXTRACT(EPOCH FROM NOW()) - $2);
                """
        rows = await self.bot.cxn.fetch(query, ctx.guild.id, (actual_time - 86400))
        counter = collections.Counter([row[0] for row in rows])
        fmt = [
            (str(ctx.guild.get_member(x[0])), x[1])
            for x in counter.items()
            if ctx.guild.get_member(x[0]) is not None
        ]
        sort = sorted(fmt, key=lambda x: x[1], reverse=True)
        enumerated = [(y, x[0], x[1]) for y, x in enumerate(sort, start=1)]
        headers = ["INDEX", "NAME", "DAYS"]
        table = formatting.TabularData()
        table.set_columns(headers)
        table.add_rows(enumerated)
        render = table.render()
        completed = f"```sml\n{render}```"
        emote = self.bot.emote_dict["graph"]
        pluralize = "" if len(sort) == 1 else "s"
        timefmt = humantime.human_timedelta(the_datetime, accuracy=1)
        await ctx.bold(
            f"{emote} {len(sort)} user{pluralize} have logged in since {timefmt} in {ctx.guild.name}."
        )
        if len(completed) > 2000:
            fp = io.BytesIO(completed.encode("utf-8"))
            await ctx.send_or_reply(file=discord.File(fp, "results.sml"))
        else:
            await ctx.send_or_reply(completed)
