import contextlib
import datetime
import dis
import fnmatch
import io
import math
import os
import random
import textwrap
import traceback

import discord
from discord import message
from discord.ext import commands, menus
from PythonGists import PythonGists

from utilities import converters, pagination, checks, helpers
from utilities import decorators


def setup(bot):
    bot.add_cog(Botadmin(bot))


class Botadmin(commands.Cog):
    """
    Bot admin only stats cog.
    """

    def __init__(self, bot):
        self.bot = bot

    # This is a bot admin only cog
    async def cog_check(self, ctx):
        if checks.is_admin(ctx):
            return True
        return

    @decorators.command(
        name="message",
        aliases=["pm", "dm"],
        brief="DM any user the bot knows.",
        hidden=True,
    )
    @commands.is_owner()
    async def _message(self, ctx, user_id: int, *, message: str):
        """
        Usage:       -message <id> <message>
        Alias:       -pm, -dm
        Example:     -dm 384059834985989 Hi
        Permissions: Bot Owner
        """
        user = self.bot.get_user(user_id)
        if not user:
            return await ctx.send_or_reply(
                content=f"Could not find any UserID matching **{user_id}**",
            )

        try:
            await user.send(message)
            await ctx.send_or_reply(
                content=f"✉️ Sent a DM to **{user_id}**",
            )
        except discord.Forbidden:
            await ctx.send_or_reply(
                "This user might be having DMs blocked or it's a bot account..."
            )

    @decorators.command(brief="Create a server invite.")
    async def inv(self, ctx, server: converters.BotServer = None):
        """
        Usage: -inv <server>
        Output: Invite for that server (if bot could create it)
        """
        if server is None:
            server = ctx.guild
        if isinstance(server, list):
            if len(server) > 1:
                msg = ""
                for x in server:
                    guild = self.bot.get_guild(int(x))
                    msg += f"ID: {guild.id} Name: {guild.name}\n"
                await ctx.send_or_reply(
                    content=f"Multiple results. Please use the server ID instead",
                )
                t = pagination.MainMenu(
                    pagination.TextPageSource(text=msg, max_size=500)
                )
                try:
                    return await t.start(ctx)
                except menus.MenuError as e:
                    await ctx.send_or_reply(e)
            else:
                try:
                    server = self.bot.get_guild(int(server[0]))
                except IndexError:
                    return await ctx.send_or_reply(
                        content=f"Couldn't find that server.",
                    )

        s = random.choice(server.text_channels)
        try:
            inv = await s.create_invite()
        except Exception as e:
            return await ctx.send_or_reply(e)
        await ctx.send_or_reply(inv)

    @decorators.command(
        brief="Lists the servers I'm connected to.", aliases=["servers", "serverlist"]
    )
    async def listservers(self, ctx):
        """
        Usage: -listservers
        Alias: -servers, -serverlist
        Output: Lists the servers I'm connected to.
        """
        our_list = []
        for guild in self.bot.guilds:
            our_list.append(
                {
                    "name": guild.name,
                    "value": "{:,} member{}\nID: `{}`".format(
                        len(guild.members),
                        "" if len(guild.members) == 1 else "s",
                        guild.id,
                    ),
                    "users": len(guild.members),
                }
            )
        p = pagination.MainMenu(
            pagination.FieldPageSource(
                entries=[
                    ("{}. {}".format(y + 1, x["name"]), x["value"])
                    for y, x in enumerate(our_list)
                ],
                title="Server's I'm Connected To ({:,} total)".format(
                    len(self.bot.guilds)
                ),
                per_page=15,
            )
        )

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @decorators.command(brief="Show most member servers.")
    async def topservers(self, ctx):
        """
        Usage: -topservers
        Output: The servers with the most memebers
        """
        our_list = []
        for guild in self.bot.guilds:
            our_list.append(
                {
                    "name": guild.name,
                    "value": "{:,} member{}".format(
                        len(guild.members), "" if len(guild.members) == 1 else "s"
                    ),
                    "users": len(guild.members),
                }
            )
        our_list = sorted(our_list, key=lambda x: x["users"], reverse=True)
        p = pagination.MainMenu(
            pagination.FieldPageSource(
                entries=[
                    ("{}. {}".format(y + 1, x["name"]), x["value"])
                    for y, x in enumerate(our_list)
                ],
                title="Top Servers By Population ({} total)".format(
                    len(self.bot.guilds)
                ),
                per_page=15,
            )
        )

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @decorators.command(brief="Show least member servers.")
    async def bottomservers(self, ctx):
        """
        Usage: -bottomservers
        Output: The servers with the least memebers
        """
        our_list = []
        for guild in self.bot.guilds:
            our_list.append(
                {
                    "name": guild.name,
                    "value": "{:,} member{}".format(
                        len(guild.members), "" if len(guild.members) == 1 else "s"
                    ),
                    "users": len(guild.members),
                }
            )
        our_list = sorted(our_list, key=lambda x: x["users"])
        p = pagination.MainMenu(
            pagination.FieldPageSource(
                entries=[
                    ("{}. {}".format(y + 1, x["name"]), x["value"])
                    for y, x in enumerate(our_list)
                ],
                title="Bottom Servers By Population ({:,} total)".format(
                    len(self.bot.guilds)
                ),
                per_page=15,
            )
        )

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @decorators.command(brief="Show first joined servers.")
    async def firstservers(self, ctx):
        """
        Usage: -firstservers
        Output: Lists the first servers I joined
        """
        our_list = []
        for guild in self.bot.guilds:
            bot = guild.me
            our_list.append(
                {
                    "name": "{} ({:,} member{})".format(
                        guild.name,
                        len(guild.members),
                        "" if len(guild.members) == 1 else "s",
                    ),
                    "value": "{} UTC".format(
                        bot.joined_at.strftime("%Y-%m-%d %I:%M %p")
                        if bot.joined_at is not None
                        else "Unknown"
                    ),
                    "date": bot.joined_at,
                }
            )
        our_list = sorted(
            our_list,
            key=lambda x: x["date"].timestamp() if x["date"] is not None else -1,
        )
        p = pagination.MainMenu(
            pagination.FieldPageSource(
                entries=[
                    ("{}. {}".format(y + 1, x["name"]), x["value"])
                    for y, x in enumerate(our_list)
                ],
                title="First Servers I Joined ({:,} total)".format(
                    len(self.bot.guilds)
                ),
                per_page=15,
            )
        )

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @decorators.command(brief="Show latest joined servers.", aliases=["lastservers"])
    async def recentservers(self, ctx):
        """
        Usage: -recentservers
        Alias: -lastservers
        Output: Lists the most recent servers I've joined
        """
        our_list = []
        for guild in self.bot.guilds:
            bot = guild.me
            our_list.append(
                {
                    "name": "{} ({} member{})".format(
                        guild.name,
                        len(guild.members),
                        "" if len(guild.members) == 1 else "s",
                    ),
                    "value": "{} UTC".format(
                        bot.joined_at.strftime("%Y-%m-%d %I:%M %p")
                        if bot.joined_at is not None
                        else "Unknown"
                    ),
                    "date": bot.joined_at,
                }
            )
        our_list = sorted(
            our_list,
            key=lambda x: x["date"].timestamp() if x["date"] is not None else -1,
            reverse=True,
        )
        p = pagination.MainMenu(
            pagination.FieldPageSource(
                entries=[
                    ("{}. {}".format(y + 1, x["name"]), x["value"])
                    for y, x in enumerate(our_list)
                ],
                title="Most Recent Servers I Joined ({:,} total)".format(
                    len(self.bot.guilds)
                ),
                per_page=15,
            )
        )

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    # Basic info commands
    @decorators.command(brief="Show commands in the cache.")
    async def cachedcommands(self, ctx, limit=20):
        """
        Usage: -cachedcommands
        Output:
            Show the commands in the bot's cache
        """
        counter = self.bot.command_stats
        width = len(max(counter, key=len))
        total = sum(counter.values())

        if limit > 0:
            common = counter.most_common(limit)
        else:
            common = counter.most_common()[limit:]
        output = "\n".join("{0:<{1}} : {2}".format(k, width, c) for k, c in common)

        p = pagination.MainMenu(pagination.TextPageSource(output, prefix="```yaml"))
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @decorators.command(aliases=["ns"], brief="List all bot nicknames.")
    async def nickscan(self, ctx):
        """
        Usage: -nickscan
        Alias: -ns
        Output:
            All my nicknames across all servers
        """
        nick = ""
        bool = None
        for guild in self.bot.guilds:
            if (
                len(
                    nick
                    + "**Server:** `{}` **Nick:** `{}`\n".format(
                        guild.name, guild.get_member(self.bot.user.id).nick
                    )
                )
                > 2000
            ):
                bool = False
                break
            if guild.get_member(self.bot.user.id).nick:
                nick += "**Server:** `{}` **Nick:** `{}`\n".format(
                    guild.name, guild.get_member(self.bot.user.id).nick
                )
        if not nick:
            await ctx.send_or_reply(content="I have no nicknames set!")
        else:
            if len(nick) <= 1964 and bool is False:
                nick += "**Could not print the rest, sorry.**"
            elif bool is False:
                bool = True
            try:
                embed = discord.Embed(
                    title="Servers I Have Nicknames In", color=self.bot.constants.embed
                )
                embed.description = nick
                await ctx.send_or_reply(embed=embed)
            except BaseException:
                await ctx.send_or_reply(content="```{}```".format(nick))
            if bool is True:
                await ctx.send_or_reply(
                    content="**Could not print the rest, sorry.**",
                )

    def _get_imports(self, file_name):
        if not os.path.exists("cogs/" + file_name):
            return []
        file_string = open("cogs/" + file_name, "rb").read().decode("utf-8")
        instructions = dis.get_instructions(file_string)
        imports = [__ for __ in instructions if "IMPORT" in __.opname]
        i = []
        for instr in imports:
            if not instr.opname == "IMPORT_FROM":
                continue
            i.append(instr.argval)
        cog_imports = []
        for f in i:
            if os.path.exists("cogs/" + f + ".py"):
                cog_imports.append(f)
        return cog_imports

    def _get_imported_by(self, file_name):
        ext_list = []
        for ext in os.listdir("cogs"):
            # Avoid reloading Settings and Mute
            if not ext.lower().endswith(".py") or ext == file_name:
                continue
            if file_name[:-3] in self._get_imports(ext):
                ext_list.append(ext)
        return ext_list

    async def _send_embed(self, ctx, embed, pm=False):
        # Helper method to send embeds to their proper location
        if pm is True and not ctx.channel == ctx.author.dm_channel:
            # More than 2 pages, try to dm
            try:
                await ctx.send_or_reply(embed=embed)
                # await ctx.author.send(embed=embed)
                # await ctx.message.add_reaction("📬")
            except discord.Forbidden:
                await ctx.send_or_reply(embed=embed)
            return
        await ctx.send_or_reply(embed=embed)

    def _is_submodule(self, parent, child):
        return parent == child or child.startswith(parent + ".")

    @decorators.command(
        hidden=True, brief="Show info on an extension.", aliases=["ext"]
    )
    async def extension(self, ctx, *, extension=None):
        """
        Usage: -extension <extension>
        Alias: -ext
        Outputs the cogs attatched to the passed extension.
        """
        if extension is None:
            # run the extensions command
            await ctx.invoke(self.extensions)
            return

        cog_list = []
        for e in self.bot.extensions:
            if not str(e[5:]).lower() == extension.lower():
                continue
            # At this point - we should've found it
            # Get the extension
            b_ext = self.bot.extensions.get(e)
            for cog in self.bot.cogs:
                # Get the cog
                b_cog = self.bot.get_cog(cog)
                if self._is_submodule(b_ext.__name__, b_cog.__module__):
                    # Submodule - add it to the list
                    cog_list.append(str(cog))
            # build the embed
            help_embed = discord.Embed(color=self.bot.constants.embed)

            help_embed.title = str(e[5:]) + ".py" + " Extension"
            if len(cog_list):
                total_commands = 0
                total_listeners = 0
                for cog in cog_list:
                    total_commands += len(self.bot.get_cog(cog).get_commands())
                    total_listeners += len(self.bot.get_cog(cog).get_listeners())
                if len(cog_list) > 1:
                    comm = "total command"
                    event = "total event"
                else:
                    comm = "command"
                    event = "event"
                if total_commands == 1:
                    comm = "> 1 " + comm
                else:
                    comm = "> {:,} {}s".format(total_commands, comm)
                if total_listeners == 1:
                    event = "> 1 " + event
                else:
                    event = "> {:,} {}s".format(total_listeners, event)
                help_embed.add_field(name=", ".join(cog_list), value=comm, inline=True)
                help_embed.add_field(name=", ".join(cog_list), value=event, inline=True)
            else:
                help_embed.add_field(name="No Cogs", value="> 0 commands", inline=True)
            await ctx.send_or_reply(embed=help_embed)
            return
        await ctx.send_or_reply(content="I couldn't find that extension.")

    @decorators.command(
        hidden=True, brief="List all extensions and cogs.", aliases=["exts"]
    )
    async def extensions(self, ctx):
        """
        Usage: -extensions
        Alias: -exts
        Output: Lists all extensions and their corresponding cogs.
        """
        # Build the embed
        if isinstance(ctx.author, discord.Member):
            help_embed = discord.Embed(color=self.bot.constants.embed)
        else:
            help_embed = discord.Embed(color=random.choice(self.colors))

        # Setup blank dict
        ext_list = {}
        cog_less = []
        for extension in self.bot.extensions:
            if not str(extension)[5:] in ext_list:
                ext_list[str(extension)[5:]] = []
            # Get the extension
            b_ext = self.bot.extensions.get(extension)
            for cog in self.bot.cogs:
                # Get the cog
                b_cog = self.bot.get_cog(cog)
                if self._is_submodule(b_ext.__name__, b_cog.__module__):
                    # Submodule - add it to the list
                    ext_list[str(extension)[5:]].append(str(cog))
            if not len(ext_list[str(extension)[5:]]):
                ext_list.pop(str(extension)[5:])
                cog_less.append(str(extension)[5:])

        if not len(ext_list) and not len(cog_less):
            # no extensions - somehow... just return
            return

        # Get all keys and sort them
        key_list = list(ext_list.keys())
        key_list = sorted(key_list)

        if len(cog_less):
            ext_list["Cogless"] = cog_less
            # add the cogless extensions at the end
            key_list.append("Cogless")

        to_pm = len(ext_list) > 24
        page_count = 1
        page_total = math.ceil(len(ext_list) / 24)
        if page_total > 1:
            help_embed.title = "Extensions (Page {:,} of {:,})".format(
                page_count, page_total
            )
        else:
            help_embed.title = "Extensions"
        for embed in key_list:
            if len(ext_list[embed]):
                help_embed.add_field(
                    name=embed, value="> " + ", ".join(ext_list[embed]), inline=True
                )
            else:
                help_embed.add_field(name=embed, value="> None", inline=True)
            # 25 field max - send the embed if we get there
            if len(help_embed.fields) >= 24:
                if page_total == page_count:
                    if len(ext_list) == 1:
                        help_embed.set_footer(text="1 Extension Total")
                    else:
                        help_embed.set_footer(
                            text="{} Extensions Total".format(len(ext_list))
                        )
                await self._send_embed(ctx, help_embed, to_pm)
                help_embed.clear_fields()
                page_count += 1
                if page_total > 1:
                    help_embed.title = "Extensions (Page {:,} of {:,})".format(
                        page_count, page_total
                    )

        if len(help_embed.fields):
            if len(ext_list) == 1:
                help_embed.set_footer(text="1 Extension Total")
            else:
                help_embed.set_footer(text="{} Extensions Total".format(len(ext_list)))
            await self._send_embed(ctx, help_embed, to_pm)

    @decorators.command(
        aliases=["emojicount", "ec", "botemojis"],
        brief="Bot emoji count across all servers.",
    )
    async def emotecount(self, ctx):
        """
        Usage: emotecount
        Aliases: {0}emojicount, {0}ec, {0}botemojis
        Output:
            Emoji count accross all servers
        """
        large_msg = False
        msg = ""
        totalecount = 0
        for g in self.bot.guilds:
            ecount = 0
            for e in g.emojis:
                ecount = ecount + 1
                totalecount = totalecount + 1
            msg = msg + (g.name + ": " + str(ecount)) + "\n"
        if len(msg) > 1900:
            msg = PythonGists.Gist(
                description="Emoji Count for " + self.bot.user.name,
                content=msg,
                name="emoji.txt",
            )
            large_msg = True
        embed = discord.Embed(
            title="Emoji count for " + self.bot.user.name,
            color=self.bot.constants.embed,
        )
        if large_msg:
            embed.add_field(
                name="Individual Server Emote Count",
                value="[Gist of Server Emote Count](" + msg + ")",
                inline=False,
            )
        else:
            embed.add_field(
                name="Individual Server Emote Count", value=msg, inline=False
            )
        embed.add_field(name="Total Emote Count", value=str(totalecount), inline=False)
        await ctx.send_or_reply(embed=embed)

    @decorators.command(
        rest_is_raw=True,
        hidden=True,
        aliases=["say"],
        brief="Echo a message.",
        permissions=["bot_admin"],
        botperms=["manage_messages"],
    )
    @checks.bot_has_perms(manage_messages=True)
    @checks.is_bot_admin()
    async def echo(self, ctx, *, content):
        """
        Usage {0}echo
        Alias: {0}say
        Output:
            Deletes the command invocation
            and resends the exact content.
        """
        await ctx.message.delete()
        await ctx.send_or_reply(content)

    @decorators.command(
        name="del",
        rest_is_raw=True,
        hidden=True,
        brief="Delete a message.",
        implemented="2021-05-05 05:12:24.354214",
        updated="2021-05-05 05:12:24.354214",
    )
    @checks.is_bot_admin()
    async def _del(self, ctx, *, msg_id: int):
        """
        Usage {0}del
        Output:
            Delete a specific message ID.
        """
        # Ever accidentally have the bot post a password
        # in a server you can't delete it's message in?
        msg = ctx.channel.get_partial_message(msg_id)
        try:
            await msg.delete()
        except Exception as e:
            ctx.author.fail(e)
        await ctx.react(self.bot.emote_dict["success"])

    @decorators.command()
    @checks.is_bot_admin()
    @checks.bot_has_perms(add_reactions=True, external_emojis=True)
    async def sss(self, ctx, user: converters.DiscordUser = None):
        if user is None:
            user = ctx.author

        shared = []
        for guild in self.bot.guilds:
            for member in guild.members:
                if member.id == user.id:
                    shared.append((guild.id, guild.name))

        width = max([len(str(x[0])) for x in shared])
        formatted = "\n".join([f"{str(x[0]).ljust(width)} : {x[1]}" for x in shared])
        p = pagination.MainMenu(
            pagination.TextPageSource(formatted, prefix="```fix", max_size=500)
        )
        await ctx.send_or_reply(f"** I share {len(shared)} servers with `{user}`**")
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @decorators.command(
        aliases=["guildinfo", "gi"],
        brief="Get stats on a bot server.",
        implemented="2021-03-17 22:48:40.720122",
        updated="2021-05-06 00:57:41.774846",
    )
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    @checks.is_bot_admin()
    async def guild(self, ctx, *, argument=None):
        """
        Usage: {0}guild [server]
        Alias: {0}guildinfo, {0}gi
        Output:
            Lists some info about the
            current or specified server.
        """
        if not argument:
            guild = ctx.guild
        options = await converters.BotServer().convert(ctx, argument)
        option_dict = dict()
        if isinstance(options, list):
            for x in options:
                option_dict[x.name] = x
            guild, message = await helpers.choose(ctx, argument, option_dict)
            if not guild:
                return
        else:
            guild = options
        server_embed = discord.Embed(color=self.bot.constants.embed)
        server_embed.title = guild.name

        # Get localized user time
        local_time = datetime.datetime.utcnow()
        # local_time = UserTime.getUserTime(ctx.author, self.settings, guild.created_at)
        time_str = "{}".format(local_time)

        server_embed.description = "Created at {}".format(time_str)
        online_members = 0
        bot_member = 0
        bot_online = 0
        for member in guild.members:
            if member.bot:
                bot_member += 1
                if not member.status == discord.Status.offline:
                    bot_online += 1
                continue
            if not member.status == discord.Status.offline:
                online_members += 1
        # bot_percent = "{:,g}%".format((bot_member/len(guild.members))*100)
        try:
            rounded = round(
                (online_members / (len(guild.members) - bot_member) * 100), 2
            )
        except ZeroDivisionError:
            rounded = 0
        user_string = "{:,}/{:,} online ({:,g}%)".format(
            online_members, len(guild.members) - bot_member, rounded
        )
        b_string = "bot" if bot_member == 1 else "bots"
        user_string += "\n{:,}/{:,} {} online ({:,g}%)".format(
            bot_online, bot_member, b_string, round((bot_online / bot_member) * 100, 2)
        )
        # server_embed.add_field(name="Members", value="{:,}/{:,} online ({:.2f}%)\n{:,} {} ({}%)".format(online_members, len(guild.members), bot_percent), inline=True)
        server_embed.add_field(
            name="Members ({:,} total)".format(len(guild.members)),
            value=user_string,
            inline=True,
        )
        server_embed.add_field(name="Roles", value=str(len(guild.roles)), inline=False)
        chandesc = "{:,} text, {:,} voice".format(
            len(guild.text_channels), len(guild.voice_channels)
        )
        server_embed.add_field(name="Channels", value=chandesc, inline=False)
        server_embed.add_field(
            name="Owner",
            value=guild.owner.name + "#" + guild.owner.discriminator,
            inline=True,
        )
        server_embed.add_field(
            name="AFK Channel", value=guild.afk_channel, inline=False
        )
        server_embed.add_field(
            name="Verification", value=guild.verification_level, inline=False
        )
        server_embed.add_field(name="Voice Region", value=guild.region, inline=False)
        # server_embed.add_field(name="Shard ID", value="{}/{}".format(guild.shard_id+1, self.bot.shard_count), inline=False)
        server_embed.add_field(
            name="Nitro Boosts",
            value="{} (level {})".format(
                guild.premium_subscription_count, guild.premium_tier
            ),
            inline=False,
        )
        # Find out where in our join position this server is
        joinedList = []
        popList = []
        for g in self.bot.guilds:
            joinedList.append({"ID": g.id, "Joined": g.me.joined_at})
            popList.append({"ID": g.id, "Population": len(g.members)})

        # sort the guilds by join date
        joinedList = sorted(
            joinedList,
            key=lambda x: x["Joined"].timestamp() if x["Joined"] is not None else -1,
        )
        popList = sorted(popList, key=lambda x: x["Population"], reverse=True)

        check_item = {"ID": guild.id, "Joined": guild.me.joined_at}
        total = len(joinedList)
        position = joinedList.index(check_item) + 1
        server_embed.add_field(
            name="Join Position",
            value="{:,} of {:,}".format(position, total),
            inline=False,
        )

        # Get our population position
        check_item = {"ID": guild.id, "Population": len(guild.members)}
        total = len(popList)
        position = popList.index(check_item) + 1
        server_embed.add_field(
            name="Population Rank",
            value="{:,} of {:,}".format(position, total),
            inline=False,
        )

        emojitext = ""
        emojifields = []
        disabledemojis = 0
        twitchemojis = 0
        for i, emoji in enumerate(guild.emojis):
            if not emoji.available:
                disabledemojis += 1
                continue
            if emoji.managed:
                twitchemojis += 1
                continue
            emojiMention = "<{}:{}:{}>".format(
                "a" if emoji.animated else "", emoji.name, emoji.id
            )
            test = emojitext + emojiMention
            if len(test) > 1024:
                # TOOO BIIIIIIIIG
                emojifields.append(emojitext)
                emojitext = emojiMention
            else:
                emojitext = emojitext + emojiMention

        if len(emojitext):
            emojifields.append(emojitext)  # Add any leftovers
        if twitchemojis:
            emojifields.append("{:,} managed".format(twitchemojis))
        if disabledemojis:
            emojifields.append(
                "{:,} unavailable".format(disabledemojis)
            )  # Add the disabled if any

        server_embed.set_thumbnail(
            url=guild.icon_url if len(guild.icon_url) else ctx.author.default_avatar_url
        )
        server_embed.set_footer(text="Server ID: {}".format(guild.id))
        # Let's send all the embeds we need finishing off with extra emojis as
        # needed
        for i, e in enumerate(emojifields):
            name = (
                "Disabled Emojis"
                if e.lower().endswith("unavailable")
                else "Twitch Emojis"
                if e.lower().endswith("managed")
                else "Emojis ({} of {})".format(i + 1, len(emojifields))
            )
            server_embed.add_field(name=name, value=e, inline=False)
            if len(server_embed) > 6000:  # too big
                server_embed.remove_field(len(server_embed.fields) - 1)
                await ctx.send_or_reply(embed=server_embed)
                server_embed = discord.Embed(color=self.bot.constants.embed)
                server_embed.title = guild.name
                server_embed.set_thumbnail(
                    url=guild.icon_url
                    if len(guild.icon_url)
                    else ctx.author.default_avatar_url
                )
                server_embed.set_footer(text="Server ID: {}".format(guild.id))
                server_embed.description = "Continued Emojis:"
                server_embed.add_field(name=name, value=e, inline=False)
        if len(server_embed.fields):
            if message:
                try:
                    await message.edit(embed=server_embed)
                except BaseException:
                    await ctx.send_or_reply(embed=server_embed)
            else:
                await ctx.send_or_reply(embed=server_embed)

    @decorators.command(brief="Show members for a server.")
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    async def members(self, ctx, *, argument=None):
        """
        Usage: {0}members
        Output: Lists the members of a passed server
        """
        if not argument:
            guild = ctx.guild
        options = await converters.BotServer().convert(ctx, argument)
        option_dict = dict()
        if isinstance(options, list):
            for x in options:
                option_dict[x.name] = x
            guild, message = await helpers.choose(ctx, argument, option_dict)
            if not guild:
                return
        else:
            guild = options
        members = guild.members
        member_list = []
        for entity in members:
            member_list.append(
                {
                    "name": entity,
                    "value": "Mention: {}\nID: `{}`\nNickname: {}".format(
                        entity.mention, entity.id, entity.display_name
                    ),
                }
            )
        p = pagination.MainMenu(
            pagination.FieldPageSource(
                entries=[
                    ("{}. {}".format(y + 1, x["name"]), x["value"])
                    for y, x in enumerate(member_list)
                ],
                per_page=10,
                title=f"Member list for **{guild.name}** ({len(members):,} total)",
            )
        )
        if message:
            await message.delete()
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)
