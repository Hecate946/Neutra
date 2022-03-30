import re
import copy
import json
import shlex
import typing
import asyncio
import discord

from collections import Counter
from discord.ext import commands
from discord.ext.commands import converter

from utilities import utils
from utilities import checks
from utilities import helpers
from utilities import humantime
from utilities import converters
from utilities import decorators


async def setup(bot):
    await bot.add_cog(Mod(bot))


class Mod(commands.Cog):
    """
    Moderate server users.
    """

    def __init__(self, bot):
        self.bot = bot

    ##########################
    ## Restriction Commands ##
    ##########################

    async def restrictor(self, ctx, targets, on_or_off, block_or_blind):
        overwrite = discord.PermissionOverwrite()
        if on_or_off == "on":
            boolean = False
        else:
            boolean = None
        if block_or_blind == "block":
            overwrite.send_messages = boolean
        else:
            overwrite.read_messages = boolean

        for target in targets:
            await ctx.channel.set_permissions(target, overwrite=overwrite)

        await ctx.success(
            f"{ctx.command.name.capitalize()}ed `{', '.join(str(t) for t in targets)}`"
        )
        self.bot.dispatch("mod_action", ctx, targets=targets)

    @decorators.command(
        brief="Restrict users from sending messages.",
        implemented="2021-04-09 19:26:19.417481",
        updated="2021-07-04 18:46:24.713058",
    )
    @checks.guild_only()
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(manage_channels=True)
    @checks.cooldown()
    async def block(self, ctx, *targets: converters.UniqueMember):
        """
        Usage: {0}block <target> [target]...
        Example: {0}block Hecate 708584008065351681 @Elizabeth
        Permission: Kick Members
        Output: Stops users from messaging in the channel.
        Notes: This mutes users in one channel
        """
        await self.restrictor(ctx, targets, "on", "block")

    @decorators.command(
        brief="Reallow users to send messages.",
        implemented="2021-04-09 19:26:19.417481",
        updated="2021-07-04 18:46:24.713058",
    )
    @checks.guild_only()
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(manage_channels=True)
    @checks.cooldown()
    async def unblock(self, ctx, *targets: converters.UniqueMember):
        """
        Usage:      {0}unblock <target> [target]...
        Example:    {0}unblock Hecate 708584008065351681 @Elizabeth
        Permission: Kick Members
        Output:     Reallows blocked users to send messages.
        Notes:      This unmutes users in one channel
        """
        await self.restrictor(ctx, targets, "off", "unblock")

    @decorators.command(
        brief="Hide a channel from a user.",
        implemented="2021-04-09 19:26:19.417481",
        updated="2021-07-04 18:46:24.713058",
    )
    @checks.guild_only()
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(manage_channels=True)
    @checks.cooldown()
    async def blind(self, ctx, *targets: converters.UniqueMember):
        """
        Usage:      {0}blind <target> [target]...
        Example:    {0}blind Hecate 708584008065351681 @Elizabeth
        Permission: Kick Members
        Output:     Prevents users from seeing the channel.
        """
        await self.restrictor(ctx, targets, "on", "blind")

    @decorators.command(
        brief="Reallow users see a channel.",
        implemented="2021-04-09 19:26:19.417481",
        updated="2021-07-04 18:46:24.713058",
    )
    @checks.guild_only()
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(manage_channels=True)
    @checks.cooldown()
    async def unblind(self, ctx, *targets: converters.UniqueMember):
        """
        Usage:      {0}unblind <targets>...
        Example:    {0}unblind Hecate 708584008065351681 @Elizabeth
        Permission: Kick Members
        Output:     Reallows blinded users to see the channel.
        """
        await self.restrictor(ctx, targets, "off", "unblind")

    #######################
    ## Kick/Ban commands ##
    #######################

    @decorators.command(
        brief="Kick users from the server.",
        implemented="2021-03-22 05:39:26.804850",
        updated="2021-07-06 05:43:21.995689",
    )
    @checks.guild_only()
    @checks.bot_has_perms(kick_members=True)
    @checks.has_perms(kick_members=True)
    @checks.cooldown()
    async def kick(
        self,
        ctx,
        targets: commands.Greedy[converters.DiscordMember(False)],
        *,  # Do not disambiguate when accepting multiple users.
        reason: typing.Optional[str] = "No reason",
    ):
        """
        Usage:      {0}kick <target> [target]... [reason]
        Example:    {0}kick @Jacob Sarah for advertising
        Permission: Kick Members
        Output:     Kicks passed members from the server.
        """
        if not len(targets):
            await ctx.usage()

        kicked = []
        failed = []
        for target in targets:
            res = await checks.check_priv(ctx, target)
            if res:
                failed.append((str(target), res))
                continue
            try:
                await ctx.guild.kick(target, reason=reason)
                kicked.append(str(target))
            except Exception as e:
                failed.append((str(target), e))
                continue
        if kicked:
            await ctx.success(f"Kicked `{', '.join(kicked)}`")
            self.bot.dispatch("mod_action", ctx, targets=kicked)
        if failed:
            await helpers.error_info(ctx, failed)

    ##################
    ## Ban Commands ##
    ##################

    @decorators.command(
        brief="Ban users from the server.",
        implemented="2021-03-22 05:39:26.804850",
        updated="2021-07-06 05:43:21.995689",
    )
    @checks.guild_only()
    @checks.bot_has_perms(ban_members=True)
    @checks.has_perms(ban_members=True)
    async def ban(
        self,
        ctx,
        targets: commands.Greedy[converters.DiscordUser(False)],
        delete_message_days: typing.Optional[int] = 1,
        *,  # Do not disambiguate when accepting multiple users.
        reason: typing.Optional[str] = "No reason.",
    ):
        """
        Usage: {0}ban <targets>... [delete message days = 1] [reason = "No reason"]
        Example: {0}ban @Jacob Sarah 4 for advertising
        Permission: Ban Members
        Output: Ban passed members from the server.
        """
        if not len(targets):
            await ctx.usage()

        if delete_message_days > 7:
            raise commands.BadArgument(
                "The number of days to delete messages must be less than 7."
            )
        elif delete_message_days < 0:
            raise commands.BadArgument(
                "The number of days to delete messages must be greater than 0."
            )

        banned = []
        failed = []
        for target in targets:
            res = await checks.check_priv(ctx, target)
            if res:
                failed.append((str(target), res))
                continue
            try:
                await ctx.guild.ban(
                    target,
                    reason=await converters.ActionReason().convert(ctx, reason),
                    delete_message_days=delete_message_days,
                )
                banned.append(str(target))
            except Exception as e:
                failed.append((str(target), e))
                continue
        if banned:
            await ctx.success(f"Banned `{', '.join(banned)}`")
            self.bot.dispatch("mod_action", ctx, targets=banned)
        if failed:
            await helpers.error_info(ctx, failed)

    @decorators.command(
        brief="Softban users from the server.",
        implemented="2021-03-22 05:39:26.804850",
        updated="2021-07-06 05:43:21.995689",
    )
    @checks.guild_only()
    @checks.bot_has_perms(ban_members=True)
    @checks.has_perms(kick_members=True)
    async def softban(
        self,
        ctx,
        targets: commands.Greedy[converters.DiscordMember(False)],
        delete_message_days: typing.Optional[int] = 7,
        *,
        reason: typing.Optional[str] = "No reason.",
    ):
        """
        Usage:      {0}softban <targets> [delete message = 7] [reason]
        Example:    {0}softban @Jacob Sarah 6 for advertising
        Permission: Kick Members
        Output:     Softbans members from the server.
        Notes:
            A softban bans the user and immediately
            unbans them in order to delete messages.
            The days to delete messages is set to 7 days.
        """
        if not len(targets):
            return await ctx.usage()

        if delete_message_days > 7:
            raise commands.BadArgument(
                "The number of days to delete messages must be less than 7."
            )
        elif delete_message_days < 0:
            raise commands.BadArgument(
                "The number of days to delete messages must be greater than 0."
            )

        banned = []
        failed = []
        for target in targets:
            res = await checks.check_priv(ctx, target)
            if res:
                failed.append((str(target), res))
                continue
            try:
                await ctx.guild.ban(
                    target,
                    reason=await converters.ActionReason().convert(ctx, reason),
                    delete_message_days=delete_message_days,
                )
                await ctx.guild.unban(
                    target, reason=await converters.ActionReason().convert(ctx, reason)
                )
                banned.append(str(target))
            except Exception as e:
                failed.append((str(target), e))
                continue
        if banned:
            await ctx.success(f"Softbanned `{', '.join(banned)}`")
            self.bot.dispatch("mod_action", ctx, targets=banned)
        if failed:
            await helpers.error_info(ctx, failed)

    @decorators.command(
        aliases=["revokeban"],
        brief="Unban a previously banned user.",
        implemented="2021-03-22 05:39:26.804850",
        updated="2021-07-06 05:43:21.995689",
    )
    @checks.guild_only()
    @checks.bot_has_perms(ban_members=True)
    @checks.has_perms(ban_members=True)
    @checks.cooldown()
    async def unban(self, ctx, member: converters.BannedMember, *, reason: str = None):
        """
        Usage:      {0}unban <user> [reason]
        Alias:      {0}revokeban
        Example:    Unban Hecate#3523 Because...
        Permission: Ban Members
        Output:     Unbans a member from the server.
        Notes:      Pass either the user's ID or their username
        """
        if reason is None:
            reason = utils.responsible(
                ctx.author, f"Unbanned member {member} by command execution"
            )

        await ctx.guild.unban(member.user, reason=reason)
        if member.reason:
            await ctx.success(
                f"Unbanned `{member.user} (ID: {member.user.id})`, previously banned for `{member.reason}.`"
            )
        else:
            await ctx.success(f"Unbanned `{member.user} (ID: {member.user.id}).`")
        self.bot.dispatch("mod_action", ctx, targets=[str(member.user)])

    @decorators.command(brief="Set the slowmode for a channel")
    @checks.guild_only()
    @checks.bot_has_perms(manage_channels=True)
    @checks.has_perms(manage_channels=True)
    @checks.cooldown()
    async def slowmode(
        self,
        ctx,
        channel: typing.Optional[discord.TextChannel] = None,
        time: float = None,
    ):
        """
        Usage: {0}slowmode [channel] [seconds]
        Permission: Manage Channels
        Output:
            Sets the channel's slowmode to your input value.
        Notes:
            If no slowmode is passed, will reset the slowmode.
        """
        channel = channel or ctx.channel
        if time is None:  # Output current slowmode.
            return await ctx.success(
                f"The current slowmode for {channel.mention} is `{channel.slowmode_delay}s`"
            )
        try:
            await channel.edit(slowmode_delay=time)
        except discord.HTTPException as e:
            await ctx.fail(f"Failed to set slowmode because of an error\n{e}")
        else:
            await ctx.success(f"Slowmode for {channel.mention} set to `{time}s`")

    @decorators.command(
        aliases=["lockdown", "lockchannel"],
        brief="Prevent messages in a channel.",
        implemented="2021-04-05 17:55:24.797692",
        updated="2021-06-07 23:50:42.589677",
        examples="""
                {0}lock #chatting 2 mins
                {0}lockchannel
                {0}lockdown #help until 3 pm
                """,
    )
    @checks.guild_only()
    @checks.bot_has_guild_perms(manage_roles=True)
    @checks.has_perms(administrator=True)
    @checks.cooldown()
    async def lock(
        self,
        ctx,
        channel: typing.Optional[converters.DiscordChannel] = None,
        *,
        duration: humantime.UserFriendlyTime(
            commands.clean_content, default="\u2026"
        ) = None,
    ):
        """
        Usage: {0}lock [channel] [duration]
        Aliases: {0}lockdown, {0}lockchannel
        Permission: Administrator
        Output:
            Locked channel for a specified duration.
            Infinite if not specified
        """
        if channel is None:
            channel = ctx.channel

        def fmt(channel):
            return (
                str(type(channel).__name__)
                .split(".")[-1]
                .lower()
                .replace("channel", " channels")
            )

        if not isinstance(channel, discord.TextChannel):
            raise commands.BadArgument(f"I cannot lock {fmt(channel)}.")

        await ctx.trigger_typing()
        if not channel.permissions_for(ctx.guild.me).read_messages:
            raise commands.BadArgument(
                f"I need to be able to read messages in {channel.mention}"
            )
        if not channel.permissions_for(ctx.guild.me).send_messages:
            raise commands.BadArgument(
                f"I need to be able to send messages in {channel.mention}"
            )

        query = """
                select (id)
                from tasks
                where event = 'lockdown'
                and extra->'kwargs'->>'channel_id' = $1;
                """
        s = await self.bot.cxn.fetchval(query, str(channel.id))
        if s:
            raise commands.BadArgument(f"Channel {channel.mention} is already locked.")

        overwrites = channel.overwrites_for(ctx.guild.default_role)
        perms = overwrites.send_messages
        if perms is False:
            raise commands.BadArgument(f"Channel {channel.mention} is already locked.")

        task = self.bot.get_cog("Tasks")
        if not task:
            raise commands.BadArgument("This feature is unavailable.")

        msg = await ctx.load(f"Locking channel {channel.mention}...")
        bot_perms = channel.overwrites_for(ctx.guild.me)
        if not bot_perms.send_messages:
            bot_perms.send_messages = True
            await channel.set_permissions(
                ctx.guild.me, overwrite=bot_perms, reason="For channel lockdown."
            )

        endtime = duration.dt.replace(tzinfo=None) if duration and duration.dt else None

        timer = await task.create_timer(
            endtime,
            "lockdown",
            ctx.guild.id,
            ctx.author.id,
            channel.id,
            perms=perms,
            channel_id=channel.id,
            connection=self.bot.cxn,
            created=ctx.message.created_at.replace(tzinfo=None),
        )
        overwrites.send_messages = False
        reason = "Channel locked by command."
        await channel.set_permissions(
            ctx.guild.default_role,
            overwrite=overwrites,
            reason=await converters.ActionReason().convert(ctx, reason),
        )

        if duration and duration.dt:
            timefmt = humantime.human_timedelta(endtime, source=timer.created_at)
        else:
            timefmt = None

        formatting = f" for {timefmt}" if timefmt else ""
        await msg.edit(
            content=f"{self.bot.emote_dict['lock']} Channel {channel.mention} locked{formatting}."
        )

    @decorators.command(
        brief="Unlock a channel.",
        aliases=["unlockchannel", "unlockdown"],
        implemented="2021-04-05 17:55:24.797692",
        updated="2021-06-07 23:50:42.589677",
        examples="""
                {0}unlock #chatting
                {0}unlockchannel
                {0}unlockdown #help
                """,
    )
    @checks.guild_only()
    @checks.bot_has_guild_perms(manage_roles=True)
    @checks.has_perms(administrator=True)
    async def unlock(self, ctx, *, channel: discord.TextChannel = None):
        """
        Usage: {0}unlock [channel]
        Aliases: {0}unlockchannel, {0}unlockdown
        Output: Unlocks a previously locked channel.
        """
        channel = channel or ctx.channel

        await ctx.trigger_typing()
        if not channel.permissions_for(ctx.guild.me).read_messages:
            raise commands.BadArgument(
                f"I need to be able to read messages in {channel.mention}"
            )
        if not channel.permissions_for(ctx.guild.me).send_messages:
            raise commands.BadArgument(
                f"I need to be able to send messages in {channel.mention}"
            )

        query = """
                SELECT (id, extra)
                FROM tasks
                WHERE event = 'lockdown'
                AND extra->'kwargs'->>'channel_id' = $1;
                """
        s = await self.bot.cxn.fetchval(query, str(channel.id))
        if not s:
            return await ctx.fail(f"Channel {channel.mention} is already unlocked.")

        msg = await ctx.load(f"Unlocking {channel.mention}...")
        task_id = s[0]
        args_and_kwargs = json.loads(s[1])
        perms = args_and_kwargs["kwargs"]["perms"]
        reason = "Channel unlocked by command execution"

        query = """
                DELETE FROM tasks
                WHERE id = $1
                """
        await self.bot.cxn.execute(query, task_id)

        overwrites = channel.overwrites_for(ctx.guild.default_role)
        overwrites.send_messages = perms
        await channel.set_permissions(
            ctx.guild.default_role,
            overwrite=overwrites,
            reason=await converters.ActionReason().convert(ctx, reason),
        )
        await msg.edit(
            content=f"{self.bot.emote_dict['unlock']} Channel {channel.mention} unlocked."
        )

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_lockdown_timer_complete(self, timer):
        guild_id, mod_id, channel_id = timer.args
        perms = timer.kwargs["perms"]

        guild = self.bot.get_guild(guild_id)
        if guild is None:
            # RIP
            return

        channel = self.bot.get_channel(channel_id)
        if channel is None:
            # RIP
            return

        moderator = guild.get_member(mod_id)
        if moderator is None:
            try:
                moderator = await self.bot.fetch_user(mod_id)
            except:
                # request failed somehow
                moderator = f"Mod ID {mod_id}"
            else:
                moderator = f"{moderator} (ID: {mod_id})"
        else:
            moderator = f"{moderator} (ID: {mod_id})"

        reason = (
            f"Automatic unlock from timer made on {timer.created_at} by {moderator}."
        )
        overwrites = channel.overwrites_for(guild.default_role)
        overwrites.send_messages = perms
        await channel.set_permissions(
            guild.default_role,
            overwrite=overwrites,
            reason=reason,
        )

    @decorators.command(
        aliases=["tban"],
        brief="Temporarily ban users.",
        implemented="2021-04-27 03:59:16.293041",
        updated="2021-05-13 00:04:42.463263",
        examples="""
                {0}tempban @Hecate 2 days for advertising
                {0}tban 708584008065351681 Hecate 2 hours for spamming
                """,
    )
    @checks.guild_only()
    @checks.bot_has_perms(ban_members=True)
    @checks.has_perms(ban_members=True)
    async def tempban(
        self,
        ctx,
        users: commands.Greedy[converters.DiscordMember(False)],
        *,
        duration: humantime.UserFriendlyTime(commands.clean_content, default="\u2026"),
    ):
        """
        Usage: {0}tempban <users> [duration] [reason]
        Alias: {0}tban
        Output:
            Temporarily bans a member for the specified duration.
            The duration can be a a short time form, e.g. 30d or a more human
            duration like "until thursday at 3PM".
        """
        task = self.bot.get_cog("Tasks")
        if not task:
            raise commands.BadArgument(f"This feature is unavailable.")
        if not len(users):
            return await ctx.usage()
        if not duration.dt:
            raise commands.BadArgument(
                "Invalid duration. Try using `2 days` or `3 hours`"
            )

        reason = duration.arg if duration and duration.arg != "…" else None
        endtime = duration.dt.replace(tzinfo=None)

        banned = []
        failed = []
        for user in users:
            res = await checks.check_priv(ctx, user)
            if res:
                failed.append((str(user), res))
                continue
            try:
                if reason:
                    embed = discord.Embed(color=self.bot.config.EMBED_COLOR)
                    timefmt = humantime.human_timedelta(
                        endtime, source=ctx.message.created_at
                    )
                    embed.title = f"{self.bot.emote_dict['ban']} Tempban Notice"
                    embed.description = (
                        f"**Server: `{ctx.guild.name} ({ctx.guild.id})`**\n"
                    )
                    embed.description += (
                        f"**Moderator: `{ctx.author} ({ctx.author.id})`**\n"
                    )
                    embed.description += f"**Duration: `{timefmt}`**\n"
                    embed.description += f"**Reason: `{reason}`**"
                    try:
                        await user.send(embed=embed)
                    except (AttributeError, discord.HTTPException):
                        pass

                await ctx.guild.ban(user, reason=reason)
                timer = await task.create_timer(
                    endtime,
                    "tempban",
                    ctx.guild.id,
                    ctx.author.id,
                    user.id,
                    connection=self.bot.cxn,
                    created=ctx.message.created_at.replace(tzinfo=None),
                )
                banned.append(str(user))
            except Exception as e:
                failed.append((str(user), e))
        if banned:
            self.bot.dispatch("mod_action", ctx, targets=banned)
            await ctx.success(
                f"Tempbanned `{', '.join(banned)}` for {humantime.human_timedelta(duration.dt, source=timer.created_at)}."
            )
        if failed:
            await helpers.error_info(ctx, failed)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_tempban_timer_complete(self, timer):
        guild_id, mod_id, member_id = timer.args

        guild = self.bot.get_guild(guild_id)
        if guild is None:
            # RIP
            return

        moderator = guild.get_member(mod_id)
        if moderator is None:
            try:
                moderator = await self.bot.fetch_user(mod_id)
            except:
                # request failed somehow
                moderator = f"Mod ID {mod_id}"
            else:
                moderator = f"{moderator} (ID: {mod_id})"
        else:
            moderator = f"{moderator} (ID: {mod_id})"

        reason = (
            f"Automatic unban from timer made on {timer.created_at} by {moderator}."
        )
        await guild.unban(discord.Object(id=member_id), reason=reason)

    ###################
    ## Mute Commands ##
    ###################

    @decorators.command(
        aliases=["tempmute"],
        brief="Mute users for a duration.",
        implemented="2021-04-02 00:16:54.164723",
        updated="2021-05-09 15:44:25.714321",
        examples="""
                {0}mute @Hecate
                {0}mute Hecate#3523 @John 2 minutes
                {0}mute 708584008065351681 John 3 days for advertising
                {0}mute John --duration 3 hours
                {0}mute Hecate for spamming
                {0}mute Hecate John for 2 days
                """,
    )
    @commands.guild_only()
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(kick_members=True)
    @checks.cooldown()
    async def mute(
        self,
        ctx,
        users: commands.Greedy[converters.DiscordMember(False)],
        *,
        duration: humantime.UserFriendlyTime(
            commands.clean_content, default="\u2026"
        ) = None,
    ):
        """
        Usage: {0}mute <users>... [duration] [reason]
        Alias: {0}tempmute
        Permission: Kick Members
        Output:
            Mutes multiple users.
            This command will attempt
            to remove all the roles from
            the passed users, and reaasign
            them on unmute. If no duration
            is specified, mute will be indefinite.
        Notes:
            Duration and reason are optional.
            Running the command with a reason
            will dm the user while running the
            command without a reason will not dm.
            Run the command: {0}examples mute
            for specific usage examples.
        """
        task = self.bot.get_cog("Tasks")
        if not task:
            raise commands.BadArgument(f"This feature is currently unavailable.")
        if not len(users):
            return await ctx.usage()

        await ctx.trigger_typing()
        query = """
                SELECT muterole
                FROM servers
                WHERE server_id = $1;
                """
        muterole = await self.bot.cxn.fetchval(query, ctx.guild.id)
        muterole = ctx.guild.get_role(muterole)
        if not muterole:
            raise commands.BadArgument(
                f"Run the `{ctx.clean_prefix}muterole <role>` command to set up a mute role."
            )
        if duration:
            reason = duration.arg if duration.arg != "…" else None
            endtime = duration.dt.replace(tzinfo=None) if duration.dt else None
            dm = True if reason else False
        else:
            reason = None
            endtime = None
            dm = False

        failed = []
        muted = []
        for user in users:
            if (
                user.bot
            ):  # This is because bots sometimes have a role that cannot be removed
                failed.append((str(user), "I cannot mute bots."))
                continue  # I mean we could.. but why would someone want to mute a bot.
            res = await checks.check_priv(ctx, user)
            if res:
                failed.append((str(user), res))
                continue
            query = """
                    DELETE FROM tasks
                    WHERE event = 'mute'
                    AND extra->'kwargs'->>'user_id' = $1;
                    """
            await self.bot.cxn.fetchval(query, str(user.id))
            try:
                timer = await task.create_timer(
                    endtime,
                    "mute",
                    ctx.guild.id,
                    ctx.author.id,
                    user.id,
                    dm=dm,
                    user_id=user.id,
                    roles=[x.id for x in user.roles],
                    connection=self.bot.cxn,
                    created=ctx.message.created_at.replace(tzinfo=None),
                )
                if user.premium_since:
                    await user.edit(
                        roles=[muterole, ctx.guild.premium_subscriber_role],
                        reason=reason,
                    )
                else:
                    await user.edit(roles=[muterole], reason=reason)
                # to_remove = (role for role in user.roles if role != ctx.guild.premium_subscriber_role and role != ctx.guild.default_role)
                # await user.remove_roles(*to_remove, reason=reason)
                # await user.add_roles(muterole, reason=reason)
                muted.append(str(user))
                if reason:
                    embed = discord.Embed(color=self.bot.config.EMBED_COLOR)
                    embed.title = f"Mute Notice"
                    embed.description = (
                        f"**Server: `{ctx.guild.name} ({ctx.guild.id})`**\n"
                    )
                    embed.description += (
                        f"**Moderator: `{ctx.author} ({ctx.author.id})`**\n"
                    )
                    if endtime:
                        timefmt = humantime.human_timedelta(
                            endtime, source=timer.created_at
                        )
                        embed.description += f"**Duration: `{timefmt}`**\n"
                    embed.description += f"**Reason: `{reason}`**"
                try:
                    await user.send(embed=embed)
                except Exception:  # We tried
                    pass
            except Exception as e:
                failed.append((str(user), e))
        if muted:
            self.bot.dispatch("mod_action", ctx, targets=muted)
            reason_str = f" Reason: {reason}" if reason else ""
            if endtime:
                timefmt = humantime.human_timedelta(endtime, source=timer.created_at)
                msg = f"Muted `{', '.join(muted)}` for **{timefmt}.**{reason_str}"
            else:
                msg = f"Muted `{', '.join(muted)}`.{reason_str}"
            await ctx.success(msg)

        if failed:
            await helpers.error_info(ctx, failed)

    @decorators.command(
        brief="Unmute muted users.",
        implemented="2021-05-09 19:44:24.756715",
        updated="2021-05-09 19:44:24.756715",
        examples="""
                {0}unmute Hecate @John 708584008065351681 because I forgave them
                {0}unmute Hecate#3523
                """,
    )
    @commands.guild_only()
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(manage_roles=True)
    async def unmute(
        self,
        ctx,
        users: commands.Greedy[converters.DiscordMember(False)],
        *,
        reason: typing.Optional[str] = "No reason",
    ):
        """
        Usage: {0}unmute <users>... [reason]
        Output:
            Unmutes previously users previously
            muted by the {0}mute command. The bot
            will restore all the users' old roles
            that they had before they were muted.
        """
        if not len(users):
            return await ctx.usage()
        failed = []
        unmuted = []
        for user in users:
            res = await checks.check_priv(ctx, user)
            if res:
                failed.append((str(user), res))
                continue

            query = """
                    select (id, extra)
                    from tasks
                    where event = 'mute'
                    and extra->'kwargs'->>'user_id' = $1;
                    """
            s = await self.bot.cxn.fetchval(query, str(user.id))
            if not s:
                unmuted.append(str(user))
                continue
            await ctx.trigger_typing()
            task_id = s[0]
            args_and_kwargs = json.loads(s[1])
            dm = args_and_kwargs["kwargs"]["dm"]
            roles = args_and_kwargs["kwargs"]["roles"]
            try:
                await user.edit(
                    roles=[ctx.guild.get_role(x) for x in roles],
                    reason=await converters.ActionReason().convert(ctx, reason),
                )
                query = """
                        DELETE FROM tasks
                        WHERE id = $1
                        """
                await self.bot.cxn.execute(query, task_id)
                unmuted.append(str(user))
            except Exception as e:
                failed.append((str(user), e))
                continue
            if dm:
                embed = discord.Embed(color=self.bot.config.EMBED_COLOR)
                embed.title = f"Unmute Notice"
                embed.description = f"**Server: `{ctx.guild.name} ({ctx.guild.id})`**\n"
                embed.description += f"**Moderator: `{ctx.author} ({ctx.author.id})`**"
                try:
                    await user.send(embed=embed)
                except Exception:
                    pass
        if unmuted:
            await ctx.success(f"Unmuted `{' '.join(unmuted)}`")
        if failed:
            await helpers.error_info(ctx, failed)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_mute_timer_complete(self, timer):
        guild_id, mod_id, member_id = timer.args

        guild = self.bot.get_guild(guild_id)
        if guild is None:
            # RIP
            return

        moderator = guild.get_member(mod_id)
        if moderator is None:
            try:
                moderator = await self.bot.fetch_user(mod_id)
            except:
                # request failed somehow
                moderator = f"Mod ID {mod_id}"
            else:
                moderator = f"{moderator} ({mod_id})"
        else:
            moderator = f"{moderator} ({mod_id})"

        reason = (
            f"Automatic unmute from timer made on {timer.created_at} by {moderator}."
        )
        member = guild.get_member(member_id)
        if not member:
            return  # They left...
        roles = timer.kwargs["roles"]
        dm = timer.kwargs["dm"]
        try:
            await member.edit(roles=[guild.get_role(x) for x in roles], reason=reason)
        except Exception:  # They probably removed roles lmao.
            return
        if dm:
            embed = discord.Embed(color=self.bot.config.EMBED_COLOR)
            embed.title = f"{self.bot.emote_dict['audioadd']} Unmute Notice"
            embed.description = f"**Server: `{guild.name} ({guild.id})`**\n"
            embed.description += f"**Moderator: `{moderator}`**"
            try:
                await member.send(embed=embed)
            except Exception:
                pass

    @decorators.command(
        aliases=["trole"],
        brief="Temporarily add roles to users.",
        implemented="2021-05-31 04:09:38.799221",
        updated="2021-05-31 04:09:38.799221",
        examples="""
                {0}temprole @Hecate 2 days for advertising
                {0}trole 708584008065351681 Hecate 2 hours for spamming
                """,
    )
    @checks.guild_only()
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(manage_roles=True)
    @checks.cooldown(2, 30)
    async def temprole(
        self,
        ctx,
        user: converters.DiscordMember,
        role: converters.DiscordRole,
        *,
        duration: humantime.UserFriendlyTime(commands.clean_content, default="\u2026"),
    ):
        """
        Usage: {0}temprole <user> <duration>
        Alias: {0}trole
        Output:
            Adds a role to a user for the specified duration.
            The duration can be a a short time form, e.g. 30d or a more human
            duration like "until thursday at 3PM".
        """
        task = self.bot.get_cog("Tasks")
        if not task:
            raise commands.BadArgument("This feature is unavailable.")

        if not duration.dt:
            raise commands.BadArgument(
                "Invalid duration. Try using `2 hours` or `3d` as durations."
            )

        endtime = duration.dt.replace(tzinfo=None)

        res = await checks.role_priv(ctx, role)
        if res:  # We failed the role hierarchy test
            return await ctx.fail(res)

        if role in user.roles:
            return await ctx.fail(f"User `{user}` already has role `{role.name}`")

        try:
            await user.add_roles(role)
        except Exception as e:
            await helpers.error_info(ctx, [(str(user), e)])
            return
        timer = await task.create_timer(
            endtime,
            "temprole",
            ctx.guild.id,
            user.id,
            role.id,
            connection=self.bot.cxn,
            created=ctx.message.created_at.replace(tzinfo=None),
        )

        self.bot.dispatch("mod_action", ctx, targets=[str(user)])
        try:
            time_fmt = humantime.human_timedelta(duration.dt, source=timer.created_at)
        except Exception:
            time_fmt = "unknown duration"
        await ctx.success(f"Temproled `{user}` the role `{role.name}` for {time_fmt}.")

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_temprole_timer_complete(self, timer):
        guild_id, member_id, role_id = timer.args

        guild = self.bot.get_guild(guild_id)
        if not guild:  # We were kicked or it was deleted.
            return
        member = guild.get_member(member_id)
        if not member:  # They left the server
            return
        role = guild.get_role(role_id)
        if not role:  # Role deleted.
            return

        reason = f"Temprole removal from timer made on {timer.created_at}."
        try:
            await member.remove_roles(role, reason)
        except Exception:  # We tried
            pass

    @decorators.command(
        aliases=["ar", "addroles"],
        brief="Add multiple roles to a user.",
        implemented="2021-03-11 23:21:57.831313",
        updated="2021-07-03 17:29:45.745560",
        examples="""
                {0}ar Hecate helper verified
                {0}addrole Hecate#3523 @Helper
                """,
    )
    @checks.guild_only()
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(manage_roles=True)
    @checks.cooldown()
    async def addrole(
        self,
        ctx,
        user: converters.DiscordMember,
        *roles: converters.UniqueRole,
    ):
        """
        Usage:      {0}addrole <user> [roles]...
        Aliases:    {0}ar, {0}addroles
        Permission: Manage Roles
        Output:     Adds multiple roles to a user
        Notes:
            If the role is multiple words, it must
            be surrounded in quotations.
            e.g. {0}ar Hecate "this role"
        """
        await user.add_roles(*roles, reason="Roles added by command")
        await ctx.success(
            f"Added user `{user}` "
            f'the role{"" if len(roles) == 1 else "s"} `{", ".join(str(r) for r in roles)}`'
        )
        self.bot.dispatch("mod_action", ctx, targets=[str(user)])

    @decorators.command(
        aliases=["rr", "rmrole", "remrole"],
        brief="Remove multiple roles to a user.",
        implemented="2021-03-11 23:21:57.831313",
        updated="2021-07-03 17:29:45.745560",
        examples="""
                {0}rr Hecate helper verified
                {0}rmrole Hecate#3523 @Helper
                """,
    )
    @checks.guild_only()
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(manage_roles=True)
    @checks.cooldown()
    async def removerole(
        self,
        ctx,
        user: converters.DiscordMember,
        *roles: converters.UniqueRole,
    ):
        """
        Usage:      {0}removerole <user> [roles]...
        Aliases:    {0}rr, {0}rmrole, {0}remrole
        Permission: Manage Roles
        Output:     Removes multiple roles to a user
        Notes:
            If the role is multiple words, it must
            be surrounded in quotations.
            e.g. {0}rr Hecate "this role"
        """
        await user.remove_roles(*roles, reason="Roles removed by command")
        await ctx.success(
            f"Removed user `{user}` "
            f'the role{"" if len(roles) == 1 else "s"} `{", ".join(str(r) for r in roles)}`'
        )
        self.bot.dispatch("mod_action", ctx, targets=[str(user)])
