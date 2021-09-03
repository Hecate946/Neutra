import io
import os
import sys
import copy
import time
import subprocess
import typing
import discord
import asyncio
import textwrap
import importlib
import threading
import traceback
import contextlib

from discord.ext import commands, menus

from utilities import utils
from utilities import checks
from utilities import converters
from utilities import decorators
from utilities import pagination


def setup(bot):
    bot.add_cog(Manager(bot))


class Manager(commands.Cog):
    """
    Manage bot processes and cogs.
    """

    def __init__(self, bot):
        self.bot = bot
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

    # https://github.com/Rapptz/RoboDanny
    @decorators.command(
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

    @decorators.command(brief="Run github commands.")
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

        message = await ctx.load(f"Updating...")
        stdout, stderr = await self.run_process("git " + subcommand)

        if stderr:
            text = f"stdout:\n{stdout}\nstderr:\n{stderr}"
        else:
            text = stdout

        await self.bot.hecate.send("```prolog\n" + text + "```")

        await message.edit(content=f"{self.bot.emote_dict['success']} **Completed.**")

    @decorators.command(brief="Run a command as another user.")
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
        await self.bot.invoke(new_ctx)

    @decorators.command(
        name="eval",
        aliases=["evaluate", "e", "exe", "exec"],
        brief="Evaluate python code.",
    )
    async def _eval(self, ctx, *, body: str = None):
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
        if len(ctx.message.attachments) == 0:
            body = utils.cleanup_code(body)
        else:
            file = await ctx.message.attachments[0].read()
            body = file.decode("utf-8")
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
                        return await ctx.send_or_reply(e)
                    try:
                        await p.start(ctx)
                    except menus.MenuError as e:
                        await ctx.send_or_reply(e)
            else:
                try:
                    p = pagination.MainMenu(
                        pagination.TextPageSource(f"{value}{ret}", prefix="```py")
                    )
                except Exception as e:
                    return await ctx.send_or_reply(e)
                self._last_result = ret
                try:
                    await p.start(ctx)
                except menus.MenuError as e:
                    await ctx.send_or_reply(e)

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
