import re
import discord

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
    @commands.guild_only()
    @checks.bot_has_perms(embed_links=True)
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
    @commands.guild_only()
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
                {0}userinfo Snowbot
                {0}whois 810377376269205546
                {0}profile Hecate#3523
                {0}ui @Snowbot
                """,
    )
    @checks.bot_has_perms(embed_links=True)
    async def userinfo(self, ctx, member: converters.DiscordMember = None):
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

        if member is None:
            member = ctx.author

        joinedList = []
        for mem in ctx.guild.members:
            joinedList.append({"ID": mem.id, "Joined": mem.joined_at})

        # sort the users by join date
        joinedList = sorted(
            joinedList,
            key=lambda x: x["Joined"].timestamp() if x["Joined"] is not None else -1,
        )

        check_item = {"ID": member.id, "Joined": member.joined_at}

        position = joinedList.index(check_item) + 1

        msg = "{:,}".format(position)

        query = """
                SELECT COUNT(*)
                FROM commands
                WHERE author_id = $1
                AND server_id = $2;
                """
        command_count = (
            await self.bot.cxn.fetchrow(query, member.id, ctx.guild.id) or None
        )
        if command_count is None:
            command_count = 0

        query = """
                SELECT COUNT(*)
                FROM messages
                WHERE author_id = $1
                AND server_id = $2;
                """
        messages = await self.bot.cxn.fetchrow(query, member.id, ctx.guild.id) or None
        if messages is None:
            messages = 0

        status_dict = {
            "online": f"{self.bot.emote_dict['online']} Online",
            "offline": f"{self.bot.emote_dict['offline']} Offline",
            "dnd": f"{self.bot.emote_dict['dnd']} Do Not Disturb",
            "idle": f"{self.bot.emote_dict['idle']} Idle",
        }
        embed = discord.Embed(color=self.bot.constants.embed)
        embed.set_author(name=f"{member}", icon_url=member.avatar_url)
        embed.set_thumbnail(url=member.avatar_url)
        embed.set_footer(
            text=f"User ID: {member.id} | Created on {member.created_at.__format__('%m/%d/%Y')}"
        )
        embed.add_field(
            name="Nickname",
            value=f"{self.bot.emote_dict['owner'] if member.id == ctx.guild.owner.id else self.bot.emote_dict['bot'] if member.bot else ''} {member.display_name}",
        )
        embed.add_field(
            name="Messages", value=f"{self.bot.emote_dict['messages']}  {messages[0]}"
        )
        embed.add_field(
            name="Commands",
            value=f"{self.bot.emote_dict['commands']}  {command_count[0]}",
        )
        embed.add_field(name="Status", value=f"{status_dict[str(member.status)]}")
        embed.add_field(
            name="Highest Role",
            value=f"{self.bot.emote_dict['role']} {'@everyone' if member.top_role.name == '@everyone' else member.top_role.mention}",
        )
        embed.add_field(
            name="Join Position", value=f"{self.bot.emote_dict['invite']} #{msg}"
        )
        await ctx.send_or_reply(embed=embed)

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
    @commands.guild_only()
    @checks.bot_has_perms(embed_links=True)
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
        em.set_thumbnail(url=server.icon_url)
        em.set_author(name=server.name, icon_url=server.icon_url)
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
            value=f"{self.bot.emote_dict['members']} {server.member_count}",
            inline=True,
        )
        em.add_field(
            name="Online Members",
            value=f"{self.bot.emote_dict['online']} {online}",
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
            value=f"{self.bot.emote_dict['emoji']} {len(server.emojis)}",
            inline=True,
        )
        em.add_field(
            name="Categories",
            value=f"{self.bot.emote_dict['categories']} {len(server.categories)}",
            inline=True,
        )
        em.add_field(
            name="Text Channels",
            value=f"{self.bot.emote_dict['textchannel']} {total_text_channels}",
            inline=True,
        )
        em.add_field(
            name="Voice Channels",
            value=f"{self.bot.emote_dict['voicechannel']} {total_voice_channels}",
            inline=True,
        )
        await ctx.send_or_reply(embed=em)

    @decorators.command(
        aliases=["moderators"],
        brief="Show the server mods.",
        implemented="2021-03-17 07:08:21.480899",
        updated="2021-05-06 18:12:21.041255",
        examples="""
                {0}mods
                {0}moderators
                """,
    )
    @commands.guild_only()
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
            content=f"Mods in **{ctx.guild.name}:**\n\n{message}",
        )

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
    @commands.guild_only()
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
            content=f"Admins in **{ctx.guild.name}:**\n\n{message}",
        )

    @decorators.command(
        aliases=["estats"],
        brief="Emoji usage tracking.",
        implemented="2021-03-23 04:40:06.282347",
        updated="2021-05-06 18:18:31.394648",
        examples="""
                {0}emojistats
                {0}emojistats Hecate
                {0}emojistats @Hecate
                {0}emojistats Hecate#3523
                {0}emojistats 839929135988342824
                {0}estats
                {0}estats Hecate
                {0}estats @Hecate
                {0}estats Hecate#3523
                {0}estats 839929135988342824
                """,
    )
    @commands.guild_only()
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    @checks.has_perms(view_audit_log=True)
    async def emojistats(self, ctx, user: converters.DiscordMember = None):
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
        async with ctx.channel.typing():
            msg = await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['loading']} **Collecting Emoji Statistics...**",
            )
            if user is None:
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
                p.embed.title = f"Emoji usage in **{ctx.guild.name}**"
                await msg.delete()
                try:
                    await p.start(ctx)
                except menus.MenuError as e:
                    await ctx.send_or_reply(e)
            else:
                if user.bot:
                    return await ctx.fail(f"I do not track bots.")
                query = """
                        SELECT (content)
                        FROM messages
                        WHERE content ~ '<a?:.+?:([0-9]{15,21})>'
                        AND author_id = $1
                        AND server_id = $2
                        """

                emoji_list = []
                result = await self.bot.cxn.fetch(query, user.id, ctx.guild.id)
                if not result:
                    return await ctx.fail(
                        f"`{user}` has no recorded emoji usage stats."
                    )

                matches = re.compile(r"<a?:.+?:[0-9]{15,21}>").findall(str(result))
                total_uses = len(matches)
                for x in matches:
                    emoji = self.bot.get_emoji(int(x.split(":")[2].strip(">")))
                    if emoji is None:
                        continue
                    emoji_list.append(emoji)

                emojis = Counter(emoji_list).most_common()

                p = pagination.SimplePages(
                    entries=["{}: Uses: {}".format(e[0], e[1]) for e in emojis],
                    per_page=15,
                )
                p.embed.title = (
                    f"{user.display_name}'s Emoji Usage\n`(Total: {total_uses:,})`"
                )
                await msg.delete()
                try:
                    await p.start(ctx)
                except menus.MenuError as e:
                    await ctx.send_or_reply(e)

    @decorators.command(
        aliases=["emojiusage", "emote", "emoteusage"],
        brief="Get usage stats on an emoji.",
        implemented="2021-03-23 05:05:29.999518",
        updated="2021-05-06 18:24:09.933406",
        examples="""
                {0}emoji pepe
                {0}emoji :pepe:
                {0}emoji <:pepe:779433733400166420>
                {0}emote pepe
                {0}emote :pepe:
                {0}emote <:pepe:779433733400166420>
                {0}emojistats pepe
                {0}emojistats :pepe:
                {0}emojistats <:pepe:779433733400166420>
                {0}emotestats pepe
                {0}emotestats :pepe:
                {0}emotestats <:pepe:779433733400166420>
                """,
    )
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    @checks.has_perms(view_audit_log=True)
    async def emoji(self, ctx, emoji: converters.SearchEmojiConverter):
        """
        Usage: {0}emoji <custom emoji>
        Aliases:
            {0}emote, {0}emojiusage, {0}emoteusage
        Output: Usage stats on the passed emoji
        """
        async with ctx.channel.typing():
            emoji_id = emoji.id

            msg = await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['loading']} **Collecting Emoji Statistics...**",
            )
            query = f"""
                    SELECT (author_id, content)
                    FROM messages
                    WHERE content ~ '<a?:.+?:{emoji_id}>';
                    """

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
    @commands.guild_only()
    @checks.has_perms(view_audit_log=True)
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

        embed = discord.Embed(colour=user.top_role.colour.value)
        embed.set_thumbnail(url=user.avatar_url)
        embed.description = (
            f"**{user}** joined **{ctx.guild.name}**\n{utils.date(user.joined_at)}"
        )
        await ctx.send_or_reply(embed=embed)

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
    @commands.guild_only()
    @checks.has_perms(view_audit_log=True)
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

        if user is None:
            user = ctx.author

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
        aliases=["joinedatposition"],
        brief="Show who joined at a position.",
        implemented="2021-03-23 23:37:29.560505",
        updated="2021-05-06 18:44:36.316193",
        examples="""
                {0}joinedatpos 3
                {0}joinedatposition 7
                """,
    )
    @commands.guild_only()
    @checks.has_perms(view_audit_log=True)
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
        aliases=["earlyjoins"],
        brief="Show the first users to join.",
        implemented="2021-03-11 23:57:16.694491",
        updated="2021-05-06 18:48:42.837329",
        examples="""
                {0}firstjoins
                {0}earlyjoins
                """,
    )
    @commands.guild_only()
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    @checks.has_perms(view_audit_log=True)
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
    @commands.guild_only()
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    @checks.has_perms(view_audit_log=True)
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
    @commands.guild_only()
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    @checks.has_perms(view_audit_log=True)
    async def listbots(self, ctx):
        """
        Usage: -listbots
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
    @commands.cooldown(1, 20, commands.BucketType.guild)
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

    @decorators.command(name="permissions", brief="Show a user's permissions.")
    @commands.guild_only()
    @checks.has_perms(view_audit_log=True)
    async def _permissions(
        self,
        ctx,
        member: converters.DiscordMember = None,
        channel: discord.TextChannel = None,
    ):
        """
        Usage:  -permissions [member] [channel]
        Permission: Manage Messages
        Output:
            Shows a member's permissions in a specific channel.
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
