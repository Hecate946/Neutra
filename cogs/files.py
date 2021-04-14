import io
import os
import pytz
import discord

from datetime import datetime
from discord.ext import commands

from cogs.help import COG_EXCEPTIONS, USELESS_COGS
from utilities import utils, permissions


def setup(bot):
    bot.add_cog(Files(bot))


class Files(commands.Cog):
    """
    Module for downloading files.
    """

    def __init__(self, bot):
        self.bot = bot

    ##############################
    ## Aiohttp Helper Functions ##
    ##############################

    async def query(self, url, method="get", res_method="text", *args, **kwargs):
        async with getattr(self.bot.session, method.lower())(
            url, *args, **kwargs
        ) as res:
            return await getattr(res, res_method)()

    async def get(self, url, *args, **kwargs):
        return await self.query(url, "get", *args, **kwargs)

    async def post(self, url, *args, **kwargs):
        return await self.query(url, "post", *args, **kwargs)

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

    @commands.command(
        brief="DMs you a file of commands.", aliases=["txthelp", "helpfile"]
    )
    async def dumphelp(self, ctx):
        """
        Usage: -dumphelp
        Aliases: -txthelp, -helpfile
        Output:
            DMs you a file with all my commands
            and their descriptions.
        """
        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        help_file = "Help-{}.txt".format(timestamp)

        mess = await ctx.send("Saving servers to **{}**...".format(help_file))
        msg = ""
        prefix = ctx.prefix

        # Get and format the help
        for cog in sorted(self.bot.cogs):
            if cog.upper() in COG_EXCEPTIONS + USELESS_COGS:
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
            await ctx.send(file=discord.File(data, filename=help_file))
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


    @commands.command(hidden=True, brief="DMs you a list of my servers.")
    async def dumpservers(self, ctx):
        """
        Usage: -dumpservers
        Permission: Bot Admin
        Output:
            DMs you a file with all my servers,
            their member count, owners, and their IDs
        """
        if not permissions.is_admin(ctx):
            return
        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        server_file = "Servers-{}.txt".format(timestamp)

        mess = await ctx.send("Saving servers to **{}**...".format(server_file))

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
            await ctx.send(file=discord.File(data, filename=server_file))
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

    @commands.command(
        brief="DMs you a file of server settings.", aliases=["serversettings"]
    )
    @commands.guild_only()
    @permissions.has_permissions(manage_guild=True)
    async def dumpsettings(self, ctx):
        """
        Usage: -dumpsettings
        Alias: -serversettings
        Permission: Manage Server
        Output: Sends a json file of server settings to your DMs.
        """

        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        settings_file = "Settings-{}.json".format(timestamp)

        mess = await ctx.send("Saving settings to **{}**...".format(settings_file))

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
            await ctx.send(
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

    @commands.command(brief="DMs you a file of server roles.")
    @commands.guild_only()
    @permissions.has_permissions(manage_roles=True)
    async def dumproles(self, ctx):
        """
        Usage:  -dumproles
        Alias:  -txtroles
        Permission: Manage Roles
        Output:  Sends a list of roles for the server to your DMs
        """
        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        role_file = "Roles-{}.txt".format(timestamp)

        mess = await ctx.send("Saving roles to **{}**...".format(role_file))

        allroles = ""

        for num, role in enumerate(sorted(ctx.guild.roles, reverse=True), start=1):
            allroles += f"[{str(num).zfill(2)}] {role.id}\t{role.name}\t[ Users: {len(role.members)} ]\r\n"

        data = io.BytesIO(allroles.encode("utf-8"))

        await mess.edit(content="Uploading `{}`...".format(role_file))
        try:
            await ctx.author.send(file=discord.File(data, filename=role_file))
        except Exception:
            await ctx.send(file=discord.File(data, filename=role_file))
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

    @commands.command(
        brief="DMs you a file of text channels.", aliases=["dumptc", "dumptextchannels"]
    )
    @commands.guild_only()
    @permissions.has_permissions(manage_channels=True)
    async def dumpchannels(self, ctx):
        """
        Usage:  -dumptextchannels
        Alias:  -dumptc, -dumptextchannels
        Output:  Sends a list of channels for the server to your DMs
        Permission: Manage Channels
        """
        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        role_file = "Channels-{}.txt".format(timestamp)

        mess = await ctx.send("Saving channels to **{}**...".format(role_file))

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
            await ctx.send(file=discord.File(data, filename=role_file))
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

    @commands.command(brief="DMs you a file of voice channels.", aliases=["dumpvc"])
    @commands.guild_only()
    @permissions.has_permissions(manage_channels=True)
    async def dumpvoicechannels(self, ctx):
        """
        Usage:  -dumpvoicechannels
        Alias:  -dumpvc
        Output:  Sends a list of voice channels to your DMs
        Permission: Manage Channels
        """
        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        role_file = "Channels-{}.txt".format(timestamp)

        mess = await ctx.send("Saving channels to **{}**...".format(role_file))

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
            await ctx.send(file=discord.File(data, filename=role_file))
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

    @commands.command(brief="DMs you a file of voice channels.", aliases=["dumpcc"])
    @commands.guild_only()
    @permissions.has_permissions(manage_channels=True)
    async def dumpcategories(self, ctx):
        """
        Usage:  -dumpcategories
        Alias:  -dumpcc
        Permission: Manage Channels
        Output:  Sends a list of categories to your DMs
        """
        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        role_file = "Channels-{}.txt".format(timestamp)

        mess = await ctx.send("Saving channels to **{}**...".format(role_file))

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
            await ctx.send(file=discord.File(data, filename=role_file))
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

    @commands.command(brief="DMs you a file of server emojis.", aliases=["dumpemojis"])
    @commands.guild_only()
    @permissions.has_permissions(manage_emojis=True)
    async def dumpemotes(self, ctx):
        """
        Usage:  -dumpemotes
        Alias:  -dumpemojis
        Permission: Manage Emojis
        Output:  Sends a list of server emojis to your DMs
        """
        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        role_file = "Emotes-{}.txt".format(timestamp)

        mess = await ctx.send("Saving emotes to **{}**...".format(role_file))

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
            await ctx.send(file=discord.File(data, filename=role_file))
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

    @commands.command(
        aliases=["logmessages", "messagedump"],
        brief="DMs you a file of channel messages.",
    )
    @commands.guild_only()
    @permissions.has_permissions(manage_messages=True)
    async def dumpmessages(
        self, ctx, messages: int = 25, *, chan: discord.TextChannel = None
    ):
        """
        Usage:      -dumpmessages [message amount] [channel]
        Aliases:    -messagedump, -dumpmessages, logmessages
        Permission: Manage Messages
        Output:
            Logs a passed number of messages from a specified channel
            - 25 by default.
        """

        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        log_file = "Logs-{}.txt".format(timestamp)

        if not chan:
            chan = ctx

        mess = await ctx.send("Saving logs to **{}**...".format(log_file))

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
            await ctx.send(file=discord.File(data, filename=log_file))
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

    @commands.command(
        aliases=["timezonelist", "listtimezones"], brief="DMs you a file of time zones."
    )
    @commands.guild_only()
    async def dumptimezones(self, ctx):
        """
        Usage:      -dumptimezones
        Aliases:    -listtimezones, -timezonelist
        Output:
            Sends a txt file to your DMs with all
            available timezones to set using -settz
        """

        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        time_file = "Timezones-{}.txt".format(timestamp)

        mess = await ctx.send("Saving logs to **{}**...".format(time_file))

        all_tz = pytz.all_timezones

        msg = ""
        for x in all_tz:
            msg += f"{x}\n"

        data = io.BytesIO(msg.encode("utf-8"))
        await mess.edit(content="Uploading `{}`...".format(time_file))
        try:
            await ctx.author.send(file=discord.File(data, filename=time_file))
        except Exception:
            await ctx.send(file=discord.File(data, filename=time_file))
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

    @commands.command(aliases=["humanlist"], brief="DMs you a file of server humans.")
    @commands.guild_only()
    @permissions.has_permissions(manage_messages=True)
    async def dumphumans(self, ctx):
        """
        Usage:      -dumphumans
        Aliases:    -humanlist
        Permission: Manage Messages
        Output:
            Sends a txt file to your DMs with all
            server humans
        """

        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        time_file = "Humans-{}.txt".format(timestamp)

        mess = await ctx.send("Saving logs to **{}**...".format(time_file))

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
            await ctx.send(file=discord.File(data, filename=time_file))
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

    @commands.command(
        aliases=["dumprobots", "robotlist", "botlist"],
        brief="DMs you a file of server bots.",
    )
    @commands.guild_only()
    @permissions.has_permissions(manage_messages=True)
    async def dumpbots(self, ctx):
        """
        Usage:      -dumphumans
        Aliases:    -botlist, -robotlist, dumprobots
        Permission: Manage Messages
        Output:
            Sends a txt file to your DMs with all
            server bots
        """

        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        time_file = "Bots-{}.txt".format(timestamp)

        mess = await ctx.send("Saving logs to **{}**...".format(time_file))

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
            await ctx.send(file=discord.File(data, filename=time_file))
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

    @commands.command(
        aliases=["dumpusers", "memberlist", "userlist"],
        brief="DMs you a file of server members.",
    )
    @commands.guild_only()
    @permissions.has_permissions(manage_messages=True)
    async def dumpmembers(self, ctx):
        """
        Usage:      -dumpmembers
        Aliases:    -dumpusers, -memberlist, -userlist
        Permission: Manage Messages
        Output:
            Sends a txt file to your DMs with all
            server members.
        """

        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        time_file = "Members-{}.txt".format(timestamp)

        mess = await ctx.send("Saving logs to **{}**...".format(time_file))

        member_list = ctx.guild.members

        msg = ""
        for x, y in enumerate(sorted(member_list, key=lambda m: str(m)), start=1):
            msg += f"{x}\t{y.id}\t{str(y)}\n"

        data = io.BytesIO(msg.encode("utf-8"))
        await mess.edit(content="Uploading `{}`...".format(time_file))
        try:
            await ctx.author.send(file=discord.File(data, filename=time_file))
        except Exception:
            await ctx.send(file=discord.File(data, filename=time_file))
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

    @commands.command(
        aliases=["banlist", "txtbans"],
        brief="DMs you a file of server bans.",
    )
    @commands.guild_only()
    @permissions.bot_has_permissions(ban_members=True)
    @permissions.has_permissions(ban_members=True)
    async def dumpbans(self, ctx):
        """
        Usage:      -dumpbans
        Aliases:    -banlist, txtbans
        Permission: Ban Members
        Output:
            Sends a txt file to your DMs with all
            server bans.
        """

        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        time_file = "Bans-{}.txt".format(timestamp)

        mess = await ctx.send("Saving bans to **{}**...".format(time_file))

        ban_list = await ctx.guild.bans()

        msg = ""
        for x, y in enumerate(sorted(ban_list, key=lambda m: str(m.user)), start=1):
            msg += f"{x}\t{y.user.id}\t{str(y.user)}\tReason: {y.reason}\n"

        data = io.BytesIO(msg.encode("utf-8"))
        await mess.edit(content="Uploading `{}`...".format(time_file))
        try:
            await ctx.author.send(file=discord.File(data, filename=time_file))
        except Exception:
            await ctx.send(file=discord.File(data, filename=time_file))
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

    @commands.command(aliases=['md'], brief="DMs you my readme file.")
    async def readme(self, ctx):
        """
        Usage: -readme
        Alias: -md
        Output: Sends my readme file on github to your DMs
        Notes:
            This command actually updates the readme file
            to include all the current command descriptions
            for each registered category.
        """ 
        premsg = ""
        premsg += f"# NGC0000 Moderation & Stat Tracking Discord Bot\n"
        "![6010fc1cf1ae9c815f9b09168dbb65a7-1](https://user-images.githubusercontent.com/74381783/108671227-f6d3f580-7494-11eb-9a77-9478f5a39684.png)"
        f"### [Bot Invite Link]({self.bot.constants.oauth})\n"
        f"### [Support Server]({self.bot.constants.support})\n"
        "### [DiscordBots.gg](https://discord.bots.gg/bots/810377376269205546)\n"
        "## Overview\n"
        "Hello there! NGC0000 is an awesome feature rich bot named after the Milky Way. She features over 100 commands, all with extensive and easy to understand help. Her commands are fast and offer every opportunity for customization and utility.\n"
        "## Categories"   
        msg = ""

        cog_list = [self.bot.get_cog(cog) for cog in self.bot.cogs]
        for cog in cog_list:
            if cog.qualified_name.upper() in COG_EXCEPTIONS + USELESS_COGS:
                continue
            premsg += f"##### [{cog.qualified_name}](#{cog.qualified_name}-1)\n"
            cmds = [c for c in cog.get_commands() if not c.hidden]


            msg += "\n\n### {}\n#### {} ({} Commands)\n\n```yaml\n{}\n```""".format(
                cog.qualified_name,
                cog.description, len(cmds),
                '\n\n'.join([f"{cmd.name}: {cmd.brief}" for cmd in sorted(cmds, key=lambda c: c.name)])
            )
        final = premsg + msg
        data = io.BytesIO(final.encode("utf-8"))
        import codecs

        with codecs.open("./README.md", 'w', encoding='utf-8') as fp:
            fp.write(final)

            await ctx.send(file=discord.File(data, filename="README.md"))