import io
from collections import Counter, OrderedDict
from datetime import datetime
from operator import itemgetter
from re import M

import discord
from PIL import Image
from discord import member
from discord.ext import commands, menus

from utilities import converters, pagination, permissions, utils


def setup(bot):
    bot.add_cog(Tracking(bot))


class Tracking(commands.Cog):
    """
    Module for all user stats
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["mobile"], brief="Show which platform a user is on.")
    @commands.guild_only()
    async def platform(self, ctx, members: commands.Greedy[discord.Member]):
        """
        Usage:  -mobile <member> [member] [member]...
        Alias:  -platform
        Output: Shows whether a user is on desktop or mobile.
        Notes:  Cannot determine platform when users are offline.
        """
        if not len(members):
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}platform <member> [member] [member]...`",
            )
        mobilestatus = []
        notmobilestatus = []
        web_status = []
        offline = []
        for member in members:
            try:
                mobile = member.is_on_mobile()
            except Exception as e:
                await ctx.send_or_reply(
                    f"{self.bot.emote_dict['failed']} Somthing went wrong: {e}"
                )

            if mobile is True:
                mobilestatus.append(member)
            elif mobile is False and str(member.status) == "offline":
                offline.append(member)
            elif mobile is False and str(member.web_status) != "offline":
                web_status.append(member)
            else:
                notmobilestatus.append(member)
        if notmobilestatus:
            notmobile = []
            for member in notmobilestatus:
                users = []
                people = self.bot.get_user(int(member.id))
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    notmobile += [username]
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['desktop']} User{'' if len(notmobile) == 1 else 's'} `{', '.join(notmobile)}` {'is' if len(notmobile) == 1 else 'are'} on discord desktop.",
            )
        if mobilestatus:
            mobile = []
            for member in mobilestatus:
                users = []
                people = self.bot.get_user(int(member.id))
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    mobile += [username]
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['mobile']} User{'' if len(mobile) == 1 else 's'} `{', '.join(mobile)}` {'is' if len(mobile) == 1 else 'are'} on discord mobile.",
            )
        if web_status:
            mobile = []
            for member in web_status:
                users = []
                people = self.bot.get_user(int(member.id))
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    mobile += [username]
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['web']} User{'' if len(mobile) == 1 else 's'} `{', '.join(mobile)}` {'is' if len(mobile) == 1 else 'are'} on discord web.",
            )
        if offline:
            mobile = []
            for member in offline:
                users = []
                people = self.bot.get_user(int(member.id))
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    mobile += [username]
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['offline']} User{'' if len(mobile) == 1 else 's'} `{', '.join(mobile)}` {'is' if len(mobile) == 1 else 'are'} offline",
            )

    # @commands.command(
    #     brief="Show information on a user.",
    #     aliases=["whois", "ui", "profile", "user", "rawuser", "lookup"],
    # )
    # async def userinfo(self, ctx, member: converters.DiscordUser = None):
    #     """
    #     Usage:    -userinfo <member>
    #     Aliases:  -profile, -ui, -whois
    #     Examples: -userinfo Snowbot, -userinfo 810377376269205546
    #     Output:   Roles, permissions, and general stats on a user.
    #     Notes:
    #         Invoke command with -user, -rawuser, or -lookup
    #         to see all information collected on the user.
    #     """

    # if member is None:
    #     member = ctx.author

    # if member is None:
    #     member = ctx.author

    # if ctx.invoked_with in ["user", "rawuser", "lookup"]:
    #     return await self.user(ctx, user=member)

    # joinedList = []
    # for mem in ctx.guild.members:
    #     joinedList.append({"ID": mem.id, "Joined": mem.joined_at})

    # # sort the users by join date
    # joinedList = sorted(
    #     joinedList,
    #     key=lambda x: x["Joined"].timestamp() if x["Joined"] is not None else -1,
    # )

    # check_item = {"ID": member.id, "Joined": member.joined_at}

    # position = joinedList.index(check_item) + 1

    # msg = "{:,}".format(position)

    # query = '''
    #         SELECT COUNT(*)
    #         FROM commands
    #         WHERE author_id = $1
    #         AND server_id = $2;
    #         '''
    # command_count = (
    #     await self.bot.cxn.fetchrow(query, member.id, ctx.guild.id) or None
    # )
    # if command_count is None:
    #     command_count = 0

    # query = """
    #         SELECT COUNT(*)
    #         FROM messages
    #         WHERE author_id = $1
    #         AND server_id = $2;
    #         """
    # messages = await self.bot.cxn.fetchrow(query, member.id, ctx.guild.id) or None
    # if messages is None:
    #     messages = 0

    # status_dict = {
    #     "online": f"{self.bot.emote_dict['online']} Online",
    #     "offline": f"{self.bot.emote_dict['offline']} Offline",
    #     "dnd": f"{self.bot.emote_dict['dnd']} Do Not Disturb",
    #     "idle": f"{self.bot.emote_dict['idle']} Idle",
    # }
    # embed = discord.Embed(color=self.bot.constants.embed)
    # embed.set_author(name=f"{member}", icon_url=member.avatar_url)
    # embed.set_thumbnail(url=member.avatar_url)
    # embed.set_footer(
    #     text=f"User ID: {member.id} | Created on {member.created_at.__format__('%m/%d/%Y')}"
    # )
    # embed.add_field(
    #     name="Nickname",
    #     value=f"{self.bot.emote_dict['owner'] if member.id == ctx.guild.owner.id else self.bot.emote_dict['bot'] if member.bot else ''} {member.display_name}",
    # )
    # embed.add_field(
    #     name="Messages", value=f"{self.bot.emote_dict['messages']}  {messages[0]}"
    # )
    # embed.add_field(
    #     name="Commands",
    #     value=f"{self.bot.emote_dict['commands']}  {command_count[0]}",
    # )
    # embed.add_field(name="Status", value=f"{status_dict[str(member.status)]}")
    # embed.add_field(
    #     name="Highest Role",
    #     value=f"{self.bot.emote_dict['role']} {'@everyone' if member.top_role.name == '@everyone' else member.top_role.mention}",
    # )
    # embed.add_field(
    #     name="Join Position", value=f"{self.bot.emote_dict['invite']} #{msg}"
    # )
    # # perm_list = [Perm[0] for Perm in member.guild_permissions if Perm[1]]
    # # if len(member.roles) > 1:
    # #    role_list = member.roles[::-1]
    # #    role_list.remove(member.roles[0])
    # #    embed.add_field(name=f"Roles: [{len(role_list)}]", value =" ".join([role.mention for role in role_list]), inline=False)
    # # else:
    # #    embed.add_field(name=f"Roles: [0]", value ="** **", inline=False)
    # # embed.add_field(name="Permissions:", value=", ".join(perm_list).replace("_", " ").replace("guild", "server").title().replace("Tts", "TTS"), inline=False)
    # await ctx.send_or_reply(embed=embed)

    @commands.command(
        brief="Show information on a user.",
        aliases=["whois", "ui", "profile", "userinfo", "rawuser", "lookup"],
    )
    async def user(self, ctx, *, user: converters.DiscordUser = None):
        """
        Usage:   -user <user>
        Alias:   -lookup
        Example: -user 810377376269205546
        Output:  General information on any discord user.
        Notes:
            Accepts nickname, ID, mention, username, and username+discrim
            Neither you nor the bot must share a server with the user.
        """
        async with ctx.channel.typing():
            if user is None:
                user = ctx.author

            message = await ctx.send_or_reply(
                content=f"**{self.bot.emote_dict['loading']} Collecting User Data...**",
            )

            sid = int(user.id)
            timestamp = ((sid >> 22) + 1420070400000) / 1000
            cdate = datetime.utcfromtimestamp(timestamp)
            fdate = cdate.strftime("%A, %B %d, %Y at %H:%M:%S")

            try:
                member = self.bot.get_member(sid)
                user = member
            except Exception:
                pass

            tracking = self.bot.get_cog("Batch")

            title_str = f"{self.bot.emote_dict['info']} Information on **{user}**"
            msg = ""
            msg += f"Username      : {user}\n"
            if ctx.guild:
                if isinstance(user, discord.Member):
                    msg += f"Nickname      : {user.display_name}\n"
            msg += f"ID            : {user.id}\n"
            if tracking is not None:
                names = (await tracking.user_data(ctx, user))["usernames"]
                if names != str(user):
                    msg += f"Usernames     : {names}\n"
                # avatars = (await tracking.user_data(ctx, user))['avatars']
                # msg += f"Avatars       : {avatars}\n"
                if ctx.guild:
                    if isinstance(user, discord.Member):
                        nicknames = (await tracking.user_data(ctx, user))["nicknames"]
                        if nicknames:
                            if nicknames != user.display_name:
                                msg += f"Nicknames     : {nicknames}\n"
            msg += f"Common Servers: {sum(g.get_member(user.id) is not None for g in ctx.bot.guilds)}\n"
            unix = user.created_at.timestamp()
            msg += f"Created       : {utils.format_time(user.created_at)}\n"
            if ctx.guild:
                if isinstance(user, discord.Member):
                    unix = user.joined_at.timestamp()
                    msg += f"Joined        : {utils.format_time(user.joined_at)}\n"
                    joined_list = []
                    for mem in ctx.guild.members:
                        joined_list.append({"ID": mem.id, "Joined": mem.joined_at})
                    # sort the users by join date
                    joined_list = sorted(
                        joined_list,
                        key=lambda x: x["Joined"].timestamp()
                        if x["Joined"] is not None
                        else -1,
                    )
                    check_item = {"ID": user.id, "Joined": user.joined_at}

                    position = joined_list.index(check_item) + 1
                    pos = "{:,}".format(position)
                    msg += f"Join Position : {pos}/{len(user.guild.members)}\n"
            if tracking is not None:
                last_observed = await tracking.last_observed(user)
                if last_observed["last_seen"] is not None:
                    msg += f"Last Seen     : {last_observed['last_seen']} ago\n"
                if last_observed["last_spoke"] is not None:
                    msg += f"Last Spoke    : {last_observed['last_spoke']} ago\n"
                if ctx.guild:
                    if isinstance(user, discord.Member):
                        if last_observed["server_last_spoke"] is not None:
                            msg += f"Spoke here    : {last_observed['server_last_spoke']} ago\n"
            if ctx.guild:
                if isinstance(user, discord.Member):
                    query = """
                            SELECT COUNT(*)
                            FROM commands
                            WHERE author_id = $1
                            AND server_id = $2;
                            """
                    command_count = (
                        await self.bot.cxn.fetchrow(query, user.id, ctx.guild.id)
                        or None
                    )
                    if command_count is None:
                        command_count = 0

                    msg += f"Commands Run  : {command_count[0]}\n"

                    query = """
                            SELECT COUNT(*)
                            FROM messages
                            WHERE author_id = $1
                            AND server_id = $2;
                            """
                    message_count = (
                        await self.bot.cxn.fetchrow(query, user.id, ctx.guild.id)
                        or None
                    )
                    if message_count is None:
                        message_count = 0

                    msg += f"Messages Sent : {message_count[0]}\n"

            if ctx.guild:
                if isinstance(user, discord.Member) and user.activities:
                    msg += "Status        : {}\n".format(
                        "\n".join(self.activity_string(a) for a in user.activities)
                    )
            if ctx.guild:
                if isinstance(user, discord.Member):
                    msg += f"Roles         : {', '.join([r.name for r in sorted(user.roles, key=lambda r: -r.position) if r.name != '@everyone'])}\n"
            if ctx.guild:
                if isinstance(user, discord.Member):
                    perm_list = [Perm[0] for Perm in user.guild_permissions if Perm[1]]
                    msg += f'Permissions   : {", ".join(perm_list).replace("_", " ").replace("guild", "server").title().replace("Tts", "TTS")}'

            await message.edit(content=title_str)
            t = pagination.MainMenu(
                pagination.TextPageSource(
                    msg.replace("`", "\U0000ff40"), prefix="```yaml\n", suffix="```"
                )
            )
            try:
                await t.start(ctx)
            except menus.MenuError as e:
                await ctx.send_or_reply(e)

    @commands.command(name="status", brief="Show a user's status")
    async def status_(self, ctx, *, member: discord.Member = None):
        """
        Usage: -status <member>
        """
        if member is None:
            member = ctx.author
        status = "\n".join(self.activity_string(a) for a in member.activities)
        if status == "":
            return await ctx.send_or_reply(
                content=f"**{member.display_name}** has no current status.",
            )
        msg = f"**{member.display_name}'s** Status: {status}\n"
        await ctx.send_or_reply(msg)

    def activity_string(self, activity):
        if isinstance(activity, (discord.Game, discord.Streaming)):
            return str(activity)
        elif isinstance(activity, discord.Activity):
            ret = activity.name
            if activity.details:
                ret += " ({})".format(activity.details)
            if activity.state:
                ret += " - {}".format(activity.state)
            return ret
        elif isinstance(activity, discord.Spotify):
            elapsed = datetime.utcnow() - activity.start
            return "{}: {} by {} from {} [{}/{}]".format(
                activity.name,
                activity.title or "Unknown Song",
                activity.artist or "Unknown Artist",
                activity.album or "Unknown Album",
                self.format_timedelta(elapsed),
                self.format_timedelta(activity.duration),
            )
        else:
            return str(activity)

    def format_timedelta(self, td):
        ts = td.total_seconds()
        return "{:02d}:{:06.3f}".format(int(ts // 60), ts % 60)

    @commands.command(aliases=["mc"], brief="Count the messages a user sent.")
    @commands.guild_only()
    async def messagecount(self, ctx, member: discord.Member = None):
        """
        Usage:  -messagecount [user]
        Alias:  -mc
        Output: Shows how many messages a user has sent on the server.
        Permission: Manage Messages
        Notes:
            Will default to yourself if no user is passed.
        """
        user = ctx.author if member is None else member
        query = """SELECT COUNT(*) as c FROM messages WHERE author_id = $1 AND server_id = $2"""
        a = await self.bot.cxn.fetchrow(query, user.id, ctx.guild.id) or None
        if a is None:
            # await self.fix_member(ctx.author)
            return await ctx.send_or_reply(
                content="`{}` has sent **0** messages.".format(user),
            )
        else:
            a = int(a[0])
            await ctx.send_or_reply(
                content=f"`{user}` has sent **{a}** message{'' if a == 1 else 's'}",
            )

    @commands.command(brief="Show the top message senders.", aliases=["top"])
    @commands.guild_only()
    async def messagestats(self, ctx, limit: int = 100):
        """
        Usage: -messagestats
        Alias: -top
        Output: Top message senders in the server
        Permission: Manage Messages
        """

        query = """
                SELECT author_id,
                count(author_id)
                FROM messages
                WHERE server_id = $1
                GROUP BY author_id
                ORDER BY COUNT(author_id)
                DESC LIMIT $2
                """
        a = await self.bot.cxn.fetch(query, ctx.guild.id, limit)
        sum_query = """SELECT COUNT(*) FROM messages WHERE server_id = $1"""
        b = await self.bot.cxn.fetchrow(sum_query, ctx.guild.id)
        b = b[0]
        p = pagination.SimplePages(
            entries=[f"<@!{row[0]}>. [ Messages: {row[1]} ]" for row in a], per_page=20
        )
        p.embed.title = "**{0}** messages by **{1}** users.".format(
            b, len([x for x in ctx.guild.members])
        )

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @commands.command(brief="Show a user's nicknames.", aliases=["nicknames"])
    @commands.guild_only()
    @permissions.has_permissions(manage_messages=True)
    async def nicks(self, ctx, user: discord.Member = None):
        """
        Usage: -nicks [user]
        Alias: -nicknames
        Output: Embed of all user's nicknames.
        Permission: Manage Messages
        Notes:
            Will default to yourself if no user is passed
        """
        if user is None:
            user = ctx.author
        query = (
            """SELECT nicknames FROM nicknames WHERE server_id = $1 AND user_id = $2"""
        )
        name_list = await self.bot.cxn.fetchrow(query, ctx.guild.id, user.id)
        name_list = name_list[0].split(",")
        name_list = list(OrderedDict.fromkeys(name_list))

        p = pagination.SimplePages(entries=[f"`{n}`" for n in name_list])
        p.embed.title = f"Nicknames for {user}"

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @commands.command(brief="Show a user's usernames.", aliases=["usernames"])
    @commands.guild_only()
    @permissions.has_permissions(manage_messages=True)
    async def names(self, ctx, user: discord.Member = None):
        """
        Usage: -names [user]
        Alias: -usernames
        Output: Embed of all user's names.
        Permission: Manage Messages
        Notes:
            Will default to yourself if no user is passed
        """
        if user is None:
            user = ctx.author
        if user.bot:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['warn']} I do not track bots.",
            )

        query = """SELECT usernames FROM usernames WHERE user_id = $1"""
        name_list = await self.bot.cxn.fetchrow(query, user.id)
        name_list = name_list[0].split(",")
        name_list = list(OrderedDict.fromkeys(name_list))

        p = pagination.SimplePages(entries=[f"`{n}`" for n in name_list])
        p.embed.title = f"Usernames for {user}"

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @commands.command(brief="Show a user's avatars.", aliases=["avs"])
    @commands.guild_only()
    async def avatars(self, ctx, user: discord.Member = None):
        """
        Usage: -avatars [user]
        Alias: -avs
        Output:
            Embed of the past 16 avatars
            A user has had
        Permission: Manage Messages
        Notes:
            Will default to yourself if no user is passed
        """
        if user is None:
            user = ctx.author
        tracking = self.bot.get_cog("Batch")
        if not tracking:
            return await ctx.fail(f"This command is currently unavailable. Please try again later.")
        msg = await ctx.load(f"Collecting {user}'s Avatars...")
        res = await tracking.user_data(ctx, user)
        if not res['avatars']:
            # Tack on their current avatar
            res['avatars'] = [str(user.avatar_url_as(format="png", size=256))]
        
        em = discord.Embed(color=self.bot.constants.embed)
        em.title = f"Recorded Avatars for {user}"
        iteration = 0
        parent = Image.open("./data/assets/mask.png")
        for av in res['avatars']:
            print(av)
            if iteration < 4:
                val = 0
                x = iteration
            elif iteration >= 4 and iteration < 8:
                val = 1
                x = iteration - 4
            elif iteration >=8 and iteration < 12:
                val = 2
                x = iteration - 8
            elif iteration >=12 and iteration < 16:
                val = 3
                x = iteration - 12
            else:
                break

            res = await self.bot.get(av, res_method="read")
            av_bytes = io.BytesIO(res)
            im = Image.open(av_bytes)
            im = im.resize((256, 256))
            parent.paste(im, (x * 256, 256 * val))
            iteration += 1

        buffer = io.BytesIO()
        parent.save(buffer, "png")  # 'save' function for PIL
        buffer.seek(0)
        dfile = discord.File(fp=buffer, filename="avatars.png")
        em.set_image(url="attachment://avatars.png")
        await msg.delete()
        await ctx.send_or_reply(embed=em, file=dfile)


    @commands.command(
        brief="Check when a user was last seen.",
        aliases=["lastseen", "track", "tracker"],
    )
    @permissions.has_permissions(manage_messages=True)
    async def seen(self, ctx, user: converters.DiscordUser = None):
        """
        Usage:  -seen [user]
        Alias:  -lastseen, -track, -tracker
        Output: Get when a user was last observed on discord.
        Permission: Manage Messages
        Notes:
            User can be a mention, user id, or full discord
            username with discrim Username#0001.
            Will default to yourself if no user is passed
        """
        if user is None:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}seen <user>`",
            )

        if user.bot:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['warn']} I do not track bots.",
            )

        tracker = self.bot.get_cog("Batch")

        data = await tracker.last_observed(user)

        if data["last_seen"] is None:
            return await ctx.send_or_reply(content=f"I have not seen `{user}`")

        await ctx.send_or_reply(
            content=f"User `{user}` was last seen {data['last_seen']} ago.",
        )

    @commands.command(brief="Bot commands listed by popularity.")
    @commands.guild_only()
    @permissions.has_permissions(manage_messages=True)
    async def commandstats(self, ctx, user: discord.Member = None, limit=100):
        """
        Usage: -commandstats [user] [limit]
        Output: Most popular commands
        Permission: Manage Messages
        """
        if user is None:
            query = """SELECT command FROM commands WHERE server_id = $1"""
            command_list = await self.bot.cxn.fetch(query, ctx.guild.id)
            premsg = f"Commands most frequently used in **{ctx.guild.name}**"
        else:
            if user.bot:
                return await ctx.send_or_reply(
                    f"{self.bot.emote_dict['warn']} I do not track bots."
                )
            query = """SELECT command FROM commands WHERE server_id = $1 AND author_id = $2"""
            command_list = await self.bot.cxn.fetch(query, ctx.guild.id, user.id)
        formatted_list = []
        for c in command_list:
            formatted_list.append(c[0])

        counter = Counter(formatted_list)
        try:
            width = len(max(counter, key=len))
        except ValueError:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['warn']} User `{user}` has not run any commands.",
            )
        total = sum(counter.values())

        if limit > 0:
            common = counter.most_common(limit)
        else:
            common = counter.most_common()[limit:]
        output = "\n".join("{0:<{1}} : {2}".format(str(k), width, c) for k, c in common)

        msg = "{0} \n\nTOTAL: {1}".format(output, total)
        # await ctx.send_or_reply(premsg + '```yaml\n{}\n\nTOTAL: {}```'.format(output, total))
        pages = pagination.MainMenu(
            pagination.TextPageSource(msg, prefix="```yaml", max_size=500)
        )
        if user is None:
            title = f"Most common commands used in **{ctx.guild.name}**"
        else:
            title = f"Most common commands used by **{user.display_name}**"

        await ctx.send_or_reply(title)
        try:
            await pages.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(str(e))

    @commands.command(
        name="commands", brief="Count the commands run.", aliases=["commandcount"]
    )
    @commands.guild_only()
    @permissions.has_permissions(manage_messages=True)
    async def commandcount(self, ctx, user: discord.Member = None):
        """
        Usage:  -commands [user]
        Output: Command count for the user or server
        Permission: Manage Messages
        Notes:
            If no user is passed, will show total server commands
        """
        if user is None:
            query = """SELECT COUNT(*) as c FROM commands WHERE server_id = $1"""
            command_count = await self.bot.cxn.fetchrow(query, ctx.guild.id)
            return await ctx.send_or_reply(
                content=f"A total of **{command_count[0]:,}** command{' has' if int(command_count[0]) == 1 else 's have'} been executed on this server.",
            )
        else:
            if user.bot:
                return await ctx.send_or_reply(
                    f"{self.bot.emote_dict['warn']} I do not track bots."
                )
            query = """SELECT COUNT(*) as c FROM commands WHERE author_id = $1 AND server_id = $2"""
            command_count = await self.bot.cxn.fetchrow(query, user.id, ctx.guild.id)
            return await ctx.send_or_reply(
                content=f"User `{user}` has executed **{int(command_count[0]):,}** commands.",
            )

    @commands.command(brief="Show the top bot users.", aliases=["botusage"])
    @commands.guild_only()
    @permissions.has_permissions(manage_messages=True)
    async def usage(self, ctx, unit: str = "month"):
        """
        Usage: -usage [unit of time]
        ALias: -botusage
        Output: Top bot users in the server
        Permission: Manage Messages
        """
        unit = unit.lower()
        time_dict = {"day": 86400, "week": 604800, "month": 2592000, "year": 31556952}
        if unit not in time_dict:
            unit = "month"
        query = """SELECT COUNT(*) as c, author_id FROM commands WHERE server_id = $1 GROUP BY author_id ORDER BY c DESC LIMIT 25"""
        usage = await self.bot.cxn.fetch(query, ctx.guild.id)
        e = discord.Embed(
            title=f"Bot usage for the last {unit}",
            description=f"{sum(x[0] for x in usage)} commands from {len(usage)} user{'' if len(usage) == 1 else 's'}",
            color=self.bot.constants.embed,
        )
        for n, v in enumerate(usage[:24]):
            name = self.bot.get_user(v[1])
            e.add_field(
                name=f"{n+1}. {name}",
                value=f"{v[0]} command{'' if int(v[0]) == 1 else 's'}",
            )

        await ctx.send_or_reply(embed=e)

    @commands.command(brief="Most used words from a user.")
    @commands.guild_only()
    @permissions.has_permissions(manage_messages=True)
    async def words(self, ctx, mem_input=None, limit: int = 100):
        """
        Usage: -words [user]
        Output: Most commonly used words by the passed user
        Permission: Manage Messages
        Notes:
            Will default to yourself if no user is passed.
        """
        if mem_input is None:
            member = ctx.author
        else:
            try:
                member = await commands.MemberConverter().convert(ctx, mem_input)
            except commands.MemberNotFound:
                member = ctx.author
                if mem_input.isdigit():
                    limit = int(mem_input)

        if member.bot:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['warn']} I do not track bots.",
            )
        message = await ctx.send_or_reply(
            content=f"**{self.bot.emote_dict['loading']} Collecting Word Statistics...**",
        )
        query = """
                SELECT content
                FROM messages
                WHERE author_id = $1
                AND server_id = $2;
                """
        all_msgs = await self.bot.cxn.fetch(
            query,
            member.id,
            ctx.guild.id,
        )
        all_msgs = [x[0] for x in all_msgs]
        all_msgs = " ".join(all_msgs).split()
        all_msgs = list(filter(lambda x: len(x) > 0, all_msgs))
        all_words = Counter(all_msgs).most_common()[:limit]
        msg = ""
        for i in all_words:
            msg += f"Uses: [{str(i[1]).zfill(2)}] Word: {i[0]}\n"

        try:
            pages = pagination.MainMenu(
                pagination.TextPageSource(msg, prefix="```ini", max_size=1000)
            )
        except RuntimeError:
            return await message.edit(
                content=f"{self.bot.emote_dict['failed']} **Failed. Please try again.**"
            )
        await message.edit(
            content=f"Most common words sent by **{member.display_name}**",
        )
        try:
            await pages.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(str(e))

    @commands.command(brief="Usage for a specific word.")
    @commands.guild_only()
    @permissions.has_permissions(manage_messages=True)
    async def word(self, ctx, word: str = None, member: discord.Member = None):
        """
        Usage: -word <word> [user]
        Output: Number of times a word has been used by a user
        Permission: Manage Messages
        Notes:
            Will default to you if no user is passed.
        """
        if word is None:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}word <word> [user]`",
            )
        if member is None:
            member = ctx.author
        if member.bot:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['warn']} I do not track bots.",
            )

        message = await ctx.send_or_reply(
            content=f"**{self.bot.emote_dict['loading']} Collecting Word Statistics...**",
        )
        all_msgs = await self.bot.cxn.fetch(
            """SELECT content FROM messages WHERE author_id = $1 AND server_id = $2""",
            member.id,
            ctx.guild.id,
        )
        all_msgs = [x[0] for x in all_msgs]
        all_msgs = " ".join(all_msgs).split()
        all_msgs = list(filter(lambda x: len(x) > 0, all_msgs))
        all_msgs = " ".join(all_msgs).split()
        all_msgs = list(all_msgs)
        all_words = Counter(all_msgs).most_common()
        found = []
        for x in all_words:
            if x[0] == word:
                found.append(x)
                found.append(int(all_words.index(x)) + 1)
        if found == []:
            return await message.edit(
                content=f"The word `{word}` has never been used by **{member.display_name}**",
            )
        if str(found[1]).endswith("1") and found[1] != 11:
            common = str(found[1]) + "st"
        elif str(found[1]).endswith("2") and found[1] != 12:
            common = str(found[1]) + "nd"
        elif str(found[1]).endswith("3") and found[1] != 13:
            common = str(found[1]) + "rd"
        else:
            common = str(found[1]) + "th"
        await message.edit(
            content=f"The word `{word}` has been used {found[0][1]} time{'' if found[0][1] == 1 else 's'} and is the {common} most common word used by **{member.display_name}**"
        )

    @commands.command(brief="Show all users who spam.")
    @permissions.has_permissions(manage_messages=True)
    async def spammers(self, ctx):
        """
        Usage: -spammers
        Permission: Manage Messages
        Output: Users recorded spamming
        """
        query = """
                SELECT (user_id, spamcount)
                FROM spammers
                WHERE server_id = $1
                ORDER BY spamcount DESC;
                """
        result = await self.bot.cxn.fetch(query, ctx.guild.id)
        page_list = []
        for x in result:
            name = ctx.guild.get_member(x[0][0])
            if not name:
                continue
            page_list.append(
                {"name": name, "value": f"Times recorded spamming: {x[0][1]}"}
            )

        p = pagination.MainMenu(
            pagination.FieldPageSource(
                entries=[
                    ("{}. {}".format(y + 1, x["name"]), x["value"])
                    for y, x in enumerate(page_list)
                ],
                per_page=10,
                title=f"Recorded spammers in **{ctx.guild.name}** ({len(page_list):,} total)",
            )
        )
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @commands.group(
        brief="Show the most active server users.", invoke_without_command=True
    )
    @commands.guild_only()
    @permissions.has_permissions(manage_messages=True)
    async def activity(self, ctx, unit: str = "month"):
        """
        Usage: -activity [unit of time]
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

        await ctx.send_or_reply(embed=e)

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

        await ctx.send_or_reply(embed=e)
