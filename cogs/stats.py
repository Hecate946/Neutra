import re
import discord

from collections import Counter
from discord.ext import commands, menus

from utilities import converters, utils, pagination, permissions

def setup(bot):
    bot.add_cog(Stats(bot))

class Stats(commands.Cog):
    """
    Module for server stats
    """
    def __init__(self, bot):
        self.bot = bot

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
        await ctx.send_or_reply(embed=em)

    @commands.command(brief="Show a channel topic.")
    @commands.guild_only()
    async def topic(self, ctx, *, channel: converters.DiscordChannel = None):
        """Quote the channel topic at people."""
        if channel is None:
            channel = ctx.channel
        await ctx.send_or_reply(
            content=("**Channel topic:** " + channel.topic)
            if channel.topic
            else "No topic set.",
        )


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
            value=f"{self.bot.emote_dict['announce']} {str(role_count)}",
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
        await ctx.send_or_reply(embed=em)

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

        await ctx.send_or_reply(
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

        await ctx.send_or_reply(
            content=f"Admins in **{ctx.guild.name}:**\n\n{message}",
        )


    @commands.command(brief="Emoji usage tracking.")
    @commands.guild_only()
    async def emojistats(self, ctx):
        """
        Usage -emojistats
        Output: Get detailed emoji usage stats.
        """
        async with ctx.channel.typing():
            msg = await ctx.send_or_reply(content=f"{self.bot.emote_dict['loading']} **Collecting Emoji Statistics**",
            )
            query = """
                    SELECT (emoji_id, total)
                    FROM emojistats
                    WHERE server_id = $1
                    ORDER BY total DESC;
                    """

            emoji_list = []
            result = await self.bot.cxn.fetch(query, ctx.guild.id)
            for x in result:
                try:
                    emoji = self.bot.get_emoji(int(x[0][0]))
                    if emoji is None:
                        continue
                    emoji_list.append((emoji, x[0][1]))

                except Exception as e:
                    print(e)
                    continue

            p = pagination.SimplePages(
                entries=["{}: Uses: {}".format(e[0], e[1]) for e in emoji_list],
                per_page=15,
            )
            p.embed.title = f"Emoji usage stats in **{ctx.guild.name}**"
            await msg.delete()
            try:
                await p.start(ctx)
            except menus.MenuError as e:
                await ctx.send_or_reply(e)

    @commands.command(brief="Get usage stats on an emoji.")
    async def emoji(self, ctx, emoji: converters.SearchEmojiConverter = None):
        """
        Usage: -emoji <custom emoji>
        Output: Usage stats on the passed emoji
        """
        async with ctx.channel.typing():
            if emoji is None:
                return await ctx.send_or_reply(
                    content=f"Usage: `{ctx.prefix}emoji <custom emoji>`",
                )
            emoji_id = emoji.id

            msg = await ctx.send_or_reply(content=f"{self.bot.emote_dict['loading']} **Collecting Emoji Statistics**",
            )
            query = f"""SELECT (author_id, content) FROM messages WHERE content ~ '<a?:.+?:{emoji_id}>';"""

            stuff = await self.bot.cxn.fetch(query)

            emoji_users = []
            for x in stuff:
                emoji_users.append(x[0][0])

            fat_msg = ""
            for x in stuff:
                fat_msg += x[0][1]

            emoji_users = Counter(emoji_users).most_common()

            matches = re.compile(f"<a?:.+?:{emoji_id}>").findall(fat_msg)
            total_uses = len(matches)

            p = pagination.SimplePages(
                entries=[
                    "`{}`: Uses: {}".format(self.bot.get_user(u[0]), u[1])
                    for u in emoji_users
                ],
                per_page=15,
            )
            p.embed.title = f"Emoji usage stats for {emoji} (Total: {total_uses})"
            await msg.delete()
            try:
                await p.start(ctx)
            except menus.MenuError as e:
                await ctx.send_or_reply(e)








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
        await ctx.send_or_reply(embed=embed)

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
        await ctx.send_or_reply(msg)

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
            return await ctx.send_or_reply(
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
        await ctx.send_or_reply(msg)

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
            await ctx.send_or_reply(e)

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
            await ctx.send_or_reply(e)

    @commands.command(brief="Shows all the server's bots.")
    @permissions.bot_has_permissions(embed_links=True)
    @permissions.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def listbots(self, ctx, *, _input = None):
        """
        Usage: -listbots [server]
        """
        if _input is None:
            guild = ctx.guild
        else:
            guild = await converters.DiscordGuild().convert(ctx, _input)

        author = guild.get_member(ctx.author.id)
        if author is None:
            raise commands.BadArgument(f"Server `{_input}` not found.")

        list_of_bots = [x for x in guild.members if x.bot]
        if not len(list_of_bots):
            # No bots.
            await ctx.send_or_reply(content=f"This server has no bots."
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
                await ctx.send_or_reply(e)


    @commands.command(brief="Show the server's channels.", aliases=["channels"])
    @commands.guild_only()
    @permissions.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 20, commands.BucketType.guild)
    @permissions.has_permissions(manage_channels=True)
    async def listchannels(self, ctx, guild: int = None):
        """
        Usage:      -listchannels
        Alias:      -channels
        Output:     Embed of all server channels
        Permission: Manage Channels
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
            await ctx.send_or_reply(embed=page)


    @commands.command(name="permissions", brief="Show a user's permissions.")
    @commands.guild_only()
    async def _permissions(
        self, ctx, member: discord.Member = None, channel: discord.TextChannel = None
    ):
        """
        Usage:  -permissions [member] [channel]
        Output: Shows a member's permissions in a specific channel.
        Notes:
            Will default to yourself and the current channel
            if they are not specified.
        """
        channel = channel or ctx.channel
        if member is None:
            member = ctx.author

        await self.say_permissions(ctx, member, channel)

    async def say_permissions(self, ctx, member, channel):
        permissions = channel.permissions_for(member)
        e = discord.Embed(colour=member.colour)
        avatar = member.avatar_url_as(static_format="png")
        e.set_author(name=str(member), url=avatar)
        allowed, denied = [], []
        for name, value in permissions:
            name = name.replace("_", " ").replace("guild", "server").title()
            if value:
                allowed.append(name)
            else:
                denied.append(name)

        e.add_field(name="Allowed", value="\n".join(allowed))
        e.add_field(name="Denied", value="\n".join(denied))
        await ctx.send_or_reply(embed=e)
