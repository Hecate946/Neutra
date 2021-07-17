import discord
import os
import io
import asyncio
import threading
import psutil
import sys
import functools
import objgraph
import traceback

from discord.ext import commands, menus

from utilities import checks
from utilities import decorators
from utilities import pagination

def setup(bot):
    bot.add_cog(Monitor(bot))


class Monitor(commands.Cog):
    """
    Module for monitoring bot status.
    """
    def __init__(self, bot):
        self.bot = bot
        self.process = psutil.Process()

    # Admin only cog.
    async def cog_check(self, ctx):
        return checks.is_admin(ctx)

    @decorators.command(
        aliases=["objg"],
        brief="Debug memory leaks.",
        implemented="2021-05-11 01:47:43.865390",
        updated="2021-05-11 01:47:43.865390",
    )
    async def objgrowth(self, ctx):
        """
        Usage: {0}objgrowth
        Alias: {0}objg
        Output:
            Shows detailed object memory usage
        """
        stdout = io.StringIO()
        await ctx.bot.loop.run_in_executor(
            None, functools.partial(objgraph.show_growth, file=stdout)
        )
        await ctx.send_or_reply("```fix\n" + stdout.getvalue() + "```")


    @decorators.group(
        case_insensitive=True,
        aliases=["to-do"],
        invoke_without_command=True,
        brief="Manage the bot's todo list.",
    )
    async def todo(self, ctx):
        """
        Usage: {0}todo <method>
        Alias: {0}to-do
        Methods:
            no subcommand: shows the todo list
            add: Adds an entry to the todo list
            remove|rm|rem: Removes an entry from the todo list
        """
        if ctx.invoked_subcommand is None:
            try:
                with open(self.todo) as fp:
                    data = fp.readlines()
            except FileNotFoundError:
                return await ctx.send_or_reply(
                    f"{self.bot.emote_dict['exclamation']} No current todos."
                )
            if data is None or data == "":
                return await ctx.send_or_reply(
                    f"{self.bot.emote_dict['exclamation']} No current todos."
                )
            msg = ""
            for index, line in enumerate(data, start=1):
                msg += f"{index}. {line}\n"
            p = pagination.MainMenu(
                pagination.TextPageSource(msg, prefix="```prolog\n")
            )
            try:
                await p.start(ctx)
            except menus.MenuError as e:
                await ctx.send_or_reply(e)

    @todo.command(brief="Add a todo entry.")
    async def add(self, ctx, *, todo: str = None):
        if todo is None:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.clean_prefix}todo add <todo>`",
            )
        with open(self.todo, "a", encoding="utf-8") as fp:
            fp.write(todo + "\n")
        await ctx.success(f"Successfully added `{todo}` to the todo list.")

    @todo.command(aliases=["rm", "rem"], brief="Remove a todo entry.")
    async def remove(self, ctx, *, index_or_todo: str = None):
        with open(self.todo, mode="r", encoding="utf-8") as fp:
            lines = fp.readlines()
            print(lines)
        found = False
        for index, line in enumerate(lines, start=1):
            if str(index) == index_or_todo:
                lines.remove(line)
                found = True
                break
            elif line.lower().strip("\n") == index_or_todo.lower():
                lines.remove(line)
                found = True
                break
        if found is True:
            with open(self.todo, mode="w", encoding="utf-8") as fp:
                print(lines)
                fp.write("".join(lines))
            await ctx.success(f"Successfully removed todo `{index_or_todo}` from the todo list.")
        else:
            await ctx.fail(f"Could not find todo `{index_or_todo}` in the todo list.")

    @todo.command(brief="Clear the todo list.")
    async def clear(self, ctx):
        try:
            os.remove(self.todo)
        except FileNotFoundError:
            return await ctx.success("Successfully cleared the todo list.")
        await ctx.success("Successfully cleared the todo list.")

    @decorators.group(
        aliases=["l"],
        invoke_without_command=True,
        brief="View logging files.",
        implemented="2021-05-08 20:16:22.917120",
        updated="2021-05-11 02:51:30.992778",
    )
    async def logger(self, ctx):
        """
        Usage: {0}logger <option>
        Alias: {0}l
        Permission: Bot owner
        Output: View any log recorded in ./data/logs
        Options:
            commands|command|cmds|cmd
            errors|stderr|error|err|e
            information|info|i
            tracebacks|traceback|trace|tb|t
            clear|clr|cl
        """
        if not ctx.invoked_subcommand:
            return await ctx.usage("<option>")

    @logger.command(
        name="commands", aliases=["cmds"], brief="Show the commands.log file."
    )
    async def _get_cmds(self, ctx):
        """
        Usage: {0}logger commands
        Aliases: {0}logger cmds
        Output:
            Starts a pagination session
            showing the commands.log file
        """
        sh = self.bot.get_command("sh")
        await ctx.invoke(sh, prefix="prolog", command="cat ./data/logs/commands.log")

    @logger.command(
        name="traceback",
        aliases=["tracebacks", "trace", "t", "tb"],
        brief="Show the traceback.log file",
    )
    async def _traceback(self, ctx):
        """
        Usage: {0}logger traceback
        Aliases:
            {0}logger t
            {0}logger tb
            {0}logger trace
            {0}logger tracebacks
        Output:
            Starts a pagination session
            showing the traceback.log file
        """
        sh = self.bot.get_command("sh")
        await ctx.invoke(sh, prefix="prolog", command="cat ./data/logs/traceback.log")

    @logger.command(
        name="info",
        aliases=["i", "information"],
        brief="Show the info.log file.",
    )
    async def _info(self, ctx):
        """
        Usage: {0}logger info
        Aliases:
            {0}logger i
            {0}logger information
        Output:
            Starts a pagination session
            showing the info.log file
        """
        sh = self.bot.get_command("sh")
        await ctx.invoke(sh, prefix="prolog", command="cat ./data/logs/info.log")

    @logger.command(
        name="errors",
        aliases=["err", "error", "stderr", "e"],
        brief="Show the errors.log file.",
    )
    async def _errors(self, ctx):
        """
        Usage: {0}logger errors
        Aliases:
            {0}logger e
            {0}logger err
            {0}logger error
            {0}logger stderr
        Output:
            Starts a pagination session
            showing the errors.log file
        """
        sh = self.bot.get_command("sh")
        await ctx.invoke(sh, prefix="prolog", command="cat ./data/logs/errors.log")

    @logger.command(
        name="clear",
        aliases=["cl", "clr"],
        brief="Delete a logging file.",
    )
    async def _cl(self, ctx, search):
        """
        Usage: {0}logger clear <search>
        Aliases: {0}cl, {0}clr
        Output: Deletes a logging file.
        Searches:
            commands|command|cmds|cmd
            errors|stderr|error|err
            information|info|i
            tracebacks|traceback|trace|t
        """
        if search in ["cmd", "cmds", "command", "commands"]:
            search = "commands"
            msg = "command"
        elif search in ["err", "stderr", "error", "errors"]:
            search = "errors"
            msg = "error"
        elif search in ["info", "i", "information"]:
            search = "info"
            msg = "info"
        elif search in ["t", "trace", "traceback", "tracebacks"]:
            search = "traceback"
            msg = "traceback"
        else:
            raise commands.BadArgument(f"Invalid file search.")
        logdir = os.listdir("./data/logs/")
        for filename in logdir:
            if filename.startswith(search):
                os.remove("./data/logs/" + filename)
                break
        await ctx.success(f"Cleared the {msg} log file.")

    @decorators.group(
        brief="View pm2 files.",
        case_insensitive=True,
        invoke_without_command=True,
        implemented="2021-05-08 20:16:22.917120",
        updated="2021-05-11 02:51:30.992778",
    )
    async def pm2(self, ctx):
        """
        Usage: {0}pm2 <option>
        Output: View any pm2 log file in ./data/pm2
        Options:
            stdout|out|output
            stderr|err|error|errors
            pid|process|processid
            clear|clr|cl
        """
        if ctx.invoked_subcommand is None:
            return await ctx.usage("<option>")

    @pm2.command(aliases=["out", "output"], brief="View the pm2 stdout file.")
    async def stdout(self, ctx):
        """
        Usage: {0}pm2 stdout
        Aliases:
            {0}pm2 out
            {0}pm2 output
        Output:
            Starts a pagination session
            showing the pm2 stdout file.
        """
        sh = self.bot.get_command("sh")
        pm2dir = os.listdir("./data/pm2/")
        for filename in pm2dir:
            if filename.startswith("out"):
                await ctx.invoke(sh, prefix="yml", command=f"cat ./data/pm2/{filename}")
                return
        else:
            raise commands.BadArgument(f"No stdout file currently exists.")

    @pm2.command(
        aliases=["err", "error", "errors"],
        brief="View the pm2 stderr file",
    )
    async def stderr(self, ctx):
        """
        Usage: {0}pm2 stderr
        Aliases:
            {0}pm2 err
            {0}pm2 error
            {0}pm2 errors
        Output:
            Starts a pagination session
            showing the pm2 stderr file.
        """
        sh = self.bot.get_command("sh")
        pm2dir = os.listdir("./data/pm2/")
        for filename in pm2dir:
            if filename.startswith("err"):
                await ctx.invoke(sh, prefix="yml", command=f"cat ./data/pm2/{filename}")
                return
        else:
            raise commands.BadArgument(f"No stderr file currently exists.")

    @pm2.command(
        aliases=["process", "processid"],
        brief="View the pm2 process ID.",
    )
    async def pid(self, ctx):
        """
        Usage: {0}pm2 pid
        Aliases:
            {0}pm2 process
            {0}pm2 processid
        Output:
            Shows the process ID
            of the pm2 process.
        """
        sh = self.bot.get_command("sh")
        pm2dir = os.listdir("./data/pm2/")
        for filename in pm2dir:
            if filename.startswith("pid"):
                await ctx.invoke(sh, prefix="yml", command=f"cat ./data/pm2/{filename}")
                return
        else:
            raise commands.BadArgument(f"No pid file currently exists.")

    @pm2.command(name="clear", aliases=["cl", "clr"], brief="Delete a pm2 log file.")
    async def _clr(self, ctx, search):
        """
        Usage: {0}pm2 clear <search>
        Aliases: {0}cl, {0}clr
        Output: Deletes a pm2 file.
        Searches:
            out|output|stdout
            errors|stderr|error|err
            pid|process|processid
        """
        if search in ["out", "output", "stdout"]:
            search = "out"
            msg = "stdout"
        elif search in ["err", "stderr", "error", "errors"]:
            search = "err"
            msg = "stderr"
        elif search in ["pid", "p", "process", "processid"]:
            search = "pid"
            msg = "pid"
        else:
            raise commands.BadArgument(f"Invalid file search.")
        pm2dir = os.listdir("./data/pm2/")
        for filename in pm2dir:
            if filename.startswith(search):
                os.remove("./data/pm2/" + filename)
                break
        await ctx.success(f"Cleared the pm2 {msg} log.")
    
    @decorators.command(brief="Show bot threadinfo.")
    async def threadinfo(self, ctx):
        """
        Usage: {0}threadinfo
        Output:
            Shows some info on bot threads.
        """
        buf = io.StringIO()
        for th in threading.enumerate():
            buf.write(str(th) + "\n")
            traceback.print_stack(sys._current_frames()[th.ident], file=buf)
            buf.write("\n")

        p = pagination.MainMenu(
            pagination.TextPageSource(buf.getvalue(), prefix="```prolog")
        )
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @decorators.command(brief="Show bot health.")
    async def bothealth(self, ctx):
        """
        Usage: {0}bothealth
        Output:
            Various bot health monitoring tools.
        """

        # This uses a lot of private methods because there is no
        # clean way of doing this otherwise.

        HEALTHY = discord.Colour(value=0x1CA381)
        UNHEALTHY = discord.Colour(value=0xF04947)
        WARNING = discord.Colour(value=0xF09E47)
        total_warnings = 0

        embed = discord.Embed(title="Bot Health Report", colour=HEALTHY)

        # Check the connection pool health.
        pool = self.bot.cxn
        total_waiting = len(pool._queue._getters)
        current_generation = pool._generation

        description = [
            f"Total `Pool.acquire` Waiters: {total_waiting}",
            f"Current Pool Generation: {current_generation}",
            f"Connections In Use: {len(pool._holders) - pool._queue.qsize()}",
        ]

        questionable_connections = 0
        connection_value = []
        for index, holder in enumerate(pool._holders, start=1):
            generation = holder._generation
            in_use = holder._in_use is not None
            is_closed = holder._con is None or holder._con.is_closed()
            display = f"gen={holder._generation} in_use={in_use} closed={is_closed}"
            questionable_connections += any((in_use, generation != current_generation))
            connection_value.append(f"<Holder i={index} {display}>")

        joined_value = "\n".join(connection_value)
        embed.add_field(
            name="Connections", value=f"```py\n{joined_value}\n```", inline=False
        )

        description.append(f"Questionable Connections: {questionable_connections}")

        total_warnings += questionable_connections

        task_retriever = asyncio.all_tasks

        all_tasks = task_retriever(loop=self.bot.loop)

        event_tasks = [
            t for t in all_tasks if "Client._run_event" in repr(t) and not t.done()
        ]

        cogs_directory = os.path.dirname(__file__)
        tasks_directory = os.path.join("discord", "ext", "tasks", "__init__.py")
        inner_tasks = [
            t
            for t in all_tasks
            if cogs_directory in repr(t) or tasks_directory in repr(t)
        ]

        bad_inner_tasks = ", ".join(
            hex(id(t)) for t in inner_tasks if t.done() and t._exception is not None
        )
        total_warnings += bool(bad_inner_tasks)
        embed.add_field(
            name="Inner Tasks",
            value=f'Total: {len(inner_tasks)}\nFailed: {bad_inner_tasks or "None"}',
        )
        embed.add_field(
            name="Events Waiting", value=f"Total: {len(event_tasks)}", inline=False
        )

        memory_usage = self.process.memory_full_info().uss / 1024 ** 2
        cpu_usage = self.process.cpu_percent() / psutil.cpu_count()
        embed.add_field(
            name="Process",
            value=f"{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU",
            inline=False,
        )

        global_rate_limit = not self.bot.http._global_over.is_set()
        description.append(f"Global Rate Limit: {global_rate_limit}")

        if global_rate_limit or total_warnings >= 9:
            embed.colour = UNHEALTHY

        embed.set_footer(text=f"{total_warnings} warning(s)")
        embed.description = "\n".join(description)
        await ctx.send_or_reply(embed=embed)