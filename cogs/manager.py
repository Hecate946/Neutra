import asyncio
import contextlib
import copy
import datetime
import importlib
import io
import os
import subprocess
import sys
import textwrap
import time
import traceback
import typing
from collections import defaultdict

import asyncpg
import discord
import psutil
from discord.ext import commands, menus

from settings import constants
from utilities import converters, formatting, pagination, utils


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
        if not await self.bot.is_owner(ctx.author):
            return
        return True

    @commands.command(name="eval", aliases=["evaluate", "e"])
    async def _eval(self, ctx, *, body: str):
        """Evaluates a code"""

        env = {
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
            "_": self._last_result,
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"```py\n{e.__class__.__name__}: {e}\n```",
            )

        func = env["func"]
        try:
            with contextlib.redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send(
                reference=self.bot.rep_ref(ctx),
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
                    await ctx.send(
                        reference=self.bot.rep_ref(ctx), content=f"```py\n{value}\n```"
                    )
            else:
                self._last_result = ret
                await ctx.send(
                    reference=self.bot.rep_ref(ctx), content=f"```py\n{value}{ret}\n```"
                )

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])

        # remove `foo`
        return content.strip("` \n")

    @commands.command(brief="Refresh the bot variables.")
    async def refresh(self, ctx):
        """
        Usage: -refresh
        Output: Resets all global bot variables
        Permission: Bot owner
        Notes:
            Useful to use this command as an
            alternative to restarting the bot when
            changes are made to the config.json file
        """
        config = utils.config().copy()
        constants.token = config["token"]
        constants.postgres = config["postgres"]
        constants.github = config["github"]
        constants.webhook = config["webhook"]
        constants.imgur = config["imgur"]
        constants.prefix = config["prefix"]
        constants.owners = config["owners"]
        constants.admins = config["admins"]
        constants.embed = config["embed"]
        constants.status = config["status"]
        constants.activity = config["activity"]
        constants.presence = config["presence"]
        constants.version = config["version"]
        constants.reboot = config["reboot"]

        self.bot.owner_ids = constants.owners

        await ctx.send(
            reference=self.bot.rep_ref(ctx),
            content=f"{self.bot.emote_dict['success']} **Refreshed Configuration.**",
        )

    @commands.command(hidden=True, brief="Load an extension.")
    async def load(self, ctx, name: str):
        """ Loads an extension. """
        try:
            self.bot.load_extension(f"cogs.{name}")
        except Exception:
            try:
                self.bot.load_extension(f"{name}")
            except Exception as e:
                return await ctx.send(str(e).replace("'", "**"))
        await ctx.send(
            reference=self.bot.rep_ref(ctx),
            content=f"{self.bot.emote_dict['success']} Loaded extension **{name}**",
        )

    @commands.command(hidden=True, brief="Unload an extension.")
    async def unload(self, ctx, name: str):
        """ Unloads an extension. """
        try:
            self.bot.unload_extension(f"cogs.{name}")
        except Exception:
            try:
                self.bot.unload_extension(f"{name}")
            except Exception as e:
                return await ctx.send(str(e).replace("'", "**"))
        await ctx.send(
            reference=self.bot.rep_ref(ctx),
            content=f"{self.bot.emote_dict['success']} Unloaded extension **{name}**",
        )

    @commands.command(name="reload", hidden=True, brief="Reload an extension.")
    async def _reload(self, ctx, name: str):
        """ Reloads an extension. """
        try:
            self.bot.reload_extension(f"cogs.{name}")
        except Exception:
            try:
                self.bot.reload_extension(f"{name}")
            except Exception as e:
                return await ctx.send(str(e).replace("'", "**"))
        await ctx.send(
            reference=self.bot.rep_ref(ctx),
            content=f"{self.bot.emote_dict['success']} Reloaded extension **{name}.py**",
        )

    @commands.command(hidden=True, brief="Reload all extensions.")
    async def reloadall(self, ctx):
        """ Reloads all extensions. """
        error_collection = []
        for file in os.listdir("cogs"):
            if file.endswith(".py"):
                name = file[:-3]
                try:
                    self.bot.reload_extension(f"cogs.{name}")
                except Exception as e:
                    error_collection.append(
                        [file, utils.traceback_maker(e, advance=False)]
                    )

        if error_collection:
            output = "\n".join(
                [f"**{g[0]}** ```diff\n- {g[1]}```" for g in error_collection]
            )
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"Attempted to reload all extensions, was able to reload, "
                f"however the following failed...\n\n{output}",
            )

        await ctx.send(
            reference=self.bot.rep_ref(ctx),
            content=f"{self.bot.emote_dict['success']} Successfully reloaded all extensions",
        )

    @commands.command(hidden=True, brief="Reload a utilities module.")
    async def reloadutils(self, ctx, name: str):
        """ Reloads a utils module. """
        name_maker = f"./utilities/{name}.py"
        try:
            module_name = importlib.import_module(f"./utilities.{name}")
            importlib.reload(module_name)
        except ModuleNotFoundError:
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"Couldn't find module named **{name_maker}**",
            )
        except Exception as e:
            error = utils.traceback_maker(e)
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"Module **{name_maker}** returned error and was not reloaded...\n{error}",
            )
        await ctx.send(
            reference=self.bot.rep_ref(ctx),
            content=f"{self.bot.emote_dict['success']} Reloaded module **{name_maker}**",
        )

    @commands.command(hidden=True, brief="Reload all utilities modules.")
    async def reloadallutils(self, ctx):
        """ Reloads a utils module. """
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
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"Attempted to reload all utilties, was able to reload, "
                f"however the following failed...\n\n{output}",
            )

        await ctx.send(
            reference=self.bot.rep_ref(ctx),
            content=f"{self.bot.emote_dict['success']} Successfully reloaded all utilities.",
        )

    @commands.command(hidden=True, aliases=["restart"], brief="Reboot the bot.")
    async def reboot(self, ctx):
        """
        Usage:       -reboot
        Alias:       -restart
        Permissions: Bot Owner
        """
        msg = await ctx.send(
            reference=self.bot.rep_ref(ctx),
            content=f"{self.bot.emote_dict['loading']} {ctx.invoked_with.capitalize()}ing...",
        )
        utils.modify_config(
            key="reboot",
            value={
                "invoker": ctx.invoked_with.capitalize(),
                "message": msg.id,
                "channel": msg.channel.id,
            },
        )
        self.bot.loop.stop()
        self.bot.loop.close()
        await self.bot.close()
        # Kill the process
        sys.exit(0)

    ####################
    ## Shell Commands ##
    ####################

    @commands.group(
        hidden=True, brief="View log files.", aliases=["l"], case_insensitive=True
    )
    async def logger(self, ctx):
        """
        Usage: -logger <option>
        Alias: -l
        Permission: Bot owner
        Output: View any log recorded in ./data/logs
        Options:
            commands
            errors
            info
            traceback
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))

    @logger.command(name="commands", aliases=["cmds"])
    async def _get_cmds(self, ctx):
        sh = self.bot.get_command("sh")
        await ctx.invoke(sh, prefix="prolog", command="cat ./data/logs/commands.log")

    @logger.command(name="traceback")
    async def _traceback(self, ctx):
        sh = self.bot.get_command("sh")
        await ctx.invoke(sh, prefix="prolog", command="cat ./data/logs/traceback.log")

    @logger.command(name="info")
    async def _info(self, ctx):
        sh = self.bot.get_command("sh")
        await ctx.invoke(sh, prefix="prolog", command="cat ./data/logs/info.log")

    @logger.command(name="errors")
    async def _errors(self, ctx):
        sh = self.bot.get_command("sh")
        await ctx.invoke(sh, prefix="prolog", command="cat ./data/logs/errors.log")

    @commands.group(hidden=True, brief="View pm2 files.", case_insensitive=True)
    async def pm2(self, ctx):
        """
        Usage: -pm2 <option>
        Output: View any pm2 log file in ./data/pm2
        Options:
            stdout      Alias: out
            stderr      Aliases: err, error, errors
            pid         Aliases: process, processid
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))

    @pm2.command(aliases=["out", "output"])
    async def stdout(self, ctx):
        sh = self.bot.get_command("sh")
        pm2dir = os.listdir("./data/pm2/")
        for filename in pm2dir:
            print(filename)
            if filename.startswith("out"):
                await ctx.invoke(sh, prefix="yml", command=f"cat ./data/pm2/{filename}")

    @pm2.command(aliases=["err", "error", "errors"])
    async def stderr(self, ctx):
        sh = self.bot.get_command("sh")
        pm2dir = os.listdir("./data/pm2/")
        for filename in pm2dir:
            if filename.startswith("err"):
                await ctx.invoke(sh, prefix="yml", command=f"cat ./data/pm2/{filename}")

    @pm2.command(aliases=["process", "processid"])
    async def pid(self, ctx):
        sh = self.bot.get_command("sh")
        pm2dir = os.listdir("./data/pm2/")
        for filename in pm2dir:
            if filename.startswith("pid"):
                await ctx.invoke(sh, prefix="yml", command=f"cat ./data/pm2/{filename}")

    @commands.group(
        hidden=True,
        brief="View ./data/json files.",
        aliases=["j"],
        case_insensitive=True,
    )
    async def json(self, ctx):
        """
        Usage: -json <option>
        Alias: -j
        Output: View any json file in ./data/json
        Options:
            commands        Aliases: command, commandstats
            socket          Aliases: socket, socketstats
            stats           Alias: statistics
            settings        Alias: config
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))

    @json.command(name="commands", aliases=["commandstats", "command"])
    async def _commands(self, ctx):
        sh = self.bot.get_command("sh")
        await ctx.invoke(sh, prefix="json", command="cat ./data/json/commands.json")

    @json.command(name="socket", aliases=["sockets", "socketstats"])
    async def _sockets(self, ctx):
        sh = self.bot.get_command("sh")
        await ctx.invoke(sh, prefix="json", command="cat ./data/json/sockets.json")

    @json.command(name="stats", aliases=["statistics"])
    async def _stats(self, ctx):
        sh = self.bot.get_command("sh")
        await ctx.invoke(sh, prefix="json", command="cat ./data/json/stats.json")

    @json.command(name="settings", aliases=["config"])
    async def _settings(self, ctx):
        sh = self.bot.get_command("sh")
        await ctx.invoke(sh, prefix="json", command="cat ./data/json/settings.log")

    @commands.command(hidden=True, brief="Update the database.", aliases=["update_db"])
    async def update(self, ctx):
        """
        Usage: -update
        Permission: Bot owner
        Output:
            Performs the mass database insertion
            that normally occurs on bot startup
        """
        from settings.database import initialize

        members = self.bot.get_all_members()
        await initialize(self.bot.guilds, members)
        await ctx.send(
            reference=self.bot.rep_ref(ctx),
            content=f"{self.bot.emote_dict['success']} Updated Database",
        )

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])

        # remove `foo`
        return content.strip("` \n")

    # Thank you R. Danny
    @commands.command(hidden=True, brief="Run sql and get results in rst fmt.")
    async def sql(self, ctx, *, query: str):
        """
        Usage: -sql <query>
        """

        if query is None:
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"Usage: `{ctx.prefix}sql <query>`",
            )

        query = self.cleanup_code(query)

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
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"```py\n{traceback.format_exc()}\n```",
            )

        rows = len(results)
        if is_multistatement or rows == 0:
            return await ctx.send(
                reference=self.bot.rep_ref(ctx), content=f"`{dt:.2f}ms: {results}`"
            )

        headers = list(results[0].keys())
        table = formatting.TabularData()
        table.set_columns(headers)
        table.add_rows(list(r.values()) for r in results)
        render = table.render()

        fmt = f"```\n{render}\n```\n*Returned {formatting.plural(rows):row} in {dt:.2f}ms*"
        if len(fmt) > 2000:
            fp = io.BytesIO(fmt.encode("utf-8"))
            await ctx.send(
                reference=self.bot.rep_ref(ctx), file=discord.File(fp, "results.txt")
            )
        else:
            await ctx.send(reference=self.bot.rep_ref(ctx), content=fmt)

    @commands.command(
        hidden=True, brief="Show info on a sql table.", aliases=["tables", "database"]
    )
    async def table(self, ctx, *, table_name: str = None):
        """Runs a query describing the table schema."""

        if ctx.invoked_with in ["tables", "database"]:
            query = """SELECT table_schema, table_name FROM INFORMATION_SCHEMA.TABLES
                       WHERE table_schema = 'public'
                       ORDER BY table_schema, table_name;
                    """
            results = await self.bot.cxn.fetch(query)
        else:
            query = """SELECT column_name, data_type, column_default, is_nullable
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE table_name = $1
                    """
            results = await self.bot.cxn.fetch(query, table_name)
        try:
            headers = list(results[0].keys())
        except IndexError:
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"Usage: `{ctx.prefix}table <table name>`",
            )
        table = formatting.TabularData()
        table.set_columns(headers)
        table.add_rows(list(r.values()) for r in results)
        render = table.render()

        fmt = f"```\n{render}\n```"
        if len(fmt) > 2000:
            fp = io.BytesIO(fmt.encode("utf-8"))
            await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content="Too many results...",
                file=discord.File(fp, "results.txt"),
            )
        else:
            await ctx.send(reference=self.bot.rep_ref(ctx), content=fmt)

    @commands.group(hidden=True, brief="Show info on the database.", aliases=["pg"])
    async def postgres(self, ctx):
        """
        Usage: -postgres <option>
        Alias: -pg
        Output: Gets specific info on the database
        Options:
            Size: Get the size of the total db or a table.
            lb/largest: Show the largest tables
            types: Show general info on postgres datatypes
            i/info: Show all data on database tables
            r/relation/relations: Show the database relations
        """
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(str(ctx.command))

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
                return await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content=f"{self.bot.emote_dict['failed']} Table `{table_name}` does not exist.",
                )
        else:
            query = """SELECT pg_size_pretty( pg_total_relation_size($1));"""
            try:
                results = await self.bot.cxn.fetch(query, table_name)
            except asyncpg.UndefinedTableError:
                return await ctx.send(
                    reference=self.bot.rep_ref(ctx),
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
            await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content="Too many results...",
                file=discord.File(fp, "results.txt"),
            )
        else:
            await ctx.send(reference=self.bot.rep_ref(ctx), content=fmt)

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
            await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content="Too many results...",
                file=discord.File(fp, "results.txt"),
            )
        else:
            await ctx.send(reference=self.bot.rep_ref(ctx), content=fmt)

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
            await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content="Too many results...",
                file=discord.File(fp, "results.txt"),
            )
        else:
            await ctx.send(reference=self.bot.rep_ref(ctx), content=fmt)

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
            await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content="Too many results...",
                file=discord.File(fp, "results.txt"),
            )
        else:
            await ctx.send(reference=self.bot.rep_ref(ctx), content=fmt)

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
            await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content="Too many results...",
                file=discord.File(fp, "results.txt"),
            )
        else:
            await ctx.send(reference=self.bot.rep_ref(ctx), content=fmt)

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
    @commands.command(
        hidden=True, aliases=["shell", "bash"], brief="Run a shell command."
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
            await ctx.send(str(e))

    @commands.command(hidden=True, aliases=["repeat"], brief="Repeat a command.")
    async def do(self, ctx, times: int, *, command):
        """Repeats a command a specified number of times."""
        msg = copy.copy(ctx.message)
        msg.content = ctx.prefix + command

        new_ctx = await self.bot.get_context(msg, cls=type(ctx))

        for i in range(times):
            await asyncio.sleep(0.5)
            try:
                await new_ctx.reinvoke()
            except ValueError:
                return await ctx.send(
                    reference=self.bot.rep_ref(ctx), content=f"Invalid Context"
                )

    async def tabulate_query(self, ctx, query, *args):
        records = await self.bot.cxn.fetch(query, *args)

        if len(records) == 0:
            return await ctx.send(
                reference=self.bot.rep_ref(ctx), content="No results found."
            )

        headers = list(records[0].keys())
        table = formatting.TabularData()
        table.set_columns(headers)
        table.add_rows(list(r.values()) for r in records)
        render = table.render()

        fmt = f"```\n{render}\n```"
        if len(fmt) > 2000:
            fp = io.BytesIO(fmt.encode("utf-8"))
            await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content="Too many results...",
                file=discord.File(fp, "results.txt"),
            )
        else:
            await ctx.send(reference=self.bot.rep_ref(ctx), content=fmt)

    @commands.group(
        hidden=True, invoke_without_command=True, brief="Show command history."
    )
    @commands.is_owner()
    async def command_history(self, ctx):
        """Command history."""
        query = """SELECT
                        CASE failed
                            WHEN TRUE THEN command || ' [!]'
                            ELSE command
                        END AS "command",
                        to_char(timestamp, 'Mon DD HH12:MI:SS AM') AS "invoked",
                        author_id,
                        server_id
                   FROM commands
                   ORDER BY timestamp DESC
                   LIMIT 15;
                """
        await self.tabulate_query(ctx, query)

    @command_history.command(name="for")
    @commands.is_owner()
    async def command_history_for(
        self, ctx, days: typing.Optional[int] = 7, *, command: str
    ):
        """Command history for a command."""

        query = """SELECT *, t.success + t.failed AS "total"
                   FROM (
                       SELECT server_id,
                              SUM(CASE WHEN failed THEN 0 ELSE 1 END) AS "success",
                              SUM(CASE WHEN failed THEN 1 ELSE 0 END) AS "failed"
                       FROM commands
                       WHERE command=$1
                       AND timestamp > (CURRENT_TIMESTAMP - $2::interval)
                       GROUP BY server_id
                   ) AS t
                   ORDER BY "total" DESC
                   LIMIT 30;
                """

        await self.tabulate_query(ctx, query, command, datetime.timedelta(days=days))

    @command_history.command(name="guild", aliases=["server"])
    @commands.is_owner()
    async def command_history_guild(self, ctx, server_id: int):
        """Command history for a guild."""

        query = """SELECT
                        CASE failed
                            WHEN TRUE THEN command || ' [!]'
                            ELSE command
                        END AS "command",
                        channel_id,
                        author_id,
                        timestamp
                   FROM commands
                   WHERE server_id=$1
                   ORDER BY timestamp DESC
                   LIMIT 15;
                """
        await self.tabulate_query(ctx, query, server_id)

    @command_history.command(name="user", aliases=["member"])
    @commands.is_owner()
    async def command_history_user(self, ctx, user_id: int):
        """Command history for a user."""

        query = """SELECT
                        CASE failed
                            WHEN TRUE THEN command || ' [!]'
                            ELSE command
                        END AS "command",
                        server_id,
                        timestamp
                   FROM commands
                   WHERE author_id=$1
                   ORDER BY timestamp DESC
                   LIMIT 20;
                """
        await self.tabulate_query(ctx, query, user_id)

    @command_history.command(name="log")
    @commands.is_owner()
    async def command_history_log(self, ctx, days=7):
        """Command history log for the last N days."""

        query = """SELECT command, COUNT(*)
                   FROM commands
                   WHERE timestamp > (CURRENT_TIMESTAMP - $1::interval)
                   GROUP BY command
                   ORDER BY 2 DESC
                """

        all_commands = {c.qualified_name: 0 for c in self.bot.walk_commands()}

        records = await self.bot.cxn.fetch(query, datetime.timedelta(days=days))
        for name, uses in records:
            if name in all_commands:
                all_commands[name] = uses

        as_data = sorted(all_commands.items(), key=lambda t: t[1], reverse=True)
        table = formatting.TabularData()
        table.set_columns(["Command", "Uses"])
        table.add_rows(tup for tup in as_data)
        render = table.render()

        embed = discord.Embed(title="Summary", color=self.bot.constants.embed)
        embed.set_footer(
            text="Since"
        ).timestamp = datetime.datetime.utcnow() - datetime.timedelta(days=days)

        top_ten = "\n".join(f"{command}: {uses}" for command, uses in records[:10])
        bottom_ten = "\n".join(f"{command}: {uses}" for command, uses in records[-10:])
        embed.add_field(name="Top 10", value=top_ten)
        embed.add_field(name="Bottom 10", value=bottom_ten)

        unused = ", ".join(name for name, uses in as_data if uses == 0)
        if len(unused) > 1024:
            unused = "Way too many..."

        embed.add_field(name="Unused", value=unused, inline=False)

        await ctx.send(
            reference=self.bot.rep_ref(ctx),
            embed=embed,
            file=discord.File(io.BytesIO(render.encode()), filename="full_results.txt"),
        )

    @command_history.command(name="cog")
    @commands.is_owner()
    async def command_history_cog(
        self, ctx, days: typing.Optional[int] = 7, *, cog: str = None
    ):
        """Command history for a cog or grouped by a cog."""

        interval = datetime.timedelta(days=days)
        if cog is not None:
            cog = self.bot.get_cog(cog)
            if cog is None:
                return await ctx.send(
                    reference=self.bot.rep_ref(ctx), content=f"Unknown cog: {cog}"
                )

            query = """SELECT *, t.success + t.failed AS "total"
                       FROM (
                           SELECT command,
                                  SUM(CASE WHEN failed THEN 0 ELSE 1 END) AS "success",
                                  SUM(CASE WHEN failed THEN 1 ELSE 0 END) AS "failed"
                           FROM commands
                           WHERE command = any($1::text[])
                           AND timestamp > (CURRENT_TIMESTAMP - $2::interval)
                           GROUP BY command
                       ) AS t
                       ORDER BY "total" DESC
                       LIMIT 30;
                    """
            return await self.tabulate_query(
                ctx, query, [c.qualified_name for c in cog.walk_commands()], interval
            )

        # A more manual query with a manual grouper.
        query = """SELECT *, t.success + t.failed AS "total"
                   FROM (
                       SELECT command,
                              SUM(CASE WHEN failed THEN 0 ELSE 1 END) AS "success",
                              SUM(CASE WHEN failed THEN 1 ELSE 0 END) AS "failed"
                       FROM commands
                       WHERE timestamp > (CURRENT_TIMESTAMP - $1::interval)
                       GROUP BY command
                   ) AS t;
                """

        class Count:
            __slots__ = ("success", "failed", "total")

            def __init__(self):
                self.success = 0
                self.failed = 0
                self.total = 0

            def add(self, record):
                self.success += record["success"]
                self.failed += record["failed"]
                self.total += record["total"]

        data = defaultdict(Count)
        records = await self.bot.cxn.fetch(query, interval)
        for record in records:
            command = self.bot.get_command(record["command"])
            if command is None or command.cog is None:
                data["No Cog"].add(record)
            else:
                data[command.cog.qualified_name].add(record)

        table = formatting.TabularData()
        table.set_columns(["Cog", "Success", "Failed", "Total"])
        data = sorted(
            [(cog, e.success, e.failed, e.total) for cog, e in data.items()],
            key=lambda t: t[-1],
            reverse=True,
        )

        table.add_rows(data)
        render = table.render()
        await ctx.safe_send(f"```\n{render}\n```")

    @commands.command(hidden=True, brief="Bot health monitoring tools.")
    @commands.is_owner()
    async def bothealth(self, ctx):
        """Various bot health monitoring tools."""

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
        await ctx.send(reference=self.bot.rep_ref(ctx), embed=embed)

    @commands.command(
        hidden=True, aliases=["perf", "elapsed"], brief="Time a command response."
    )
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
            return await ctx.send(
                reference=self.bot.rep_ref(ctx), content="No command found"
            )

        start = time.perf_counter()
        try:
            await new_ctx.command.invoke(new_ctx)
        except commands.CommandError:
            end = time.perf_counter()
            success = False
            try:
                await ctx.send(
                    reference=self.bot.rep_ref(ctx),
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

        await ctx.send(
            reference=self.bot.rep_ref(ctx),
            content=f"{emote} `{(end - start) * 1000:.2f}ms`",
        )

    @commands.command(aliases=["github"], brief="Update to and from github repo.")
    async def git(self, ctx, subcommand):
        """Updates from git."""
        if subcommand is None:
            return await ctx.send_help(str(ctx.command))

        url = self.bot.constants.github

        # Let's find out if we *have* git first
        if os.name == "nt":
            # Check for git
            command = "where"
        else:
            command = "which"
        try:
            p = subprocess.run(
                command + " git",
                shell=True,
                check=True,
                stderr=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
            )
            git_location = p.stdout.decode("utf-8").split("\n")[0].split("\r")[0]
        except:
            git_location = None

        if not git_location:
            await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"{self.bot.emote_dict['error']} Git not found.",
            )
            return
        # Try to update
        message = await ctx.send(
            reference=self.bot.rep_ref(ctx),
            content=f"{self.bot.emote_dict['loading']} **Updating...**",
        )
        try:
            u = subprocess.Popen(
                [git_location, subcommand, url],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            out, err = u.communicate()
            msg = "```\n"
            if len(out.decode("utf-8")):
                msg += out.decode("utf-8").replace("`", "\`") + "\n"
            if len(err.decode("utf-8")):
                msg += err.decode("utf-8").replace("`", "\`") + "\n"
            msg += "```"
            await ctx.send(msg)
            await message.edit(
                content=f"{self.bot.emote_dict['success']} **Completed.**"
            )
        except:
            await message.edit(
                content=f"{self.bot.emote_dict['failed']} Git not installed."
            )
            return

    @commands.command(hidden=True, brief="Run a command as another user.")
    async def sudo(
        self,
        ctx,
        channel: typing.Optional[converters.GlobalChannel],
        who: typing.Union[discord.Member, discord.User],
        *,
        command: str,
    ):
        """Run a command as another user optionally in another channel."""
        msg = copy.copy(ctx.message)
        channel = channel or ctx.channel
        msg.channel = channel
        msg.author = who
        msg.content = ctx.prefix + command
        new_ctx = await self.bot.get_context(msg, cls=type(ctx))
        # new_ctx._db = ctx._db
        await self.bot.invoke(new_ctx)


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
