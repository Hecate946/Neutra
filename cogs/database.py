import io
import time
import asyncio
import asyncpg
import discord
import traceback
import subprocess

from discord.ext import commands

from utilities import utils
from utilities import checks
from utilities import decorators
from utilities import converters
from utilities import pagination
from utilities import formatting


async def setup(bot):
    await bot.add_cog(Database(bot))


class Database(commands.Cog):
    """
    Module for handling the database
    """

    def __init__(self, bot):
        self.bot = bot

    # Owner only cog.
    async def cog_check(self, ctx):
        return checks.is_owner(ctx)

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
        if await ctx.confirm("This action will restart my database."):

            members = [x for x in self.bot.get_all_members()]
            await self.bot.database.initialize(self.bot, members)
            await ctx.success("**Updated database**")

    @decorators.command(
        aliases=["drop"],
        brief="Discard the data on a server.",
    )
    async def discard(self, ctx, server: converters.DiscordGuild = None):
        """
        Usage: {0}discard
        Alias: {0}drop
        Permission: Bot owner
        Output:
            Runs a cleanup function that
            removes all data on the server.
        """
        if server is None:
            server = ctx.guild
        c = await ctx.confirm("This action will purge all this server's data.")
        if c:
            msg = await ctx.load("Recursively discarding all server data...")

            await self.bot.database.destroy_server(server.id)
            await msg.edit(
                content=f"**{self.bot.emote_dict['delete']} Successfully discarded all server data.**"
            )

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

    @decorators.group(brief="Show info on the database.", aliases=["pg"])
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
                results = await self.bot.cxn.fetch(query, self.bot.config.POSTGRES.name)
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
