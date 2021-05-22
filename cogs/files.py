import io
import os
import pytz
import typing
import discord

from datetime import datetime
from discord.ext import commands

from utilities import humantime
from utilities import utils
from utilities import checks
from utilities import converters
from utilities import decorators


def setup(bot):
    bot.add_cog(Files(bot))


class Files(commands.Cog):
    """
    Module for downloading files.
    """

    def __init__(self, bot):
        self.bot = bot

    def _get_help(self, command, max_len=0):
        # A helper method to return the command help - or a placeholder if none
        if max_len == 0:
            # Get the whole thing
            if command.help is None:
                return "No description..."
            else:
                return command.help
        else:
            if command.help is None:
                c_help = "No description..."
            else:
                c_help = command.help.split("\n")[0]
            return (c_help[: max_len - 3] + "...") if len(c_help) > max_len else c_help

    def _is_submodule(self, parent, child):
        return parent == child or child.startswith(parent + ".")

    @decorators.command(
        aliases=["txthelp", "helpfile"],
        brief="DMs you a file of commands.",
        implemented="2021-03-15 21:08:44.890889",
        updated="2021-05-06 15:48:48.484178",
    )
    async def dumphelp(self, ctx):
        """
        Usage: {0}dumphelp
        Aliases: {0}txthelp, {0}helpfile
        Output:
            DMs you a file with all my commands
            and their descriptions.
        Notes:
            If you have your DMs blocked, the bot
            will send the file to the channel
            where the the command was invoked.
        """
        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        help_file = "Help-{}.txt".format(timestamp)

        mess = await ctx.send_or_reply(
            content="Saving servers to **{}**...".format(help_file),
        )
        msg = ""
        prefix = ctx.prefix

        # Get and format the help
        for cog in sorted(self.bot.cogs):
            if cog.upper() in self.bot.cog_exceptions + self.bot.useless_cogs:
                continue
            cog_commands = sorted(
                self.bot.get_cog(cog).get_commands(), key=lambda x: x.name
            )
            cog_string = ""
            # Get the extension
            the_cog = self.bot.get_cog(cog)
            # Make sure there are non-hidden commands here
            visible = []
            for command in self.bot.get_cog(cog).get_commands():
                if not command.hidden:
                    visible.append(command)
            if not len(visible):
                # All hidden - skip
                continue
            cog_count = (
                "1 command" if len(visible) == 1 else "{} commands".format(len(visible))
            )
            for e in self.bot.extensions:
                b_ext = self.bot.extensions.get(e)
                if self._is_submodule(b_ext.__name__, the_cog.__module__):
                    # It's a submodule
                    cog_string += "{}{} Cog ({}) - {}.py Extension:\n".format(
                        "    ", cog, cog_count, e[5:]
                    )
                    break
            if cog_string == "":
                cog_string += "{}{} Cog ({}):\n".format("    ", cog, cog_count)
            for command in cog_commands:
                cog_string += "{}  {}\n".format(
                    "    ", prefix + command.name + " " + command.signature
                )
                cog_string += "\n{}  {}  {}\n\n".format(
                    "\t", " " * len(prefix), self._get_help(command, 80)
                )
            cog_string += "\n"
            msg += cog_string

        # Encode to binary
        # Trim the last 2 newlines
        msg = msg[:-2].encode("utf-8")
        data = io.BytesIO(msg)

        await mess.edit(content="Uploading `{}`...".format(help_file))
        try:
            await ctx.author.send(file=discord.File(data, filename=help_file))
        except Exception:
            await ctx.send_or_reply(
                file=discord.File(data, filename=help_file),
            )
            await mess.edit(
                content="{} Uploaded `{}`.".format(
                    self.bot.emote_dict["success"], help_file
                )
            )
            return
        await mess.edit(
            content="{} Uploaded `{}`.".format(
                self.bot.emote_dict["success"], help_file
            )
        )
        await mess.add_reaction(self.bot.emote_dict["letter"])

    @decorators.command(
        aliases=["dumpguilds", "txtguilds", "txtservers"],
        brief="DMs you a list of my servers.",
        hidden=True,
        implemented="2021-04-09 02:05:49.278468",
        updated="2021-05-06 15:57:20.290636",
    )
    @checks.is_bot_admin()
    async def dumpservers(self, ctx):
        """
        Usage: {0}dumpservers
        ALiases:
            {0}dumpguilds, {0]txtguilds, {0}txtservers
        Permission: Bot Admin
        Output:
            DMs you a file with all my servers,
            their member count, owners, and their IDs
        Notes:
            If you have your DMs blocked, the bot
            will send the file to the channel
            where the the command was invoked.
        """
        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        server_file = "Servers-{}.txt".format(timestamp)

        mess = await ctx.send_or_reply(
            content="Saving servers to **{}**...".format(server_file),
        )

        msg = ""
        for server in self.bot.guilds:
            msg += "Name:    " + server.name + "\n"
            msg += "ID:      " + str(server.id) + "\n"
            msg += "Owner:   " + str(server.owner) + "\n"
            msg += "Members: " + str(len(server.members)) + "\n"
            msg += "\n\n"

        data = io.BytesIO(msg.encode("utf-8"))

        await mess.edit(content="Uploading `{}`...".format(server_file))
        try:
            await ctx.author.send(file=discord.File(data, filename=server_file))
        except Exception:
            await ctx.send_or_reply(
                file=discord.File(data, filename=server_file),
            )
            await mess.edit(
                content="{} Uploaded `{}`.".format(
                    self.bot.emote_dict["success"], server_file
                )
            )
            return
        await mess.edit(
            content="{} Uploaded `{}`.".format(
                self.bot.emote_dict["success"], server_file
            )
        )
        await mess.add_reaction(self.bot.emote_dict["letter"])

    @decorators.command(
        aliases=["serversettings", "dumpserversettings"],
        brief="DMs you a file of server settings.",
        implemented="2021-03-29 21:22:04.309922",
        updated="2021-05-06 16:08:45.057353",
    )
    @commands.guild_only()
    @checks.has_perms(manage_guild=True)
    async def dumpsettings(self, ctx):
        """
        Usage: {0}dumpsettings
        Aliases:
            {0}serversettings, {0}dumpserversettings
        Permission: Manage Server
        Output:
            Sends a json file of server settings to your DMs.
        Notes:
            If you have your DMs blocked, the bot
            will send the file to the channel
            where the the command was invoked.
        """

        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        settings_file = "Settings-{}.json".format(timestamp)

        mess = await ctx.send_or_reply(
            content="Saving settings to **{}**...".format(settings_file),
        )

        settings = self.bot.server_settings[ctx.guild.id]

        utils.write_json(settings_file, settings)

        await mess.edit(content="Uploading `{}`...".format(settings_file))
        try:
            await ctx.author.send(
                file=discord.File(
                    settings_file, filename=settings_file.replace("json", "txt")
                )
            )
        except Exception:
            await ctx.send_or_reply(
                file=discord.File(
                    settings_file, filename=settings_file.replace("json", "txt")
                )
            )
            await mess.edit(
                content="{} Uploaded `{}`.".format(
                    self.bot.emote_dict["success"], settings_file
                )
            )
            os.remove(settings_file)
            return
        await mess.edit(
            content="{} Uploaded `{}`.".format(
                self.bot.emote_dict["success"], settings_file
            )
        )
        await mess.add_reaction(self.bot.emote_dict["letter"])
        os.remove(settings_file)

    @decorators.command(
        aliases=["txtroles", "rolefile"],
        brief="DMs you a file of server roles.",
        implemented="2021-03-29 21:28:14.146367",
        updated="2021-05-06 16:15:01.162059",
    )
    @commands.guild_only()
    @checks.has_perms(manage_roles=True)
    async def dumproles(self, ctx):
        """
        Usage: {0}dumproles
        Aliases: {0}txtroles, {0}rolefile
        Permission: Manage Roles
        Output:
            Sends a list of roles for the server to your DMs
        Notes:
            If you have your DMs blocked, the bot
            will send the file to the channel
            where the the command was invoked.
        """
        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        role_file = "Roles-{}.txt".format(timestamp)

        mess = await ctx.send_or_reply(
            content="Saving roles to **{}**...".format(role_file),
        )

        allroles = ""

        for num, role in enumerate(sorted(ctx.guild.roles, reverse=True), start=1):
            allroles += f"[{str(num).zfill(2)}] {role.id}\t{role.name}\t[ Users: {len(role.members)} ]\r\n"

        data = io.BytesIO(allroles.encode("utf-8"))

        await mess.edit(content="Uploading `{}`...".format(role_file))
        try:
            await ctx.author.send(file=discord.File(data, filename=role_file))
        except Exception:
            await ctx.send_or_reply(
                file=discord.File(data, filename=role_file),
            )
            await mess.edit(
                content="{} Uploaded `{}`.".format(
                    self.bot.emote_dict["success"], role_file
                )
            )
            return
        await mess.edit(
            content="{} Uploaded `{}`.".format(
                self.bot.emote_dict["success"], role_file
            )
        )
        await mess.add_reaction(self.bot.emote_dict["letter"])

    @decorators.command(
        aliases=["dumptc", "dumptcc", "dumptextchannels"],
        brief="DMs you a file of text channels.",
        implemented="2021-04-08 17:46:29.171255",
        updated="2021-05-06 16:10:22.394728",
    )
    @commands.guild_only()
    @checks.has_perms(manage_channels=True)
    async def dumpchannels(self, ctx):
        """
        Usage: {0}dumptextchannels
        Aliases: {0}dumptc, {0}dumptcs, {0}dumptextchannels
        Permission: Manage Channels
        Output:
            Sends a list of channels for the server to your DMs
        Notes:
            If you have your DMs blocked, the bot
            will send the file to the channel
            where the the command was invoked.
        """
        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        role_file = "Channels-{}.txt".format(timestamp)

        mess = await ctx.send_or_reply(
            content="Saving channels to **{}**...".format(role_file),
        )

        allchannels = ""

        channel_list = []
        for c in ctx.guild.channels:
            if type(c) == discord.TextChannel:
                channel_list.append(c)
        for num, chan in enumerate(
            sorted(channel_list, key=lambda p: p.position), start=1
        ):
            allchannels += f"[{str(num).zfill(2)}] {chan.id}\t{chan.name}\t\r\n"

        data = io.BytesIO(allchannels.encode("utf-8"))

        await mess.edit(content="Uploading `{}`...".format(role_file))
        try:
            await ctx.author.send(file=discord.File(data, filename=role_file))
        except Exception:
            await ctx.send_or_reply(
                file=discord.File(data, filename=role_file),
            )
            await mess.edit(
                content="{} Uploaded `{}`.".format(
                    self.bot.emote_dict["success"], role_file
                )
            )
            return
        await mess.edit(
            content="{} Uploaded `{}`.".format(
                self.bot.emote_dict["success"], role_file
            )
        )
        await mess.add_reaction(self.bot.emote_dict["letter"])

    @decorators.command(
        aliases=["dumpvc", "dumpvcs"],
        brief="DMs you a file of voice channels.",
        implemented="2021-04-08 18:03:17.759494",
        updated="2021-05-06 16:12:56.649004",
    )
    @commands.guild_only()
    @checks.has_perms(manage_channels=True)
    async def dumpvoicechannels(self, ctx):
        """
        Usage: {0}dumpvoicechannels
        Aliases: {0}dumpvc, {0}dumpvcs
        Permission: Manage Channels
        Output:
            Sends a list of voice channels to your DMs
        Notes:
            If you have your DMs blocked, the bot
            will send the file to the channel
            where the the command was invoked.
        """
        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        role_file = "Channels-{}.txt".format(timestamp)

        mess = await ctx.send_or_reply(
            content="Saving channels to **{}**...".format(role_file),
        )

        allchannels = ""

        channel_list = []
        for c in ctx.guild.channels:
            if type(c) == discord.VoiceChannel:
                channel_list.append(c)
        for num, chan in enumerate(
            sorted(channel_list, key=lambda p: p.position), start=1
        ):
            allchannels += f"[{str(num).zfill(2)}] {chan.id}\t{chan.name}\t\r\n"

        data = io.BytesIO(allchannels.encode("utf-8"))

        await mess.edit(content="Uploading `{}`...".format(role_file))
        try:
            await ctx.author.send(file=discord.File(data, filename=role_file))
        except Exception:
            await ctx.send_or_reply(
                file=discord.File(data, filename=role_file),
            )
            await mess.edit(
                content="{} Uploaded `{}`.".format(
                    self.bot.emote_dict["success"], role_file
                )
            )
            return
        await mess.edit(
            content="{} Uploaded `{}`.".format(
                self.bot.emote_dict["success"], role_file
            )
        )
        await mess.add_reaction(self.bot.emote_dict["letter"])

    @decorators.command(
        aliases=["dumpcc", "dumpccs"],
        brief="DMs you a file of voice channels.",
        implemented="2021-04-08 18:03:28.697338",
        updated="2021-05-06 16:17:04.697120",
    )
    @commands.guild_only()
    @checks.has_perms(manage_channels=True)
    async def dumpcategories(self, ctx):
        """
        Usage: {0}dumpcategories
        Alias: {0}dumpcc, {0}dumpccs
        Permission: Manage Channels
        Output:
            Sends a list of categories to your DMs
        Notes:
            If you have your DMs blocked, the bot
            will send the file to the channel
            where the the command was invoked.
        """
        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        role_file = "Channels-{}.txt".format(timestamp)

        mess = await ctx.send_or_reply(
            content="Saving channels to **{}**...".format(role_file),
        )

        allchannels = ""

        channel_list = []
        for c in ctx.guild.channels:
            if type(c) == discord.CategoryChannel:
                channel_list.append(c)
        for num, chan in enumerate(
            sorted(channel_list, key=lambda p: p.position), start=1
        ):
            allchannels += f"[{str(num).zfill(2)}] {chan.id}\t{chan.name}\t\r\n"

        data = io.BytesIO(allchannels.encode("utf-8"))

        await mess.edit(content="Uploading `{}`...".format(role_file))
        try:
            await ctx.author.send(file=discord.File(data, filename=role_file))
        except Exception:
            await ctx.send_or_reply(
                file=discord.File(data, filename=role_file),
            )
            await mess.edit(
                content="{} Uploaded `{}`.".format(
                    self.bot.emote_dict["success"], role_file
                )
            )
            return
        await mess.edit(
            content="{} Uploaded `{}`.".format(
                self.bot.emote_dict["success"], role_file
            )
        )
        await mess.add_reaction(self.bot.emote_dict["letter"])

    @decorators.command(
        aliases=["dumpemojis"],
        brief="DMs you a file of server emojis.",
        implemented="2021-03-30 23:00:39.720920",
        updated="2021-05-06 16:18:48.309094",
    )
    @commands.guild_only()
    @checks.has_perms(manage_emojis=True)
    async def dumpemotes(self, ctx):
        """
        Usage: {0}dumpemotes
        Alias: {0}dumpemojis
        Permission: Manage Emojis
        Output:
            Sends a list of server emojis to your DMs
        Notes:
            If you have your DMs blocked, the bot
            will send the file to the channel
            where the the command was invoked.
        """
        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        role_file = "Emotes-{}.txt".format(timestamp)

        mess = await ctx.send_or_reply(
            content="Saving emotes to **{}**...".format(role_file),
        )

        allemotes = ""
        emote_list = sorted(ctx.guild.emojis, key=lambda e: str(e.name))

        for num, emote in enumerate(
            sorted(emote_list, key=lambda a: str(a.url).endswith("gif")), start=1
        ):
            allemotes += f"[{str(num).zfill(len(str(len(ctx.guild.emojis))))}]\tID: {emote.id}\tURL: {emote.url}\t{emote.name}\t\r\n"

        data = io.BytesIO(allemotes.encode("utf-8"))

        await mess.edit(content="Uploading `{}`...".format(role_file))
        try:
            await ctx.author.send(file=discord.File(data, filename=role_file))
        except Exception:
            await ctx.send_or_reply(
                file=discord.File(data, filename=role_file),
            )
            await mess.edit(
                content="{} Uploaded `{}`.".format(
                    self.bot.emote_dict["success"], role_file
                )
            )
            return
        await mess.edit(
            content="{} Uploaded `{}`.".format(
                self.bot.emote_dict["success"], role_file
            )
        )
        await mess.add_reaction(self.bot.emote_dict["letter"])

    @decorators.command(
        aliases=["logmessages", "messagedump"],
        brief="DMs you a file of channel messages.",
        implemented="2021-03-30 05:29:13.886950",
        updated="2021-05-06 16:19:33.543435",
    )
    @commands.guild_only()
    @checks.has_perms(manage_messages=True)
    async def dumpmessages(
        self, ctx, messages: int = 25, *, chan: discord.TextChannel = None
    ):
        """
        Usage: {0}dumpmessages [message amount] [channel]
        Aliases: {0}messagedump, {0}dumpmessages, {0}logmessages
        Permission: Manage Messages
        Output:
            Logs a passed number of messages from a specified channel
            - 25 by default.
        Notes:
            If you have your DMs blocked, the bot
            will send the file to the channel
            where the the command was invoked.
        """

        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        log_file = "Logs-{}.txt".format(timestamp)

        if not chan:
            chan = ctx

        mess = await ctx.send_or_reply(
            content="Saving logs to **{}**...".format(log_file),
        )

        counter = 0
        msg = ""
        async for message in chan.history(limit=messages):
            counter += 1
            msg += message.content + "\n"
            msg += (
                "----Sent-By: "
                + message.author.name
                + "#"
                + message.author.discriminator
                + "\n"
            )
            msg += (
                "---------At: " + message.created_at.strftime("%Y-%m-%d %H.%M") + "\n"
            )
            if message.edited_at:
                msg += (
                    "--Edited-At: "
                    + message.edited_at.strftime("%Y-%m-%d %H.%M")
                    + "\n"
                )
            msg += "\n"

        data = io.BytesIO(msg[:-2].encode("utf-8"))

        await mess.edit(content="Uploading `{}`...".format(log_file))
        try:
            await ctx.author.send(file=discord.File(data, filename=log_file))
        except Exception:
            await ctx.send_or_reply(
                file=discord.File(data, filename=log_file),
            )
            await mess.edit(
                content="{} Uploaded `{}`.".format(
                    self.bot.emote_dict["success"], log_file
                )
            )
            return
        await mess.edit(
            content="{} Uploaded `{}`.".format(self.bot.emote_dict["success"], log_file)
        )
        await mess.add_reaction(self.bot.emote_dict["letter"])

    @decorators.command(
        aliases=["timezonelist", "listtimezones"],
        brief="DMs you a file of time zones.",
        implemented="2021-03-31 06:56:01.017282",
        updated="2021-05-06 16:20:59.298405",
    )
    @commands.guild_only()
    async def dumptimezones(self, ctx):
        """
        Usage: {0}dumptimezones
        Aliases: {0}listtimezones, {0}timezonelist
        Output:
            Sends a txt file to your DMs with all
            available timezones to set using {0}settz
        Notes:
            If you have your DMs blocked, the bot
            will send the file to the channel
            where the the command was invoked.
        """

        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        time_file = "Timezones-{}.txt".format(timestamp)

        mess = await ctx.send_or_reply(
            content="Saving logs to **{}**...".format(time_file),
        )

        all_tz = pytz.all_timezones

        msg = ""
        for x in all_tz:
            msg += f"{x}\n"

        data = io.BytesIO(msg.encode("utf-8"))
        await mess.edit(content="Uploading `{}`...".format(time_file))
        try:
            await ctx.author.send(file=discord.File(data, filename=time_file))
        except Exception:
            await ctx.send_or_reply(
                file=discord.File(data, filename=time_file),
            )
            await mess.edit(
                content="{} Uploaded `{}`.".format(
                    self.bot.emote_dict["success"], time_file
                )
            )
            return
        await mess.edit(
            content="{} Uploaded `{}`.".format(
                self.bot.emote_dict["success"], time_file
            )
        )
        await mess.add_reaction(self.bot.emote_dict["letter"])

    @decorators.command(
        aliases=["humanlist"],
        brief="DMs you a file of server humans.",
        implemented="2021-04-07 23:11:42.549620",
        updated="2021-05-06 16:22:31.888866",
    )
    @commands.guild_only()
    @checks.has_perms(manage_guild=True)
    async def dumphumans(self, ctx):
        """
        Usage: {0}dumphumans
        Aliases: {0}humanlist
        Permission: Manage Server
        Output:
            Sends a txt file to your DMs with all
            server humans
        Notes:
            If you have your DMs blocked, the bot
            will send the file to the channel
            where the the command was invoked.
        """

        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        time_file = "Humans-{}.txt".format(timestamp)

        mess = await ctx.send_or_reply(
            content="Saving logs to **{}**...".format(time_file),
        )

        member_list = ctx.guild.members

        humans = []
        for m in member_list:
            if not m.bot:
                humans.append(m)

        msg = ""
        for x, y in enumerate(sorted(humans, key=lambda m: str(m)), start=1):
            msg += f"{x}\t{y.id}\t{str(y)}\n"

        data = io.BytesIO(msg.encode("utf-8"))
        await mess.edit(content="Uploading `{}`...".format(time_file))
        try:
            await ctx.author.send(file=discord.File(data, filename=time_file))
        except Exception:
            await ctx.send_or_reply(
                file=discord.File(data, filename=time_file),
            )
            await mess.edit(
                content="{} Uploaded `{}`.".format(
                    self.bot.emote_dict["success"], time_file
                )
            )
            return
        await mess.edit(
            content="{} Uploaded `{}`.".format(
                self.bot.emote_dict["success"], time_file
            )
        )
        await mess.add_reaction(self.bot.emote_dict["letter"])

    @decorators.command(
        aliases=["dumprobots", "robotlist", "botlist"],
        brief="DMs you a file of server bots.",
        implemented="2021-04-07 23:11:37.665030",
        updated="2021-05-06 16:23:46.251790",
    )
    @commands.guild_only()
    @checks.has_perms(manage_guild=True)
    async def dumpbots(self, ctx):
        """
        Usage: {0}dumpbots
        Aliases:
            {0}botlist, {0}robotlist, {0}dumprobots
        Permission: Manage Server
        Output:
            Sends a txt file to your DMs with all
            bots currently in the server.
        Notes:
            If you have your DMs blocked, the bot
            will send the file to the channel
            where the the command was invoked.
        """

        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        time_file = "Bots-{}.txt".format(timestamp)

        mess = await ctx.send_or_reply(
            content="Saving logs to **{}**...".format(time_file),
        )

        member_list = ctx.guild.members

        bots = []
        for m in member_list:
            if m.bot:
                bots.append(m)

        msg = ""
        for x, y in enumerate(sorted(bots, key=lambda m: str(m)), start=1):
            msg += f"{x}\t{y.id}\t{str(y)}\n"

        data = io.BytesIO(msg.encode("utf-8"))
        await mess.edit(content="Uploading `{}`...".format(time_file))
        try:
            await ctx.author.send(file=discord.File(data, filename=time_file))
        except Exception:
            await ctx.send_or_reply(
                file=discord.File(data, filename=time_file),
            )
            await mess.edit(
                content="{} Uploaded `{}`.".format(
                    self.bot.emote_dict["success"], time_file
                )
            )
            return
        await mess.edit(
            content="{} Uploaded `{}`.".format(
                self.bot.emote_dict["success"], time_file
            )
        )
        await mess.add_reaction(self.bot.emote_dict["letter"])

    @decorators.command(
        aliases=["dumpmembers", "memberlist", "userlist"],
        brief="DMs you a file of server members.",
        implemented="2021-04-07 23:06:22.487209",
        updated="2021-05-06 16:27:03.146078",
    )
    @commands.guild_only()
    @checks.has_perms(manage_guild=True)
    async def dumpusers(self, ctx):
        """
        Usage: {0}dumpusers
        Aliases: {0}dumpmembers, {0}memberlist, {0}userlist
        Permission: Manage Server
        Output:
            Sends a txt file to your DMs with all
            server members. Bots are included.
        Notes:
            If you have your DMs blocked, the bot
            will send the file to the channel
            where the the command was invoked.
        """

        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        time_file = "Members-{}.txt".format(timestamp)

        mess = await ctx.send_or_reply(
            content="Saving logs to **{}**...".format(time_file),
        )

        member_list = ctx.guild.members

        msg = ""
        for x, y in enumerate(sorted(member_list, key=lambda m: str(m)), start=1):
            msg += f"{x}\t{y.id}\t{str(y)}\n"

        data = io.BytesIO(msg.encode("utf-8"))
        await mess.edit(content="Uploading `{}`...".format(time_file))
        try:
            await ctx.author.send(file=discord.File(data, filename=time_file))
        except Exception:
            await ctx.send_or_reply(
                file=discord.File(data, filename=time_file),
            )
            await mess.edit(
                content="{} Uploaded `{}`.".format(
                    self.bot.emote_dict["success"], time_file
                )
            )
            return
        await mess.edit(
            content="{} Uploaded `{}`.".format(
                self.bot.emote_dict["success"], time_file
            )
        )
        await mess.add_reaction(self.bot.emote_dict["letter"])

    @decorators.command(
        aliases=["banlist", "txtbans"],
        brief="DMs you a file of server bans.",
        implemented="2021-04-09 21:29:18.563027",
        updated="2021-05-06 16:26:05.161487",
    )
    @commands.guild_only()
    @checks.bot_has_perms(ban_members=True)
    @checks.has_perms(ban_members=True)
    async def dumpbans(self, ctx):
        """
        Usage: {0}dumpbans
        Aliases: {0}banlist, {0}txtbans
        Permission: Ban Members
        Output:
            Sends a txt file to your DMs with all
            past server bans.
        Notes:
            If you have your DMs blocked, the bot
            will send the file to the channel
            where the the command was invoked.
        """
        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        time_file = "Bans-{}.txt".format(timestamp)

        mess = await ctx.send_or_reply(
            content="Saving bans to **{}**...".format(time_file),
        )

        ban_list = await ctx.guild.bans()

        msg = ""
        for x, y in enumerate(sorted(ban_list, key=lambda m: str(m.user)), start=1):
            msg += f"{x}\t{y.user.id}\t{str(y.user)}\tReason: {y.reason}\n"

        data = io.BytesIO(msg.encode("utf-8"))
        await mess.edit(content="Uploading `{}`...".format(time_file))
        try:
            await ctx.author.send(file=discord.File(data, filename=time_file))
        except Exception:
            await ctx.send_or_reply(
                file=discord.File(data, filename=time_file),
            )
            await mess.edit(
                content="{} Uploaded `{}`.".format(
                    self.bot.emote_dict["success"], time_file
                )
            )
            return
        await mess.edit(
            content="{} Uploaded `{}`.".format(
                self.bot.emote_dict["success"], time_file
            )
        )
        await mess.add_reaction(self.bot.emote_dict["letter"])

    @decorators.command(
        aliases=["md"],
        brief="DMs you my readme file.",
        implemented="2021-04-14 00:48:12.179355",
        updated="2021-05-06 16:30:04.761423",
    )
    @commands.cooldown(2, 60, commands.BucketType.user)
    async def readme(self, ctx):
        """
        Usage: {0}readme
        Alias: {0}md
        Output: Sends my readme file on github to your DMs
        Notes:
            This command updates the readme file
            to include all the current command descriptions
            for each registered category.
        """
        mess = await ctx.send_or_reply(
            content="Saving readme to **{}**...".format(self.bot.constants.github),
        )

        owner, cmds, cogs = self.bot.public_stats()
        overview = (
            open("./data/txts/overview.txt")
            .read()
            .format("Snowbot", len(cmds), len(cogs))
        )
        premsg = ""
        premsg += f"# Snowbot Moderation & Stat Tracking Discord Bot\n"
        # premsg += "![6010fc1cf1ae9c815f9b09168dbb65a7-1](https://user-images.githubusercontent.com/74381783/108671227-f6d3f580-7494-11eb-9a77-9478f5a39684.png)\n"
        premsg += f"### [Bot Invite Link]({self.bot.oauth})\n"
        premsg += f"### [Support Server]({self.bot.constants.support})\n"
        premsg += (
            "### [DiscordBots.gg](https://discord.bots.gg/bots/810377376269205546)\n"
        )
        premsg += "### [Top.gg](https://top.gg/bot/810377376269205546)\n"
        premsg += "## Overview\n"
        premsg += overview
        premsg += "\n## Categories\n"
        msg = ""

        cog_list = [self.bot.get_cog(cog) for cog in self.bot.cogs]
        for cog in cog_list:
            if (
                cog.qualified_name.upper()
                in self.bot.cog_exceptions + self.bot.useless_cogs
            ):
                continue
            premsg += f"##### [{cog.qualified_name}](#{cog.qualified_name}-1)\n"
            cmds = [c for c in cog.get_commands() if not c.hidden]

            msg += "\n\n### {}\n#### {} ({} Commands)\n\n```yaml\n{}\n```" "".format(
                cog.qualified_name,
                cog.description,
                len(cmds),
                "\n\n".join(
                    [
                        f"{cmd.name}: {cmd.brief}"
                        for cmd in sorted(cmds, key=lambda c: c.name)
                    ]
                ),
            )
        final = premsg + msg
        data = io.BytesIO(final.encode("utf-8"))

        with open("./README.md", "w", encoding="utf-8") as fp:
            fp.write(final)

        await mess.edit(content="Uploading `README.md`...")
        try:
            await ctx.author.send(file=discord.File(data, filename="README.md"))
        except Exception:
            await ctx.send_or_reply(
                file=discord.File(data, filename="README.md"),
            )
            await mess.edit(
                content="{} Uploaded `{}`.".format(
                    self.bot.emote_dict["success"], "README.md"
                )
            )
            return
        await mess.edit(
            content="{} Uploaded `{}`.".format(
                self.bot.emote_dict["success"], "README.md"
            )
        )
        await mess.add_reaction(self.bot.emote_dict["letter"])

    @decorators.group(
        aliases=["dump", "actions"],
        case_insensitive=True,
        invoke_without_command=True,
        brief="Get a file of a user's audit actions.",
        implemented="2021-05-09 21:48:00.663306",
        updated="2021-05-09 21:48:00.663306",
    )
    async def audit(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: audit [option] [user] [after]
        Aliases {0}dump, {0}actions, {0}audits, {0}dumps
        Output:
            Sends a file of all audit entries
            of a user. Specify an optional
            category, user, and date to search
            entries after that date.
        Notes:
            Will default to you if no user is passed.
            Run with no subcommands to get all actions.
        Options:
            bans, botadds, channelcreates,
            channeldeletes, channelupdates,
            deletes, disconnects, emojicreates,
            emojideletes, emojiupdates,
            invitecreates, invitedeletes,
            inviteupdates, kicks, nicknames,
            rolecreates, roledeletes, roleupdates,
            unbans, userroles, webhookcreates,
            webhookdeletes, webhookupdates.
        """
        if not user:
            user = ctx.author
        await self.get_and_send_actions(
            ctx=ctx,
            user=user,
            after=after,
            action=None,
            emote=self.bot.emote_dict["success"],
            string="Actions",
        )

    @audit.command()
    async def bans(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember] = None,
        *,
        after: humantime.PastTime = None,
    ):
        if not user:
            user = ctx.author
        await self.get_and_send_actions(
            ctx=ctx,
            user=user,
            after=after,
            action=discord.AuditLogAction.ban,
            emote=self.bot.emote_dict["ban"],
            string="Users banned",
        )

    @audit.command()
    async def kicks(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember] = None,
        *,
        after: humantime.PastTime = None,
    ):
        if not user:
            user = ctx.author
        await self.get_and_send_actions(
            ctx=ctx,
            user=user,
            after=after,
            action=discord.AuditLogAction.kick,
            emote=self.bot.emote_dict["kick"],
            string="Users kicked",
        )

    @audit.command()
    async def channelcreates(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember] = None,
        *,
        after: humantime.PastTime = None,
    ):
        if not user:
            user = ctx.author
        await self.get_and_send_actions(
            ctx=ctx,
            user=user,
            after=after,
            action=discord.AuditLogAction.channel_create,
            emote=self.bot.emote_dict["plus"],
            string="Channels created",
        )

    @audit.command()
    async def channelupdates(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember] = None,
        *,
        after: humantime.PastTime = None,
    ):
        if not user:
            user = ctx.author
        await self.get_and_send_actions(
            ctx=ctx,
            user=user,
            after=after,
            action=discord.AuditLogAction.channel_update,
            emote=self.bot.emote_dict["redo"],
            string="Channels updated",
        )

    @audit.command()
    async def channeldeletes(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember] = None,
        *,
        after: humantime.PastTime = None,
    ):
        if not user:
            user = ctx.author
        await self.get_and_send_actions(
            ctx=ctx,
            user=user,
            after=after,
            action=discord.AuditLogAction.channel_delete,
            emote=self.bot.emote_dict["minus"],
            string="Channels deleted",
        )

    @audit.command()
    async def unbans(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember] = None,
        *,
        after: humantime.PastTime = None,
    ):
        if not user:
            user = ctx.author
        await self.get_and_send_actions(
            ctx=ctx,
            user=user,
            after=after,
            action=discord.AuditLogAction.unban,
            emote=self.bot.emote_dict["ban"],
            string="Users unbanned",
        )

    @audit.command()
    async def nicknames(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember] = None,
        *,
        after: humantime.PastTime = None,
    ):
        if not user:
            user = ctx.author
        await self.get_and_send_actions(
            ctx=ctx,
            user=user,
            after=after,
            action=discord.AuditLogAction.member_update,
            emote=self.bot.emote_dict["redo"],
            string="Nicknames updated",
        )

    @audit.command()
    async def userroles(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember] = None,
        *,
        after: humantime.PastTime = None,
    ):
        if not user:
            user = ctx.author
        await self.get_and_send_actions(
            ctx=ctx,
            user=user,
            after=after,
            action=discord.AuditLogAction.member_role_update,
            emote=self.bot.emote_dict["redo"],
            string="User roles updated",
        )

    @audit.command()
    async def disconnects(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember] = None,
        *,
        after: humantime.PastTime = None,
    ):
        if not user:
            user = ctx.author
        await self.get_and_send_actions(
            ctx=ctx,
            user=user,
            after=after,
            action=discord.AuditLogAction.member_update,
            emote=self.bot.emote_dict["audioremove"],
            string="Users disconnected",
        )

    @audit.command()
    async def botadds(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember] = None,
        *,
        after: humantime.PastTime = None,
    ):
        if not user:
            user = ctx.author
        await self.get_and_send_actions(
            ctx=ctx,
            user=user,
            after=after,
            action=discord.AuditLogAction.bot_add,
            emote=self.bot.emote_dict["bot"],
            string="Bots added",
        )

    @audit.command()
    async def rolecreates(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember] = None,
        *,
        after: humantime.PastTime = None,
    ):
        if not user:
            user = ctx.author
        await self.get_and_send_actions(
            ctx=ctx,
            user=user,
            after=after,
            action=discord.AuditLogAction.role_create,
            emote=self.bot.emote_dict["plus"],
            string="Roles created",
        )

    @audit.command()
    async def roleupdates(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember] = None,
        *,
        after: humantime.PastTime = None,
    ):
        if not user:
            user = ctx.author
        await self.get_and_send_actions(
            ctx=ctx,
            user=user,
            after=after,
            action=discord.AuditLogAction.role_update,
            emote=self.bot.emote_dict["plus"],
            string="Roles updated",
        )

    @audit.command()
    async def roledeletes(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember] = None,
        *,
        after: humantime.PastTime = None,
    ):
        if not user:
            user = ctx.author
        await self.get_and_send_actions(
            ctx=ctx,
            user=user,
            after=after,
            action=discord.AuditLogAction.role_delete,
            emote=self.bot.emote_dict["plus"],
            string="Roles deleted",
        )

    @audit.command()
    async def invitecreates(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember] = None,
        *,
        after: humantime.PastTime = None,
    ):
        if not user:
            user = ctx.author
        await self.get_and_send_actions(
            ctx=ctx,
            user=user,
            after=after,
            action=discord.AuditLogAction.invite_create,
            emote=self.bot.emote_dict["plus"],
            string="Invites created",
        )

    @audit.command()
    async def inviteupdates(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember] = None,
        *,
        after: humantime.PastTime = None,
    ):
        if not user:
            user = ctx.author
        await self.get_and_send_actions(
            ctx=ctx,
            user=user,
            after=after,
            action=discord.AuditLogAction.invite_update,
            emote=self.bot.emote_dict["redo"],
            string="Invites updated",
        )

    @audit.command()
    async def invitedeletes(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember] = None,
        *,
        after: humantime.PastTime = None,
    ):
        if not user:
            user = ctx.author
        await self.get_and_send_actions(
            ctx=ctx,
            user=user,
            after=after,
            action=discord.AuditLogAction.invite_delete,
            emote=self.bot.emote_dict["minus"],
            string="Invites deleted",
        )

    @audit.command()
    async def webhookcreates(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember] = None,
        *,
        after: humantime.PastTime = None,
    ):
        if not user:
            user = ctx.author
        await self.get_and_send_actions(
            ctx=ctx,
            user=user,
            after=after,
            action=discord.AuditLogAction.webhook_create,
            emote=self.bot.emote_dict["plus"],
            string="Webhooks created",
        )

    @audit.command()
    async def webhookupdates(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember] = None,
        *,
        after: humantime.PastTime = None,
    ):
        if not user:
            user = ctx.author
        await self.get_and_send_actions(
            ctx=ctx,
            user=user,
            after=after,
            action=discord.AuditLogAction.webhook_update,
            emote=self.bot.emote_dict["redo"],
            string="Webhooks updated",
        )

    @audit.command()
    async def webhookdeletes(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember] = None,
        *,
        after: humantime.PastTime = None,
    ):
        if not user:
            user = ctx.author
        await self.get_and_send_actions(
            ctx=ctx,
            user=user,
            after=after,
            action=discord.AuditLogAction.webhook_delete,
            emote=self.bot.emote_dict["minus"],
            string="Webhooks deleted",
        )

    @audit.command()
    async def emojicreates(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember] = None,
        *,
        after: humantime.PastTime = None,
    ):
        if not user:
            user = ctx.author
        await self.get_and_send_actions(
            ctx=ctx,
            user=user,
            after=after,
            action=discord.AuditLogAction.emoji_create,
            emote=self.bot.emote_dict["plus"],
            string="Emojis created",
        )

    @audit.command()
    async def emojiupdates(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember] = None,
        *,
        after: humantime.PastTime = None,
    ):
        if not user:
            user = ctx.author
        await self.get_and_send_actions(
            ctx=ctx,
            user=user,
            after=after,
            action=discord.AuditLogAction.emoji_updates,
            emote=self.bot.emote_dict["redo"],
            string="Emojis updated",
        )

    @audit.command()
    async def emojideletes(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember] = None,
        *,
        after: humantime.PastTime = None,
    ):
        if not user:
            user = ctx.author
        await self.get_and_send_actions(
            ctx=ctx,
            user=user,
            after=after,
            action=discord.AuditLogAction.emoji_updates,
            emote=self.bot.emote_dict["minus"],
            string="Emojis deleted",
        )

    @audit.command()
    async def deletes(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember] = None,
        *,
        after: humantime.PastTime = None,
    ):
        if not user:
            user = ctx.author
        await self.get_and_send_actions(
            ctx=ctx,
            user=user,
            after=after,
            action=discord.AuditLogAction.message_delete,
            emote=self.bot.emote_dict["minus"],
            string="Messages deleted",
        )

    async def get_and_send_actions(self, ctx, user, after, action, emote, string):
        name = str(action).split(".")[-1] if action else "Action"
        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        filename = f"{name.capitalize()}s-{timestamp}.sml"
        mess = await ctx.send_or_reply(
            content="Saving logs to **{}...**".format(filename),
        )
        await ctx.trigger_typing()
        entries = await ctx.guild.audit_logs(
            limit=None, user=user, action=action
        ).flatten()
        entries = [x for x in entries if hasattr(x.target, "id")]
        if after:
            valid = [x for x in entries if x.created_at > after.dt]
            entries = valid
            premsg = f"**{emote} {len(entries)} {string} by `{user} (ID: {user.id})` since {utils.short_time(after.dt)}**"
            if len(valid) == 0:
                return await mess.edit(
                    content=f"{self.bot.emote_dict['failed']} User `{user}` has no {name} entries since **{utils.short_time(after.dt)}.**"
                )
        else:
            entries = entries
            premsg = f"**{emote} {len(entries)} {string} by `{user} (ID: {user.id})`**"
            if len(entries) == 0:
                return await mess.edit(
                    content=f"{self.bot.emote_dict['failed']} User `{user}` has no {name} entries."
                )
        msg = ""
        name_width = max([len(str(x.target)) for x in entries])
        id_width = max([len(str(x.target.id)) for x in entries])
        time_width = max([len(utils.short_time(x.created_at)) for x in entries])
        for y, x in enumerate(
            sorted(entries, key=lambda d: d.created_at, reverse=True), start=1
        ):
            msg += f"{str(y).zfill(len(str(len(entries))))}. {utils.short_time(x.created_at).ljust(time_width)} Target: (ID: {str(x.target.id).ljust(id_width)}) {str(x.target).ljust(name_width)} Reason: {x.reason}\n"

        await mess.edit(content="Uploading `{}...`".format(filename))
        data = io.BytesIO(msg.encode("utf-8"))
        dfile = discord.File(data, filename=filename)
        try:
            await ctx.author.send(content=premsg, file=dfile)
        except Exception:
            await ctx.send_or_reply(content=premsg, file=dfile)
            await mess.edit(
                content="{} Uploaded `{}`".format(
                    self.bot.emote_dict["success"], filename
                )
            )
            return
        await mess.edit(
            content="{} Uploaded `{}`".format(self.bot.emote_dict["success"], filename)
        )
        await mess.add_reaction(self.bot.emote_dict["letter"])
