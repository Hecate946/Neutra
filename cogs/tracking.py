import io
import time
import typing
import asyncio
import discord
import inspect

from datetime import datetime, timedelta
from discord.ext import commands, menus
from PIL import Image, ImageDraw, ImageFont

from utilities import utils
from utilities import checks
from utilities import images
from utilities import cleaner
from utilities import humantime
from utilities import converters
from utilities import decorators
from utilities import formatting
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
    @checks.guild_only()
    @checks.cooldown()
    async def invited(
        self, ctx, *, user: converters.SelfMember(view_guild_insights=True) = None
    ):
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
        user = user or ctx.author
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
    @checks.guild_only()
    @checks.cooldown()
    async def invites(self, ctx, *, user: converters.DiscordMember = None):
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
    @checks.cooldown(2, 20)
    async def user(self, ctx, *, user: converters.SelfUser(view_guild_insights=True) = None):
        """
        Usage:   {0}user [user]
        Alias:   {0}lookup
        Output:  General information on any discord user.
        Notes:
            Accepts nickname, ID, mention, username, and username+discrim
            Neither you nor the bot must share a server with the passed user.
            Will default to you if no user is passed into the command.
        """
        user = user or ctx.author

        message = await ctx.load("Collecting User Data...")
        await ctx.trigger_typing()
        title_str = (
            f"{self.bot.emote_dict['info']} Information on **{user}** `{user.id}`."
        )

        batch = self.bot.get_cog("Batch")

        if isinstance(user, discord.Member):  # Member obj, get all data.
            usernames = await batch.get_names(user)
            nicknames = await batch.get_nicks(user)
            joined_at = utils.format_time(user.joined_at)
            status = utils.get_status(user)
            server_spoke = await batch.get_server_last_spoke(user)
            server_messages = await batch.get_server_message_count(user)
            server_commands = await batch.get_server_command_count(user)
        else:
            usernames = [str(user)]
            nicknames = None
            joined_at = None
            status = None
            server_spoke = None
            server_messages = None
            server_commands = None

        last_spoke = await batch.get_last_spoke(user)
        messages_sent = await batch.get_message_count(user)
        commands_run = await batch.get_command_count(user)
        last_seen = await batch.get_last_seen(user, raw=True)

        msg = ""
        msg += f"ID             : {user.id}\n"
        msg += f"Username{' ' if len(usernames) == 1 else 's'}      : {', '.join(usernames)}\n"

        if nicknames:
            msg += f"Nickname{' ' if len(nicknames) == 1 else 's'}      : {', '.join(nicknames)}\n"
        if status:
            msg += f"Status         : {status}\n"

        msg += f"Common Servers : {len(user.mutual_guilds)}\n"
        msg += f"Created        : {utils.format_time(user.created_at)}\n"

        if joined_at:
            msg += f"Joined         : {joined_at}\n"
            # Next get the position that the user joined in.
            joined_list = sorted(user.guild.members, key=lambda m: m.joined_at)
            position = joined_list.index(user) + 1
            msg += f"Join Position  : {position:,}/{len(user.guild.members)}\n"

        if last_seen:
            msg += f"Last Seen      : {last_seen}\n"
        if last_spoke:
            msg += f"Last Spoke     : {last_spoke} ago\n"
        if server_spoke:
            msg += f"Spoke Here     : {server_spoke} ago\n"

        msg += f"Messages Sent  : {messages_sent}\n"
        if server_messages:
            msg += f"Messages Here  : {server_messages}\n"

        msg += f"Commands Run   : {commands_run}\n"
        if server_commands:
            msg += f"Commands Here  : {server_commands}\n"

        if isinstance(user, discord.Member):
            msg += f"Roles          : {', '.join([r.name for r in sorted(user.roles, key=lambda r: -r.position)])}\n"
            perm_list = [Perm[0] for Perm in user.guild_permissions if Perm[1]]
            msg += f'Permissions    : {", ".join(perm_list).replace("_", " ").replace("guild", "server").title().replace("Tts", "TTS")}'

        await message.edit(content=title_str)
        t = pagination.TextPages(
            cleaner.clean_all(msg), prefix="```yaml\n", suffix="```"
        )
        try:
            await t.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    # Deprecated
    '''
    @decorators.command(aliases=["activities"], brief="Show all recorded statuses")
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    @checks.cooldown()
    async def statuses(
        self, ctx, *, user: converters.SelfMember(view_guild_insights=True) = None
    ):
        """
        Usage: {0}statuses [user]
        Alias: {0}activities
        Permission: View Audit Log
        Output:
            Shows an embed of all the passed user's
            statuses (past and present).
        Notes:
            Will default to yourself if no user is passed
        """
        user = user or ctx.author
        batch = self.bot.get_cog("Batch")
        if not batch:
            raise commands.DisabledCommand()
        await ctx.trigger_typing()
        statuses = await batch.get_activities(user)

        p = pagination.SimplePages([f"**{x}**" for x in statuses], per_page=15)
        p.embed.title = f"{user}'s Recorded Statuses"
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)
    '''

    @decorators.command(brief="Get voice data", aliases=["vtime"])
    @checks.guild_only()
    @checks.cooldown()
    async def voicetime(self, ctx, *, user: converters.SelfMember(view_guild_insights=True) = None):
        user = user or ctx.author
        query = """
                with voice_data as(
                    SELECT connected,
                    user_id,
                    first_seen,
                    case when 
                        lag(first_seen) over (order by first_seen desc) is null then
                            now() at time zone 'utc'
                        else
                            lag(first_seen) over (order by first_seen desc)
                        end as last_seen
                        from voice
                    where user_id = $1
                    and connected = True
                    group by connected, user_id, first_seen
                )
                select sum(extract(epoch from(last_seen - first_seen))) as sum
                from voice_data
                order by sum desc
                """
        record = await self.bot.cxn.fetchval(query, user.id) or 0
        voice_time = utils.time_between(time.time() - record, time.time())
        await ctx.send_or_reply(
            f"{self.bot.emote_dict['graph']} User **{user}** `{user.id}` has spent **{voice_time}** in voice channels throughout this server."
        )

    @decorators.command(brief="Get status data", aliases=["_ps"], hidden=True)
    @checks.guild_only()
    @checks.cooldown()
    async def _piestatus(self, ctx, *, user: converters.SelfMember(view_guild_insights=True) = None):
        user = user or ctx.author
        query = """
                with status_data as(
                    SELECT status,
                    first_seen,
                    case when 
                        lag(first_seen) over (order by first_seen desc) is null then
                            now() at time zone 'utc'
                        else
                            lag(first_seen) over (order by first_seen desc)
                    end as last_seen
                    from statuses
                    where user_id = $1
                )
                select
                    status,
                    sum(
                    extract(
                    epoch from(
                    last_seen - first_seen
                ))) as sum
                from status_data
                group by status
                order by sum desc
                """
        records = await self.bot.cxn.fetch(query, user.id)
        statuses = {record["status"]: record["sum"] for record in records}
        startdate = await self.bot.cxn.fetchval("select min(first_seen) from statuses where user_id = $1", user.id)
        buffer = await self.bot.loop.run_in_executor(None, images.get_piestatus, statuses, startdate)

        em = discord.Embed(color=self.bot.constants.embed)
        dfile = discord.File(fp=buffer, filename="piestatus.png")
        em.title = f"{ctx.author}'s Status Statistics"
        em.set_image(url="attachment://piestatus.png")
        await ctx.send_or_reply(embed=em, file=dfile)


    @decorators.command(aliases=["mc"], brief="Count the messages a user sent.")
    @checks.guild_only()
    @checks.cooldown()
    async def messagecount(self, ctx, *, user: converters.DiscordMember = None):
        """
        Usage:  {0}messagecount [user]
        Alias:  {0}mc
        Output: Shows how many messages a user has sent on the server.
        Permission: Manage Messages
        Notes:
            Will default to yourself if no user is passed.
        """
        user = user or ctx.author
        if user.bot:
            raise commands.BadArgument("I do not track bots.")
        query = """
                SELECT COUNT(*) as c
                FROM messages
                WHERE author_id = $1
                AND server_id = $2
                """
        count = await self.bot.cxn.fetchval(query, user.id, ctx.guild.id)
        await ctx.send_or_reply(
            f"`{user}` has sent **{count}** message{'' if count == 1 else 's'}"
        )

    @decorators.command(
        brief="Show top message senders.",
        implemented="2021-04-03 01:56:35.751553",
        updated="2021-05-06 23:36:18.959143",
        examples="""
                {0}top
                {0}top 500
                """,
    )
    @checks.guild_only()
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    @checks.cooldown()
    async def top(self, ctx, limit: int = 100):
        """
        Usage: {0}top
        Permission: View Audit Log
        Output:
            Show top message senders in the server
        Notes:
            Specify the limit kwarg to adjust the
            number of members to include in the
            messagestats embed
        """
        if not str(limit).isdigit():
            raise commands.BadArgument("The `limit` argument must be an integer.")

        query = """
                SELECT author_id,
                count(author_id)
                FROM messages
                WHERE server_id = $1
                GROUP BY author_id
                ORDER BY COUNT(author_id)
                DESC LIMIT $2
                """

        msg_data = await self.bot.cxn.fetch(query, ctx.guild.id, limit)
        total = sum([row[1] for row in msg_data])
        entries = [f"<@!{row[0]}>. **Messages:** {row[1]:,}" for row in msg_data]

        p = pagination.SimplePages(entries=entries, per_page=20)
        p.embed.title = f"**{total:,}** messages by **{len(msg_data):,}** users."

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
    @checks.guild_only()
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    @checks.cooldown()
    async def nicknames(
        self, ctx, *, user: converters.SelfMember(view_guild_insights=True) = None
    ):
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
        user = user or ctx.author
        if user.bot:
            raise commands.BadArgument("I do not track bots.")

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
    @checks.guild_only()
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    async def usernames(
        self, ctx, *, user: converters.SelfMember(view_guild_insights=True) = None
    ):
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
        user = user or ctx.author
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
        brief="Show past user avatars.",
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
    @checks.guild_only()
    @checks.bot_has_perms(attach_files=True, embed_links=True)
    @checks.cooldown(1, 10)
    async def avatars(
        self, ctx, *, user: converters.SelfMember(view_guild_insights=True) = None
    ):
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
        user = user or ctx.author
        if user.bot:
            return await ctx.fail("I do not track bots.")

        await ctx.trigger_typing()

        query = """
                SELECT avatars.url
                FROM (SELECT avatar, first_seen
                FROM (SELECT avatar, LAG(avatar)
                OVER (order by first_seen desc) AS old_avatar, first_seen
                FROM useravatars WHERE useravatars.user_id = $1) a
                WHERE avatar != old_avatar OR old_avatar IS NULL) avys
                LEFT JOIN avatars ON avatars.hash = avys.avatar
                ORDER BY avys.first_seen DESC LIMIT 100;
                """

        urls = await self.bot.cxn.fetch(query, user.id)

        async def url_to_bytes(url):
            if not url:
                return None
            bytes_av = await self.bot.get(url, res_method="read")
            return bytes_av

        avys = await asyncio.gather(*[url_to_bytes(url["url"]) for url in urls])
        if avys:
            file = await self.bot.loop.run_in_executor(None, images.quilt, avys)
            dfile = discord.File(file, "avatars.png")
            embed = discord.Embed(color=self.bot.constants.embed)
            embed.title = f"Recorded Avatars for {user}"
            embed.set_image(url="attachment://avatars.png")
            await ctx.send_or_reply(embed=embed, file=dfile)
        else:
            if self.bot.avatar_saver.is_saving:
                batch = self.bot.get_cog("Batch")
                if user.id not in batch.whitelist:
                    self.bot.avatar_saver.save(user)
                embed = discord.Embed(color=self.bot.constants.embed)
                embed.title = f"Recorded Avatars for {user}"
                embed.set_image(url=str(user.display_avatar.with_size(1024)))
                await ctx.send_or_reply(embed=embed)
            else:
                raise commands.DisabledCommand()

    # @decorators.command(
    #     aliases=["avpages", "avbrowser"],
    #     brief="Show past user avatars.",
    #     examples="""
    #             {0}avs
    #             {0}avs Hecate
    #             {0}avs @Hecate
    #             {0}avs Hecate#3523
    #             {0}avs 708584008065351681
    #             {0}avatars
    #             {0}avatars Hecate
    #             {0}avatars @Hecate
    #             {0}avatars Hecate#3523
    #             {0}avatars 708584008065351681
    #             """,
    # )
    # @checks.guild_only()
    # @checks.bot_has_perms(attach_files=True, embed_links=True)
    # @checks.cooldown(1, 10)
    # async def avatarpages(
    #     self, ctx, *, user: converters.SelfMember(view_guild_insights=True) = None
    # ):
    #     """
    #     Usage: {0}avatars [user]
    #     Alias: {0}avs, {0}avhistory {0}avatarhistory
    #     Output:
    #         Shows an embed containing up to
    #         the 16 last avatars of a user.
    #     Permission: View Audit Log
    #     Notes:
    #         Will default to you if no user is passed.
    #     """
    #     user = user or ctx.author
    #     if user.bot:
    #         return await ctx.fail("I do not track bots.")

    #     await ctx.trigger_typing()

    #     query = """
    #             SELECT ARRAY(
    #                 SELECT avatars.url
    #                 FROM (SELECT avatar, first_seen
    #                 FROM (SELECT avatar, LAG(avatar)
    #                 OVER (order by first_seen desc) AS old_avatar, first_seen
    #                 FROM useravatars WHERE useravatars.user_id = $1) a
    #                 WHERE avatar != old_avatar OR old_avatar IS NULL) avys
    #                 LEFT JOIN avatars ON avatars.hash = avys.avatar
    #                 ORDER BY avys.first_seen DESC LIMIT 100
    #             ) as urls;
    #             """

    #     urls = await self.bot.cxn.fetchval(query, user.id)
    #     if urls:
    #         #urls = [record["url"] for record in urls]
    #         from utilities import views
    #         #views.ImageView(ctx, urls)
    #         await views.ImageView(ctx, urls).start()

    #     else:
    #         if self.bot.avatar_saver.is_saving:
    #             self.bot.avatar_saver.save(user)
    #             embed = discord.Embed(color=self.bot.constants.embed)
    #             embed.title = f"Recorded Avatars for {user}"
    #             embed.set_image(url=str(user.display_avatar.with_size(1024)))
    #             await ctx.send_or_reply(embed=embed)
    #         else:
    #             raise commands.DisabledCommand()

    @decorators.command(
        aliases=["iconhistory"],
        brief="Show past server icons.",
        implemented="2021-03-27 01:14:06.076262",
        updated="2021-05-06 23:50:27.540481",
        examples="""
                {0}icons
                {0}iconhistory
                """,
    )
    @checks.guild_only()
    @checks.bot_has_perms(attach_files=True, embed_links=True)
    @checks.cooldown(1, 10)
    async def icons(self, ctx):
        """
        Usage: {0}icons
        Alias: {0}iconhistory
        Output:
            Shows an embed containing up to
            the 16 last icons of the server.
        Permission: View Audit Log
        """
        await ctx.trigger_typing()

        query = """
                SELECT icons.url
                FROM (SELECT icon, first_seen
                FROM (SELECT icon, LAG(icon)
                OVER (order by first_seen desc) AS old_icon, first_seen
                FROM servericons WHERE servericons.server_id = $1) a
                WHERE icon != old_icon OR old_icon IS NULL) icns
                LEFT JOIN icons ON icons.hash = icns.icon
                ORDER BY icns.first_seen DESC LIMIT 100;
                """

        urls = await self.bot.cxn.fetch(query, ctx.guild.id)

        async def url_to_bytes(url):
            if not url:
                return None
            bytes_av = await self.bot.get(url, res_method="read")
            return bytes_av

        avys = await asyncio.gather(*[url_to_bytes(url["url"]) for url in urls])
        if avys:
            file = await self.bot.loop.run_in_executor(None, images.quilt, avys)
            dfile = discord.File(file, "icons.png")
            embed = discord.Embed(color=self.bot.constants.embed)
            embed.title = f"Recorded icons for {ctx.guild.name}"
            embed.set_image(url="attachment://icons.png")
            await ctx.send_or_reply(embed=embed, file=dfile)
        else:
            if self.bot.icon_saver.is_saving:
                if ctx.guild.icon:
                    self.bot.icon_saver.save(ctx.guild)
                    embed = discord.Embed(color=self.bot.constants.embed)
                    embed.title = f"Recorded icons for {ctx.guild.name}"
                    embed.set_image(url=str(ctx.guild.icon.with_size(1024)))
                    await ctx.send_or_reply(embed=embed)
                else:
                    await ctx.fail("No icons have been recorded for this server.")
            else:
                raise commands.DisabledCommand()

    @decorators.command(
        aliases=["lastseen", "tracker", "observed"],
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
    @checks.cooldown()
    async def seen(self, ctx, *, user: converters.SelfMember(view_guild_insights=True) = None):
        """
        Usage: {0}seen [user]
        Aliases:
            {0}lastseen, {0}track, {0}tracker, {0}observed
        Permission: View Audit Log
        Output:
            Show how long its been since a user
            was last observed using discord.
        Notes:
            User can be a mention, user id, or full discord
            username with discrim Username#0001.
            Will default to you if no user is specified.
        """
        await ctx.trigger_typing()
        user = user or ctx.author

        if user.bot:
            raise commands.BadArgument("I do not track bots.")

        tracker = self.bot.get_cog("Batch")
        data = await tracker.get_last_seen(user)

        if not data:
            return await ctx.fail(f"I have not seen **{user}** `{user.id}`.")
        await ctx.send_or_reply(data)

    @decorators.command(
        aliases=["lastspoke"],
        brief="Check when a user last spoke.",
        implemented="2021-07-02 00:30:48.728244",
        updated="2021-07-02 00:30:48.728244",
        examples="""
                {0}spoke Hecate
                {0}spoke @Hecate
                {0}spoke Hecate#3523
                {0}spoke 708584008065351681
                {0}lastspoke Hecate
                {0}lastspoke @Hecate
                {0}lastspoke Hecate#3523
                {0}lastspoke 708584008065351681
                """,
    )
    @checks.cooldown()
    async def spoke(
        self, ctx, *, user: converters.SelfMember(view_guild_insights=True) = None
    ):
        """
        Usage: {0}spoke [user]
        Alias: {0}lastspoke
        Permission: View Audit Log
        Output:
            Show how long its been since a user
            last sent a message tracked by the bot.
        Notes:
            User can be a mention, user id, or full discord
            username with discrim Username#0001.
            Will default to you if no user is specified.
        """
        await ctx.trigger_typing()
        user = user or ctx.author

        if user.bot:
            raise commands.BadArgument("I do not track bots.")

        tracker = self.bot.get_cog("Batch")
        data = await tracker.get_last_spoke(user)

        if not data:
            return await ctx.fail(f"I have not seen `{user}` speak.")
        await ctx.send_or_reply(f"User `{user}` last spoke **{data}** ago.")

    @decorators.command(
        aliases=["lastspokehere"],
        brief="Check when a user last spoke here.",
        implemented="2021-07-02 00:30:48.728244",
        updated="2021-07-02 00:30:48.728244",
        examples="""
                {0}spokehere Hecate
                {0}spokehere @Hecate
                {0}spokehere Hecate#3523
                {0}spokehere 708584008065351681
                {0}lastspokehere Hecate
                {0}lastspokehere @Hecate
                {0}lastspokehere Hecate#3523
                {0}lastspokehere 708584008065351681
                """,
    )
    @checks.cooldown()
    async def spokehere(
        self, ctx, *, user: converters.SelfMember(view_guild_insights=True) = None
    ):
        """
        Usage: {0}spokehere [user]
        Alias: {0}lastspokehere
        Permission: View Audit Log
        Output:
            Show how long its been since a user
            last sent a message in the server.
        Notes:
            User can be a mention, user id, or full discord
            username with discrim Username#0001.
            Will default to you if no user is specified.
        """
        await ctx.trigger_typing()
        user = user or ctx.author

        if user.bot:
            raise commands.BadArgument("I do not track bots.")

        tracker = self.bot.get_cog("Batch")
        data = await tracker.get_server_last_spoke(user)

        if not data:
            return await ctx.fail(f"I have not seen `{user}` speak here.")
        await ctx.send_or_reply(f"User `{user}` last spoke here **{data}** ago.")

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
    @checks.guild_only()
    @checks.bot_has_perms(add_reactions=True, external_emojis=True)
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
        if limit < 1:
            raise commands.BadArgument("The `limit` argument must be greater than 1.")

        if user is None:  # Check for whole server
            query = """
                    SELECT command, COUNT(command) as c
                    FROM commands
                    WHERE server_id = $1
                    GROUP BY command
                    ORDER BY c DESC
                    LIMIT $2;
                    """

            command_list = await self.bot.cxn.fetch(query, ctx.guild.id, limit)
            if not command_list:
                return await ctx.fail(
                    f"No commands have been recorded in for this server."
                )
        else:
            if user.bot:
                raise commands.BadArgument("I do not track bots.")

            user = await converters.SelfMember(view_guild_insights=True).convert(
                ctx, user.id
            )

            query = """
                    SELECT command, COUNT(commands) as c
                    FROM commands
                    WHERE server_id = $1
                    AND author_id = $2
                    GROUP BY command
                    ORDER BY c DESC
                    LIMIT $3;
                    """
            command_list = await self.bot.cxn.fetch(query, ctx.guild.id, user.id, limit)
            if not command_list:
                return await ctx.fail(f"User `{user}` has not run any commands.")

        usage_dict = {record["command"]: record["c"] for record in command_list}

        width = len(max(usage_dict, key=len))

        total = sum(usage_dict.values())

        output = "\n".join(f"{cmd:<{width}} : {cnt}" for cmd, cnt in usage_dict.items())

        msg = "{0} \n\nTOTAL: {1}".format(output, total)
        pages = pagination.MainMenu(
            pagination.LinePageSource(msg, prefix="```yaml", lines=20)
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
        brief="Show a user's commands.",
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
    @checks.guild_only()
    @checks.cooldown()
    async def commandcount(self, ctx, *, user: converters.DiscordMember = None):
        """
        Usage: {0}commandcount [user]
        Alias: {0}cc
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
            command_count = await self.bot.cxn.fetchval(query, ctx.guild.id)
            return await ctx.send_or_reply(
                f"{self.bot.emote_dict['graph']} A total of **{command_count:,}** command{' has' if command_count == 1 else 's have'} been executed on this server.",
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
            command_count = await self.bot.cxn.fetchval(query, user.id, ctx.guild.id)
            return await ctx.send_or_reply(
                f"{self.bot.emote_dict['graph']} User `{user}` has executed **{command_count:,}** command{'' if command_count == 1 else 's'}.",
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
    @checks.guild_only()
    @checks.bot_has_perms(embed_links=True)
    @checks.has_perms(view_guild_insights=True)
    @checks.cooldown()
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

    # DEPRECATED TO SATISFY DISCORD VERIFICATION REQUIREMENTS
    # @decorators.command(
    #     brief="Most used words from a user.",
    #     implemented="2021-03-11 20:10:05.766906",
    #     updated="2021-05-07 02:24:13.585137",
    #     examples="""
    #             {0}words
    #             {0}words 700
    #             {0}words Hecate
    #             {0}words @Hecate
    #             {0}words Hecate#3523
    #             {0}words 708584008065351681
    #             {0}words Hecate 300
    #             {0}words @Hecate 400
    #             {0}words Hecate#3523 500
    #             {0}words 708584008065351681 600
    #             """,
    # )
    # @checks.guild_only()
    # @checks.bot_has_perms(add_reactions=True, external_emojis=True)
    # @checks.cooldown()
    # async def words(
    #     self,
    #     ctx,
    #     user: typing.Optional[converters.DiscordMember] = None,
    #     limit: int = 100,
    # ):
    #     """
    #     Usage: {0}words [user] [limit]
    #     Output: Most commonly used words by the passed user
    #     Permission: Manage Messages
    #     Notes:
    #         Will default to yourself if no user is passed.
    #         Pass a limit argument after or instead of a user
    #         argument to limit the number of common words to show.
    #     """
    #     if user:
    #         user = await converters.SelfMember(manage_messages=True).convert(
    #             ctx, user.id
    #         )
    #     else:
    #         user = ctx.author

    #     if user.bot:
    #         raise commands.BadArgument("I do not track bots.")

    #     if limit < 1:
    #         raise commands.BadArgument("The `limit` argument must be greater than 1.")
    #     if limit > 1000:
    #         raise commands.BadArgument("The `limit` argument must be less than 1000.")

    #     message = await ctx.load("Collecting Word Statistics...")

    #     query = """
    #             SELECT word, count(*)
    #             FROM messages, unnest(
    #             string_to_array(
    #             translate(content, '\n', ' '),
    #             ' ')) word
    #             WHERE LENGTH(word) > 1
    #             AND server_id = $1
    #             AND author_id = $2
    #             GROUP BY 1
    #             ORDER BY 2 DESC
    #             LIMIT $3;
    #             """
    #     records = await self.bot.cxn.fetch(query, ctx.guild.id, user.id, limit)
    #     if not records:
    #         return await message.edit(
    #             content=f"No words have been recorded for `{user}`"
    #         )

    #     msg = "\n".join(
    #         [
    #             f"Uses: [{str(record['count']).zfill(2)}] Word: {record['word']}"
    #             for record in records
    #         ]
    #     )
    #     pages = pagination.MainMenu(
    #         pagination.LinePageSource(msg, prefix="```ini", lines=20)
    #     )

    #     await message.edit(
    #         content=f"{self.bot.emote_dict['graph']} Top **{limit}** most common words sent by **{user}**",
    #     )
    #     try:
    #         await pages.start(ctx)
    #     except menus.MenuError as e:
    #         await ctx.send_or_reply(str(e))

    # @decorators.command(
    #     brief="Usage for a specific word.",
    #     implemented="2021-03-13 18:18:34.790741",
    #     updated="2021-05-07 03:51:54.934511",
    #     ignore_extra=False,
    #     examples="""
    #             {0}word Hello
    #             {0}word Hecate Hello
    #             {0}word @Hecate Hello
    #             {0}word Hecate#3523 Hello
    #             {0}word 708584008065351681 Hello
    #             """,
    # )
    # @checks.guild_only()
    # @checks.bot_has_perms(add_reactions=True, external_emojis=True)
    # @checks.cooldown()
    # async def word(
    #     self,
    #     ctx,
    #     user: typing.Optional[converters.DiscordMember],
    #     word: str,
    # ):
    #     """
    #     Usage: {0}word [user] <word>
    #     Permission: Manage Messages
    #     Output:
    #         Show how many times a specific word
    #         has been used by a user.
    #     Notes:
    #         Will default to you if no user is passed.
    #     """
    #     if user:
    #         user = await converters.SelfMember(manage_messages=True).convert(
    #             ctx, user.id
    #         )
    #     else:
    #         user = ctx.author
    #     if user.bot:
    #         raise commands.BadArgument("I do not track bots.")
    #     if len(word) < 2:
    #         raise commands.BadArgument("Word must be at least 2 characters in length.")
    #     message = await ctx.load("Collecting Word Statistics...")

    #     query = """
    #             SELECT word, count(*)
    #             FROM messages, unnest(
    #             string_to_array(
    #             translate(content, '\n', ' '),
    #             ' ')) word
    #             WHERE word = $1
    #             AND LENGTH(word) > 1
    #             AND server_id = $2
    #             AND author_id = $3
    #             GROUP BY 1;
    #             """
    #     data = await self.bot.cxn.fetchrow(query, word, ctx.guild.id, user.id)
    #     if not data:
    #         return await message.edit(
    #             content=f"{self.bot.emote_dict['failed']} The word `{word}` has never been used by **{user}**",
    #         )

    #     await message.edit(
    #         content=f"{self.bot.emote_dict['graph']} The word `{data['word']}` has been used {data['count']} time{'' if data['count'] == 1 else 's'} by **{user}**"
    #     )

    # @word.error
    # async def word_error(self, ctx, error):
    #     if isinstance(error, commands.TooManyArguments):
    #         await ctx.fail("Please only provide one word at a time to search.")
    #         ctx.handled = True

    @decorators.command(
        brief="Show the most active users.",
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
    @checks.guild_only()
    @checks.bot_has_perms(embed_links=True)
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
        aliases=["ms", "mstats", "messagestatistics"],
        brief="Show message stats.",
        implemented="2021-03-13 04:47:25.624232",
        updated="2021-05-07 04:26:00.620200",
        examples="""
                {0}mstats
                {0}messagestats 2d
                {0}ms since 3 weeks ago
                {0}messagestatistics 10 mins ago
                {0}ms since 1 year ago
                """,
    )
    @checks.guild_only()
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    @checks.cooldown()
    async def messagestats(
        self,
        ctx,
        channel: typing.Optional[discord.TextChannel],
        *,
        since: humantime.PastTime = None,
    ):
        """
        Usage: {0}messagestats [since]
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
        await ctx.trigger_typing()
        if not since:  # They didn't specify. Default to past month
            since = discord.utils.utcnow() - timedelta(30)  # 30 days ago
        else:
            since = since.dt

        seconds_ago = (discord.utils.utcnow() - since).total_seconds()
        diff = time.time() - seconds_ago

        if channel:
            condition = "AND channel_id = $3"
            args = (ctx.guild.id, diff, channel.id)
            title_fmt = channel.mention
        else:
            condition = ""
            args = (ctx.guild.id, diff)
            title_fmt = f"**{ctx.guild.name}**"

        query = f"""
                SELECT COUNT(*) as c, author_id as author
                FROM messages
                WHERE server_id = $1
                AND unix > $2
                {condition}
                GROUP BY author_id
                ORDER BY c DESC
                LIMIT 100;
                """
        records = await self.bot.cxn.fetch(query, *args)
        if not records:
            await ctx.fail(
                f"No messate statistics available in {title_fmt} for that time period."
            )
            return

        def pred(snowflake):
            mem = ctx.guild.get_member(snowflake)
            if mem:
                return str(mem)

        usage_dict = {
            str(pred(record["author"])): record["c"]
            for record in records
            if pred(record["author"])
        }

        width = len(max(usage_dict, key=len))

        total = sum(usage_dict.values())

        output = "\n".join(
            f"{user:<{width}} : {cnt}" for user, cnt in usage_dict.items()
        )

        msg = "{0} \n\nTOTAL: {1}".format(output, total)
        pages = pagination.MainMenu(
            pagination.LinePageSource(msg, prefix="```autohotkey", lines=20)
        )
        title = f"{self.bot.emote_dict['graph']} Message leaderboard for {title_fmt} since **{utils.short_time(since)}**"

        await ctx.send_or_reply(title)
        try:
            await pages.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(str(e))

    @decorators.command(
        aliases=["cstats", "chanstats", "channelstatistics"],
        brief="Show channel activity.",
        implemented="2021-03-13 04:47:25.624232",
        updated="2021-05-07 04:26:00.620200",
        examples="""
                {0}cstats
                {0}channelstats 2d
                {0}cstats since 3 weeks ago
                {0}channelstatistics 10 mins ago
                {0}chanstats since 1 year ago
                """,
    )
    @checks.guild_only()
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    @checks.cooldown()
    async def channelstats(
        self,
        ctx,
        *,
        since: humantime.PastTime = None,
    ):
        """
        Usage: {0}channelstats [since]
        Aliases: {0}cstats, {0}chanstats
        Permission: Manage Messages
        Output:
            Shows the most active server
            channels ordered by the number
            of messages sent in them.
        Notes:
            If no unit of time is specified,
            of if the unit is invalid, the bot
            will default to one month for its unit.
        """
        await ctx.trigger_typing()
        if not since:  # They didn't specify. Default to past month
            since = discord.utils.utcnow() - timedelta(30)  # 30 days ago
        else:
            since = since.dt

        seconds_ago = (discord.utils.utcnow() - since).total_seconds()
        diff = time.time() - seconds_ago

        query = """
                SELECT COUNT(*) as c, channel_id
                FROM messages
                WHERE server_id = $1
                AND unix > $2
                GROUP BY channel_id
                ORDER BY c DESC
                """
        records = await self.bot.cxn.fetch(query, ctx.guild.id, diff)
        if not records:
            await ctx.fail(
                f"No channel activity statistics available in **{ctx.guild.name}** for that time period."
            )
            return

        def pred(snowflake):
            chan = self.bot.get_channel(snowflake)
            if chan:
                return "#" + chan.name

        usage_dict = {
            pred(record["channel_id"]): record["c"]
            for record in records
            if pred(record["channel_id"])
        }

        width = len(max(usage_dict, key=len))

        total = sum(usage_dict.values())

        output = "\n".join(
            f"{channel:<{width}} : {cnt}" for channel, cnt in usage_dict.items()
        )

        msg = "{0} \n\nTOTAL: {1}".format(output, total)
        pages = pagination.MainMenu(
            pagination.LinePageSource(msg, prefix="```autohotkey", lines=20)
        )
        title = f"{self.bot.emote_dict['graph']} Channel activity leaderboard for **{ctx.guild.name}** since **{utils.short_time(since)}**"

        await ctx.send_or_reply(title)
        try:
            await pages.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(str(e))

    # DEPRECATED TO SATISFY DISCORD VERIFICATION REQUIREMENTS
    # @decorators.command(
    #     aliases=["chars"],
    #     brief="Show character usage.",
    #     implemented="2021-04-19 06:02:49.713396",
    #     updated="2021-05-07 04:31:07.411009",
    #     examples="""
    #             {0}chars
    #             {0}chars day
    #             {0}chars week
    #             {0}chars month
    #             {0}chars year
    #             {0}characters
    #             {0}characters day
    #             {0}characters week
    #             {0}characters month
    #             {0}characters year
    #             """,
    # )
    # @checks.guild_only()
    # @checks.bot_has_perms(embed_links=True)
    # @checks.has_perms(manage_messages=True)
    # async def characters(self, ctx, unit: str = "day"):
    #     """
    #     Usage: {0}characters [unit of time]
    #     Alias: {0}chars
    #     Permission: Manage Messages
    #     Output:
    #         Shows the most active server
    #         users ordered by the number
    #         of characters they've sent.
    #     Notes:
    #         If no unit of time is specified,
    #         of if the unit is invalid, the bot
    #         will default to day for its unit.
    #     """
    #     unit = unit.lower()
    #     time_dict = {"day": 86400, "week": 604800, "month": 2592000, "year": 31556952}
    #     if unit not in time_dict:
    #         unit = "day"
    #     time_seconds = time_dict.get(unit, 2592000)
    #     now = int(time.time())
    #     diff = now - time_seconds
    #     query = """
    #             SELECT SUM(LENGTH(content)) as c, author_id, COUNT(*)
    #             FROM messages
    #             WHERE server_id = $1
    #             AND unix > $2
    #             GROUP BY author_id
    #             ORDER BY c DESC LIMIT 25"""
    #     stuff = await self.bot.cxn.fetch(query, ctx.guild.id, diff)
    #     e = discord.Embed(
    #         title="Character Leaderboard",
    #         description=f"{sum(x[0] for x in stuff)} characters from {len(stuff)} user{'' if len(stuff) == 1 else 's'} in the last {unit}",
    #         color=self.bot.constants.embed,
    #     )
    #     for n, v in enumerate(stuff):
    #         try:
    #             name = ctx.guild.get_member(int(v[1])).name
    #         except AttributeError:
    #             continue
    #         e.add_field(name=f"{n+1}. {name}", value=f"{v[0]:,} chars")

    #     await ctx.send_or_reply(embed=e)

    @decorators.command(
        brief="Show days a user was active.",
        implemented="2021-05-12 07:46:53.635661",
        updated="2021-05-12 15:25:00.152528",
        examples="""
                {0}clocker
                {0}clocker Hecate
                """,
    )
    @checks.cooldown()
    async def clocker(
        self,
        ctx,
        *,
        user: typing.Optional[converters.DiscordMember] = None,
    ):
        """
        Usage: {0}clocker [user] [time]
        Output:
            Counts the days that
            a user has sent a message
            in the specified time period.
        Notes:
            If no time frame is specified,
            will default to 1 week.
        """
        if user:
            user = await converters.SelfMember(view_guild_insights=True).convert(
                ctx, user.id
            )
        else:
            user = ctx.author
        await ctx.trigger_typing()

        query = """
                SELECT COUNT(subquery.days) FROM (SELECT DISTINCT
                (SELECT EXTRACT(DAY FROM (TO_TIMESTAMP(unix)))::SMALLINT AS days)
                FROM messages
                WHERE unix > (SELECT EXTRACT(EPOCH FROM NOW()) - 2592000)
                AND server_id = $1 AND author_id = $2) AS subquery;
                """  # 2592000 = seconds in a month
        days = await self.bot.cxn.fetchval(
            query,
            ctx.guild.id,
            user.id,
        )
        emote = self.bot.emote_dict["graph"]
        user = f"**{user}** `{user.id}`"
        pluralize = f"time{'' if days == 1 else 's'}"
        msg = f"{emote} User {user} logged into **{ctx.guild.name}** {days} {pluralize} during the past month."
        await ctx.send_or_reply(msg)

    @decorators.command(
        brief="Show all active users.",
        implemented="2021-05-12 15:25:00.152528",
        updated="2021-05-12 15:25:00.152528",
        examples="""
                {0}clocking
                """,
    )
    @checks.bot_has_perms(attach_files=True)
    @checks.has_perms(manage_guild=True)
    async def clocking(self, ctx):
        """
        Usage: {0}clocking
        Output:
            Shows the number of days that
            a user sent at least one message
            in the server during the past month.
        """
        await ctx.trigger_typing()
        query = """
                SELECT subquery.user, COUNT(subquery.days) AS days FROM (SELECT DISTINCT
                (SELECT EXTRACT(DAY FROM (TO_TIMESTAMP(unix)))::SMALLINT AS days),
                (SELECT author_id AS user)
                FROM messages
                WHERE unix > (SELECT EXTRACT(EPOCH FROM NOW()) - 2592000)
                AND server_id = $1) AS subquery
                GROUP BY subquery.user
                ORDER BY days DESC;
                """  # 2592000 = seconds in a month
        rows = await self.bot.cxn.fetch(query, ctx.guild.id)

        def pred(snowflake):
            mem = ctx.guild.get_member(snowflake)
            if mem:
                return str(mem)

        fmt = {pred(r["user"]): r["days"] for r in rows if pred(r["user"])}

        table = formatting.TabularData()
        table.set_columns(["NAME", "DAYS"])
        table.add_rows(fmt.items())
        render = table.render()

        completed = f"```sml\n{render}```"
        emote = self.bot.emote_dict["graph"]
        pluralize = " has" if len(fmt) == 1 else "s have"
        await ctx.send_or_reply(
            f"{emote} {len(fmt)} user{pluralize} logged in to **{ctx.guild.name}** during the past month."
        )
        if len(completed) > 2000:
            fp = io.BytesIO(completed.encode("utf-8"))
            await ctx.send_or_reply(file=discord.File(fp, "results.sml"))
        else:
            await ctx.send_or_reply(completed)

    @decorators.command(
        aliases=["statusinfo", "ps"],
        brief="Status info in a piechart.",
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
    @checks.guild_only()
    @checks.bot_has_perms(attach_files=True, embed_links=True)
    @checks.cooldown()
    async def piestatus(
        self, ctx, *, user: converters.SelfMember(view_guild_insights=True) = None
    ):
        """
        Usage: {0}statusinfo [user]
        Aliases: {0}piestatus, {0}ps,
        Output:
            Show a pie chart graph with details of the
            passed user's status statistics.
        Notes:
            Will default to yourself if no user is passed.
        """
        user = user or ctx.author
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
        dfile = discord.File(fp=buffer, filename="piestatus.png")
        em.title = f"{user}'s Status Statistics"
        em.set_image(url="attachment://piestatus.png")
        await ctx.send_or_reply(embed=em, file=dfile)

    @decorators.command(
        aliases=["bstatus", "bs"],
        brief="Status info in a bar graph.",
        implemented="2021-06-16 03:45:38.139631",
        updated="2021-06-16 03:45:38.139631",
        examples="""
                {0}bs
                {0}bs Hecate
                {0}bs @Hecate
                {0}bs Hecate#3523
                {0}bs 708584008065351681
                {0}bstatus
                {0}bstatus Hecate
                {0}bstatus @Hecate
                {0}bstatus Hecate#3523
                {0}bstatus 708584008065351681
                {0}barstatus
                {0}barstatus Hecate
                {0}barstatus @Hecate
                {0}barstatus Hecate#3523
                {0}barstatus 708584008065351681
                """,
    )
    @checks.guild_only()
    @checks.bot_has_perms(attach_files=True, embed_links=True)
    @checks.cooldown()
    async def barstatus(
        self, ctx, *, user: converters.SelfMember(view_guild_insights=True) = None
    ):
        """
        Usage: {0}barstatus [user]
        Aliases: {0}bs {0}bstatus
        Output:
            Generates a bar graph showing
            a given user's status info.
        Notes:
            Will default to you if no
            user is explicitly specified
        """
        user = user or ctx.author
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

        unix = time.time()
        if str(user.status) == "online":
            online_time += unix - last_change
        elif str(user.status) == "idle":
            idle_time += unix - last_change
        elif str(user.status) == "dnd":
            dnd_time += unix - last_change

        offline_time = unix - starttime
        statuses = {
            "online": online_time,
            "idle": idle_time,
            "dnd": dnd_time,
            "offline": offline_time,
        }
        barstatus_file = await self.bot.loop.run_in_executor(
            None, images.get_barstatus, "", statuses
        )
        embed = discord.Embed(color=self.bot.constants.embed)
        embed.title = f"{user}'s status usage since {datetime.utcfromtimestamp(starttime).__format__('%B %-d, %Y')}"
        embed.set_image(url="attachment://barstatus.png")
        await ctx.send_or_reply(
            embed=embed, file=discord.File(barstatus_file, filename="barstatus.png")
        )
