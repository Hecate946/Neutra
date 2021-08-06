import io
import os
import sys
import time
import codecs
import psutil
import struct
import asyncio
import discord
import inspect
import pathlib
import platform
import statistics
import subprocess
import collections

from datetime import datetime
from discord import __version__ as dv
from discord.ext import commands, menus
from PIL import Image, ImageDraw, ImageFont

from utilities import utils
from utilities import checks
from utilities import converters
from utilities import decorators
from utilities import pagination


def setup(bot):
    bot.add_cog(Info(bot))


class Info(commands.Cog):
    """
    Module for bot information.
    """

    def __init__(self, bot):
        self.bot = bot
        self.socket_event_total = 0
        self.process = psutil.Process(os.getpid())
        self.socket_since = discord.utils.utcnow()
        self.message_latencies = collections.deque(maxlen=500)

    #####################
    ## Event Listeners ##
    #####################

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_message(self, message):
        now = discord.utils.utcnow()
        self.message_latencies.append((now, now - message.created_at))

    @commands.Cog.listener()  # Update our socket counters
    async def on_socket_response(self, msg: dict):
        """When a websocket event is received, increase our counters."""
        if event_type := msg.get("t"):
            self.socket_event_total += 1
            self.bot.socket_events[event_type] += 1

    #############
    ## Helpers ##
    #############

    async def total_global_commands(self):
        query = """SELECT COUNT(*) FROM commands"""
        value = await self.bot.cxn.fetchval(query)
        return value

    async def total_global_messages(self):
        query = """SELECT COUNT(*) FROM messages"""
        value = await self.bot.cxn.fetchval(query)
        return value

    async def get_version(self):
        query = """
                SELECT version
                FROM config
                WHERE client_id = $1;
                """
        v = await self.bot.cxn.fetchval(query, self.bot.user.id)
        version = ".".join(str(round(v, 1)).replace(".", ""))
        return version

    ##############
    ## Commands ##
    ##############

    @decorators.command(
        aliases=["info", "bot", "botstats", "botinfo", "ab"],
        brief="Display information about the bot.",
        implemented="2021-03-15 22:27:29.973811",
        updated="2021-05-06 00:06:19.096095",
        examples="""
                {0}about
                {0}bot
                {0}botinfo
                {0}botstats
                {0}info
                """,
    )
    @checks.bot_has_perms(embed_links=True)
    @checks.cooldown()  # Cooldown default (3, 10)
    async def about(self, ctx):
        """
        Usage: {0}about
        Aliases: {0}info, {0}bot, {0}botstats, {0}botinfo, {0}ab
        Output: Version info and bot stats
        """
        msg = await ctx.load("Collecting Bot Info...")
        total_members = sum(1 for x in self.bot.get_all_members())
        voice_channels = []
        text_channels = []
        for guild in self.bot.guilds:
            voice_channels.extend(guild.voice_channels)
            text_channels.extend(guild.text_channels)

        text = len(text_channels)
        voice = len(voice_channels)

        ram_usage = self.process.memory_full_info().rss / 1024 ** 2

        embed = discord.Embed(colour=self.bot.constants.embed)
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.add_field(
            name="Last Boot",
            value=str(
                utils.timeago(discord.utils.utcnow() - self.bot.uptime)
            ).capitalize(),
        )
        embed.add_field(
            name=f"Developer{'' if len(self.bot.constants.owners) == 1 else 's'}",
            value=",\n ".join(
                [str(self.bot.get_user(x)) for x in self.bot.constants.owners]
            ),
        )
        embed.add_field(
            name="Python Version", value=f"{platform.python_version()}", inline=True
        )
        embed.add_field(name="Library", value="Discord.py", inline=True)
        embed.add_field(name="API Version", value=f"{dv}", inline=True)
        embed.add_field(
            name="Command Count",
            value=len([x.name for x in self.bot.commands if not x.hidden]),
        )
        embed.add_field(
            name="Server Count", value=f"{len(ctx.bot.guilds):,}", inline=True
        )
        embed.add_field(
            name="Channel Count",
            value=f"""{self.bot.emote_dict['textchannel']} {text:,}\t\t{self.bot.emote_dict['voicechannel']} {voice:,}""",
        )
        embed.add_field(name="Member Count", value=f"{total_members:,}", inline=True)
        embed.add_field(
            name="Commands Run",
            value=f"{await self.total_global_commands():,}",
        )
        embed.add_field(
            name="Messages Seen",
            value=f"{await self.total_global_messages():,}",
        )
        embed.add_field(name="RAM Usage", value=f"{ram_usage:.2f} MB")

        await msg.edit(
            content=f"{self.bot.emote_dict['robot']} About **{ctx.bot.user}** | **{await self.get_version()}**",
            embed=embed,
        )

    @decorators.command(
        aliases=["averageping", "averagelatency", "averagelat"],
        brief="View the average message latency.",
        implemented="2021-05-10 22:39:37.374649",
        updated="2021-05-10 22:39:37.374649",
        examples="""
                {0}avgping
                {0}averagelat
                {0}averageping
                {0}averagelatency
                """,
    )
    @checks.cooldown()  # Cooldown default (3, 10)
    async def avgping(self, ctx):
        """
        Usage: {0}avgping
        Aliases:
            {0}averageping
            {0}avglat
            {0}avglatency
        Output:
            Shows the average message latency
            over the past 500 messages sent.
        """
        await ctx.send_or_reply(
            f"{self.bot.emote_dict['stopwatch']} "
            + "`{:.2f}ms`".format(
                1000
                * statistics.mean(
                    lat.total_seconds() for ts, lat in self.message_latencies
                )
            )
        )

    @decorators.command(
        aliases=["badmins"],
        brief="Show the bot's admins.",
        implemented="2021-04-02 21:37:49.068681",
        updated="2021-05-05 19:08:47.761913",
    )
    @checks.cooldown()  # Cooldown default (3, 10)
    @checks.bot_has_perms(embed_links=True)
    async def botadmins(self, ctx):
        """
        Usage: {0}botadmins
        Alias: {0}badmins
        Output:
            An embed of all the current bot admins
        """
        our_list = []
        for user_id in self.bot.constants.admins:
            user = self.bot.get_user(user_id)
            our_list.append({"name": f"**{str(user)}**", "value": f"ID: `{user.id}`"})
        p = pagination.MainMenu(
            pagination.FieldPageSource(
                entries=[
                    ("{}. {}".format(y + 1, x["name"]), x["value"])
                    for y, x in enumerate(our_list)
                ],
                title="My Admins ({:,} total)".format(len(self.bot.constants.admins)),
                per_page=15,
            )
        )

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @decorators.command(
        aliases=["owners"],
        brief="Show the bot's owners.",
        implemented="2021-04-12 06:23:15.545363",
        updated="2021-05-05 19:08:47.761913",
        examples="""
                {0}owners
                {0}botowners
                """,
    )
    @checks.bot_has_perms(embed_links=True)
    @checks.cooldown()  # Cooldown default (3, 10)
    async def botowners(self, ctx):
        """
        Usage: {0}botowners
        Alias: {0}owners
        Output:
            An embed of the bot's owners
        """
        our_list = []
        for user_id in self.bot.constants.owners:
            user = self.bot.get_user(user_id)
            our_list.append({"name": f"**{str(user)}**", "value": f"ID: `{user.id}`"})
        p = pagination.MainMenu(
            pagination.FieldPageSource(
                entries=[
                    ("{}. {}".format(y + 1, x["name"]), x["value"])
                    for y, x in enumerate(our_list)
                ],
                title="My Owners ({:,} total)".format(len(self.bot.constants.owners)),
                per_page=15,
            )
        )
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @decorators.command(
        aliases=["reportbug", "reportissue", "issuereport"],
        brief="Send a bugreport to the developer.",
        implemented="2021-03-26 19:10:10.345853",
        examples="""
                {0}bugreport Hi! I found an issue when running the avgping command.
                            (please be specific and feel free to include images)
                 """,
    )
    @checks.cooldown(2, 60)
    async def bugreport(self, ctx, *, bug):
        """
        Usage:    {0}bugreport <report>
        Aliases:  {0}issuereport, {0}reportbug, {0}reportissue
        Examples: {0}bugreport Hello! I found a bug with this command...
        Output:   Confirmation that your bug report has been sent.
        Notes:
            Do not hesitate to use this command,
            but please be very specific when describing the bug so
            that the developer may easily see the issue and
            correct it as soon as possible.
        """
        author = ctx.author
        if ctx.guild:
            server = ctx.guild
            source = "server **{}** ({})".format(server.name, server.id)
        else:
            source = "a direct message"
        sender = f"**{author}** ({author.id}) sent you a bug report from {source}:\n\n"
        message = sender + bug
        try:
            await self.bot.hecate.send(message, files=ctx.message.attachments)
        except discord.errors.InvalidArgument:
            await ctx.send_or_reply(
                "I cannot send your bug report, I'm unable to find my owner."
            )
        except discord.errors.HTTPException:
            await ctx.fail("Your bug report is too long.")
        except Exception:
            await ctx.fail("I'm currently unable to deliver your bug report.")
        else:
            if ctx.guild:
                if ctx.channel.permissions_for(ctx.guild.me).add_reactions:
                    await ctx.react(self.bot.emote_dict["letter"])
            else:
                await ctx.react(self.bot.emote_dict["letter"])
            await ctx.success("Your bug report has been sent.")

    @decorators.command(
        aliases=["updates"],
        brief="Show my changelog.",
        implemented="2021-04-18 04:38:20.652565",
        updated="2021-06-24 17:41:39.374116",
        examples="""
                {0}changelog
                {0}updates
                 """,
    )
    @checks.cooldown(3, 20)
    @checks.bot_has_perms(add_reactions=True, external_emojis=True)
    async def changelog(self, ctx):
        """
        Usage: {0}changelog
        Alias: {0}updates
        Output: My changelog
        """
        with open("./data/txts/changelog.txt", "r", encoding="utf-8") as fp:
            changelog = fp.read()
        await ctx.send_or_reply(
            f"**{self.bot.emote_dict['github']} {self.bot.user.name}'s Changelog**"
        )
        p = pagination.MainMenu(
            pagination.TextPageSource(changelog, prefix="```prolog")
        )
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @decorators.command(
        aliases=["listcogs"],
        brief="List all my cogs in an embed.",
        implemented="2021-05-05 19:01:15.387930",
        updated="2021-05-05 19:01:15.387930",
        examples="""
                {0}cogs
                {0}listcogs
                 """,
    )
    @checks.cooldown()
    @checks.bot_has_perms(embed_links=True)
    async def cogs(self, ctx):
        """
        Usage: {0}cogs
        Output: An embed of all my current cogs
        """
        cog_list = []
        for cog in os.listdir("./cogs"):
            if cog.endswith(".py"):
                cog_list.append(f"{cog}")
        if len(cog_list):
            cog_list = sorted(cog_list)

        embed = discord.Embed(
            title="Extensions",
            description="```css\n" + "\n".join(cog_list) + "```",
            color=self.bot.constants.embed,
        )
        await ctx.send_or_reply(embed=embed)

    @decorators.command(
        aliases=["vps"],
        brief="Show the bot's host environment.",
        implemented="2021-03-14 17:21:40.041524",
        updated="2021-06-24 17:51:56.480886",
        examples="""
                {0}hostinfo
                {0}vps
                 """,
    )
    @checks.cooldown(2, 20)
    async def hostinfo(self, ctx):
        """
        Usage: {0}hostinfo
        Output: Detailed information on the bot's host environment
        """
        message = await ctx.load("Collecting Information...")

        with self.process.oneshot():
            process = self.process.name
        swap = psutil.swap_memory()

        process_name = self.process.name()
        pid = self.process.ppid()
        swap_usage = "{0:.1f}".format(((swap[1] / 1024) / 1024) / 1024)
        swap_total = "{0:.1f}".format(((swap[0] / 1024) / 1024) / 1024)
        swap_perc = swap[3]
        cpu_cores = psutil.cpu_count(logical=False)
        cpu_thread = psutil.cpu_count()
        cpu_usage = psutil.cpu_percent(interval=1)
        mem_stats = psutil.virtual_memory()
        mem_perc = mem_stats.percent
        mem_used = mem_stats.used
        mem_total = mem_stats.total
        mem_used_GB = "{0:.1f}".format(((mem_used / 1024) / 1024) / 1024)
        mem_total_GB = "{0:.1f}".format(((mem_total / 1024) / 1024) / 1024)
        current_OS = platform.platform()
        system = platform.system()
        release = platform.release()
        processor = platform.processor()
        bot_owner = self.bot.hecate
        bot_name = self.bot.user.name
        current_time = int(time.time())
        time_string = utils.time_between(self.bot.starttime, current_time)
        python_major = sys.version_info.major
        python_minor = sys.version_info.minor
        python_micro = sys.version_info.micro
        python_release = sys.version_info.releaselevel
        py_bit = struct.calcsize("P") * 8
        process = subprocess.Popen(
            ["git", "rev-parse", "--short", "HEAD"], shell=False, stdout=subprocess.PIPE
        )
        git_head_hash = process.communicate()[0].strip()

        thread_string = "thread"
        if not cpu_thread == 1:
            thread_string += "s"

        msg = "***{}'s*** ***Home:***\n".format(bot_name)
        msg += "```fix\n"
        msg += "OS       : {}\n".format(current_OS)
        msg += "Owner    : {}\n".format(bot_owner)
        msg += "Client   : {}\n".format(bot_name)
        msg += "Commit   : {}\n".format(git_head_hash.decode("utf-8"))
        msg += "Uptime   : {}\n".format(time_string)
        msg += "Process  : {}\n".format(process_name)
        msg += "PID      : {}\n".format(pid)
        msg += "Hostname : {}\n".format(platform.node())
        msg += "Language : Python {}.{}.{} {} ({} bit)\n".format(
            python_major, python_minor, python_micro, python_release, py_bit
        )
        msg += "Processor: {}\n".format(processor)
        msg += "System   : {}\n".format(system)
        msg += "Release  : {}\n".format(release)
        msg += "CPU Core : {} Threads\n\n".format(cpu_cores)
        msg += (
            utils.center(
                "{}% of {} {}".format(cpu_usage, cpu_thread, thread_string), "CPU"
            )
            + "\n"
        )
        msg += utils.make_bar(int(round(cpu_usage))) + "\n\n"
        msg += (
            utils.center(
                "{} ({}%) of {}GB used".format(mem_used_GB, mem_perc, mem_total_GB),
                "RAM",
            )
            + "\n"
        )
        msg += utils.make_bar(int(round(mem_perc))) + "\n\n"
        msg += (
            utils.center(
                "{} ({}%) of {}GB used".format(swap_usage, swap_perc, swap_total),
                "Swap",
            )
            + "\n"
        )
        msg += utils.make_bar(int(round(swap_perc))) + "\n"
        msg += "```"

        await message.edit(content=msg)

    @decorators.command(
        brief="Invite me to your server!",
        aliases=["botinvite", "bi"],
        implemented="2021-05-05 18:05:30.156694",
        updated="2021-05-05 18:05:30.156694",
        examples="""
                {0}invite
                {0}botinvite
                {0}bi
                 """,
    )
    @checks.cooldown()
    async def invite(self, ctx):
        """
        Usage: {0}invite
        Aliases:
            {0}bi, {0}botinvite
        Output:
            A selection of invite links
            to invite me to your server
        """
        admin_inv = discord.utils.oauth_url(
            self.bot.user.id, permissions=discord.Permissions(8)
        )
        default_inv = discord.utils.oauth_url(self.bot.user.id)

        reco = discord.ui.Button(label="Recommended", url=self.bot.oauth)
        admin = discord.ui.Button(label="Administrator", url=admin_inv)
        default = discord.ui.Button(label="Default", url=default_inv)

        view = discord.ui.View()
        view.add_item(reco)
        view.add_item(admin)
        view.add_item(default)

        await ctx.rep_or_ref(
            "Select an invite link from the options below to invite me to your server.",
            view=view,
        )

    @decorators.command(
        aliases=["socketstats"],
        brief="Show global bot socket stats.",
        implemented="2021-03-18 17:55:01.726405",
        updated="2021-05-07 18:00:54.076428",
        examples="""
                {0}socket
                {0}socketstats
                """,
    )
    @checks.cooldown()
    @checks.bot_has_perms(add_reactions=True, external_emojis=True)
    async def socket(self, ctx):
        """
        Usage: {0}socket
        Alias: {0}socketstats
        Output:
            Fetch information on the socket
            events received from Discord.
        """
        running_s = (discord.utils.utcnow() - self.socket_since).total_seconds()

        per_s = self.socket_event_total / running_s

        width = len(max(self.bot.socket_events, key=lambda x: len(str(x))))

        line = "\n".join(
            "{0:<{1}} : {2:>{3}}".format(
                str(event_type), width, count, len(max(str(count)))
            )
            for event_type, count in self.bot.socket_events.most_common()
        )

        header = (
            "**Receiving {0:0.2f} socket events per second** | **Total: {1}**\n".format(
                per_s, self.socket_event_total
            )
        )

        m = pagination.MainMenu(
            pagination.TextPageSource(line, prefix="```yaml", max_size=500)
        )
        await ctx.send_or_reply(header)
        try:

            await m.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @decorators.command(
        brief="Show reply latencies.",
        implemented="2021-05-10 23:53:06.937010",
        updated="2021-05-10 23:53:06.937010",
    )
    @checks.cooldown()
    async def replytime(self, ctx):
        """
        Usage: {0}replytime
        Output:
            Shows 3 times showing the
            discrepancy between timestamps.
        """
        recv_time = ctx.message.created_at
        msg_content = "."

        task = asyncio.ensure_future(
            self.bot.wait_for(
                "message",
                timeout=15,
                check=lambda m: (m.author == ctx.bot.user and m.content == msg_content),
            )
        )
        now = discord.utils.utcnow()
        sent_message = await ctx.send_or_reply(msg_content)
        await task
        rtt_time = discord.utils.utcnow()
        content = "```prolog\n"
        content += "Client Timestamp - Discord  Timestamp: {:.2f}ms\n"
        content += "Posted Timestamp - Response Timestamp: {:.2f}ms\n"
        content += "Sent   Timestamp - Received Timestamp: {:.2f}ms\n"
        content += "```"
        await sent_message.edit(
            content=content.format(
                (now - recv_time).total_seconds() * 1000,
                (sent_message.created_at - recv_time).total_seconds() * 1000,
                (rtt_time - now).total_seconds() * 1000,
            )
        )

    @decorators.command(
        brief="Send a suggestion to the developer.", aliases=["suggestion"]
    )
    @checks.cooldown(2, 60)
    async def suggest(self, ctx, *, suggestion: str = None):
        """
        Usage:    {0}suggest <report>
        Alias:  {0}suggestion
        Examples: {0}suggest Hello! You should add this feature...
        Output:   Confirmation that your suggestion has been sent.
        Notes:
            Do not hesitate to use this command,
            your feedback is valued immensly.
            However, please be detailed and concise.
        """
        if suggestion is None:
            return await ctx.send_or_reply(
                content=f"Usage `{ctx.clean_prefix}suggest <suggestion>`",
            )
        author = ctx.author
        if ctx.guild:
            server = ctx.guild
            source = "server **{}** ({})".format(server.name, server.id)
        else:
            source = "a direct message"
        sender = "**{}** ({}) sent you a suggestion from {}:\n\n".format(
            author, author.id, source
        )
        message = sender + suggestion
        try:
            await self.bot.hecate.send(message, files=ctx.message.attachments)
        except discord.errors.InvalidArgument:
            await ctx.fail("I cannot send your message.")
        except discord.errors.HTTPException:
            await ctx.fail("Your message is too long.")
        except Exception:
            await ctx.fail("I'm currently unable to deliver your message.")
        else:
            if ctx.guild:
                if ctx.channel.permissions_for(ctx.guild.me):
                    await ctx.react(self.bot.emote_dict["letter"])
            else:
                await ctx.react(self.bot.emote_dict["letter"])
            await ctx.success(
                content="Your message has been sent.",
            )

    @decorators.command(brief="Show the bot's uptime.", aliases=["runtime"])
    async def uptime(self, ctx):
        """
        Usage: {0}uptime
        Alias: {0}runtime
        Output: Time since last boot.
        """
        uptime = utils.time_between(self.bot.starttime, int(time.time()))
        await ctx.send_or_reply(
            f"{self.bot.emote_dict['stopwatch']} I've been running for `{uptime}`"
        )

    @decorators.command(
        brief="Test the bot's response latency.",
        aliases=["latency", "response"],
    )
    async def ping(self, ctx):
        """
        Usage: {0}ping
        Aliases: {0}latency, {0}response
        Output: Bot latency statistics.
        Notes:
            Use {0}speed and the bot will attempt
            to run an internet speedtest. May fail.
        """
        async with ctx.channel.typing():
            start = time.time()
            message = await ctx.load("Calculating Latency...")
            end = time.time()

            db_start = time.time()
            await self.bot.cxn.fetch("SELECT 1;")
            elapsed = time.time() - db_start

            p = str(round((end - start) * 1000, 2))
            q = str(round(self.bot.latency * 1000, 2))
            v = str(round((elapsed) * 1000, 2))

            width = max(len(p), len(q), len(v))

            msg = "**Results:**\n"
            msg += "```yaml\n"
            msg += "Latency : {} ms\n".format(q.ljust(width, " "))
            msg += "Response: {} ms\n".format(p.ljust(width, " "))
            msg += "Database: {} ms\n".format(v.ljust(width, " "))
            msg += "```"
        await message.edit(content=msg)

    @decorators.command(
        aliases=["purpose"],
        brief="Show some info on the bot's purpose.",
        implemented="2021-03-15 19:38:03.463155",
        updated="2021-05-06 01:12:57.626085",
    )
    @checks.bot_has_perms(embed_links=True)
    @checks.cooldown()
    async def overview(self, ctx):
        """
        Usage:  {0}overview
        Alias:  {0}purpose
        Output: Me and my purpose
        """
        owner, command_list, category_list = self.bot.public_stats()
        with open("./data/txts/overview.txt", "r", encoding="utf-8") as fp:
            overview = fp.read()
        embed = discord.Embed(
            description=overview.format(
                self.bot.user.name, len(command_list), len(category_list)
            ),
            color=self.bot.constants.embed,
        )
        embed.set_author(name=owner, icon_url=owner.avatar.url)
        await ctx.send_or_reply(embed=embed)

    @decorators.command(brief="Display the source code.", aliases=["sourcecode", "src"])
    async def source(self, ctx, *, command: str = None):
        """
        Usage: {0}source [command]
        Alias: {0}sourcecode, {0}src
        Notes:
            If no command is specified, shows full repository
        """
        source_url = "https://github.com/Hecate946/Neutra"
        branch = "main"
        if command is None:
            return await ctx.send_or_reply("<" + source_url + ">")

        else:
            obj = self.bot.get_command(command.replace(".", " "))
            if obj is None:
                return await ctx.send_or_reply(
                    f'{self.bot.emote_dict["failed"]} Command `{command}` does not exist.'
                )
            # Show source for all commands so comment this out.
            # elif obj.hidden:
            #     return await ctx.send_or_reply(
            #         f'{self.bot.emote_dict["failed"]} Command `{command}` does not exist.'
            #     )

            src = obj.callback.__code__
            module = obj.callback.__module__
            filename = src.co_filename

        lines, firstlineno = inspect.getsourcelines(src)
        if not module.startswith("discord"):
            # not a built-in command
            location = os.path.relpath(filename).replace("\\", "/")
        else:
            location = module.replace(".", "/") + ".py"
            source_url = "https://github.com/Hecate946/Neutra"
            branch = "main"

        final_url = f"<{source_url}/blob/{branch}/{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}>"
        msg = f"**__My source {'' if command is None else f'for {command}'} is located at:__**\n\n{final_url}"
        await ctx.send_or_reply(msg)

    @decorators.command(
        brief="Show your support by voting for me!",
        implemented="2021-06-10 07:29:06.990221",
        updated="2021-06-10 07:29:06.990221",
    )
    async def vote(self, ctx):
        """
        Usage: {0}vote
        Output:
            A link to top.gg where you can
            vote to support me.
        """
        view = discord.ui.View()
        item = discord.ui.Button(
            label="Vote for me!",
            url="https://top.gg/bot/810377376269205546/vote",
        )
        view.add_item(item=item)
        await ctx.rep_or_ref(
            "Thanks for showing interest in supporting me! Click the button below to vote for me on top.gg.",
            view=view,
        )

    @decorators.command(
        aliases=["sup", "assistance", "assist"],
        brief="Join my support server!",
        implemented="2021-04-12 23:31:35.165019",
        updated="2021-05-06 01:24:02.569676",
    )
    async def support(self, ctx):
        """
        Usage: {0}support
        Aliases: {0}sup, {0}assist, {0}assistance
        Output: An invite link to my support server
        """
        await ctx.rep_or_ref(self.bot.constants.support)

    @decorators.command(
        aliases=["userstats", "usercount"],
        brief="Show users I'm connected to.",
        implemented="2021-03-23 04:20:58.938991",
        updated="2021-05-06 01:30:32.347076",
    )
    @checks.bot_has_perms(embed_links=True)
    @checks.cooldown()
    async def users(self, ctx):
        """
        Usage: {0}users
        Aliases: {0}userstats, {0}usercount
        Output:
            Shows users and bots I'm connected to and
            percentages of unique and online members.
        """
        msg = await ctx.load(f"Collecting User Stats...")
        users = [x for x in self.bot.get_all_members() if not x.bot]
        users_online = [x for x in users if x.status != discord.Status.offline]
        unique_users = set([x.id for x in users])
        bots = [x for x in self.bot.get_all_members() if x.bot]
        bots_online = [x for x in bots if x.status != discord.Status.offline]
        unique_bots = set([x.id for x in bots])
        e = discord.Embed(title="User Stats", color=self.bot.constants.embed)
        e.add_field(
            name="Humans",
            value="{:,}/{:,} online ({:,g}%) - {:,} unique ({:,g}%)".format(
                len(users_online),
                len(users),
                round((len(users_online) / len(users)) * 100, 2),
                len(unique_users),
                round((len(unique_users) / len(users)) * 100, 2),
            ),
            inline=False,
        )
        e.add_field(
            name="Bots",
            value="{:,}/{:,} online ({:,g}%) - {:,} unique ({:,g}%)".format(
                len(bots_online),
                len(bots),
                round((len(bots_online) / len(bots)) * 100, 2),
                len(unique_bots),
                round(len(unique_bots) / len(bots) * 100, 2),
            ),
            inline=False,
        )
        e.add_field(
            name="Total",
            value="{:,}/{:,} online ({:,g}%)".format(
                len(users_online) + len(bots_online),
                len(users) + len(bots),
                round(
                    ((len(users_online) + len(bots_online)) / (len(users) + len(bots)))
                    * 100,
                    2,
                ),
            ),
            inline=False,
        )
        await msg.edit(content=None, embed=e)

    @decorators.command(
        aliases=["shared"],
        brief="Show servers shared with the bot.",
        implemented="2021-03-16 18:59:54.146823",
        updated="2021-05-06 01:30:32.347076",
    )
    @checks.cooldown()
    async def sharedservers(self, ctx, *, user: converters.DiscordUser = None):
        """
        Usage: {0}sharedservers [user]
        Alias: {0}shared
        Output:
            Counts the servers in common between
            the user passed and the bot.
        Notes:
            Will default to youself if no user is passed
        """

        if user is None:
            user = ctx.author

        if user.id == self.bot.user.id:
            return await ctx.send_or_reply(
                "I'm on **{:,}** server{}. ".format(
                    len(self.bot.guilds), "" if len(self.bot.guilds) == 1 else "s"
                )
            )

        count = 0
        for guild in self.bot.guilds:
            for mem in guild.members:
                if mem.id == user.id:
                    count += 1
        if ctx.author.id == user.id:
            targ = "You share"
        else:
            targ = "**{}** shares".format(user.display_name)

        await ctx.send_or_reply(
            "{} **{:,}** server{} with me.".format(
                targ, count, "" if count == 1 else "s"
            )
        )

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

        return [
            str(output.decode()).replace("[?25l[?7l", "").replace("[?25h[?7h", "")
            for output in result
        ]

    @decorators.command(aliases=["nf"], brief="Run the neofetch command.")
    @checks.cooldown()
    async def neofetch(self, ctx):
        """
        Usage: {0}neofetch
        Alias: {0}nf
        Output: Some stats on the bot's server
        """
        async with ctx.typing():
            stdout, stderr = await self.run_process("neofetch|sed 's/\x1B[[0-9;]*m//g'")

        if stderr:
            text = f"stdout:\n{stdout}\nstderr:\n{stderr}"
        else:
            text = stdout

        text = text[:-3]

        pages = pagination.MainMenu(
            pagination.TextPageSource(text, prefix="```autohotkey")
        )
        try:
            await pages.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(str(e))

    @decorators.command(
        aliases=["code", "cloc", "codeinfo"],
        brief="Show sourcecode statistics.",
        implemented="2021-03-22 08:19:35.838365",
        updated="2021-05-06 01:21:46.580294",
    )
    @checks.bot_has_perms(embed_links=True)
    @checks.cooldown()
    async def lines(self, ctx):
        """
        Usage: {0}lines
        Aliases: {0}cloc, {0}code, {0}codeinfo
        Output:
            Gives the linecount, characters, imports, functions,
            classes, comments, and files within the source code.
        """
        async with ctx.channel.typing():
            msg = "```fix\n"
            lines = 0
            file_amount = 0
            comments = 0
            funcs = 0
            classes = 0
            chars = 0
            imports = 0
            exclude = set([".testervenv", ".venv", ".git", "__pycache__", ".vscode"])
            for path, subdirs, files in os.walk("."):
                [subdirs.remove(d) for d in list(subdirs) if d in exclude]
                for name in files:
                    if name.endswith(".py"):
                        file_amount += 1
                        with codecs.open(
                            "./" + str(pathlib.PurePath(path, name)), "r", "utf-8"
                        ) as f:
                            for l in f:
                                chars += len(l.strip())
                                if l.strip().startswith("#"):
                                    comments += 1
                                elif len(l.strip()) == 0:
                                    pass
                                else:
                                    lines += 1
                                    if l.strip().startswith(
                                        "def"
                                    ) or l.strip().startswith("async"):
                                        funcs += 1
                                    elif l.strip().startswith("class"):
                                        classes += 1
                                    elif l.strip().startswith(
                                        "import"
                                    ) or l.strip().startswith("from"):
                                        imports += 1
            width = max(
                len(f"{lines:,}"),
                len(f"{file_amount:,}"),
                len(f"{chars:,}"),
                len(f"{imports:,}"),
                len(f"{classes:,}"),
                len(f"{funcs:,}"),
                len(f"{comments:,}"),
            )
            files = "{:,}".format(file_amount)
            lines = "{:,}".format(lines)
            chars = "{:,}".format(chars)
            imports = "{:,}".format(imports)
            classes = "{:,}".format(classes)
            funcs = "{:,}".format(funcs)
            comments = "{:,}".format(comments)
            msg += f"{files.ljust(width)} Files\n"
            msg += f"{lines.ljust(width)} Lines\n"
            msg += f"{chars.ljust(width)} Characters\n"
            msg += f"{imports.ljust(width)} Imports\n"
            msg += f"{classes.ljust(width)} Classes\n"
            msg += f"{funcs.ljust(width)} Functions\n"
            msg += f"{comments.ljust(width)} Comments"
            msg += "```"
            em = discord.Embed(color=self.bot.constants.embed)
            em.title = f"{self.bot.emote_dict['info']}  Source information"
            em.description = msg
            await ctx.send_or_reply(embed=em)

    @decorators.command(
        aliases=["policy"],
        brief="View the privacy policy.",
        implemented="2021-04-26 17:22:59.340513",
        updated="2021-05-05 22:15:27.364699",
    )
    @checks.cooldown()
    async def privacy(self, ctx):
        """
        Usage: {0}privacy
        Alias: {0}policy
        Output:
            Details on terms of use and privacy
            regarding the bot and its database.
        """
        with open("./data/txts/privacy.txt") as fp:
            privacy = fp.read()
        policy = f"```fix\n{privacy.format(self.bot.user, self.bot.user.id, ctx.clean_prefix)}```"
        await ctx.send_or_reply(
            f"{self.bot.emote_dict['privacy']} **{self.bot.user}'s Privacy Policy**{policy}"
        )

    @decorators.command(
        aliases=["percentuptime", "pieuptime", "pu"],
        brief="Show a graph of uptime stats",
        implemented="2021-04-28 00:34:35.847886",
        updated="2021-05-25 19:14:05.652822",
    )
    @checks.bot_has_perms(attach_files=True, embed_links=True)
    @checks.cooldown()
    async def uptimeinfo(self, ctx):
        """
        Usage: {0}uptimeinfo
        Aliases: {0}percentuptime, {0}pieuptime, {0}pu
        Output:
            Shows a pie-chart graph
            of bot uptime across all time
        """
        await ctx.trigger_typing()
        query = """
                SELECT runtime, starttime, last_run
                FROM config WHERE client_id = $1;
                """
        botstats = await self.bot.cxn.fetchrow(query, self.bot.user.id)
        unix_timestamp = time.time()
        current_uptime = unix_timestamp - self.bot.statustime
        uptime = current_uptime + botstats["runtime"]
        total = unix_timestamp - botstats["starttime"]

        raw_percent = uptime / total
        if raw_percent > 1:
            raw_percent = 1
        if raw_percent > 0.9:  # 90% uptime. Decent
            color = (109, 255, 72)  # Green
        elif 0.7 < raw_percent < 0.9:  # 70%-90% uptime meh.
            color = (226, 232, 19)  # Yellow
        else:  # Poor uptime
            color = (232, 44, 19)  # Red
        percent = f"{raw_percent:.2%}"
        em = discord.Embed(color=self.bot.constants.embed)
        img = Image.new("RGBA", (2500, 1024), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype("./data/assets/Helvetica.ttf", 100)
        shape = [(50, 0), (1050, 1000)]
        draw.arc(shape, start=360 * raw_percent, end=0, fill=(125, 135, 140), width=200)
        draw.arc(shape, start=0, end=360 * raw_percent, fill=(10, 24, 34), width=200)
        self.center_text(img, 1100, 1000, font, percent, color)
        font = ImageFont.truetype("./data/assets/Helvetica-Bold.ttf", 85)
        draw.text((1200, 0), "Uptime Tracking Since:", fill=(255, 255, 255), font=font)
        font = ImageFont.truetype("./data/assets/Helvetica.ttf", 68)
        draw.text(
            (1200, 100),
            utils.timeago(
                datetime.utcnow() - datetime.utcfromtimestamp(botstats["starttime"])
            ),
            fill=(255, 255, 255),
            font=font,
        )
        font = ImageFont.truetype("./data/assets/Helvetica-Bold.ttf", 85)
        draw.text((1200, 300), "Total Uptime (Hours):", fill=(255, 255, 255), font=font)
        font = ImageFont.truetype("./data/assets/Helvetica.ttf", 68)
        draw.text((1200, 400), f"{uptime/3600:.2f}", fill=(255, 255, 255), font=font)
        font = ImageFont.truetype("./data/assets/Helvetica-Bold.ttf", 85)
        draw.text((1200, 600), "Runtime Information:", fill=(255, 255, 255), font=font)
        font = ImageFont.truetype("./data/assets/Helvetica.ttf", 68)
        draw.text(
            (1200, 710),
            f"Current run: {current_uptime/3600:.2f} Hours",
            fill=(255, 255, 255),
            font=font,
        )
        draw.text(
            (1200, 810),
            f"Previous run: {botstats['last_run']/3600:.2f} Hours",
            fill=(255, 255, 255),
            font=font,
        )
        draw.text(
            (1200, 910),
            f"Last reboot: {utils.timeago(discord.utils.utcnow() - self.bot.uptime)}",
            fill=(255, 255, 255),
            font=font,
        )

        buffer = io.BytesIO()
        img.save(buffer, "png")  # 'save' function for PIL
        buffer.seek(0)
        dfile = discord.File(fp=buffer, filename="uptime.png")
        em.title = "Uptime Statistics"
        em.set_image(url="attachment://uptime.png")
        await ctx.send_or_reply(embed=em, file=dfile)

    def center_text(
        self, img, strip_width, strip_height, font, text, color=(255, 255, 255)
    ):
        draw = ImageDraw.Draw(img)
        text_width, text_height = draw.textsize(text, font)
        position = ((strip_width - text_width) / 2, (strip_height - text_height) / 2)
        draw.text(position, text, color, font=font)
        return img
