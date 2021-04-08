import io
import os
import re
import pytz
import discord
import requests
from datetime import datetime
from discord.ext import commands
from .help import COG_EXCEPTIONS

from utilities import utils, permissions, pagination, converters, image
import discord
import pytz
from discord.ext import commands, menus


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
        Output: List of commands and descriptions
        """
        timestamp = datetime.today().strftime("%m-%d-%Y")

        if not os.path.exists("./data/wastebin"):
            # Create it
            os.makedirs("./data/wastebin")

        help_txt = "./data/wastebin/Help-{}.txt".format(timestamp)

        message = await ctx.send("Uploading help list...")
        msg = ""
        prefix = ctx.prefix

        # Get and format the help
        for cog in sorted(self.bot.cogs):
            if cog.upper() in COG_EXCEPTIONS:
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
        with open(help_txt, "wb") as myfile:
            myfile.write(msg)

        await ctx.send(file=discord.File(help_txt))
        await message.edit(
            content=f"{self.bot.emote_dict['success']} Uploaded Help-{timestamp}.txt"
        )
        os.remove(help_txt)

    @commands.command(hidden=True, brief="DMs you a list of my servers.")
    @commands.is_owner()
    async def dumpservers(self, ctx):
        """Dumps a timestamped list of servers."""
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
    @permissions.has_permissions(manage_messages=True)
    async def dumproles(self, ctx):
        """
        Usage:  -dumproles
        Alias:  -txtroles
        Output:  Sends a list of roles for the server to your DMs
        Permission: Manage Messages
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

    @commands.command(brief="DMs you a file of server emojis.", aliases=["dumpemojis"])
    @commands.guild_only()
    @permissions.has_permissions(manage_messages=True)
    async def dumpemotes(self, ctx):
        """
        Usage:  -dumpemotes
        Alias:  -dumpemojis
        Output:  Sends a list of server emojis to your DMs
        Permission: Manage Messages
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
    @permissions.has_permissions(manage_server=True)
    async def dumpmessages(
        self, ctx, messages: int = 25, *, chan: discord.TextChannel = None
    ):
        """
        Usage:      -dumpmessages [message amount] [channel]
        Aliases:    -messagedump, -dumpmessages, logmessages
        Permission: Manage Server
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
    @permissions.has_permissions(manage_server=True)
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
    @permissions.has_permissions(manage_server=True)
    async def dumphumans(self, ctx):
        """
        Usage:      -dumphumans
        Aliases:    -humanlist
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
    @permissions.has_permissions(manage_server=True)
    async def dumpbots(self, ctx):
        """
        Usage:      -dumphumans
        Aliases:    -botlist, -robotlist, dumprobots
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
    @permissions.has_permissions(manage_server=True)
    async def dumpmembers(self, ctx):
        """
        Usage:      -dumpmembers
        Aliases:    -dumpusers, -memberlist, -userlist
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
