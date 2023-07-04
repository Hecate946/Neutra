# R. Danny's reminder cog with a couple small modifications
# https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/reminder.py

import json
import asyncio
import asyncpg
import discord
import datetime
import textwrap

from datetime import timedelta
from discord.ext import commands, menus

from utilities import utils
from utilities import humantime
from utilities import formatting
from utilities import pagination


class Timer:
    __slots__ = ("args", "kwargs", "event", "id", "created_at", "expires")

    def __init__(self, *, record):
        self.id = record["id"]
        extra = record["extra"]
        self.args = extra.get("args", [])
        self.kwargs = extra.get("kwargs", {})
        self.event = record["event"]
        self.created_at = record["created"]
        self.expires = record["expires"]

    @classmethod
    def temporary(cls, *, expires, created, event, args, kwargs):
        pseudo = {
            "id": None,
            "extra": {"args": args, "kwargs": kwargs},
            "event": event,
            "created": created,
            "expires": expires,
        }
        return cls(record=pseudo)

    def __eq__(self, other):
        try:
            return self.id == other.id
        except AttributeError:
            return False

    def __hash__(self):
        return hash(self.id)

    @property
    def human_delta(self):
        return humantime.human_timedelta(self.created_at)

    def __repr__(self):
        return f"<Timer created={self.created_at} expires={self.expires} event={self.event}>"


async def setup(bot):
    await bot.add_cog(Tasks(bot))


class Tasks(commands.Cog):
    """
    Module for handling all timed tasks.
    """

    def __init__(self, bot):
        self.bot = bot
        self._have_data = asyncio.Event()
        self._current_timer = None
        self._task = bot.loop.create_task(self.dispatch_timers())

    def cog_unload(self):
        self._task.cancel()

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send_or_reply(error)
        if isinstance(error, commands.TooManyArguments):
            await ctx.send_or_reply(
                f"You called the {ctx.command.name} command with too many arguments."
            )

    async def get_active_timer(self, *, connection=None, days=7):
        query = "SELECT * FROM tasks WHERE expires < (CURRENT_DATE + $1::interval) ORDER BY expires LIMIT 1;"
        con = connection or self.bot.cxn

        record = await con.fetchrow(query, timedelta(days=days))
        if record:
            if type(record["extra"]) is dict:
                extra = record["extra"]
            else:
                extra = json.loads(record["extra"])
            record_dict = {
                "id": record["id"],
                "extra": extra,
                "event": record["event"],
                "created": record["created"],
                "expires": record["expires"],
            }
        return Timer(record=record_dict) if record else None

    async def wait_for_active_timers(self, *, connection=None, days=7):
        timer = await self.get_active_timer(connection=connection, days=days)
        if timer is not None:
            self._have_data.set()
            return timer

        self._have_data.clear()
        self._current_timer = None
        await self._have_data.wait()
        return await self.get_active_timer(connection=connection, days=days)

    async def call_timer(self, timer):
        # delete the timer
        query = "DELETE FROM tasks WHERE id=$1;"
        await self.bot.cxn.execute(query, timer.id)

        # dispatch the event
        event_name = f"{timer.event}_timer_complete"
        self.bot.dispatch(event_name, timer)

    async def dispatch_timers(self):
        try:
            while not self.bot.is_closed():
                # can only asyncio.sleep for up to ~48 days reliably
                # so we're gonna cap it off at 40 days
                # see: http://bugs.python.org/issue20493
                timer = self._current_timer = await self.wait_for_active_timers(days=40)
                now = datetime.datetime.utcnow()
                if timer.expires >= now:
                    to_sleep = (timer.expires - now).total_seconds()
                    await asyncio.sleep(to_sleep)

                await self.call_timer(timer)
        except asyncio.CancelledError:
            raise
        except (OSError, discord.ConnectionClosed, asyncpg.PostgresConnectionError):
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.dispatch_timers())
        except Exception as e:
            raise e

    async def short_timer_optimisation(self, seconds, timer):
        await asyncio.sleep(seconds)
        event_name = f"{timer.event}_timer_complete"
        self.bot.dispatch(event_name, timer)

    async def create_timer(self, *args, **kwargs):
        """Creates a timer.
        Parameters
        -----------
        when: datetime.datetime
            When the timer should fire.
        event: str
            The name of the event to trigger.
            Will transform to 'on_{event}_timer_complete'.
        \*args
            Arguments to pass to the event
        \*\*kwargs
            Keyword arguments to pass to the event
        connection: asyncpg.Connection
            Special keyword-only argument to use a specific connection
            for the DB request.
        created: datetime.datetime
            Special keyword-only argument to use as the creation time.
            Should make the timedeltas a bit more consistent.
        Note
        ------
        Arguments and keyword arguments must be JSON serialisable.
        Returns
        --------
        :class:`Timer`
        """
        when, event, *args = args

        try:
            connection = kwargs.pop("connection")
        except KeyError:
            connection = self.bot.cxn

        try:
            now = kwargs.pop("created")
        except KeyError:
            now = datetime.datetime.utcnow()

        timer = Timer.temporary(
            event=event, args=args, kwargs=kwargs, expires=when, created=now
        )
        if when:
            delta = (when - now).total_seconds()
            if delta <= 60:
                # a shortcut for small timers
                self.bot.loop.create_task(self.short_timer_optimisation(delta, timer))
                return timer

        query = """INSERT INTO tasks (event, extra, expires, created)
                   VALUES ($1, $2::jsonb, $3, $4)
                   RETURNING id;
                """

        jsonb = json.dumps({"args": args, "kwargs": kwargs})
        row = await connection.fetchrow(
            query,
            event,
            jsonb,
            when,
            now,
        )
        timer.id = row[0]

        if when:
            # only set the data check if it can be waited on
            if delta <= (86400 * 40):  # 40 days
                self._have_data.set()

            # check if this timer is earlier than our currently run timer
            if self._current_timer and when < self._current_timer.expires:
                # cancel the task and re-run it
                self._task.cancel()
                self._task = self.bot.loop.create_task(self.dispatch_timers())
        return timer

    @commands.group(
        aliases=["timer", "remind"],
        usage="<when>",
        invoke_without_command=True,
        brief="Set a reminder for yourself.",
    )
    async def reminder(
        self,
        ctx,
        *,
        when: humantime.UserFriendlyTime(commands.clean_content, default="\u2026"),
    ):
        """
        Usage: {0}remind <when>
        Aliases: {0}reminder, {0}timer
        Output: Reminds you after a specified amount of time.
        The input can be any direct date (e.g. YYYY-MM-DD) or a human
        readable offset.
        Examples:
            - "next thursday at 3pm do something funny"
            - "do the dishes tomorrow"
            - "in 3 days do the thing"
            - "2d unmute someone"
        Times are in UTC.
        """
        if not when.dt:
            return await ctx.fail(
                "Invalid time. Try specifying when you want to be reminded."
            )
        timer = await self.create_timer(
            when.dt.replace(tzinfo=None),
            "reminder",
            ctx.author.id,
            ctx.channel.id,
            when.arg,
            connection=self.bot.cxn,
            created=ctx.message.created_at.replace(tzinfo=None),
            message_id=ctx.message.id,
        )

        delta = humantime.human_timedelta(when.dt, source=timer.created_at)
        await ctx.reply(f"I will remind you about: `{when.arg}` in {delta}.")

    @reminder.command(
        name="list", aliases=["show"], brief="Show all your current reminders."
    )
    async def reminder_list(self, ctx):
        """
        Usage: {0}remind list
        Alias: {0}remind show
        Output: Shows all your pendind reminders
        """
        query = """
                SELECT id, expires, extra #>> '{args,2}'
                FROM tasks
                WHERE event = 'reminder'
                AND extra #>> '{args,0}' = $1
                ORDER BY expires;
                """

        records = await self.bot.cxn.fetch(query, str(ctx.author.id))

        if not records:
            return await ctx.fail("No current reminders.")

        p = pagination.MainMenu(
            pagination.FieldPageSource(
                entries=[
                    (
                        f"**Reminder ID:** {index}",
                        f"**Expires:** {utils.format_relative(expires)}\n"
                        f"**About:** {textwrap.shorten(message, width=512)}",
                    )
                    for index, expires, message in records
                ],
                title="Reminders",
                description=f'{len(records)} reminder{"s" if len(records) > 1 else ""}',
            )
        )
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    @reminder.command(
        name="delete", aliases=["remove", "cancel"], brief="Delete a reminder."
    )
    async def reminder_delete(self, ctx, *, id: int):
        """
        Usage: {0}remind delete [reminder ID]
        Aliases: {0}remind remove, {0}remind cancel
        Output: Deletes a reminder by its ID.
        Notes:
            To get a reminder ID, use `{0}reminder list`
        """

        query = """
                DELETE FROM tasks
                WHERE id=$1
                AND event = 'reminder'
                AND extra #>> '{args,0}' = $2;
                """

        status = await self.bot.cxn.execute(query, id, str(ctx.author.id))
        if status == "DELETE 0":
            return await ctx.fail("Could not delete any reminders with that ID.")

        # if the current timer is being deleted
        if self._current_timer and self._current_timer.id == id:
            # cancel the task and re-run it
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.dispatch_timers())

        await ctx.success("Successfully deleted reminder.")

    @reminder.command(name="clear", brief="Clear all your current reminders.")
    async def reminder_clear(self, ctx):
        """
        Usage: {0}remind clear
        Output: Clears all reminders you have set.
        """

        # For UX purposes this has to be two queries.

        query = """
                SELECT COUNT(*)
                FROM tasks
                WHERE event = 'reminder'
                AND extra #>> '{args,0}' = $1;
                """

        author_id = str(ctx.author.id)
        total = await self.bot.cxn.fetchrow(query, author_id)
        total = total[0]
        if total == 0:
            await ctx.fail("You do not have any reminders to delete.")
            return

        confirm = await ctx.confirm(
            f"This action will delete {formatting.plural(total):reminder}?"
        )
        if confirm:
            query = """DELETE FROM tasks WHERE event = 'reminder' AND extra #>> '{args,0}' = $1;"""
            await self.bot.cxn.execute(query, author_id)
            await ctx.success(
                f"Successfully deleted {formatting.plural(total):reminder}."
            )

    @commands.Cog.listener()
    async def on_reminder_timer_complete(self, timer):
        author_id, channel_id, message = timer.args

        try:
            channel = self.bot.get_channel(channel_id) or (
                await self.bot.fetch_channel(channel_id)
            )
        except (discord.HTTPException, discord.NotFound):
            return

        try:
            author = self.bot.get_user(author_id) or (
                await self.bot.fetch_user(author_id)
            )
        except (discord.HTTPException, discord.NotFound):
            return

        guild_id = (
            channel.guild.id
            if isinstance(channel, (discord.TextChannel, discord.Thread))
            else "@me"
        )
        message_id = timer.kwargs.get("message_id")
        msg = f"Hello {author.mention}, {timer.human_delta}, you wanted me to remind you about: `{message}`"

        view = None
        if message_id:
            url = f"https://discord.com/channels/{guild_id}/{channel.id}/{message_id}"
            view = discord.ui.View()
            view.add_item(
                discord.ui.Button(label="Click here to view your reminder.", url=url)
            )

        try:
            await author.send(msg, view=view)
        except Exception:
            try:
                await channel.send(message, view=view)
            except Exception:
                return
