import io
import time
import typing
import discord
import inspect

from collections import Counter, OrderedDict
from datetime import datetime
from discord.ext import commands, menus
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError

from utilities import utils
from utilities import checks
from utilities import cleaner
from utilities import converters
from utilities import decorators
from utilities import pagination


def setup(bot):
    bot.add_cog(Tracking(bot))


class Tracking(commands.Cog):
    """
    Module for all user stats
    """

    def __init__(self, bot):
        self.bot = bot

    @decorators.command(
        aliases=["inviter", "whoinvited"],
        brief="See who invited a user.",
        implemented="2021-05-10 09:08:00.476972",
        updated="2021-05-10 09:08:00.476972",
        examples="""
                {0}invited
                {0}invited Hecate
                {0}inviter Hecate#3523
                {0}inviter 708584008065351681
                """,
    )
    @commands.guild_only()
    @checks.has_perms(view_audit_log=True)
    async def invited(self, ctx, user: converters.DiscordMember = None):
        """
        Usage: {0}invited [user]
        Aliases: {0}inviter, {0}whoinvited
        Permission: View Audit Log
        Output:
            Show who invited the passed user.
        Notes:
            Will default to you if
            no user is passed.
        """
        if user is None:
            user = ctx.author
        query = """
                SELECT (inviter)
                FROM invites
                WHERE invitee = $1
                AND server_id = $2;
                """
        await ctx.trigger_typing()
        inviter_id = await self.bot.cxn.fetchval(query, user.id, ctx.guild.id)
        if not inviter_id:
            return await ctx.fail(f"I cannot trace who invited `{user}`")
        inviter = await self.bot.get_or_fetch_member(ctx.guild, inviter_id)
        await ctx.success(f"User `{user}` was invited by `{inviter}`")

    @decorators.command(
        brief="Count the invites of a user.",
        implemented="2021-05-10 09:08:00.476972",
        updated="2021-05-10 09:08:00.476972",
        examples="""
                {0}invites
                {0}invites Hecate
                {0}invites Hecate#3523
                {0}inviter 708584008065351681
                """,
    )
    @commands.guild_only()
    async def invites(self, ctx, user: converters.DiscordMember = None):
        """
        Usage: {0}invites [user]
        Output:
            Show how many users a user
            has invited.
        Notes:
            Will default to you if
            no user is passed.
        """
        if user is None:
            user = ctx.author
        query = """
                SELECT COUNT(*)
                FROM invites
                WHERE inviter = $1
                AND server_id = $2;
                """
        await ctx.trigger_typing()
        count = await self.bot.cxn.fetchval(query, user.id, ctx.guild.id)
        if not count or count == 0:
            return await ctx.fail(f"User `{user}` has invited zero new users.")
        await ctx.success(
            f"User `{user}` has invited {count} new user{'' if count == 1 else 's'}."
        )

    @decorators.command(
        aliases=["mobile", "web", "desktop"],
        brief="Show a user's discord platform.",
        implemented="2021-03-25 05:56:35.053930",
        updated="2021-05-06 23:25:08.685407",
        examples="""
                {0}web @Hecate Snowbot 708584008065351681
                {0}mobile @Hecate Snowbot 708584008065351681
                {0}desktop @Hecate Snowbot 708584008065351681
                {0}platform @Hecate Snowbot 708584008065351681
                """,
    )
    @commands.guild_only()
    async def platform(self, ctx, users: commands.Greedy[converters.DiscordMember]):
        """
        Usage:  {0}platform [users]...
        Alias:  {0}mobile, {0}desktop, {0}web
        Output:
            Shows which discord platform a user
            is currently on. Can be discord desktop,
            discord mobile, or discord web.
        Notes:
            The bot cannot determine platform
            when users are offline or if their
            status is invisible.
        """
        if not len(users):
            return await ctx.usage()
        mobilestatus = []
        mobilestatus = []
        notmobilestatus = []
        web_status = []
        offline = []
        for member in users:
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
                content=f"{self.bot.emote_dict['search']} User{'' if len(mobile) == 1 else 's'} `{', '.join(mobile)}` {'is' if len(mobile) == 1 else 'are'} on discord web.",
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

    @decorators.command(
        brief="Show information on a user.",
        aliases=["rawuser", "lookup"],
        implemented="2021-03-11 23:54:09.760439",
        updated="2021-05-06 23:25:08.683192",
        examples="""
                {0}user
                {0}user Hecate
                {0}user @Hecate
                {0}user Hecate#3523
                {0}user 708584008065351681
                {0}lookup
                {0}lookup Hecate
                {0}lookup @Hecate
                {0}lookup Hecate#3523
                {0}lookup 708584008065351681
                {0}rawuser
                {0}rawuser Hecate
                {0}rawuser @Hecate
                {0}rawuser Hecate#3523
                {0}rawuser 708584008065351681
                """,
    )
    @checks.has_perms(view_audit_log=True)
    async def user(self, ctx, *, user: converters.DiscordUser = None):
        """
        Usage:   {0}user [user]
        Alias:   {0}lookup
        Output:  General information on any discord user.
        Notes:
            Accepts nickname, ID, mention, username, and username+discrim
            Neither you nor the bot must share a server with the passed user.
            Will default to you if no user is passed into the command.
        """
        if user is None:
            user = ctx.author

        batch = self.bot.get_cog("Batch")
        if not batch:
            raise commands.DisabledCommand()

        message = await ctx.load(f"Collecting User Data...")
        await ctx.trigger_typing()
        title_str = f"{self.bot.emote_dict['info']} Information on **{user}**"

        msg = ""
        usernames = await batch.get_names(user)
        msg += f"ID            : {user.id}\n"
        msg += f"Username{' ' if len(usernames) == 1 else 's'}     : {', '.join(usernames)}\n"
        if ctx.guild and isinstance(user, discord.Member):
            nicknames = await batch.get_nicks(user)
            msg += f"Nickname{' ' if len(nicknames) == 1 else 's'}     : {', '.join(nicknames)}\n"
        msg += f"Common Servers: {sum(g.get_member(user.id) is not None for g in ctx.bot.guilds)}\n"
        msg += f"Created       : {utils.format_time(user.created_at)}\n"
        if ctx.guild and isinstance(user, discord.Member):
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
        last_observed = await batch.last_observed(user)
        if last_observed["last_seen"]:
            msg += f"Last Seen     : {last_observed['last_seen']} ago\n"
        if last_observed["last_spoke"]:
            msg += f"Last Spoke    : {last_observed['last_spoke']} ago\n"
        if ctx.guild and isinstance(user, discord.Member):
            if last_observed["server_last_spoke"]:
                msg += f"Spoke here    : {last_observed['server_last_spoke']} ago\n"
            query = """
                    SELECT COUNT(*)
                    FROM commands
                    WHERE author_id = $1
                    AND server_id = $2;
                    """
            command_count = await self.bot.cxn.fetchval(query, user.id, ctx.guild.id)
            if not command_count:
                command_count = 0

            msg += f"Commands Run  : {command_count}\n"

            query = """
                    SELECT COUNT(*)
                    FROM messages
                    WHERE author_id = $1
                    AND server_id = $2;
                    """
            message_count = await self.bot.cxn.fetchval(query, user.id, ctx.guild.id)
            if not message_count:
                message_count = 0

            msg += f"Messages Sent : {message_count}\n"

            if user.activities:
                try:
                    msg += "Status        : {}\n".format(
                        "\n".join(self.activity_string(a) for a in user.activities)
                    )
                except Exception:
                    pass
            msg += f"Roles         : {', '.join([r.name for r in sorted(user.roles, key=lambda r: -r.position) if r.name != '@everyone'])}\n"
            perm_list = [Perm[0] for Perm in user.guild_permissions if Perm[1]]
            msg += f'Permissions   : {", ".join(perm_list).replace("_", " ").replace("guild", "server").title().replace("Tts", "TTS")}'

        await message.edit(content=title_str)
        t = pagination.MainMenu(
            pagination.TextPageSource(
                cleaner.clean_all(msg), prefix="```yaml\n", suffix="```"
            )
        )
        try:
            await t.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @decorators.command(
        name="status",
        aliases=["game", "presence", "playing"],
        brief="Show a user's discord status.",
        implemented="2021-03-22 16:31:55.693675",
        updated="2021-05-06 23:31:16.992062",
        examples="""
                {0}game
                {0}game Hecate
                {0}game @Hecate
                {0}game Hecate#3523
                {0}game 708584008065351681
                {0}status
                {0}status Hecate
                {0}status @Hecate
                {0}status Hecate#3523
                {0}status 708584008065351681
                {0}playing
                {0}playing Hecate
                {0}playing @Hecate
                {0}playing Hecate#3523
                {0}playing 708584008065351681
                {0}presence
                {0}presence Hecate
                {0}presence @Hecate
                {0}presence Hecate#3523
                {0}presence 708584008065351681
                """,
    )
    async def status(self, ctx, *, user: converters.DiscordMember = None):
        """
        Usage: {0}status [user]
        Aliases:
            {0}game, {0}playing, {0}activity, {0}presence
        Output:
            Shows a user's current activity (if exists).
        Notes:
            Will default to you if no user is passed.
        """
        if user is None:
            user = ctx.author
        status = "\n".join(self.activity_string(a) for a in user.activities)
        if status == "":
            return await ctx.send_or_reply(
                content=f"**{user.display_name}** has no current status.",
            )
        msg = f"**{user.display_name}'s** Status: {status}\n"
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

    @decorators.command(aliases=["mc"], brief="Count the messages a user sent.")
    @commands.guild_only()
    async def messagecount(self, ctx, member: converters.DiscordMember = None):
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

    @decorators.command(
        aliases=["top", "messagestatistics"],
        brief="Show the top message senders.",
        implemented="2021-04-03 01:56:35.751553",
        updated="2021-05-06 23:36:18.959143",
        examples="""
                {0}top
                {0}top 500
                {0}messagestats
                {0}messagestats 200
                {0}messagestatistics 
                {0}messagestatistics 40
                """,
    )
    @commands.guild_only()
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    @checks.has_perms(view_audit_log=True)
    async def messagestats(self, ctx, limit: str = "100"):
        """
        Usage: {0}messagestats
        Alias: {0}top, {0}messagestatistics
        Permission: View Audit Log
        Output:
            Show top message senders in the server
        Notes:
            Specify the limit kwarg to adjust the
            number of members to include in the
            messagestats embed
        """
        if not limit.isdigit():
            raise commands.BadArgument("The `limit` argument must be an integer.")
        limit = int(limit)
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

    @decorators.command(
        aliases=["nicks", "usernicks"],
        brief="Show a user's past nicknames.",
        implemented="2021-03-12 00:00:21.562534",
        updated="2021-05-06 23:43:13.297667",
        examples="""
                {0}nicks
                {0}nicks Hecate
                {0}nicks @Hecate
                {0}nicks Hecate#3523
                {0}nicks 708584008065351681
                {0}nicknames
                {0}nicknames Hecate
                {0}nicknames @Hecate
                {0}nicknames Hecate#3523
                {0}nicknames 708584008065351681
                {0}usernicks
                {0}usernicks Hecate
                {0}usernicks @Hecate
                {0}usernicks Hecate#3523
                {0}usernicks 708584008065351681
                """,
    )
    @commands.guild_only()
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    @checks.has_perms(view_audit_log=True)
    async def nicknames(self, ctx, user: converters.DiscordMember = None):
        """
        Usage: {0}nicknames [user]
        Alias: {0}nicks, {0}usernicks
        Permission: View Audit Log
        Output:
            Shows an embed of all the passed user's
            nicknames (past and present).
        Notes:
            Will default to yourself if no user is passed
        """
        if user is None:
            user = ctx.author
        if user.bot:
            return await ctx.fail("I do not track bots.")
        batch = self.bot.get_cog("Batch")
        if not batch:
            raise commands.DisabledCommand()
        await ctx.trigger_typing()
        nicknames = await batch.get_nicks(user)

        p = pagination.SimplePages([f"**{x}**" for x in nicknames], per_page=15)
        p.embed.title = f"{user}'s Recorded Nicknames"
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @decorators.command(
        aliases=["names"],
        brief="Show a user's past usernames.",
        implemented="2021-03-27 03:31:08.799676",
        updated="2021-05-06 23:43:13.297667",
        examples="""
                {0}names
                {0}names Hecate
                {0}names @Hecate
                {0}names Hecate#3523
                {0}names 708584008065351681
                {0}usernames
                {0}usernames Hecate
                {0}usernames @Hecate
                {0}usernames Hecate#3523
                {0}usernames 708584008065351681
                """,
    )
    @commands.guild_only()
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    @checks.has_perms(view_audit_log=True)
    async def usernames(self, ctx, user: converters.DiscordUser = None):
        """
        Usage: {0}usernames [user]
        Alias: {0}names
        Output:
            Shows an embed of all past and present
            usernames for the specified user.
        Permission: View Audit Log
        Notes:
            Will default to you if no user is passed.
        """
        if user is None:
            user = ctx.author
        if user.bot:
            return await ctx.fail("I do not track bots.")
        batch = self.bot.get_cog("Batch")
        if not batch:
            raise commands.DisabledCommand()
        await ctx.trigger_typing()
        usernames = await batch.get_names(user)

        p = pagination.SimplePages([f"**{x}**" for x in usernames], per_page=15)
        p.embed.title = f"{user.display_name}'s Recorded Usernames"
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @decorators.command(
        aliases=["avs", "avatarhistory", "avhistory"],
        brief="Show a user's past avatars.",
        implemented="2021-03-27 01:14:06.076262",
        updated="2021-05-06 23:50:27.540481",
        examples="""
                {0}avs
                {0}avs Hecate
                {0}avs @Hecate
                {0}avs Hecate#3523
                {0}avs 708584008065351681
                {0}avatars
                {0}avatars Hecate
                {0}avatars @Hecate
                {0}avatars Hecate#3523
                {0}avatars 708584008065351681
                """,
    )
    @commands.guild_only()
    @checks.bot_has_perms(
        add_reactions=True, attach_files=True, embed_links=True, external_emojis=True
    )
    @checks.has_perms(view_audit_log=True)
    async def avatars(self, ctx, user: converters.DiscordMember = None):
        """
        Usage: {0}avatars [user]
        Alias: {0}avs, {0}avhistory {0}avatarhistory
        Output:
            Shows an embed containing up to
            the 16 last avatars of a user.
        Permission: View Audit Log
        Notes:
            Will default to you if no user is passed.
        """
        if user is None:
            user = ctx.author
        if user.bot:
            return await ctx.fail("I do not track bots.")

        batch = self.bot.get_cog("Batch")
        if not batch:
            raise commands.DisabledCommand()

        msg = await ctx.load(f"Collecting {user}'s Avatars...")
        avatars = await batch.get_avs(user)
        if not avatars:
            # Tack on their current avatar
            avatars.append([str(user.avatar_url_as(format="png", size=256))])

        em = discord.Embed(color=self.bot.constants.embed)
        em.title = f"Recorded Avatars for {user}"
        iteration = 0
        parent = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
        for av in avatars:
            if iteration < 4:
                val = 0
                x = iteration
            elif iteration >= 4 and iteration < 8:
                val = 1
                x = iteration - 4
            elif iteration >= 8 and iteration < 12:
                val = 2
                x = iteration - 8
            elif iteration >= 12 and iteration < 16:
                val = 3
                x = iteration - 12
            else:
                break

            res = await self.bot.get(str(av), res_method="read")
            av_bytes = io.BytesIO(res)
            av_bytes.seek(0)
            try:
                im = Image.open(av_bytes)
            except UnidentifiedImageError:
                continue
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

    @decorators.command(
        aliases=["lastseen", "track", "tracker", "observed"],
        brief="Check when a user was last seen.",
        implemented="2021-03-12 00:02:48.206914",
        updated="2021-05-06 23:52:15.847160",
        examples="""
                {0}seen Hecate
                {0}seen @Hecate
                {0}seen Hecate#3523
                {0}seen 708584008065351681
                {0}track Hecate
                {0}track @Hecate
                {0}track Hecate#3523
                {0}track 708584008065351681
                {0}tracker Hecate
                {0}tracker @Hecate
                {0}tracker Hecate#3523
                {0}tracker 708584008065351681
                {0}lastseen Hecate
                {0}lastseen @Hecate
                {0}lastseen Hecate#3523
                {0}lastseen 708584008065351681
                {0}observed Hecate
                {0}observed @Hecate
                {0}observed Hecate#3523
                {0}observed 708584008065351681
                """,
    )
    @checks.has_perms(view_audit_log=True)
    async def seen(self, ctx, *, user: converters.DiscordUser):
        """
        Usage: {0}seen <user>
        Aliases:
            {0}lastseen, {0}track, {0}tracker, {0}observed
        Permission: View Audit Log
        Output:
            Show how long its been since a user
            was last observed using discord.
        Notes:
            User can be a mention, user id, or full discord
            username with discrim Username#0001.
        """
        async with ctx.typing():
            if user.bot:
                raise commands.BadArgument("I do not track bots.")

            tracker = self.bot.get_cog("Batch")
            data = await tracker.last_observed(user)

            if not data["last_seen"]:
                return await ctx.send_or_reply(content=f"I have not seen `{user}`")
            if data["action"]:
                msg = f"User `{user}` was last seen {data['action']} **{data['last_seen']}** ago."
            else:
                msg = f"User `{user}` was last seen **{data['last_seen']}** ago."
            await ctx.send_or_reply(f"{self.bot.emote_dict['clock']} {msg}")

    @decorators.command(
        aliases=["cs"],
        brief="Bot commands listed by popularity.",
        implemented="2021-03-11 20:07:53.950050",
        updated="2021-05-07 00:03:33.918725",
        examples="""
                {0}cs
                {0}cs @Hecate
                {0}cs @Hecate 200
                {0}commandstats
                {0}commandstats @Hecate
                {0}commandstats @Hecate 200
                """,
    )
    @commands.guild_only()
    @checks.bot_has_perms(add_reactions=True, external_emojis=True)
    @checks.has_perms(view_audit_log=True)
    async def commandstats(
        self, ctx, user: typing.Optional[converters.DiscordMember], limit: int = 100
    ):
        """
        Usage: {0}commandstats [user] [limit]
        Alias: {0}cs
        Permission: View Audit Log
        Output:
            Show the most popular commands in
            a pagination session.
        Notes:
            If no user is passed, the bot will
            show the most popular commands across
            the entire server. Specify a limit
            argument to control how many commands
            should be included (100 by default).
        """
        if user is None:
            query = """
                    SELECT command
                    FROM commands
                    WHERE server_id = $1;
                    """
            command_list = await self.bot.cxn.fetch(query, ctx.guild.id)
        # if not limit.isdigit():
        #     raise commands.BadArgument("The `limit` argument must be an integer.")
        else:
            if user.bot:
                return await ctx.fail(f"I do not track bots.")
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

    @decorators.command(
        brief="Count the commands run by a user.",
        aliases=["cc"],
        implemented="2021-03-11 18:22:43.628118",
        updated="2021-05-05 04:49:50.161683",
        examples="""
                {0}cc
                {0}cc Hecate
                {0}cc @Hecate
                {0}cc Hecate#3523
                {0}cc 708584008065351681
                {0}commandcount
                {0}commandcount Hecate
                {0}commandcount @Hecate
                {0}commandcount Hecate#3523
                {0}commandcount 708584008065351681
                """,
    )
    @commands.guild_only()
    @checks.has_perms(view_audit_log=True)
    async def commandcount(self, ctx, user: converters.DiscordMember = None):
        """
        Usage: {0}commandcount [user]
        Alias: {0}cc
        Permission: View Audit Log
        Output:
            Command count for a specific user.
        Notes:
            If no user is passed, the bot
            will show total server commands.
        """
        if user is None:
            query = """
                    SELECT COUNT(*) as c
                    FROM commands
                    WHERE server_id = $1;
                    """
            command_count = await self.bot.cxn.fetchrow(query, ctx.guild.id)
            return await ctx.send_or_reply(
                f"{self.bot.emote_dict['graph']} A total of **{command_count[0]:,}** command{' has' if int(command_count[0]) == 1 else 's have'} been executed on this server.",
            )
        else:
            if user.bot:
                return await ctx.fail("I do not track bots.")
            query = """
                    SELECT COUNT(*) as c
                    FROM commands
                    WHERE author_id = $1
                    AND server_id = $2;
                    """
            command_count = await self.bot.cxn.fetchrow(query, user.id, ctx.guild.id)
            return await ctx.send_or_reply(
                f"{self.bot.emote_dict['graph']} User `{user}` has executed **{int(command_count[0]):,}** commands.",
            )

    @decorators.command(
        brief="Show the top bot users.",
        implemented="2021-03-27 22:05:32.358714",
        updated="2021-05-07 02:24:13.585137",
        examples="""
                {0}botusage
                {0}botusage day
                {0}botusage week
                {0}botusage month
                {0}botusage year
                """,
    )
    @commands.guild_only()
    @checks.bot_has_perms(embed_links=True)
    @checks.has_perms(view_audit_log=True)
    async def botusage(self, ctx, unit: str = "month"):
        """
        Usage: {0}botusage [unit of time]
        Permission: View Audit Log
        Output: Top bot users in the server
        """
        unit = unit.lower()
        time_dict = {"day": 86400, "week": 604800, "month": 2592000, "year": 31556952}
        if unit not in time_dict:
            unit = "month"
        query = """
                SELECT COUNT(*) as c, author_id
                FROM commands
                WHERE server_id = $1
                GROUP BY author_id
                ORDER BY c DESC LIMIT 25;
                """
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

    @decorators.command(
        brief="Most used words from a user.",
        implemented="2021-03-11 20:10:05.766906",
        updated="2021-05-07 02:24:13.585137",
        examples="""
                {0}words
                {0}words 700
                {0}words Hecate
                {0}words @Hecate
                {0}words Hecate#3523
                {0}words 708584008065351681
                {0}words Hecate 300
                {0}words @Hecate 400
                {0}words Hecate#3523 500
                {0}words 708584008065351681 600
                """,
    )
    @commands.guild_only()
    @checks.bot_has_perms(add_reactions=True, external_emojis=True)
    @checks.has_perms(manage_messages=True)
    async def words(self, ctx, user=None, limit: str = "100"):
        """
        Usage: {0}words [user] [limit]
        Output: Most commonly used words by the passed user
        Permission: Manage Messages
        Notes:
            Will default to yourself if no user is passed.
            Pass a limit argument after or instead of a user
            argument to limit the number of common words to show.
        """
        if user is None:
            member = ctx.author
            limit = int(limit)
        else:
            try:
                member = await commands.MemberConverter().convert(ctx, user)
                if not limit.isdigit():
                    raise commands.BadArgument(
                        "The `limit` argument must be an integer."
                    )
                else:
                    limit = int(limit)
            except commands.MemberNotFound:
                member = ctx.author
                if user.isdigit():
                    limit = int(user)
                else:
                    raise commands.BadArgument(f"User `{user}` not found.")

        if member.bot:
            return await ctx.fail("I do not track bots.")
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

    @decorators.command(
        brief="Usage for a specific word.",
        implemented="2021-03-13 18:18:34.790741",
        updated="2021-05-07 03:51:54.934511",
        examples="""
                {0}word Hello
                {0}word Hello Hecate
                {0}word Hello @Hecate
                {0}word Hello Hecate#3523
                {0}word Hello 708584008065351681
                """,
    )
    @commands.guild_only()
    @checks.bot_has_perms(add_reactions=True, external_emojis=True)
    @checks.has_perms(manage_messages=True)
    async def word(self, ctx, word, member: converters.DiscordMember = None):
        """
        Usage: {0}word <word> [user]
        Permission: Manage Messages
        Output:
            Show how many times a specific word
            has been used by a user.
        Notes:
            Will default to you if no user is passed.
        """
        if member is None:
            member = ctx.author
        if member.bot:
            raise commands.BadArgument("I do not track bots.")
        message = await ctx.send_or_reply(
            content=f"**{self.bot.emote_dict['loading']} Collecting Word Statistics...**",
        )
        query = """
                SELECT content
                FROM messages
                WHERE author_id = $1
                AND server_id = $2
                """
        all_msgs = await self.bot.cxn.fetch(query, member.id, ctx.guild.id)
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

    @decorators.command(
        brief="Show all recorded spammers.",
        implemented="2021-04-25 01:32:06.151615",
        updated="2021-05-07 04:15:46.972946",
        examples="""
                {0}spammers
                """,
    )
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    @checks.has_perms(manage_messages=True)
    async def spammers(self, ctx):
        """
        Usage: {0}spammers
        Permission: Manage Messages
        Output:
            Shows a pagination session with users
            who were recorded spamming in the server.
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
                title=f"Spammers in **{ctx.guild.name}** ({len(page_list):,} total)",
            )
        )
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @decorators.command(
        brief="Show the most active server users.",
        invoke_without_command=True,
        case_insensitive=True,
        implemented="2021-03-13 04:47:25.624232",
        updated="2021-05-07 04:26:00.620200",
        examples="""
                {0}activity
                {0}activity day
                {0}activity week
                {0}activity month
                {0}activity year
                """,
    )
    @commands.guild_only()
    @checks.bot_has_perms(embed_links=True)
    @checks.has_perms(manage_messages=True)
    async def activity(self, ctx, unit: str = "month"):
        """
        Usage: {0}activity [unit of time]
        Permission: Manage Messages
        Output:
            Shows the most active server
            users ordered by the number
            of messages they've sent.
        Notes:
            If no unit of time is specified,
            of if the unit is invalid, the bot
            will default to month for its unit.
        """
        unit = unit.lower()
        time_dict = {"day": 86400, "week": 604800, "month": 2592000, "year": 31556952}
        if unit not in time_dict:
            unit = "month"
        time_seconds = time_dict.get(unit, 2592000)
        now = int(time.time())
        diff = now - time_seconds
        query = """
                SELECT COUNT(*) as c, author_id
                FROM messages
                WHERE server_id = $1
                AND unix > $2
                GROUP BY author_id
                ORDER BY c DESC LIMIT 25;
                """
        stuff = await self.bot.cxn.fetch(query, ctx.guild.id, diff)

        e = discord.Embed(
            title=f"Message Leaderboard",
            description=f"{sum(x[0] for x in stuff)} messages from {len(stuff)} user{'' if len(stuff) == 1 else 's'} in the last {unit}",
            color=self.bot.constants.embed,
        )
        for n, v in enumerate(stuff[:24]):
            try:
                name = ctx.guild.get_member(int(v[1])).name
            except AttributeError:
                continue
            e.add_field(
                name=f"{n+1}. {name}",
                value=f"{v[0]} message{'' if int(v[0]) == 1 else 's'}",
            )

        await ctx.send_or_reply(embed=e)

    @decorators.command(
        aliases=["chars"],
        brief="Show character usage.",
        implemented="2021-04-19 06:02:49.713396",
        updated="2021-05-07 04:31:07.411009",
        examples="""
                {0}chars
                {0}chars day
                {0}chars week
                {0}chars month
                {0}chars year
                {0}characters
                {0}characters day
                {0}characters week
                {0}characters month
                {0}characters year
                """,
    )
    @commands.guild_only()
    @checks.bot_has_perms(embed_links=True)
    @checks.has_perms(manage_messages=True)
    async def characters(self, ctx, unit: str = "day"):
        """
        Usage: {0}characters [unit of time]
        Alias: {0}chars
        Permission: Manage Messages
        Output:
            Shows the most active server
            users ordered by the number
            of characters they've sent.
        Notes:
            If no unit of time is specified,
            of if the unit is invalid, the bot
            will default to day for its unit.
        """
        unit = unit.lower()
        time_dict = {"day": 86400, "week": 604800, "month": 2592000, "year": 31556952}
        if unit not in time_dict:
            unit = "day"
        time_seconds = time_dict.get(unit, 2592000)
        now = int(time.time())
        diff = now - time_seconds
        query = """
                SELECT SUM(LENGTH(content)) as c, author_id, COUNT(*)
                FROM messages
                WHERE server_id = $1
                AND unix > $2
                GROUP BY author_id
                ORDER BY c DESC LIMIT 25"""
        stuff = await self.bot.cxn.fetch(query, ctx.guild.id, diff)
        e = discord.Embed(
            title="Character Leaderboard",
            description=f"{sum(x[0] for x in stuff)} characters from {len(stuff)} user{'' if len(stuff) == 1 else 's'} in the last {unit}",
            color=self.bot.constants.embed,
        )
        for n, v in enumerate(stuff):
            try:
                name = ctx.guild.get_member(int(v[1])).name
            except AttributeError:
                continue
            e.add_field(name=f"{n+1}. {name}", value=f"{v[0]:,} chars")

        await ctx.send_or_reply(embed=e)

    @decorators.command(
        aliases=["piestatus", "ps"],
        brief="Status info and online time stats.",
        implemented="2021-04-29 22:10:20.348498",
        updated="2021-05-07 04:15:46.972946",
        examples="""
                {0}ps
                {0}ps Hecate
                {0}ps @Hecate
                {0}ps Hecate#3523
                {0}ps 708584008065351681
                {0}piestatus
                {0}piestatus Hecate
                {0}piestatus @Hecate
                {0}piestatus Hecate#3523
                {0}piestatus 708584008065351681
                {0}statusinfo
                {0}statusinfo Hecate
                {0}statusinfo @Hecate
                {0}statusinfo Hecate#3523
                {0}statusinfo 708584008065351681
                """,
    )
    @checks.bot_has_perms(attach_files=True, embed_links=True)
    @checks.has_perms(view_audit_log=True)
    async def statusinfo(self, ctx, user: converters.DiscordMember = None):
        """
        Usage: {0}statusinfo [user]
        Aliases: {0}piestatus, {0}ps,
        Output:
            Show a pie chart graph with details of the
            passed user's status statistics.
        Notes:
            Will default to yourself if no user is passed.
        """
        if not user:
            user = ctx.author
        if user.bot:
            raise commands.BadArgument("I do not track bots.")

        await ctx.trigger_typing()
        query = """
                SELECT * FROM userstatus
                WHERE user_id = $1;
                """
        data = await self.bot.cxn.fetch(query, user.id)
        if not data:
            return await self.do_generic(ctx, user)
        for row in data:
            starttime = row["starttime"]
            online_time = row["online"]
            idle_time = row["idle"]
            dnd_time = row["dnd"]
            last_change = row["last_changed"]

        em = discord.Embed(color=self.bot.constants.embed)
        img = Image.new("RGBA", (2400, 1024), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype("./data/assets/Helvetica.ttf", 100)

        unix_timestamp = time.time()
        total = unix_timestamp - starttime

        if str(user.status) == "online":
            online_time += unix_timestamp - last_change
        elif str(user.status) == "idle":
            idle_time += unix_timestamp - last_change
        elif str(user.status) == "dnd":
            dnd_time += unix_timestamp - last_change

        uptime = online_time + idle_time + dnd_time
        offline_time = total - uptime
        raw_percent = uptime / total

        status_list = [online_time, idle_time, dnd_time, offline_time]
        status_list.sort()
        if raw_percent > 1:
            raw_percent = 1
        percent = f"{raw_percent:.2%}"
        em = discord.Embed(color=self.bot.constants.embed)
        img = Image.new("RGBA", (2500, 1024), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype("./data/assets/Helvetica.ttf", 100)
        w, h = 1050, 1000
        shape = [(50, 0), (w, h)]
        draw.arc(
            shape,
            start=0,
            end=360 * (status_list[-1] / total),
            fill=self.get_color(self.retrieve_name(status_list[-1])),
            width=200,
        )
        start = 360 * (status_list[-1] / total)
        draw.arc(
            shape,
            start=start,
            end=start + 360 * (status_list[-2] / total),
            fill=self.get_color(self.retrieve_name(status_list[-2])),
            width=200,
        )
        start = start + 360 * (status_list[-2] / total)
        draw.arc(
            shape,
            start=start,
            end=start + 360 * (status_list[-3] / total),
            fill=self.get_color(self.retrieve_name(status_list[-3])),
            width=200,
        )
        start = start + 360 * (status_list[-3] / total)
        draw.arc(
            shape,
            start=start,
            end=start + 360 * (status_list[-4] / total),
            fill=self.get_color(self.retrieve_name(status_list[-4])),
            width=200,
        )
        self.center_text(img, 1100, 1000, font, percent, (255, 255, 255))
        font = ImageFont.truetype("./data/assets/Helvetica-Bold.ttf", 85)
        draw.text(
            (1200, 0), "Status Tracking Startdate:", fill=(255, 255, 255), font=font
        )
        font = ImageFont.truetype("./data/assets/Helvetica.ttf", 68)
        draw.text(
            (1200, 100),
            utils.timeago(
                datetime.utcnow() - datetime.utcfromtimestamp(starttime)
            ),  # .split(".")[0] + "]",
            fill=(255, 255, 255),
            font=font,
        )
        font = ImageFont.truetype("./data/assets/Helvetica-Bold.ttf", 85)
        draw.text((1200, 300), "Total Online Time:", fill=(255, 255, 255), font=font)
        font = ImageFont.truetype("./data/assets/Helvetica.ttf", 68)
        draw.text(
            (1200, 400),
            f"{uptime/3600:.2f} {'Hour' if int(uptime/3600) == 1 else 'Hours'}",
            fill=(255, 255, 255),
            font=font,
        )
        font = ImageFont.truetype("./data/assets/Helvetica-Bold.ttf", 85)
        draw.text((1200, 600), "Status Information:", fill=(255, 255, 255), font=font)
        font = ImageFont.truetype("./data/assets/Helvetica.ttf", 68)
        draw.rectangle((1200, 800, 1275, 875), fill=(46, 204, 113), outline=(0, 0, 0))
        draw.text(
            (1300, 810),
            f"Online: {online_time/total:.2%}",
            fill=(255, 255, 255),
            font=font,
        )
        draw.rectangle((1850, 800, 1925, 875), fill=(255, 228, 0), outline=(0, 0, 0))
        draw.text(
            (1950, 810),
            f"Idle: {idle_time/total:.2%}",
            fill=(255, 255, 255),
            font=font,
        )
        draw.rectangle((1200, 900, 1275, 975), fill=(237, 41, 57), outline=(0, 0, 0))
        draw.text(
            (1300, 910),
            f"DND: {dnd_time/total:.2%}",
            fill=(255, 255, 255),
            font=font,
        )
        draw.rectangle((1850, 900, 1925, 975), fill=(97, 109, 126), outline=(0, 0, 0))
        draw.text(
            (1950, 910),
            f"Offline: {offline_time/total:.2%}",
            fill=(255, 255, 255),
            font=font,
        )

        buffer = io.BytesIO()
        img.save(buffer, "png")  # 'save' function for PIL
        buffer.seek(0)
        dfile = discord.File(fp=buffer, filename="uptime.png")
        em.title = f"{user}'s Status Statistics"
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

    def get_color(self, status_type):
        if str(status_type).startswith("online"):
            color = discord.Color.green().to_rgb()
        elif str(status_type).startswith("idle"):
            color = (255, 228, 0)  # discord.Color.gold().to_rgb()
        elif str(status_type).startswith("dnd"):
            color = (237, 41, 57)  # discord.Color.red().to_rgb()
        else:
            color = (97, 109, 126)
        return color

    def retrieve_name(self, var):
        callers_local_vars = inspect.currentframe().f_back.f_locals.items()
        return [var_name for var_name, var_val in callers_local_vars if var_val is var][
            0
        ]

    async def do_generic(self, ctx, user):
        em = discord.Embed(color=self.bot.constants.embed)
        img = Image.new("RGBA", (2400, 1024), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype("./data/assets/Helvetica.ttf", 100)

        online_time = 0
        idle_time = 0
        dnd_time = 0
        offline_time = 0
        if str(user.status) == "online":
            online_time = 1
        elif str(user.status) == "idle":
            idle_time = 1
        elif str(user.status) == "dnd":
            dnd_time = 1
        elif str(user.status) == "offline":
            offline_time = 1

        total = offline_time + online_time + idle_time + dnd_time
        uptime = online_time + idle_time + dnd_time
        raw_percent = uptime / total
        status_list = [online_time, idle_time, dnd_time, offline_time]
        status_list.sort()
        if raw_percent > 1:
            raw_percent = 1
        percent = f"{raw_percent:.2%}"
        em = discord.Embed(color=self.bot.constants.embed)
        img = Image.new("RGBA", (2500, 1024), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype("./data/assets/Helvetica.ttf", 100)
        w, h = 1050, 1000
        shape = [(50, 0), (w, h)]
        draw.arc(
            shape,
            start=0,
            end=360 * (status_list[-1] / total),
            fill=self.get_color(self.retrieve_name(status_list[-1])),
            width=200,
        )
        start = 360 * (status_list[-1] / total)
        draw.arc(
            shape,
            start=start,
            end=start + 360 * (status_list[-2] / total),
            fill=self.get_color(self.retrieve_name(status_list[-2])),
            width=200,
        )
        start = start + 360 * (status_list[-2] / total)
        draw.arc(
            shape,
            start=start,
            end=start + 360 * (status_list[-3] / total),
            fill=self.get_color(self.retrieve_name(status_list[-3])),
            width=200,
        )
        start = start + 360 * (status_list[-3] / total)
        draw.arc(
            shape,
            start=start,
            end=start + 360 * (status_list[-4] / total),
            fill=self.get_color(self.retrieve_name(status_list[-4])),
            width=200,
        )
        self.center_text(img, 1100, 1000, font, percent, (255, 255, 255))
        font = ImageFont.truetype("./data/assets/Helvetica-Bold.ttf", 85)
        draw.text(
            (1200, 0), "Status Tracking Startdate:", fill=(255, 255, 255), font=font
        )
        font = ImageFont.truetype("./data/assets/Helvetica.ttf", 68)
        draw.text(
            (1200, 100),
            utils.format_time(datetime.utcnow()).split(".")[0] + "]",
            fill=(255, 255, 255),
            font=font,
        )
        font = ImageFont.truetype("./data/assets/Helvetica-Bold.ttf", 85)
        draw.text((1200, 300), "Total Online Time:", fill=(255, 255, 255), font=font)
        font = ImageFont.truetype("./data/assets/Helvetica.ttf", 68)
        draw.text(
            (1200, 400),
            f"{uptime/3600:.2f} {'Hour' if int(uptime/3600) == 1 else 'Hours'}",
            fill=(255, 255, 255),
            font=font,
        )
        font = ImageFont.truetype("./data/assets/Helvetica-Bold.ttf", 85)
        draw.text((1200, 600), "Status Information:", fill=(255, 255, 255), font=font)
        font = ImageFont.truetype("./data/assets/Helvetica.ttf", 68)
        draw.rectangle((1200, 800, 1275, 875), fill=(46, 204, 113), outline=(0, 0, 0))
        draw.text(
            (1300, 810),
            f"Online: {online_time/total:.2%}",
            fill=(255, 255, 255),
            font=font,
        )
        draw.rectangle((1800, 800, 1875, 875), fill=(255, 228, 0), outline=(0, 0, 0))
        draw.text(
            (1900, 810), f"Idle: {idle_time/total:.2%}", fill=(255, 255, 255), font=font
        )
        draw.rectangle((1200, 900, 1275, 975), fill=(237, 41, 57), outline=(0, 0, 0))
        draw.text(
            (1300, 910), f"DND: {dnd_time/total:.2%}", fill=(255, 255, 255), font=font
        )
        draw.rectangle((1800, 900, 1875, 975), fill=(97, 109, 126), outline=(0, 0, 0))
        draw.text(
            (1900, 910),
            f"Offline: {offline_time/total:.2%}",
            fill=(255, 255, 255),
            font=font,
        )

        buffer = io.BytesIO()
        img.save(buffer, "png")  # 'save' function for PIL
        buffer.seek(0)
        dfile = discord.File(fp=buffer, filename="uptime.png")
        em.title = f"{user}'s Status Statistics"
        em.set_image(url="attachment://statusinfo.png")
        await ctx.send_or_reply(embed=em, file=dfile)
