import itertools
import re
import discord
import colorsys

from collections import Counter
from discord.ext import commands, menus

from utilities import utils
from utilities import checks
from utilities import converters
from utilities import decorators
from utilities import pagination


def setup(bot):
    bot.add_cog(Stats(bot))


class Stats(commands.Cog):
    """
    Module for server stats
    """

    def __init__(self, bot):
        self.bot = bot
        self.statusmap1 = {
            discord.Status.online: "1",
            discord.Status.dnd: "2",
            discord.Status.idle: "3",
        }  # for sorting
        self.statusmap2 = {
            discord.Status.online: bot.emote_dict["online"],
            discord.Status.dnd: bot.emote_dict["dnd"],
            discord.Status.idle: bot.emote_dict["idle"],
            discord.Status.offline: bot.emote_dict["offline"],
        }

    @decorators.command(
        aliases=["administrators"],
        brief="Show the server admins.",
        implemented="2021-03-17 07:05:30.712141",
        updated="2021-05-06 18:14:34.407872",
        examples="""
                {0}admins
                {0}administrators
                """,
    )
    @checks.guild_only()
    @checks.cooldown()
    async def admins(self, ctx):
        """
        Usage: {0}admins
        Alias: {0}administrators
        Output:
            Show all server administrators
            and their respective statuses.
        """
        message = ""
        all_status = {
            "online": {"users": [], "emoji": self.bot.emote_dict["online"]},
            "idle": {"users": [], "emoji": self.bot.emote_dict["idle"]},
            "dnd": {"users": [], "emoji": self.bot.emote_dict["dnd"]},
            "offline": {"users": [], "emoji": self.bot.emote_dict["offline"]},
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
            f"{self.bot.emote_dict['admin']} Admins in **{ctx.guild.name}:**\n\n{message}"
        )

    @decorators.command(
        aliases=["ci"],
        brief="Get info about a channel.",
        implemented="2021-03-25 01:42:04.359878",
        updated="2021-05-06 17:33:15.040085",
        examples="""
                {0}channelinfo
                {0}channelinfo 805638877762420789
                {0}channelinfo general
                {0}ci
                {0}ci 805638877762420789
                {0}ci general
                """,
    )
    @checks.guild_only()
    @checks.bot_has_perms(embed_links=True)
    @checks.cooldown()
    async def channelinfo(self, ctx, *, channel: converters.DiscordChannel = None):
        """
        Usage: {0}channelinfo [channel]
        Output:
            Specific info on a given channel
        Notes:
            If no channel is specified,
            current channel will be used.
        """
        channel = channel or ctx.channel
        em = discord.Embed(color=self.bot.constants.embed)
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

    @decorators.command(
        aliases=["ei", "emoteinfo"],
        brief="Get info about an emoji.",
        implemented="2021-03-25 01:42:04.359878",
        updated="2021-05-06 17:33:15.040085",
        examples="""
                {0}channelinfo
                {0}channelinfo 805638877762420789
                {0}channelinfo general
                {0}ci
                {0}ci 805638877762420789
                {0}ci general
                """,
    )
    @checks.guild_only()
    @checks.bot_has_perms(embed_links=True)
    @checks.cooldown()
    async def emojiinfo(self, ctx, *, emoji: discord.Emoji):
        """
        Usage: {0}emojiinfo [emoji]
        Aliases: {0}ei, {0}emoteinfo
        Output:
            Specific info on a given channel
        Notes:
            If no channel is specified,
            current channel will be used.
        """
        em = discord.Embed(color=self.bot.constants.embed)
        em.add_field(
            name="Emoji", value="{0.name} ({0.id})".format(emoji), inline=False
        )
        em.add_field(
            name="Server",
            value="{0.guild.name} ({0.guild.id})".format(emoji),
            inline=False,
        )
        em.add_field(name="Type", value="{}".format(type(emoji).__name__), inline=False)
        em.add_field(
            name="Created", value=utils.format_time(emoji.created_at), inline=False
        )
        em.set_thumbnail(url=emoji.url)
        await ctx.send_or_reply(embed=em)

    @decorators.command(
        aliases=["emoteusage"],
        brief="Get usage stats on an emoji.",
        implemented="2021-03-23 05:05:29.999518",
        updated="2021-05-06 18:24:09.933406",
        examples="""
                {0}emojiusage pepe
                {0}emojiusage :pepe:
                {0}emojiusage <:pepe:779433733400166420>
                {0}emoteusage pepe
                {0}emoteusage :pepe:
                {0}emoteusage <:pepe:779433733400166420>
                """,
    )
    @checks.guild_only()
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    @checks.has_perms(view_guild_insights=True)
    @checks.cooldown()
    async def emojiusage(self, ctx, emoji: converters.GuildEmojiConverter):
        """
        Usage: {0}emojiusage <custom emoji>
        Aliases: 0}emojiusage, {0}emoteusage
        Output: Usage stats on the passed emoji
        """
        await ctx.trigger_typing()
        query = """
                SELECT author_id, total
                FROM emojidata
                WHERE server_id = $1
                AND emoji_id = $2
                ORDER BY total DESC;
                """

        records = await self.bot.cxn.fetch(query, ctx.guild.id, emoji.id)
        if not records:
            await ctx.fail("This emoji has no recorded emoji usage stats.")
            return

        def pred(snowflake):
            mem = ctx.guild.get_member(snowflake)
            if mem:
                return str(mem)

        p = pagination.SimplePages(
            entries=[
                f"`{pred(record['author_id'])}`: Uses: {record['total']}"
                for record in records
                if pred(record["author_id"]) is not None
            ],
            per_page=15,
        )

        p.embed.title = f"{emoji} (Total Uses: {sum([r['total'] for r in records]):,})"
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @decorators.command(
        aliases=["estats"],
        brief="Emoji usage tracking.",
        implemented="2021-03-23 04:40:06.282347",
        updated="2021-05-06 18:18:31.394648",
        examples="""
                {0}estats
                {0}estats Hecate
                {0}estats @Hecate
                {0}estats Hecate#3523
                {0}estats 839929135988342824
                {0}emojistats
                {0}emojistats Hecate
                {0}emojistats @Hecate
                {0}emojistats Hecate#3523
                {0}emojistats 839929135988342824
                """,
    )
    @checks.guild_only()
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    @checks.has_perms(view_guild_insights=True)
    async def emojistats(self, ctx, *, user: converters.DiscordMember = None):
        """
        Usage: {0}emojistats [user]
        Alias: {0}estats
        Permission: View Audit Log
        Output:
            Get detailed emoji usage stats.
        Notes:
            Specify an optional user to narrow
            statistics to be exclusive to the user.
        """
        await ctx.trigger_typing()

        def pred(emoji_id):
            emoji = self.bot.get_emoji(emoji_id)
            if emoji:
                if emoji.is_usable():
                    return emoji

        if user is None:
            query = """
                    SELECT emoji_id, total
                    FROM emojidata
                    WHERE server_id = $1
                    GROUP BY emoji_id, total
                    ORDER BY total DESC;
                    """

            records = await self.bot.cxn.fetch(query, ctx.guild.id)
            if not records:
                await ctx.fail("This server has no recorded emoji usage stats.")
                return

            p = pagination.SimplePages(
                entries=[
                    f"{pred(r['emoji_id'])}: Uses: {r['total']}"
                    for r in records
                    if pred(r["emoji_id"])
                ],
                per_page=15,
            )
            p.embed.title = (
                f"Server Emoji Usage (Total: {sum([r['total'] for r in records]):,})"
            )
            try:
                await p.start(ctx)
            except menus.MenuError as e:
                await ctx.send_or_reply(e)
        else:
            if user.bot:
                await ctx.fail("I do not track bots.")
                return

            query = """
                    SELECT emoji_id, total
                    FROM emojidata
                    WHERE author_id = $1
                    AND server_id = $2
                    GROUP BY emoji_id, total
                    ORDER BY total DESC;
                    """

            records = await self.bot.cxn.fetch(query, user.id, ctx.guild.id)
            if not records:
                await ctx.fail(
                    f"**{user}** `{user.id}` has no recorded emoji usage stats."
                )
                return

            p = pagination.SimplePages(
                entries=[
                    f"{pred(r['emoji_id'])}: Uses: {r['total']}"
                    for r in records
                    if pred(r["emoji_id"])
                ],
                per_page=15,
            )
            p.embed.title = f"{user.display_name}'s Emoji Usage (Total: {sum([r['total'] for r in records]):,})"
            try:
                await p.start(ctx)
            except menus.MenuError as e:
                await ctx.send_or_reply(e)

    @decorators.command(
        brief="Show roles that have no users.",
        implemented="2021-07-02 22:13:46.041567",
        updated="2021-07-03 02:55:29.704354",
    )
    @checks.guild_only()
    @checks.bot_has_perms(embed_links=True)
    @checks.cooldown()
    async def emptyroles(self, ctx):
        """
        Usage: {0}emptyroles
        Output: Shows all roles with zero users
        """

        check_roles = (
            ctx.guild.roles
        )  # grab in hierarchy order so they're easier to find in the server settings
        rolecounts = self.role_accumulate(
            check_roles, ctx.guild.members
        )  # same accumulate as the `roles` command

        sorted_list = []
        for role in check_roles:
            if role in rolecounts and rolecounts[role] == 0:  # only add if count = 0
                sorted_list.append((role, rolecounts.get(role, 0)))

        if not sorted_list:  # another failsafe
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['warn']} No empty roles found.",
            )

        await self.rolelist_paginate(ctx, sorted_list, title="Empty Roles")

    @decorators.command(
        aliases=["earlyjoins"],
        brief="Show the first users to join.",
        implemented="2021-03-11 23:57:16.694491",
        updated="2021-05-06 18:48:42.837329",
        examples="""
                {0}firstjoins
                {0}earlyjoins
                """,
    )
    @checks.guild_only()
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    @checks.has_perms(view_guild_insights=True)
    @checks.cooldown()
    async def firstjoins(self, ctx):
        """
        Usage: {0}firstjoins
        Alias: {0}earlyjoins
        Permission: View Audit Log
        Output:
            Embed of all users ordered by their
            join date earliest to latest.
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

    @decorators.command(
        aliases=["joinedat", "jointime"],
        brief="Check when a user joined the server.",
        implemented="2021-03-30 07:33:29.174265",
        updated="2021-05-06 18:34:44.223170",
        examples="""
                {0}joined
                {0}joined Hecate
                {0}joined @Hecate
                {0}joined Hecate#3523
                {0}joined 708584008065351681
                {0}joinedat
                {0}joinedat Hecate
                {0}joinedat @Hecate
                {0}joinedat Hecate#3523
                {0}joinedat 708584008065351681
                {0}jointime
                {0}jointime Hecate
                {0}jointime @Hecate
                {0}jointime Hecate#3523
                {0}jointime 708584008065351681
                """,
    )
    @checks.guild_only()
    @checks.has_perms(view_guild_insights=True)
    @checks.cooldown()
    async def joined(self, ctx, *, user: converters.DiscordMember = None):
        """
        Usage: {0}joined [user]
        Aliases: {0}joinedat, {0}jointime
        Permission: View Audit Log
        Output:
            Shows when the passed user joined the server
        Notes:
            Will default to youself if no member is passed.
        """
        user = user or ctx.author
        avatar = user.display_avatar.url

        embed = discord.Embed(colour=user.top_role.colour.value)
        embed.set_thumbnail(url=avatar)
        embed.description = (
            f"**{user}** joined **{ctx.guild.name}**\n{utils.date(user.joined_at)}"
        )
        await ctx.send_or_reply(embed=embed)

    @decorators.command(
        aliases=["joinedatposition"],
        brief="Show who joined at a position.",
        implemented="2021-03-23 23:37:29.560505",
        updated="2021-05-06 18:44:36.316193",
        examples="""
                {0}joinedatpos 3
                {0}joinedatposition 7
                """,
    )
    @checks.guild_only()
    @checks.has_perms(view_guild_insights=True)
    @checks.cooldown()
    async def joinedatpos(self, ctx, *, position):
        """
        Usage: {0}joinedatpos <position>
        Alias: {0}joinedatposition
        Permission: View Audit Log
        Output:
            Shows the user that joined at the passed position.
        """
        try:
            position = int(position) - 1
            assert -1 < position < len(ctx.guild.members)
        except Exception:
            return await ctx.fail(
                "Position must be an integer between 1 and {:,}".format(
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

    @decorators.command(
        aliases=["joinposition"],
        brief="Show the join position of a user.",
        implemented="2021-03-11 23:58:24.868592",
        updated="2021-05-06 18:39:09.468807",
        examples="""
                {0}joinpos
                {0}joinpos Hecate
                {0}joinpos @Hecate
                {0}joinpos Hecate#3523
                {0}joinpos 839934336363134976
                {0}joinposition
                {0}joinposition Hecate
                {0}joinposition @Hecate
                {0}joinposition Hecate#3523
                {0}joinposition 839934336363134976
                """,
    )
    @checks.guild_only()
    @checks.has_perms(view_guild_insights=True)
    @checks.cooldown()
    async def joinpos(self, ctx, *, user: converters.DiscordMember = None):
        """
        Usage: {0}joinpos [user]
        Alias: {0}joinposition
        Permission: View Audit Log
        Output:
            Shows when a user joined
            compared to other users.
        Notes:
            Will default to yourself
            if no user is passed.
        """

        user = user or ctx.author

        joinedList = []
        for mem in ctx.message.guild.members:
            joinedList.append({"ID": mem.id, "Joined": mem.joined_at})

        # sort the users by join date
        joinedList = sorted(
            joinedList,
            key=lambda x: x["Joined"].timestamp() if x["Joined"] != None else -1,
        )

        check_item = {"ID": user.id, "Joined": user.joined_at}

        total = len(joinedList)
        position = joinedList.index(check_item) + 1

        before = ""
        after = ""

        msg = "`{}'s` join position is **#{:,}**.".format(user, position, total)
        if position - 1 == 1:
            # We have previous users
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
            msg += " {} joined before, and {} after.".format(before, after)
        elif len(before):
            # Just got before
            msg += " {} joined before.".format(before)
        elif len(after):
            # Just after
            msg += " {} joined after.".format(after)
        await ctx.send_or_reply(msg)

    @decorators.command(
        aliases=["latestjoins", "recentjoins"],
        brief="Show the latest users to join.",
        implemented="2021-03-16 19:00:01.981909",
        updated="2021-05-06 18:51:13.775928",
        examples="""
                {0}lastjoins
                {0}latestjoins
                {0}recentjoins
                """,
    )
    @checks.guild_only()
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    @checks.has_perms(view_guild_insights=True)
    @checks.cooldown()
    async def lastjoins(self, ctx):
        """
        Usage: {0}lastjoins
        Aliases: {0}latestjoins, {0}recentjoins
        Permission: View Audit Log
        Output:
            Embed of all users ordered by their
            join date latest to earliest.
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

    @decorators.command(
        aliases=["allbots", "serverbots", "guildbots"],
        brief="Shows all the server's bots.",
        implemented="2021-03-22 20:17:10.609920",
        updated="2021-05-06 19:18:30.882272",
        examples="""
                {0}allbots
                {0}listbots
                {0}guildbots
                {0}serverbots
                """,
    )
    @checks.guild_only()
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    @checks.has_perms(view_guild_insights=True)
    @checks.cooldown()
    async def listbots(self, ctx):
        """
        Usage: {0}listbots
        Aliases:
            {0}allbots
            {0}serverbots
            {0}guildbots
        Permission: View Audit Log
        Output:
            A pagination session showing all
            the server's bots and their IDs.
        """
        list_of_bots = [x for x in ctx.guild.members if x.bot]
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
                    for y, x in enumerate(
                        sorted(bot_list, key=lambda x: x["name"].lower())
                    )
                ],
                title="Bots in **{}** ({:,} total)".format(
                    ctx.guild.name, len(list_of_bots)
                ),
                per_page=10,
            )
        )
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @decorators.command(
        aliases=["channels", "allchannels", "serverchannels"],
        brief="Show the server's channels.",
        implemented="2021-03-11 23:23:02.365448",
        updated="2021-05-06 19:25:20.971385",
        examples="""
                {0}channels
                {0}allchannels
                {0}listchannels
                {0}serverchannels
                """,
    )
    @commands.guild_only()
    @checks.bot_has_perms(embed_links=True)
    @checks.has_perms(manage_channels=True)
    @checks.cooldown()
    async def listchannels(self, ctx):
        """
        Usage: {0}listchannels
        Alias:
            {0}channels,
            {0}allchannels,
            {0}serverchannels
        Permission: Manage Channels
        Output:
            Embed of all the server's channels
        """
        guild = ctx.guild
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

    @decorators.command(
        aliases=["roles", "allroles"],
        brief="Show an embed of all server roles.",
        implemented="",
        updated="",
    )
    @checks.guild_only()
    @checks.cooldown()
    async def listroles(self, ctx, sort_order: str = "default"):
        """
        Usage: {0}listroles
        Alias: {0}roles, {0}allroles
        Permission: Manage Roles
        Output:
            Shows roles and their member counts. Takes one argument,
            sort_order, which can be default, name, count, or color.
        """

        sort_order = sort_order.lower()
        if not sort_order in [
            "default",
            "name",
            "count",
            "color",
        ]:  # make sure it has valid args
            return await ctx.send_or_reply(
                "Invalid arguments.\n ```yaml\nVALID OPTIONS:\n=============\n\ndefault\nname\ncount\ncolor\n```"
            )

        check_roles = (
            ctx.guild.roles
        )  # we use roles for these because sometimes we want to see the order

        ## now we iterate over the members to accumulate a count of each role
        rolecounts = self.role_accumulate(check_roles, ctx.guild.members)

        sorted_list = []
        if sort_order == "default":  # default sort = the server role hierarchy
            for role in check_roles:
                if role in rolecounts:
                    sorted_list.append((role, rolecounts.get(role, 0)))
        elif sort_order == "name":  # name sort = alphabetical by role name
            sorted_list = sorted(
                rolecounts.items(), key=lambda tup: tup[0].name.lower()
            )
        elif sort_order == "count":  # count sort = decreasing member count
            sorted_list = sorted(
                rolecounts.items(), key=lambda tup: tup[1], reverse=True
            )
        elif (
            sort_order == "color"
        ):  # color sort: by increasing hue value in HSV color space
            sorted_list = sorted(
                rolecounts.items(),
                key=lambda tup: colorsys.rgb_to_hsv(
                    tup[0].color.r, tup[0].color.g, tup[0].color.b
                )[0],
            )

        if not sorted_list:  # another failsafe
            return

        sorted_list = sorted_list[::-1]
        await self.rolelist_paginate(
            ctx, sorted_list
        )  # send the list to get actually printed to discord

    @decorators.command(
        aliases=["moderators"],
        brief="Show the server moderators.",
        implemented="2021-03-17 07:08:21.480899",
        updated="2021-05-06 18:12:21.041255",
        examples="""
                {0}mods
                {0}moderators
                """,
    )
    @checks.guild_only()
    @checks.cooldown()
    async def mods(self, ctx):
        """
        Usage: {0}mods
        Alias: {0}moderators
        Output:
            Show all the server moderators
            and their respective statuses.
        """
        message = ""
        all_status = {
            "online": {"users": [], "emoji": self.bot.emote_dict["online"]},
            "idle": {"users": [], "emoji": self.bot.emote_dict["idle"]},
            "dnd": {"users": [], "emoji": self.bot.emote_dict["dnd"]},
            "offline": {"users": [], "emoji": self.bot.emote_dict["offline"]},
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
            f"{self.bot.emote_dict['admin']} Mods in **{ctx.guild.name}:**\n\n{message}",
        )

    @decorators.command(
        name="permissions",
        aliases=["perms"],
        brief="Show a user's permissions.",
        implemented="2021-03-17 23:38:48.406038",
        updated="2021-07-02 21:58:28.689246",
    )
    @checks.guild_only()
    @checks.has_perms(view_guild_insights=True)
    async def _permissions(
        self,
        ctx,
        user: converters.DiscordMember = None,
        channel: discord.TextChannel = None,
    ):
        """
        Usage: {0}permissions [user] [channel]
        Alias: {0}perms
        Output:
            Shows a user's permissions in a specific channel.
        Notes:
            Will default to yourself and the current channel
            if they are not specified.
        """
        channel = channel or ctx.channel
        member = user or ctx.author

        permissions = channel.permissions_for(member)
        await self.do_permissions(ctx, str(member), permissions)

    @decorators.command(
        brief="Counts the users with a role.",
        implemented="2021-04-05 20:24:43.545907",
        updated="2021-07-03 03:11:00.661242",
    )
    @checks.bot_has_perms(embed_links=True)
    @checks.guild_only()
    @checks.cooldown()
    async def rolecall(self, ctx, *, role: converters.DiscordRole = None):
        """
        Usage: {0}rolecall <role>
        Output:
            Shows the number of people with the passed role.
        """
        if role is None:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.clean_prefix}rolecall <role>`",
            )

        count = 0
        online = 0
        for member in ctx.guild.members:
            if role in member.roles:
                count += 1
                if member.status != discord.Status.offline:
                    online += 1

        embed = discord.Embed(
            title=role.name,
            description="{}/{} online".format(online, count),
            color=self.bot.constants.embed,
        )
        embed.set_footer(text="ID: {}".format(role.id))
        await ctx.send_or_reply(embed=embed)

    @decorators.command(
        brief="Counts the roles on the server.",
        implemented="2021-04-05 20:24:43.545907",
        updated="2021-07-03 03:11:00.661242",
    )
    @checks.guild_only()
    @checks.cooldown()
    async def rolecount(self, ctx):
        """
        Usage: {0}rolecount
        Output: Counts all server roles
        """
        await ctx.send_or_reply(
            self.bot.emote_dict["graph"]
            + " This server has {:,} total roles.".format(len(ctx.guild.roles) - 1)
        )

    @decorators.command(
        aliases=["ri"],
        brief="Get information on a role.",
        implemented="2021-03-12 04:03:05.031691",
        updated="2021-05-10 07:11:40.514042",
        examples="""
                {0}ri 828763460346839050
                {0}roleinfo @Helper
                """,
    )
    @checks.bot_has_perms(embed_links=True)
    @checks.guild_only()
    @checks.cooldown()
    async def roleinfo(self, ctx, *, role: converters.DiscordRole):
        """
        Usage: {0}roleinfo <role>
        Alias: {0}ri
        Output:
            Shows details on the role's color,
            creation date, users, and creator.
        """
        users = users = sum(1 for m in role.guild.members if m._roles.has(role.id))
        created = f"Created on {role.created_at.__format__('%m/%d/%Y')}"

        embed = discord.Embed(color=self.bot.constants.embed)
        embed.set_author(name=role.name, icon_url=utils.get_icon(ctx.guild))
        embed.set_footer(text=f"Role ID: {role.id} | {created}")
        embed.set_thumbnail(url=utils.get_icon(ctx.guild))
        embed.add_field(name="Mention", value=role.mention)
        embed.add_field(name="Users", value=users)
        embed.add_field(name="Hoisted", value=role.hoist)
        embed.add_field(name="Color", value=str(role.color).upper())
        embed.add_field(name="Position", value=role.position)
        embed.add_field(name="Mentionable", value=role.mentionable)
        await ctx.send_or_reply(embed=embed)

    @decorators.command(
        aliases=["rp", "rolepermissions"],
        brief="Show the permissions for a role.",
        implemented="2021-06-25 01:10:57.701157",
        updated="2021-07-02 22:02:57.022399",
    )
    @commands.guild_only()
    async def roleperms(self, ctx, *, role: converters.DiscordRole):
        """
        Usage:  {0}roleperms <role>
        Alias:  {0}rp, {0}rolepermissions
        Output:
            Embed with all the permissions
            granted to the passed role
        """
        await self.do_permissions(ctx, role.name, role.permissions)

    @decorators.command(
        aliases=["si", "serverstats", "ss", "server"],
        brief="Show server information.",
        implemented="2021-03-19 00:53:00.946175",
        updated="2021-05-06 18:03:58.872774",
        examples="""
                {0}serverinfo
                {0}serverstats
                {0}server
                {0}si
                {0}ss
                """,
    )
    @checks.guild_only()
    @checks.bot_has_perms(embed_links=True)
    @checks.cooldown()
    async def serverinfo(self, ctx):
        """
        Usage: {0}serverinfo
        Aliases:
            {0}serverinfo
            {0}serverstats
            {0}server
            {0}si
            {0}ss
        Output:
            General stats on the server.
            Shows the name, ID, owner,
            user count, online member,
            role count, region, emoji count,
            channel info, and creation date.
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
        em.set_thumbnail(url=utils.get_icon(server))
        em.set_author(name=server.name, icon_url=utils.get_icon(server))
        em.set_footer(
            text=f"Server ID: {server.id} | Created on {server.created_at.__format__('%m/%d/%Y')}"
        )
        em.add_field(
            name="Owner",
            value=f"{self.bot.emote_dict['owner']} {server.owner}",
            inline=True,
        )
        em.add_field(
            name="Total Members",
            value=f"{self.bot.emote_dict['members']} {server.member_count:,}",
            inline=True,
        )
        em.add_field(
            name="Online Members",
            value=f"{self.bot.emote_dict['online']} {online:,}",
            inline=True,
        )
        em.add_field(
            name="Role Count",
            value=f"{self.bot.emote_dict['role']} {role_count:,}",
            inline=True,
        )
        em.add_field(name="Region", value=region, inline=True)
        em.add_field(
            name="Emoji Count",
            value=f"{self.bot.emote_dict['emoji']} {len(server.emojis):,}",
            inline=True,
        )
        em.add_field(
            name="Categories",
            value=f"{self.bot.emote_dict['categories']} {len(server.categories):,}",
            inline=True,
        )
        em.add_field(
            name="Text Channels",
            value=f"{self.bot.emote_dict['textchannel']} {total_text_channels:,}",
            inline=True,
        )
        em.add_field(
            name="Voice Channels",
            value=f"{self.bot.emote_dict['voicechannel']} {total_voice_channels:,}",
            inline=True,
        )
        await ctx.send_or_reply(embed=em)

    @decorators.command(
        aliases=["channeltopic"],
        brief="Show the topic of a channel.",
        implemented="2021-03-25 01:42:51.969489",
        updated="2021-05-06 19:42:21.176961",
        examples="""
                {0}topic
                {0}topic general
                {0}topic 805638877762420789
                {0}topic <#805638877762420789>
                {0}channeltopic
                {0}channeltopic general
                {0}channeltopic 805638877762420789
                {0}channeltopic <#805638877762420789>
                """,
    )
    @checks.guild_only()
    @checks.cooldown()
    async def topic(self, ctx, *, channel: converters.DiscordChannel = None):
        """
        Usage: {0}topic [channel]
        Alias: {0}channeltopic
        Output:
            Shows a channel's topic.
            Useful for replying to users
            not abiding by the channel's topic.
        Notes:
            Will default to the current channel
            if not alternative channel is passed.
        """
        if channel is None:
            channel = ctx.channel
        await ctx.send_or_reply(
            content=("**Channel topic:** " + channel.topic)
            if channel.topic
            else "No topic set."
        )

    @decorators.command(
        aliases=["whois", "ui", "profile"],
        brief="Show information on a user.",
        implemented="2021-03-11 18:42:18.403948",
        updated="2021-05-06 16:46:39.043980",
        examples="""
                {0}userinfo Neutra
                {0}whois 806953546372087818
                {0}profile Hecate#3523
                {0}ui @Neutra
                """,
    )
    @checks.guild_only()
    @checks.bot_has_perms(embed_links=True)
    @checks.cooldown()
    async def userinfo(self, ctx, user: converters.DiscordMember = None):
        """
        Usage: {0}userinfo <member>
        Aliases: {0}profile, {0}ui, {0}whois
        Output:
            General stats on a discord user.
            Includes, ID, name, highest role,
            status, messages sent, commands run
            join position, and registration date.
        Notes:
            Moderators, incoke command with {0}user,
            {0}rawuser, or {0}lookup to see all information
            currently available on a discord user.
        """

        if user is None:
            user = ctx.author

        joinedList = []
        for mem in ctx.guild.members:
            joinedList.append({"ID": mem.id, "Joined": mem.joined_at})

        # sort the users by join date
        joinedList = sorted(
            joinedList,
            key=lambda x: x["Joined"].timestamp() if x["Joined"] is not None else -1,
        )

        check_item = {"ID": user.id, "Joined": user.joined_at}

        position = joinedList.index(check_item) + 1

        msg = "{:,}".format(position)

        query = """
                SELECT COUNT(*)
                FROM commands
                WHERE author_id = $1
                AND server_id = $2;
                """
        command_count = await self.get_user_cmds(user)
        message_count = await self.get_user_msgs(user)

        status_dict = {
            "online": f"{self.bot.emote_dict['online']} Online",
            "offline": f"{self.bot.emote_dict['offline']} Offline",
            "dnd": f"{self.bot.emote_dict['dnd']} Do Not Disturb",
            "idle": f"{self.bot.emote_dict['idle']} Idle",
        }
        if user.id in self.bot.owner_ids:
            emoji = self.bot.emote_dict["dev"]
        elif user.id == ctx.guild.owner.id:
            emoji = self.bot.emote_dict["owner"]
        elif user.bot:
            emoji = self.bot.emote_dict["bot"]
        else:
            emoji = self.bot.emote_dict["user"]

        avatar = user.display_avatar.url

        embed = discord.Embed(color=self.bot.constants.embed)
        embed.set_author(name=f"{user}", icon_url=avatar)
        embed.set_thumbnail(url=avatar)
        embed.set_footer(
            text=f"User ID: {user.id} | Created on {user.created_at.__format__('%m/%d/%Y')}"
        )
        embed.add_field(
            name="Nickname",
            value=f"{emoji} {user.display_name}",
        )
        embed.add_field(
            name="Messages",
            value=f"{self.bot.emote_dict['messages']}  {message_count:,}",
        )
        embed.add_field(
            name="Commands",
            value=f"{self.bot.emote_dict['commands']}  {command_count:,}",
        )
        embed.add_field(name="Status", value=f"{status_dict[str(user.status)]}")
        embed.add_field(
            name="Highest Role",
            value=f"{self.bot.emote_dict['role']} {'@everyone' if user.top_role.name == '@everyone' else user.top_role.mention}",
        )
        embed.add_field(
            name="Join Position", value=f"{self.bot.emote_dict['invite']} #{msg}"
        )
        await ctx.send_or_reply(embed=embed)

    @decorators.command(
        brief="Show the people who have a role.",
        implemented="2021-04-05 20:24:43.545907",
        updated="2021-07-03 03:11:00.661242",
    )
    @checks.guild_only()
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    @checks.cooldown()
    async def whohas(self, ctx, *, role: converters.DiscordRole):
        """
        Usage: {0}whohas <role>
        Output:
            Lists the people who have the specified role with their status.
        Notes:
        """
        users = [member for member in ctx.guild.members if role in member.roles]

        sorted_list = sorted(
            users,
            key=lambda usr: (self.statusmap1.get(usr.status, "4"))
            + (usr.nick.lower() if usr.nick else usr.name.lower()),
        )

        page = [
            "{} {}".format(
                self.statusmap2.get(member.status, self.bot.emote_dict["offline"]),
                member.mention,
            )
            for member in sorted_list
        ]

        p = pagination.SimplePages(entries=page, per_page=20, index=False)
        p.embed.title = "{:,} members with {}".format(len(users), role.name)

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    ######################
    ## Helper Functions ##
    ######################

    async def get_user_cmds(self, member):
        """
        Get the number of commands run by a member
        inside a specific server. (Not bot wide)
        """
        query = """
                SELECT COUNT(*)
                FROM commands
                WHERE author_id = $1
                AND server_id = $2;
                """
        cmd_count = await self.bot.cxn.fetchval(query, member.id, member.guild.id)
        return cmd_count or 0

    async def get_user_msgs(self, member):
        """
        Get the number of messages send by a member
        inside a specific server. (Not bot wide)
        """
        query = """
                SELECT COUNT(*)
                FROM messages
                WHERE author_id = $1
                AND server_id = $2;
                """
        msg_count = await self.bot.cxn.fetchval(query, member.id, member.guild.id)
        return msg_count or 0

    def role_accumulate(self, check_roles, members):
        """
        Iterate over the members to accumulate a count of each role
        """
        rolecounts = {}
        for role in check_roles:  # populate the accumulator dict
            if not role.is_default():
                rolecounts[role] = 0

        for member in members:
            for role in member.roles:
                if role in check_roles and not role.is_default():  # Exclude @everyone
                    rolecounts[role] += 1

        return rolecounts

    async def rolelist_paginate(self, ctx, rlist, title="Server Roles"):
        """
        Paginates a list of roles. Will send multiple embeds if
        the character length of the combined roles goes over the limit.
        """
        pages = []
        buildstr = ""
        for role, count in rlist:  # this generates and paginates the info
            line = "{:,} {}\n".format(count, role.mention)
            if len(buildstr) + len(line) > pagination.DESC_LIMIT:
                pages.append(buildstr)  # split the page here
                buildstr = line
            else:
                buildstr += line
        if buildstr:
            pages.append(
                buildstr
            )  # if the string has data not already listed in the pages, add it

        for index, page in enumerate(pages):  # enumerate so we can add a page number
            embed = discord.Embed(
                title=f"{title}", description=page, color=self.bot.constants.embed
            )
            embed.set_footer(text="Page {:,}/{:,}".format(index + 1, len(pages)))
            await ctx.send_or_reply(embed=embed)

    async def do_permissions(self, ctx, author, permissions):
        """
        Create an embed of allowed and denied permissions
        if the bot has embed_links perm. Else send a codeblock.
        """
        allowed, denied = [], []
        for name, value in permissions:
            name = (
                name.replace("_", " ")
                .replace("guild", "server")
                .title()
                .replace("Tts", "TTS")
            )
            if value:
                allowed.append(name)
            else:
                denied.append(name)

        if ctx.channel.permissions_for(ctx.me).embed_links:
            embed = discord.Embed(color=self.bot.constants.embed)
            embed.set_author(name=author)
            embed.add_field(name="Allowed", value="\n".join(allowed))
            embed.add_field(name="Denied", value="\n".join(denied))
            return await ctx.send_or_reply(embed=embed)
        else:
            perms = list(itertools.zip_longest(allowed, denied, fillvalue=""))
            length = len(max(*(allowed + denied))) + 1
            msg = f"```yml\n{'Allowed:'.ljust(length)}\t{'Denied:'.ljust(length)}\n"
            for allowed, denied in perms:
                msg += f"{allowed.ljust(length)}\t{denied.ljust(length)}\n"
            msg += "```"
            await ctx.send_or_reply(msg)
