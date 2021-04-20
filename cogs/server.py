import datetime

import discord
from discord.ext import commands, menus

from utilities import converters, pagination, permissions, utils


def setup(bot):
    bot.add_cog(Server(bot))


class Server(commands.Cog):
    """
    Module for all server stats
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.command(brief="Check when a user joined the server.")
    @commands.guild_only()
    async def joinedat(self, ctx, *, user: discord.Member = None):
        """
        Usage: -joinedat <member>
        Output: Shows when the passed user joined the server
        Notes:
            Will default to youself if no member is passed.
        """
        user = user or ctx.author

        embed = discord.Embed(colour=user.top_role.colour.value)
        embed.set_thumbnail(url=user.avatar_url)
        embed.description = (
            f"**{user}** joined **{ctx.guild.name}**\n{utils.date(user.joined_at)}"
        )
        await ctx.send(reference=self.bot.rep_ref(ctx), embed=embed)

    @commands.command(
        brief="Show the join position of a user.", aliases=["joinposition"]
    )
    @commands.guild_only()
    async def joinpos(self, ctx, *, member: discord.Member = None):
        """
        Usage: -joinpos <member>
        Alias: -joinposition
        Example: -joinpos @Hecate
        Output: Tells when a user joined compared to other users.
        """

        if member is None:
            member = ctx.author

        joinedList = []
        for mem in ctx.message.guild.members:
            joinedList.append({"ID": mem.id, "Joined": mem.joined_at})

        # sort the users by join date
        joinedList = sorted(
            joinedList,
            key=lambda x: x["Joined"].timestamp() if x["Joined"] != None else -1,
        )

        check_item = {"ID": member.id, "Joined": member.joined_at}

        total = len(joinedList)
        position = joinedList.index(check_item) + 1

        before = ""
        after = ""

        msg = "**{}'s** join position is **{:,}**.".format(
            member.display_name, position, total
        )
        if position - 1 == 1:
            # We have previous members
            before = "**1** user"
        elif position - 1 > 1:
            before = "**{:,}** users".format(position - 1)
        if total - position == 1:
            # There were users after as well
            after = "**1** user"
        elif total - position > 1:
            after = "**{:,}** users".format(total - position)
        # Build the string!
        if len(before) and len(after):
            # Got both
            msg += "\n\n{} joined before, and {} after.".format(before, after)
        elif len(before):
            # Just got before
            msg += "\n\n{} joined before.".format(before)
        elif len(after):
            # Just after
            msg += "\n\n{} joined after.".format(after)
        await ctx.send(msg)

    @commands.command(
        brief="Show who joined at a position.", aliases=["joinedatposition"]
    )
    @commands.guild_only()
    async def joinedatpos(self, ctx, *, position):
        """
        Usage: -joinedatpos <integer>
        Alias: -joinedatposition
        Example: -joinedatpos 34
        Output: Shows the user that joined at the passed position.
        """
        try:
            position = int(position) - 1
            assert -1 < position < len(ctx.guild.members)
        except Exception:
            return await ctx.send(
                "Position must be an int between 1 and {:,}".format(
                    len(ctx.guild.members)
                )
            )
        joinedList = [
            {"member": mem, "joined": mem.joined_at} for mem in ctx.guild.members
        ]
        # sort the users by join date
        joinedList = sorted(
            joinedList,
            key=lambda x: x["joined"].timestamp() if x["joined"] != None else -1,
        )
        join = joinedList[position]
        msg = "**{}** joined at position **{:,}**.".format(
            join["member"].display_name, position + 1
        )
        await ctx.send(msg)

    @commands.command(brief="Show the first users to join.")
    @commands.guild_only()
    async def firstjoins(self, ctx):
        """
        Usage: -firstjoins
        Output: Embed of members to first join the current server.
        """
        our_list = []
        for member in ctx.guild.members:
            our_list.append(
                {
                    "name": member.display_name,
                    "value": "{} UTC".format(
                        member.joined_at.strftime("%Y-%m-%d %I:%M %p")
                        if member.joined_at != None
                        else "Unknown"
                    ),
                    "date": member.joined_at,
                }
            )
        our_list = sorted(
            our_list, key=lambda x: x["date"].timestamp() if x["date"] != None else -1
        )
        p = pagination.MainMenu(
            pagination.FieldPageSource(
                entries=[
                    ("{}. {}".format(y + 1, x["name"]), x["value"])
                    for y, x in enumerate(our_list)
                ],
                title="First Members to Join {} ({:,} total)".format(
                    ctx.guild.name, len(ctx.guild.members)
                ),
                per_page=15,
            )
        )

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    @commands.command(brief="Show the latest users to join.")
    @commands.guild_only()
    async def recentjoins(self, ctx):
        """
        Usage: -recentjoins
        Output: Embed of most recent members to join the server.
        """
        our_list = []
        for member in ctx.guild.members:
            our_list.append(
                {
                    "name": member.display_name,
                    "value": "{} UTC".format(
                        member.joined_at.strftime("%Y-%m-%d %I:%M %p")
                        if member.joined_at != None
                        else "Unknown"
                    ),
                    "date": member.joined_at,
                }
            )
        our_list = sorted(
            our_list,
            key=lambda x: x["date"].timestamp() if x["date"] != None else -1,
            reverse=True,
        )
        p = pagination.MainMenu(
            pagination.FieldPageSource(
                entries=[
                    ("{}. {}".format(y + 1, x["name"]), x["value"])
                    for y, x in enumerate(our_list)
                ],
                title="First Members to Join {} ({:,} total)".format(
                    ctx.guild.name, len(ctx.guild.members)
                ),
                per_page=15,
            )
        )

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    @commands.command(brief="Show the server's channels.", aliases=["channels"])
    @commands.guild_only()
    @permissions.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 20, commands.BucketType.guild)
    @permissions.has_permissions(manage_messages=True)
    async def listchannels(self, ctx, guild: int = None):
        """
        Usage:      -listchannels
        Alias:      -channels
        Output:     Embed of all server channels
        Permission: Manage Messages
        """
        if guild is None:
            guild = ctx.guild.id
        guild = self.bot.get_guild(guild)
        channel_categories = {}

        for chn in sorted(guild.channels, key=lambda c: c.position):
            if (
                isinstance(chn, discord.CategoryChannel)
                and chn.id not in channel_categories
            ):
                channel_categories[chn.id] = []
            else:
                category = chn.category_id
                if category not in channel_categories:
                    channel_categories[category] = []

                channel_categories[category].append(chn)

        description = None

        def make_category(channels):
            val = ""
            for chn in sorted(
                channels, key=lambda c: isinstance(c, discord.VoiceChannel)
            ):
                if isinstance(chn, discord.VoiceChannel):
                    val += "\\🔊 "
                else:
                    val += "# "

                val += f"{chn.name}\n"

            return val

        if None in channel_categories:
            description = make_category(channel_categories.pop(None))

        paginator = pagination.Paginator(title="Channels", description=description)

        for category_id in sorted(
            channel_categories.keys(), key=lambda k: ctx.guild.get_channel(k).position
        ):
            category = ctx.guild.get_channel(category_id)

            val = make_category(channel_categories[category_id])

            paginator.add_field(name=category.name.upper(), value=val, inline=False)

        paginator.finalize()

        for page in paginator.pages:
            await ctx.send(reference=self.bot.rep_ref(ctx), embed=page)

    @commands.command(
        brief="Show server information.", aliases=["si", "serverstats", "ss", "server"]
    )
    @commands.guild_only()
    async def serverinfo(self, ctx):
        """
        Usage:    -serverinfo
        Aliases:  -server, -serverstats, si, ss
        Examples: -serverinfo, -ss
        Output:   General stats on the server.
        """
        server = ctx.message.guild
        online = 0
        for i in server.members:
            if (
                str(i.status) == "online"
                or str(i.status) == "idle"
                or str(i.status) == "dnd"
            ):
                online += 1
        all_users = []
        for user in server.members:
            all_users.append("{}#{}".format(user.name, user.discriminator))
        all_users.sort()
        all = "\n".join(all_users)
        total_text_channels = len(server.text_channels)
        total_voice_channels = len(server.voice_channels)
        total_channels = total_text_channels + total_voice_channels
        role_count = len(server.roles)
        emoji_count = len(server.emojis)
        bots = []
        for member in ctx.guild.members:
            if member.bot:
                bots.append(member)
        if str(server.region) == "us-west":
            region = "🇺🇸 US West"
        elif str(server.region) == "us-east":
            region = "🇺🇸 US East"
        elif str(server.region) == "us-central":
            region = "🇺🇸 US Central"
        elif str(server.region) == "us-south":
            region = "🇺🇸 US South"
        elif str(server.region) == "hongkong":
            region = "🇭🇰 Hong Kong"
        elif str(server.region) == "southafrica":
            region = "🇿🇦 South Africa"
        elif str(server.region) == "sydney":
            region = "🇦🇺 Sydney"
        elif str(server.region) == "russia":
            region = "🇷🇺 Russia"
        elif str(server.region) == "europe":
            region = "🇪🇺 Europe"
        elif str(server.region) == "brazil":
            region = "🇧🇷 Brazil"
        elif str(server.region) == "brazil":
            region = "🇸🇬 Singapore"
        elif str(server.region) == "india":
            region = "🇮🇳 India"
        else:
            region = str(server.region).title()

        em = discord.Embed(color=self.bot.constants.embed)
        em.set_thumbnail(url=server.icon_url)
        em.set_author(name=server.name, icon_url=server.icon_url)
        em.set_footer(
            text=f"Server ID: {server.id} | Created on {server.created_at.__format__('%m/%d/%Y')}"
        )
        em.add_field(
            name="Owner",
            value=f"<:owner:810678076497068032> {server.owner}",
            inline=True,
        )
        em.add_field(
            name="Total Members",
            value=f"<:members:810677596453863444> {server.member_count}",
            inline=True,
        )
        em.add_field(
            name="Online Members",
            value=f"<:online:810650040838258711> {online}",
            inline=True,
        )
        em.add_field(
            name="Role Count",
            value=f"<:announce:807097933916405760> {str(role_count)}",
            inline=True,
        )
        em.add_field(name="Region", value=region, inline=True)
        em.add_field(
            name="Emoji Count",
            value=f"<:emoji:810678717482532874> {len(server.emojis)}",
            inline=True,
        )
        em.add_field(
            name="Categories",
            value=f"<:categories:810671569440473119> {len(server.categories)}",
            inline=True,
        )
        em.add_field(
            name="Text Channels",
            value=f"<:textchannel:810659118045331517> {total_text_channels}",
            inline=True,
        )
        em.add_field(
            name="Voice Channels",
            value=f"<:voicechannel:810659257296879684> {total_voice_channels}",
            inline=True,
        )
        await ctx.send(reference=self.bot.rep_ref(ctx), embed=em)

    @commands.command(brief="Show the server mods.", aliases=["moderators"])
    @commands.guild_only()
    async def mods(self, ctx):
        """
        Usage: -mods
        Alias: -moderators
        Output: All the server moderators and their respective status
        """
        message = ""
        all_status = {
            "online": {"users": [], "emoji": "<:online:810650040838258711>"},
            "idle": {"users": [], "emoji": "<:idle:810650560146833429>"},
            "dnd": {"users": [], "emoji": "<:dnd:810650845007708200>"},
            "offline": {"users": [], "emoji": "<:offline:810650959859810384>"},
        }

        for user in ctx.guild.members:
            user_perm = ctx.channel.permissions_for(user)
            if user_perm.kick_members or user_perm.ban_members:
                if not user.bot:
                    all_status[str(user.status)]["users"].append(f"{user}")

        for g in all_status:
            if all_status[g]["users"]:
                message += (
                    f"{all_status[g]['emoji']} `{', '.join(all_status[g]['users'])}`\n"
                )

        await ctx.send(
            reference=self.bot.rep_ref(ctx),
            content=f"Mods in **{ctx.guild.name}:**\n\n{message}",
        )

    @commands.command(brief="Show the server admins.", aliases=["administrators"])
    @commands.guild_only()
    async def admins(self, ctx):
        """
        Usage: -admins
        Alias: -administrators
        Output: All the server admins and their respective status
        """
        message = ""
        all_status = {
            "online": {"users": [], "emoji": "<:online:810650040838258711>"},
            "idle": {"users": [], "emoji": "<:idle:810650560146833429>"},
            "dnd": {"users": [], "emoji": "<:dnd:810650845007708200>"},
            "offline": {"users": [], "emoji": "<:offline:810650959859810384>"},
        }

        for user in ctx.guild.members:
            user_perm = ctx.channel.permissions_for(user)
            if user_perm.administrator:
                if not user.bot:
                    all_status[str(user.status)]["users"].append(f"{user}")

        for g in all_status:
            if all_status[g]["users"]:
                message += (
                    f"{all_status[g]['emoji']} `{', '.join(all_status[g]['users'])}`\n"
                )

        await ctx.send(
            reference=self.bot.rep_ref(ctx),
            content=f"Admins in **{ctx.guild.name}:**\n\n{message}",
        )

    @commands.command(brief="Shows all the server's bots.")
    @commands.guild_only()
    async def listbots(self, ctx, *, guild: converters.DiscordGuild = None):
        """
        Usage: -listbots [server]
        """
        if guild is None:
            guild = ctx.guild

        list_of_bots = [x for x in guild.members if x.bot]
        if not len(list_of_bots):
            # No bots - should... never... happen.
            await ctx.send(
                reference=self.bot.rep_ref(ctx), content=f"This server has no bots."
            )
        else:
            # Got some bots!
            bot_list = []
            for bot in list_of_bots:
                bot_list.append(
                    {
                        "name": str(bot),
                        "value": "Mention: {}\nID: `{}`".format(bot.mention, bot.id),
                    }
                )
            p = pagination.MainMenu(
                pagination.FieldPageSource(
                    entries=[
                        ("{}. {}".format(y + 1, x["name"]), x["value"])
                        for y, x in enumerate(bot_list)
                    ],
                    title="Bots in **{}** ({:,} total)".format(
                        guild.name, len(list_of_bots)
                    ),
                    per_page=10,
                )
            )
            try:
                await p.start(ctx)
            except menus.MenuError as e:
                await ctx.send(e)

    @commands.group(
        brief="Show the most active server users.", invoke_without_command=True
    )
    @commands.guild_only()
    async def activity(self, ctx, unit: str = "month"):
        """
        Usage: -activity [characters] [unit of time]
        Output: Top message senders in the server
        Permission: Manage Messages
        """
        unit = unit.lower()
        time_dict = {"day": 86400, "week": 604800, "month": 2592000, "year": 31556952}
        if unit not in time_dict:
            unit = "month"
        time_seconds = time_dict.get(unit, 2592000)
        now = int(datetime.datetime.utcnow().timestamp())
        diff = now - time_seconds
        query = """SELECT COUNT(*) as c, author_id FROM messages WHERE server_id = $1 AND unix > $2 GROUP BY author_id ORDER BY c DESC LIMIT 25"""
        stuff = await self.bot.cxn.fetch(query, ctx.guild.id, diff)

        e = discord.Embed(
            title=f"Activity for the last {unit}",
            description=f"{sum(x[0] for x in stuff)} messages from {len(stuff)} user{'' if len(stuff) == 1 else 's'}",
            color=self.bot.constants.embed,
        )
        for n, v in enumerate(stuff[:24]):
            try:
                name = ctx.guild.get_member(int(v[1])).name
            except AttributeError:
                name = f"Unknown member"
            e.add_field(
                name=f"{n+1}. {name}",
                value=f"{v[0]} message{'' if int(v[0]) == 1 else 's'}",
            )

        await ctx.send(reference=self.bot.rep_ref(ctx), embed=e)

    @activity.command(aliases=["characters"])
    @commands.guild_only()
    async def char(self, ctx, unit: str = "day"):
        if ctx.author.id not in self.bot.constants.owners:
            return
        unit = unit.lower()
        time_dict = {"day": 86400, "week": 604800, "month": 2592000, "year": 31556952}
        if unit not in time_dict:
            unit = "month"
        time_seconds = time_dict.get(unit, 2592000)
        now = int(datetime.datetime.utcnow().timestamp())
        diff = now - time_seconds
        query = """SELECT SUM(LENGTH(content)) as c, author_id, COUNT(*) FROM messages WHERE server_id = $1 AND unix > $2 GROUP BY author_id ORDER BY c DESC LIMIT 25"""
        stuff = await self.bot.cxn.fetch(query, ctx.guild.id, diff)
        e = discord.Embed(
            title="Current leaderboard",
            description=f"Activity for the last {unit}",
            color=self.bot.constants.embed,
        )
        for n, v in enumerate(stuff):
            try:
                name = ctx.guild.get_member(int(v[1])).name
            except AttributeError:
                name = "Unknown member"
            # ratio = int(v[0] / 1440)
            # e.add_field(name=f"{n+1}. {name}", value=f"{v[0]:,} chars ({ratio} chars/minute)")
            e.add_field(name=f"{n+1}. {name}", value=f"{v[0]:,} chars")

        await ctx.send(reference=self.bot.rep_ref(ctx), embed=e)

    @commands.command(brief="Get info about a channel.")
    @commands.guild_only()
    async def channelinfo(self, ctx, *, channel: converters.DiscordChannel = None):
        """
        Usage: -channelinfo
        Output:
            Specific info on a given channel
        Notes:
            If no channel is specified,
            current channel will be used.
        """
        channel = channel or ctx.channel
        em = discord.Embed()
        em.color = self.bot.constants.embed
        em.add_field(
            name="Channel", value="{0.name} ({0.id})".format(channel), inline=False
        )
        em.add_field(
            name="Server",
            value="{0.guild.name} ({0.guild.id})".format(channel),
            inline=False,
        )
        em.add_field(
            name="Type", value="{}".format(type(channel).__name__), inline=False
        )
        em.add_field(
            name="Created", value=utils.format_time(channel.created_at), inline=False
        )
        await ctx.send(reference=self.bot.rep_ref(ctx), embed=em)

    @commands.command(brief="Show a channel topic.")
    @commands.guild_only()
    async def topic(self, ctx, *, channel: converters.DiscordChannel = None):
        """Quote the channel topic at people."""
        if channel is None:
            channel = ctx.channel
        await ctx.send(
            content=("**Channel topic:** " + channel.topic)
            if channel.topic
            else "No topic set.",
            reference=self.bot.rep_ref(ctx),
        )
