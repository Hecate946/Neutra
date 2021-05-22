import io
import os
import sys
import copy
import time
import psutil
import typing
import discord
import asyncio
import asyncpg
import textwrap
import importlib
import threading
import traceback
import contextlib
import subprocess

from discord.ext import commands, menus

from utilities import utils
from utilities import checks
from utilities import converters
from utilities import decorators
from utilities import formatting
from utilities import pagination


def setup(bot):
    bot.add_cog(Manager(bot))


class Manager(commands.Cog):
    """
    Manage bot processes and cogs.
    """

    def __init__(self, bot):
        self.bot = bot
        self.process = psutil.Process()
        self._last_result = None

    # Owner only cog.
    async def cog_check(self, ctx):
        return checks.is_owner(ctx)

    @decorators.command(
        brief="A faster way of rebooting.",
        implemented="2021-05-11 03:03:20.517480",
        updated="2021-05-11 03:03:20.517480",
        examples="""
                {0}refresh
                """,
    )
    async def refresh(self, ctx, db=False):
        """
        Usage: {0}refresh [db|-db|--db=False]
        Output:
            Runs all reloading commands.
        Notes:
            Pass the --db flag to
            restart the database.
        """
        await ctx.trigger_typing()
        core = importlib.import_module("core", package=".")
        importlib.reload(core)
        starter = importlib.import_module("starter", package=".")
        importlib.reload(starter)
        if db in ["db", "-db", "--db"]:
            await ctx.invoke(self.update)
        await ctx.invoke(self.botvars)
        await ctx.invoke(self.rau)
        await ctx.invoke(self.ras)
        await ctx.invoke(self.reloadall)
        await ctx.success("**Completed**")

    @decorators.command(
        aliases=["batchcount"],
        brief="Get the batch insert count.",
        implemented="2021-04-25 06:13:16.030615",
        updated="2021-05-11 02:02:21.935264",
        examples="""
                {0}batches
                {0}batchcount
                """,
    )
    async def batches(self, ctx):
        """
        Usage: {0}batches
        Alias: {0}batchcount
        Output:
            Get the number of successful
            batch inserts the bot has
            performed since last reboot.
        """
        await ctx.bold(
            f"{self.bot.emote_dict['db']} {self.bot.user} ({self.bot.user.id}) Batch Inserts: {self.bot.batch_inserts}"
        )

    @decorators.command(
        brief="Reload the bot variables.",
        implemented="2021-04-03 04:30:16.385794",
        updated="2021-05-11 02:41:27.186046",
        examples="""
                {0}botvars
                """,
    )
    async def botvars(self, ctx):
        """
        Usage: {0}botvars
        Output: Resets all global bot variables
        Notes:
            Useful to use this command as an
            alternative to restarting the bot when
            changes are made to the config.json file
        """
        consts = importlib.import_module(f".constants", package="settings")
        importlib.reload(consts)
        self.bot.constants = consts
        self.bot.emote_dict = consts.emotes
        self.bot.owner_ids = consts.owners
        await ctx.success("**Reloaded all botvars.**")

    @decorators.command(
        aliases=["lc", "loadcog"],
        brief="Load an extension.",
        implemented="2021-03-19 21:57:05.162549",
        updated="2021-05-11 02:51:30.992778",
        examples="""
                {0}lc manager
                {0}load jishaku
                {0}loadcog info
                """,
    )
    async def load(self, ctx, file: str):
        """
        Usage: {0}load <file>
        Aliases: {0}loadcog, {0}lc
        Output:
            Loads the extension (cog)
            with the given name.
        """
        try:
            self.bot.load_extension(f"cogs.{file}")
        except Exception:
            try:
                self.bot.load_extension(f"{file}")
            except Exception as e:
                return await ctx.send_or_reply(str(e).replace("'", "**"))
        await ctx.success(f"Loaded extension **{file}**")

    @decorators.command(
        aliases=["uc", "unloadcog"],
        brief="Unload an extension.",
        implemented="2021-03-19 21:57:05.162549",
        updated="2021-05-11 02:51:30.992778",
        examples="""
                {0}uc manager
                {0}unload jishaku
                {0}unloadcog info
                """,
    )
    async def unload(self, ctx, file: str):
        """
        Usage: {0}unload <file>
        Aliases: {0}unloadcog, {0}uc
        Output:
            Unloads the extension (cog)
            with the given name.
        """
        try:
            self.bot.unload_extension(f"cogs.{file}")
        except Exception:
            try:
                self.bot.unload_extension(f"{file}")
            except Exception as e:
                return await ctx.send_or_reply(str(e).replace("'", "**"))
        await ctx.success(f"Unloaded extension **{file}**")

    @decorators.command(
        name="reload",
        aliases=["r"],
        brief="Reload an extension.",
        implemented="2021-03-19 21:57:05.162549",
        updated="2021-05-11 02:51:30.992778",
        examples="""
                {0}r manager
                {0}reload jishaku
                """,
    )
    async def _reload(self, ctx, file: str):
        """
        Usage: {0}reload <file>
        Alias: {0}r
        Output:
            Reloads the extension (cog)
            with the given name.
        """
        try:
            self.bot.reload_extension(f"cogs.{file}")
        except Exception:
            try:
                self.bot.reload_extension(f"{file}")
            except Exception as e:
                return await ctx.send_or_reply(str(e).replace("'", "**"))
        await ctx.success(f"Reloaded extension **{file}.py**")

    @decorators.command(
        aliases=["ra"],
        brief="Reload all extensions.",
        implemented="2021-03-19 21:57:05.162549",
        updated="2021-05-11 02:51:30.992778",
        examples="""
                {0}ra
                {0}reloadall
                """,
    )
    async def reloadall(self, ctx):
        """
        Usage: {0}reloadall
        Alias: {0}ra
        Output:
            Reloads all extensions
            in the ./cogs directory.
        """
        error_collection = []
        for fname in os.listdir("cogs"):
            if fname.endswith(".py"):
                name = fname[:-3]
                try:
                    self.bot.reload_extension(f"cogs.{name}")
                except Exception as e:
                    error_collection.append(
                        [fname, utils.traceback_maker(e, advance=False)]
                    )

        if error_collection:
            output = "\n".join(
                [f"**{g[0]}** ```diff\n- {g[1]}```" for g in error_collection]
            )
            return await ctx.fail(
                f"**Failed to reload following extensions.**\n\n{output}"
            )

        await ctx.success("**Successfully reloaded all extensions.**")

    @decorators.command(
        brief="Reload a utilities module.",
        aliases=["reloadutils", "reloadutility", "ru"],
        implemented="2021-03-19 21:57:05.162549",
        updated="2021-05-11 02:51:30.992778",
        examples="""
                {0}ru converters
                {0}reloadutil utils
                """,
    )
    async def reloadutil(self, ctx, file: str):
        """
        Usage: {0}reloadutil <file>
        Aliases:
            {0}ru
            {0}reloadutils
            {0}reloadutility
        Output:
            Reloads an extension in
            the ./utilities directory.
        """
        name_maker = f"./utilities/{file}.py"
        try:
            module_name = importlib.import_module(f".{file}", package="utilities")
            importlib.reload(module_name)
        except ModuleNotFoundError:
            return await ctx.fail(f"Couldn't find module named **{name_maker}**")
        except Exception as e:
            error = utils.traceback_maker(e)
            return await ctx.fail(
                f"Module **{name_maker}** returned error and was not reloaded...\n{error}"
            )
        await ctx.success(f"Reloaded module **{name_maker}**")

    @decorators.command(
        brief="Reload a utilities module.",
        aliases=["reloadsettings", "rss"],
        implemented="2021-03-19 21:57:05.162549",
        updated="2021-05-11 02:51:30.992778",
        examples="""
                {0}rss constants
                {0}reloadsetting cache
                """,
    )
    async def reloadsetting(self, ctx, file: str):
        """
        Usage: {0}reloadutil <file>
        Aliases:
            {0}rss
            {0}reloadsettings
        Output:
            Reloads an extension in
            the ./settings directory.
        """
        name_maker = f"./settings/{file}.py"
        try:
            module_name = importlib.import_module(f".{file}", package="settings")
            importlib.reload(module_name)
        except ModuleNotFoundError:
            return await ctx.send_or_reply(
                content=f"Couldn't find module named **{name_maker}**",
            )
        except Exception as e:
            error = utils.traceback_maker(e)
            return await ctx.fail(
                f"Module **{name_maker}** errored and was not reloaded...\n{error}"
            )
        await ctx.success(f"Reloaded module **{name_maker}**")

    @decorators.command(
        aliases=["reloadallutils"],
        brief="Reload all utilities modules.",
        implemented="2021-03-19 21:57:05.162549",
        updated="2021-05-11 02:51:30.992778",
        examples="""
                {0}rau
                {0}reloadallutils
                """,
    )
    async def rau(self, ctx):
        """
        Usage: {0}reloadallutils
        Aliases:
            {0}rau
        Output:
            Reloads all extensions in
            the ./utilties directory.
        """
        error_collection = []
        utilities = [
            x[:-3] for x in sorted(os.listdir("utilities")) if x.endswith(".py")
        ]
        for module in utilities:
            try:
                module_name = importlib.import_module(f"utilities.{module}")
                importlib.reload(module_name)
            except Exception as e:
                error_collection.append(
                    [module, utils.traceback_maker(e, advance=False)]
                )

        if error_collection:
            output = "\n".join(
                [f"**{g[0]}** ```diff\n- {g[1]}```" for g in error_collection]
            )
            return await ctx.fail(
                f"**Failed to reload following utilities.**\n\n{output}"
            )

        await ctx.success("**Successfully reloaded all utilities.**")

    @decorators.command(
        aliases=["reloadallsettings"],
        brief="Reload all settings modules.",
        implemented="2021-03-19 21:57:05.162549",
        updated="2021-05-11 02:51:30.992778",
        examples="""
                {0}rau
                {0}reloadallutils
                """,
    )
    async def ras(self, ctx):
        """
        Usage: {0}ras
        Aliases:
            {0}reloadallsettings
        Output:
            Reloads all extensions in
            the ./settings directory.
            Excludes database.py.
        """
        error_collection = []
        utilities = [
            x[:-3]
            for x in sorted(os.listdir("settings"))
            if x.endswith(".py") and x != "database.py"
        ]
        for module in utilities:
            try:
                module_name = importlib.import_module(f"settings.{module}")
                importlib.reload(module_name)
            except Exception as e:
                error_collection.append(
                    [module, utils.traceback_maker(e, advance=False)]
                )

        if error_collection:
            output = "\n".join(
                [f"**{g[0]}** ```diff\n- {g[1]}```" for g in error_collection]
            )
            return await ctx.send_or_reply(
                content=f"Attempted to reload all settings, was able to reload, "
                f"however the following failed...\n\n{output}",
            )

        await ctx.success("**Successfully reloaded all settings.**")

    @decorators.command(
        aliases=["restart"],
        brief="Cleanly reboot the bot.",
        implemented="2021-03-17 16:04:32.005532",
        updated="2021-05-11 23:52:58.544197",
        examples="""
                {0}reboot
                {0}restart
                """,
    )
    async def reboot(self, ctx):
        """
        Usage: {0}reboot
        Alias: {0}restart
        Output:
            Shuts down all processes,
            sends a confirmation message,
            then updates the message when
            the bot is once again ready.
        """
        msg = await ctx.send_or_reply(
            content=f"{self.bot.emote_dict['loading']} {ctx.invoked_with.capitalize()}ing...",
        )

        client_id = self.bot.user.id
        invoker = ctx.invoked_with.capitalize()
        message = msg.id
        channel = msg.channel.id

        query = """
                UPDATE config SET
                reboot_invoker = $2,
                reboot_message_id = $3,
                reboot_channel_id = $4
                WHERE client_id = $1
                """
        await self.bot.cxn.execute(query, client_id, invoker, message, channel)
        self.bot.loop.stop()
        self.bot.loop.close()
        await self.bot.close()
        # Kill the process
        sys.exit(0)

    ####################
    ## Shell Commands ##
    ####################

    @decorators.group(
        aliases=["l"],
        case_insensitive=True,
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

    @decorators.group(
        hidden=True,
        brief="View ./data/json files.",
        aliases=["j"],
        case_insensitive=True,
    )
    async def json(self, ctx):
        """
        Usage: {0}json <option>
        Alias: {0}j
        Output: View any json file in ./data/json
        Options:
            blacklist|bl
            stats|statistics
            settings|config
        """
        if ctx.invoked_subcommand is None:
            return await ctx.usage("<option>")

    @json.command(aliases=["bl"], brief="Show blacklisted discord objects.")
    async def blacklist(self, ctx):
        """
        Usage: {0}json blacklist
        Alias: {0}json bl
        Output:
            Stars a pagination session
            showing all blacklisted objects.
        """
        sh = self.bot.get_command("sh")
        await ctx.invoke(sh, prefix="json", command="cat ./data/json/blacklist.json")

    @json.command(
        name="stats",
        aliases=["statistics"],
        brief="Basic stats on the last bot run.",
    )
    async def _stats(self, ctx):
        """
        Usage: {0}json stats
        Alias: {0}json statistics
        Output:
            Stars a pagination session
            showing stats from the last
            run the bot made.
        """
        sh = self.bot.get_command("sh")
        await ctx.invoke(sh, prefix="json", command="cat ./data/json/stats.json")

    @json.command(name="settings", aliases=["config"])
    async def _settings(self, ctx):
        """
        Usage: {0}json settings
        Alias: {0}json config
        Output:
            Stars a pagination session
            showing all server settings.
        """
        sh = self.bot.get_command("sh")
        await ctx.invoke(sh, prefix="json", command="cat ./data/json/settings.json")

    @decorators.command(
        aliases=["updatedb"],
        brief="Update the database.",
    )
    async def update(self, ctx):
        """
        Usage: {0}update
        Permission: Bot owner
        Output:
            Performs the mass database insertion
            that normally occurs on bot startup
        """
        c = await pagination.Confirmation(
            f"**{self.bot.emote_dict['exclamation']} This action will restart my database. Do you wish to continue?**"
        ).prompt(ctx)
        if c:
            from settings.database import initialize

            members = self.bot.get_all_members()
            await initialize(self.bot, members)
            await ctx.success("**Updated database**")
        else:
            await ctx.bold("Cancelled")

    # Thank you R. Danny
    @decorators.command(
        writer=80088516616269824,
        brief="Run sql and get results in rst fmt.",
        implemented="2021-03-11 18:29:30.103412",
        updated="2021-05-11 03:03:20.517480",
    )
    async def sql(self, ctx, *, query: str):
        """
        Usage: {0}sql <query>
        Output:
            Shows results in rst format.
            Sends traceback if query failed.
        """

        if query is None:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}sql <query>`",
            )

        query = utils.cleanup_code(query)

        is_multistatement = query.count(";") > 1
        if is_multistatement:
            # fetch does not support multiple statements
            strategy = self.bot.cxn.execute
        else:
            strategy = self.bot.cxn.fetch

        try:
            start = time.perf_counter()
            results = await strategy(query)
            dt = (time.perf_counter() - start) * 1000.0
        except Exception:
            return await ctx.send_or_reply(
                content=f"```py\n{traceback.format_exc()}\n```",
            )

        rows = len(results)
        if is_multistatement or rows == 0:
            return await ctx.send_or_reply(content=f"`{dt:.2f}ms: {results}`")

        headers = list(results[0].keys())
        table = formatting.TabularData()
        table.set_columns(headers)
        table.add_rows(list(r.values()) for r in results)
        render = table.render()

        fmt = f"```sml\n{render}\n```\n*Returned {formatting.plural(rows):row} in {dt:.2f}ms*"
        if len(fmt) > 2000:
            fp = io.BytesIO(fmt.encode("utf-8"))
            await ctx.send_or_reply(file=discord.File(fp, "results.sml"))
        else:
            await ctx.send_or_reply(content=fmt)

    @decorators.command(brief="Show info on a db table.")
    async def table(self, ctx, *, table_name: str = None):
        """Runs a query describing the table schema."""

        query = """
                SELECT column_name, data_type, column_default, is_nullable
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE table_name = $1
                """
        results = await self.bot.cxn.fetch(query, table_name)
        try:
            headers = list(results[0].keys())
        except IndexError:
            return await ctx.usage()
        table = formatting.TabularData()
        table.set_columns(headers)
        table.add_rows(list(r.values()) for r in results)
        render = table.render()

        fmt = f"```\n{render}\n```"
        if len(fmt) > 2000:
            fp = io.BytesIO(fmt.encode("utf-8"))
            await ctx.send_or_reply(
                content="Too many results...",
                file=discord.File(fp, "results.txt"),
            )
        else:
            await ctx.send_or_reply(content=fmt)

    @decorators.command(
        aliases=["tables"],
        brief="Show the database schema.",
    )
    async def database(self, ctx):
        """Runs a query describing the table schema."""
        await ctx.trigger_typing()
        query = """
                SELECT table_schema, table_name FROM INFORMATION_SCHEMA.TABLES
                WHERE table_schema = 'public'
                ORDER BY table_schema, table_name;
                """
        results = await self.bot.cxn.fetch(query)
        try:
            headers = list(results[0].keys())
        except IndexError:
            return await ctx.usage()
        table = formatting.TabularData()
        table.set_columns(headers)
        table.add_rows(list(r.values()) for r in results)
        render = table.render()

        fmt = f"```\n{render}\n```"
        if len(fmt) > 2000:
            fp = io.BytesIO(fmt.encode("utf-8"))
            await ctx.send_or_reply(
                content="Too many results...",
                file=discord.File(fp, "results.txt"),
            )
        else:
            await ctx.send_or_reply(content=fmt)

    @decorators.group(hidden=True, brief="Show info on the database.", aliases=["pg"])
    async def postgres(self, ctx):
        """
        Usage: {0}postgres <option>
        Alias: {0}pg
        Output: Gets specific info on the database
        Options:
            Size: Get the size of the total db or a table.
            lb|largest: Show the largest tables
            types: Show general info on postgres datatypes
            i|info: Show all data on database tables
            r|relation|relations: Show the database relations
        """
        if ctx.invoked_subcommand is None:
            return await ctx.usage(ctx.command.signature)

    @postgres.command(brief="Get the size of the total db or a table.")
    async def size(self, ctx, *, table_name: str = None):
        """Runs a query describing the table schema."""

        if table_name is None:
            query = """SELECT pg_size_pretty(pg_database_size($1));"""
            try:
                results = await self.bot.cxn.fetch(
                    query, self.bot.constants.postgres.split("/")[-1]
                )
            except asyncpg.UndefinedTableError:
                return await ctx.send_or_reply(
                    content=f"{self.bot.emote_dict['failed']} Table `{table_name}` does not exist.",
                )
        else:
            query = """SELECT pg_size_pretty( pg_total_relation_size($1));"""
            try:
                results = await self.bot.cxn.fetch(query, table_name)
            except asyncpg.UndefinedTableError:
                return await ctx.send_or_reply(
                    content=f"{self.bot.emote_dict['failed']} Table `{table_name}` does not exist.",
                )

        headers = list(results[0].keys())
        table = formatting.TabularData()
        table.set_columns(headers)
        table.add_rows(list(r.values()) for r in results)
        render = table.render()

        fmt = f"```\n{render}\n```"
        if len(fmt) > 2000:
            fp = io.BytesIO(fmt.encode("utf-8"))
            await ctx.send_or_reply(
                content="Too many results...",
                file=discord.File(fp, "results.txt"),
            )
        else:
            await ctx.send_or_reply(content=fmt)

    @postgres.command(aliases=["largest"], brief="Get the largest tables.")
    async def lb(self, ctx):
        """Runs a query describing the table schema."""

        query = """ WITH RECURSIVE pg_inherit(inhrelid, inhparent) AS
                    (select inhrelid, inhparent
                    FROM pg_inherits
                    UNION
                    SELECT child.inhrelid, parent.inhparent
                    FROM pg_inherit child, pg_inherits parent
                    WHERE child.inhparent = parent.inhrelid),
                pg_inherit_short AS (SELECT * FROM pg_inherit WHERE inhparent NOT IN (SELECT inhrelid FROM pg_inherit))
                SELECT table_schema
                    , TABLE_NAME
                    , row_estimate
                    , pg_size_pretty(total_bytes) AS total
                    , pg_size_pretty(index_bytes) AS INDEX
                    , pg_size_pretty(toast_bytes) AS toast
                    , pg_size_pretty(table_bytes) AS TABLE
                FROM (
                    SELECT *, total_bytes-index_bytes-COALESCE(toast_bytes,0) AS table_bytes
                    FROM (
                        SELECT c.oid
                            , nspname AS table_schema
                            , relname AS TABLE_NAME
                            , SUM(c.reltuples) OVER (partition BY parent) AS row_estimate
                            , SUM(pg_total_relation_size(c.oid)) OVER (partition BY parent) AS total_bytes
                            , SUM(pg_indexes_size(c.oid)) OVER (partition BY parent) AS index_bytes
                            , SUM(pg_total_relation_size(reltoastrelid)) OVER (partition BY parent) AS toast_bytes
                            , parent
                        FROM (
                                SELECT pg_class.oid
                                    , reltuples
                                    , relname
                                    , relnamespace
                                    , pg_class.reltoastrelid
                                    , COALESCE(inhparent, pg_class.oid) parent
                                FROM pg_class
                                    LEFT JOIN pg_inherit_short ON inhrelid = oid
                                WHERE relkind IN ('r', 'p')
                            ) c
                            LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
                            ) a
                            WHERE oid = parent
                            ) a
                            WHERE table_schema = 'public'
                            ORDER BY total_bytes DESC;"""
        results = await self.bot.cxn.fetch(query)

        headers = list(results[0].keys())
        table = formatting.TabularData()
        table.set_columns(headers)
        table.add_rows(list(r.values()) for r in results)
        render = table.render()

        fmt = f"```\n{render}\n```"
        if len(fmt) > 2000:
            fp = io.BytesIO(fmt.encode("utf-8"))
            await ctx.send_or_reply(
                content="Too many results...",
                file=discord.File(fp, "results.txt"),
            )
        else:
            await ctx.send_or_reply(content=fmt)

    @postgres.command(aliases=["t"], brief="Show some info on postgres datatypes.")
    async def types(self, ctx):
        """Runs a query describing the table schema."""

        query = """SELECT typname, typlen from pg_type where typtype='b';"""
        results = await self.bot.cxn.fetch(query)

        headers = list(results[0].keys())
        table = formatting.TabularData()
        table.set_columns(headers)
        table.add_rows(list(r.values()) for r in results)
        render = table.render()

        fmt = f"```\n{render}\n```"
        if len(fmt) > 2000:
            fp = io.BytesIO(fmt.encode("utf-8"))
            await ctx.send_or_reply(
                content="Too many results...",
                file=discord.File(fp, "results.txt"),
            )
        else:
            await ctx.send_or_reply(content=fmt)

    @postgres.command(aliases=["info"], brief="Show some info on postgres table sizes.")
    async def i(self, ctx):
        """Runs a query describing the table schema."""
        query = """ 
                SELECT *, pg_size_pretty(total_bytes) AS total
                    , pg_size_pretty(index_bytes) AS index
                    , pg_size_pretty(toast_bytes) AS toast
                    , pg_size_pretty(table_bytes) AS table
                FROM (
                SELECT *, total_bytes-index_bytes-coalesce(toast_bytes,0) AS table_bytes FROM (
                    SELECT c.oid,nspname AS table_schema, relname AS table_name
                            , c.reltuples AS row_estimate
                            , pg_total_relation_size(c.oid) AS total_bytes
                            , pg_indexes_size(c.oid) AS index_bytes
                            , pg_total_relation_size(reltoastrelid) AS toast_bytes
                        FROM pg_class c
                        LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
                        WHERE relkind = 'r'
                ) a
                ) a
                WHERE table_schema = 'public'; 
                """
        results = await self.bot.cxn.fetch(query)

        headers = list(results[0].keys())
        table = formatting.TabularData()
        table.set_columns(headers)
        table.add_rows(list(r.values()) for r in results)
        render = table.render()

        fmt = f"```\n{render}\n```"
        if len(fmt) > 2000:
            fp = io.BytesIO(fmt.encode("utf-8"))
            await ctx.send_or_reply(
                content="Too many results...",
                file=discord.File(fp, "results.txt"),
            )
        else:
            await ctx.send_or_reply(content=fmt)

    @postgres.command(
        aliases=["relation", "relations"], brief="Show some info on postgres relations."
    )
    async def r(self, ctx):
        """Runs a query describing the table schema."""
        query = """ 
                SELECT nspname || '.' || relname AS "relation",
                    pg_size_pretty(pg_relation_size(C.oid)) AS "size"
                FROM pg_class C
                LEFT JOIN pg_namespace N ON (N.oid = C.relnamespace)
                WHERE nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                ORDER BY pg_relation_size(C.oid) DESC;
                """
        results = await self.bot.cxn.fetch(query)

        headers = list(results[0].keys())
        table = formatting.TabularData()
        table.set_columns(headers)
        table.add_rows(list(r.values()) for r in results)
        render = table.render()

        fmt = f"```\n{render}\n```"
        if len(fmt) > 2000:
            fp = io.BytesIO(fmt.encode("utf-8"))
            await ctx.send_or_reply(
                content="Too many results...",
                file=discord.File(fp, "results.txt"),
            )
        else:
            await ctx.send_or_reply(content=fmt)

    async def run_process(self, command):
        try:
            process = await asyncio.create_subprocess_shell(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            result = await process.communicate()
        except NotImplementedError:
            process = subprocess.Popen(
                command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            result = await self.bot.loop.run_in_executor(None, process.communicate)

        return [output.decode() for output in result]

    # https://github.com/Rapptz/RoboDanny
    @decorators.command(
        hidden=True,
        aliases=["shell", "bash"],
        brief="Run shell commands.",
        writer=80088516616269824,
    )
    async def sh(self, ctx, prefix=None, *, command):
        """Runs a shell command."""

        async with ctx.typing():
            stdout, stderr = await self.run_process(command)

        if stderr:
            text = f"stdout:\n{stdout}\nstderr:\n{stderr}"
        else:
            text = stdout

        pages = pagination.MainMenu(
            pagination.TextPageSource(text, prefix="```" + prefix)
        )
        try:
            await pages.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(str(e))

    @decorators.command(
        hidden=True,
        aliases=["repeat"],
        brief="Repeat a command.",
        writer=80088516616269824,
    )
    async def do(self, ctx, times: int, *, command):
        """
        Usage: {0}do <times> <command>
        Output:
            Repeats a command a specified number of times.
        """
        msg = copy.copy(ctx.message)
        msg.content = ctx.prefix + command

        new_ctx = await self.bot.get_context(msg, cls=type(ctx))

        for i in range(times):
            await asyncio.sleep(0.5)
            try:
                await new_ctx.reinvoke()
            except ValueError:
                return await ctx.send_or_reply(content=f"Invalid Context")

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
            await ctx.send(e)

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

    @decorators.command(aliases=["perf", "elapsed"], brief="Time a command response.")
    async def elapse(self, ctx, *, command):
        """Checks the timing of a command, attempting to suppress HTTP and DB calls."""

        msg = copy.copy(ctx.message)
        msg.content = ctx.prefix + command

        new_ctx = await self.bot.get_context(msg, cls=type(ctx))
        new_ctx._db = PerformanceMocker()

        # Intercepts the Messageable interface a bit
        new_ctx._state = PerformanceMocker()
        new_ctx.channel = PerformanceMocker()

        if new_ctx.command is None:
            return await ctx.send_or_reply(content="No command found")

        start = time.perf_counter()
        try:
            await new_ctx.command.invoke(new_ctx)
        except commands.CommandError:
            end = time.perf_counter()
            success = False
            try:
                await ctx.send_or_reply(
                    content=f"```py\n{traceback.format_exc()}\n```",
                )
            except discord.HTTPException:
                pass
        else:
            end = time.perf_counter()
            success = True

        if success is True:
            emote = self.bot.emote_dict["success"]
        else:
            emote = self.bot.emote_dict["failed"]

        await ctx.send_or_reply(
            content=f"{emote} `{(end - start) * 1000:.2f}ms`",
        )

    @decorators.command(aliases=["clearconsole", "cl"], brief="Clear the console.")
    async def cleartrace(self, ctx):
        """
        Usage: {0}cleartrace
        Alias: {0}cl
        Output:
            Clears the console and
            prints a clean nicely
            formatted message.
        """
        print("hello")
        if os.name == "nt":
            os.system("cls")
        else:
            try:
                os.system("clear")
            except Exception:
                for _ in range(100):
                    print("\n")

        message = "Logged in as %s." % self.bot.user
        uid_message = "User ID: %s." % self.bot.user.id
        separator = "-" * max(len(message), len(uid_message))
        print(separator)
        try:
            print(message)
        except:  # some bot usernames with special chars fail on shitty platforms
            print(message.encode(errors="replace").decode())
        print(uid_message)
        print(separator)
        await ctx.success("Console cleared.")

    @decorators.command(aliases=["github"], brief="Run github commands.")
    async def git(self, ctx, *, subcommand):
        """
        Usage: {0}git <command>
        Alias: {0}github
        Output:
            Runs a git command.
        Notes:
            Use the shorthand {0}git give
            to run 3 commands concurrently.
            namely,
                git add .
                git commit -m "update"
                git push
        """
        if subcommand is None:
            return await ctx.send_help(str(ctx.command))

        # I never remember to keep track of bot versions...
        query = """
                UPDATE config
                SET version = version + 0.1
                WHERE client_id = $1;
                """
        await self.bot.cxn.execute(query, self.bot.user.id)

        if subcommand == "give":
            subcommand = "add . && git commit -m 'update' && git push"

        message = await ctx.send_or_reply(
            content=f"{self.bot.emote_dict['loading']} **Updating...**",
        )
        async with ctx.typing():
            stdout, stderr = await self.run_process("git " + subcommand)

        if stderr:
            text = f"stdout:\n{stdout}\nstderr:\n{stderr}"
        else:
            text = stdout

        await self.bot.hecate.send("```prolog\n" + text + "```")

        await message.edit(content=f"{self.bot.emote_dict['success']} **Completed.**")

    @decorators.command(hidden=True, brief="Run a command as another user.")
    async def sudo(
        self,
        ctx,
        channel: typing.Optional[converters.GlobalChannel],
        who: typing.Union[discord.Member, discord.User],
        *,
        command: str,
    ):
        """
        Usage: {0}sudo [channel] [user] <command>
        Outpue:
            Run a command as another user
            optionally in another channel.
        """
        msg = copy.copy(ctx.message)
        channel = channel or ctx.channel
        msg.channel = channel
        msg.author = who
        msg.content = ctx.prefix + command
        new_ctx = await self.bot.get_context(msg, cls=type(ctx))
        # new_ctx._db = ctx._db
        await self.bot.invoke(new_ctx)

    @decorators.command(
        name="eval",
        aliases=["evaluate", "e", "exe", "exec"],
        brief="Evaluate python code.",
    )
    async def _eval(self, ctx, *, body: str):
        """
        Usage: {0}eval <body>
        Aliases:
            {0}e
            {0}exe
            {0}exec
            {0}evaluate
        Output: Code evaluation
        Environment:
            "self": Manager,
            "utils": utils,
            "converters": converters,
            "discord": discord,
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
            "_": self._last_result,
        """
        env = {
            "self": self,
            "utils": utils,
            "converters": converters,
            "discord": discord,
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
            "_": self._last_result,
        }

        env.update(globals())

        body = utils.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send_or_reply(
                content=f"```py\n{e.__class__.__name__}: {e}\n```",
            )

        func = env["func"]
        try:
            with contextlib.redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send_or_reply(
                content=f"```py\n{value}{traceback.format_exc()}\n```",
            )
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction(self.bot.emote_dict["success"])
            except:
                pass

            if ret is None:
                if value:
                    try:
                        p = pagination.MainMenu(
                            pagination.TextPageSource(f"{value}", prefix="```py")
                        )
                    except Exception as e:
                        return await ctx.send(e)
                    try:
                        await p.start(ctx)
                    except menus.MenuError as e:
                        await ctx.send(e)
            else:
                try:
                    p = pagination.MainMenu(
                        pagination.TextPageSource(f"{value}{ret}", prefix="```py")
                    )
                except Exception as e:
                    return await ctx.send(e)
                self._last_result = ret
                try:
                    await p.start(ctx)
                except menus.MenuError as e:
                    await ctx.send(e)


class PerformanceMocker:
    """A mock object that can also be used in await expressions."""

    def __init__(self):
        self.loop = asyncio.get_event_loop()

    def permissions_for(self, obj):
        # Lie and say we don't have permissions to embed
        # This makes it so pagination sessions just abruptly end on __init__
        # Most checks based on permission have a bypass for the owner anyway
        # So this lie will not affect the actual command invocation.
        perms = discord.Permissions.all()
        perms.administrator = False
        perms.embed_links = False
        perms.add_reactions = False
        return perms

    def __getattr__(self, attr):
        return self

    def __call__(self, *args, **kwargs):
        return self

    def __repr__(self):
        return "<PerformanceMocker>"

    def __await__(self):
        future = self.loop.create_future()
        future.set_result(self)
        return future.__await__()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return self

    def __len__(self):
        return 0

    def __bool__(self):
        return False
