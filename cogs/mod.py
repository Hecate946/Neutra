import re
import shlex
import typing
import asyncio
import asyncpg
import discord

from better_profanity import profanity
from collections import Counter
from datetime import datetime, timedelta
from discord.ext import commands


from settings import database
from utilities import converters, checks, utils, helpers, time
from utilities import decorators


def setup(bot):
    bot.add_cog(Mod(bot))


class Mod(commands.Cog):
    """
    Keep your server under control.
    """

    def __init__(self, bot):
        self.bot = bot
        self.mregex = re.compile(r"[0-9]{17,21}")
        self.dregex = re.compile(
            r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?"
        )
        self.uregex = re.compile(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
        )

    ####################
    ## VOICE COMMANDS ##
    ####################

    @decorators.command(brief="Move a user from a voice channel.")
    @commands.guild_only()
    @checks.bot_has_perms(move_members=True)
    @checks.has_perms(move_members=True)
    async def vcmove(
        self,
        ctx,
        targets: commands.Greedy[converters.DiscordMember] = None,
        channel: discord.VoiceChannel = None,
    ):
        """
        Usage: -vcmove <target> <target>... <channel>
        Output: Moves members into a new voice channel
        Permission: Move Members
        """
        if not targets:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}vc move <to channel> <target> [target]...`",
            )
        if not channel:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}vc move <to channel> <target> [target]...`",
            )
        vcmoved = []
        for target in targets:
            try:
                await target.edit(voice_channel=channel)
            except discord.HTTPException:
                await ctx.send_or_reply(
                    content=f"{self.bot.emote_dict['warn']} Target is not connected to a voice channel"
                )
                continue
            vcmoved.append(str(target))
        if vcmoved:
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['success']} VC Moved `{', '.join(vcmoved)}`"
            )

    @decorators.command(brief="Kick all users from a voice channel.")
    @commands.guild_only()
    @checks.has_perms(move_members=True)
    @checks.bot_has_perms(move_members=True)
    async def vcpurge(self, ctx, channel: discord.VoiceChannel = None):
        """
        Usage: -vcpurge <voice channel>
        Output: Kicks all members from the channel
        Permission: Move Members
        """
        if channel is None:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}vcpurge <voice channel name/id>`",
            )
        if len(channel.members) == 0:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['warn']} No members in voice channel {channel.mention}.",
            )
        failed = []
        for member in channel.members:
            try:
                await member.edit(voice_channel=None)
            except Exception as e:
                failed.append((str(member), e))
                continue
        await ctx.send_or_reply(
            content=f"{self.bot.emote_dict['success']} Purged {channel.mention}.",
        )
        if failed:
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['success']} Failed to vckick {len(failed)} user{'' if len(failed) == 1 else 's'}.",
            )

    @decorators.command(brief="Kick users from a voice channel.")
    @commands.guild_only()
    @checks.has_perms(move_members=True)
    @checks.bot_has_perms(move_members=True)
    async def vckick(self, ctx, targets: commands.Greedy[converters.DiscordMember]):
        """
        Usage: -vckick <target> <target>..
        Output: Kicks passed members from their channel
        Permission: Move Members
        """
        if not len(targets):
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}vckick <target> [target]...`",
            )
        vckicked = []
        for target in targets:
            try:
                await target.edit(voice_channel=None)
            except discord.HTTPException:
                await ctx.send_or_reply(
                    f"{self.bot.emote_dict['warn']} Target is not connected to a voice channel."
                )
            vckicked.append(str(target))
        if vckicked:
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['success']} VC Kicked `{', '.join(vckicked)}`"
            )

    ###################
    ## Mute Commands ##
    ###################

    @decorators.command(
        brief="Mute users for misbehaving.", aliases=["hackmute", "hardmute"]
    )
    @commands.guild_only()
    @checks.has_perms(kick_members=True)
    async def mute(
        self,
        ctx,
        targets: commands.Greedy[converters.DiscordMember],
        minutes: typing.Optional[int],
        *,
        reason: typing.Optional[str] = None,
    ):
        """
        Usage:     -hardmute <target> [target]... [minutes] [reason]
        Alias:     -hackmute
        Example:   -hardmute person1 person2 10 for spamming
        Pemission: Kick Members
        Output:    Takes all roles from passed users and mutes them.
        Notes:
            Command -muterole must be executed prior to usage of
            this command. Upon usage, will not be able to read
            messages in any channel. Roles will be given back to
            the user upon {0}unmute, or when their timed mute ends.
        """
        global target
        if not len(targets):
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}mute <target> [target]... [minutes] [reason]`",
            )

        else:
            unmutes = []
            try:
                self.mute_role = (
                    await self.bot.cxn.fetchval(
                        "SELECT muterole FROM servers WHERE server_id = $1",
                        ctx.guild.id,
                    )
                    or None
                )
                if self.mute_role is None:
                    return await ctx.send_or_reply(
                        f"use `{ctx.prefix}muterole <role>` to initialize the muted role."
                    )
                self.mute_role = ctx.guild.get_role(int(self.mute_role))
            except Exception as e:
                print("really?")
                return await ctx.send_or_reply(e)
            muted = []
            for target in targets:
                if target.bot:
                    await ctx.send_or_reply(
                        f"{self.bot.emote_dict['failed']} I cannot mute bots."
                    )
                    continue
                if self.mute_role not in target.roles:
                    role_ids = ",".join([str(r.id) for r in target.roles])
                    end_time = (
                        datetime.utcnow() + timedelta(seconds=minutes * 60)
                        if minutes
                        else None
                    )
                    if target.id in self.bot.constants.owners:
                        return await ctx.send_or_reply(
                            content="You cannot mute my developer.",
                        )
                    if target.id == ctx.author.id:
                        return await ctx.send_or_reply(
                            "I don't think you really want to mute yourself..."
                        )
                    if target.id == self.bot.user.id:
                        return await ctx.send_or_reply(
                            content="I don't think I want to mute myself...",
                        )
                    if (
                        target.guild_permissions.kick_members
                        and ctx.author.id != ctx.guild.owner.id
                    ):
                        return await ctx.send_or_reply(
                            content="You cannot punish other staff members.",
                        )
                    if ctx.guild.me.top_role.position < target.top_role.position:
                        return await ctx.send_or_reply(
                            f"My highest role is below `{target}'s` highest role. Aborting mute."
                        )

                    if ctx.guild.me.top_role.position == target.top_role.position:
                        return await ctx.send_or_reply(
                            f"I have the same permissions as `{target}`. Aborting mute."
                        )
                    if ctx.guild.me.top_role.position < self.mute_role.position:
                        return await ctx.send_or_reply(
                            "My highest role is below the mute role. Aborting mute."
                        )
                    try:
                        await self.bot.cxn.execute(
                            "INSERT INTO mutes VALUES ($1, $2, $3, $4)",
                            target.id,
                            ctx.guild.id,
                            role_ids,
                            getattr(end_time, "isoformat", lambda: None)(),
                        )
                    except Exception as e:
                        return await ctx.send_or_reply(e)
                    try:
                        await target.edit(roles=[self.mute_role])
                        muted.append(target)
                    except Exception as e:
                        return await ctx.send_or_reply(e)
                    if reason:
                        try:
                            await target.send(
                                f"{self.bot.emote_dict['announce']} You have been muted in **{ctx.guild.name}** {reason}. Mute duration: `{minutes if minutes is not None else 'Infinite'} minute{'' if minutes == 1 else 's'}`"
                            )
                        except Exception:
                            return
                    global unmutereason
                    unmutereason = reason

                    if minutes:
                        unmutes.append(target)
                else:
                    await ctx.send_or_reply(
                        f"{self.bot.emote_dict['warn']} Member `{target.display_name}` is already muted."
                    )
            if muted:
                allmuted = []
                for member in muted:
                    users = []
                    people = self.bot.get_user(int(member.id))
                    users.append(people)
                    for user in users:
                        username = f"{user.name}#{user.discriminator}"
                        allmuted += [username]
                if minutes is None:
                    msg = f'{self.bot.emote_dict["success"]} Muted `{", ".join(allmuted)}` indefinetely'
                else:
                    msg = f'{self.bot.emote_dict["success"]} Muted `{", ".join(allmuted)}` for {minutes:,} minute{"" if minutes == 1 else "s"}'
                await ctx.send_or_reply(msg)
                self.bot.dispatch("mod_action", ctx, targets=allmuted)
            if len(unmutes):
                await asyncio.sleep(minutes * 60)
                await self.unmute(ctx, targets)

    async def unmute(self, ctx, targets):
        try:
            self.mute_role = (
                await self.bot.cxn.fetchrow(
                    "SELECT muterole FROM servers WHERE server_id = $1", ctx.guild.id
                )
                or None
            )
            self.mute_role = self.mute_role[0]
            self.mute_role = ctx.guild.get_role(int(self.mute_role))
        except Exception as e:
            return await ctx.send_or_reply(e)
        unmuted = []
        for target in targets:
            if self.mute_role in target.roles:
                role_ids = (
                    await self.bot.cxn.fetchrow(
                        "SELECT role_ids FROM mutes WHERE muted_user = $1", target.id
                    )
                    or None
                )
                if str(role_ids) == "None":
                    await target.remove_roles(self.mute_role)
                    unmuted.append(str(target))
                    continue
                role_ids = role_ids[0]
                roles = [
                    ctx.guild.get_role(int(id_))
                    for id_ in role_ids.split(",")
                    if len(id_)
                ]

                await self.bot.cxn.execute(
                    "DELETE FROM mutes WHERE muted_user = $1", target.id
                )

                await target.edit(roles=roles)
                unmuted.append(str(target))
                if unmutereason:
                    try:
                        await target.send(
                            f"{self.bot.emote_dict['announce']} You have been unmuted in **{ctx.guild.name}**"
                        )
                    except Exception:
                        return

            else:
                return await ctx.send_or_reply(
                    content=f"{self.bot.emote_dict['warn']} Member is not muted",
                )

        if unmuted:
            await ctx.send_or_reply(
                content=f'{self.bot.emote_dict["success"]} Unmuted `{", ".join(unmuted)}`',
            )
            self.bot.dispatch("mod_action", ctx, targets=unmuted)

    @decorators.command(
        name="unmute", brief="Unmute previously muted members.", aliases=["endmute"]
    )
    @commands.guild_only()
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(kick_members=True)
    async def unmute_members(
        self, ctx, targets: commands.Greedy[converters.DiscordMember]
    ):
        """
        Usage: -unmute <target> [target]...
        Alias: -endmute
        Example: -unmute Hecate @Elizabeth 708584008065351681
        Permissiom: Kick Members
        Output: Unmutes members muted by the -hardmute command.
        """
        await self.unmute(ctx, targets)

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
        restrict = []
        failed = []
        for target in targets:
            res = await checks.check_priv(ctx, target)
            if res:
                failed.append((str(target), res))
                continue
            try:
                await ctx.channel.set_permissions(target, overwrite=overwrite)
                restrict.append(str(target))
            except Exception as e:
                failed.append((str(target), e))
                continue
        if restrict:
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['success']} {ctx.command.name.capitalize()}ed `{', '.join(restrict)}`"
            )
            self.bot.dispatch("mod_action", ctx, targets=restrict)
        if failed:
            await helpers.error_info(ctx, failed)

    @decorators.command(brief="Restrict users from sending messages.")
    @commands.guild_only()
    @checks.has_perms(kick_members=True)
    async def block(self, ctx, targets: commands.Greedy[converters.DiscordMember]):
        """
        Usage: -block <target> [target]...
        Example: -block Hecate 708584008065351681 @Elizabeth
        Permission: Kick Members
        Output: Stops users from messaging in the channel.
        """
        if not len(targets):
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}block <target> [target] [target]...`",
            )
        await self.restrictor(ctx, targets, "on", "block")

    @decorators.command(brief="Reallow users to send messages.")
    @commands.guild_only()
    @checks.has_perms(kick_members=True)
    async def unblock(
        self, ctx, targets: commands.Greedy[converters.DiscordMember] = None
    ):
        """
        Usage:      -unblock <target> [target]...
        Example:    -unblock Hecate 708584008065351681 @Elizabeth
        Permission: Kick Members
        Output:     Reallows blocked users to send messages.
        """
        if not targets:  # checks if there is user
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}unblock <target> [target] [target]...`",
            )
        await self.restrictor(ctx, targets, "off", "unblock")

    @decorators.command(brief="Hide a channel from a user.")
    @commands.guild_only()
    @checks.has_perms(kick_members=True)
    async def blind(
        self, ctx, targets: commands.Greedy[converters.DiscordMember] = None
    ):
        """
        Usage:      -blind <target> [target]...
        Example:    -blind Hecate 708584008065351681 @Elizabeth
        Permission: Kick Members
        Output:     Prevents users from seeing the channel.
        """
        if not targets:  # checks if there is user
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}blind <target> [target] [target]...`",
            )
        await self.restrictor(ctx, targets, "on", "blind")

    @decorators.command(brief="Reallow users see a channel.")
    @commands.guild_only()
    @checks.has_perms(kick_members=True)
    async def unblind(
        self, ctx, targets: commands.Greedy[converters.DiscordMember] = None
    ):
        """
        Usage:      -unblind <target> [target]...
        Example:    -unblind Hecate 708584008065351681 @Elizabeth
        Permission: Kick Members
        Output:     Reallows blinded users to see the channel.
        """
        if not targets:  # checks if there is user
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}unblind <target> [target] [target]...`",
            )
        await self.restrictor(ctx, targets, "off", "unblind")

    ##################
    ## Kick Command ##
    ##################

    @decorators.command(brief="Kick users from the server.")
    @commands.guild_only()
    @checks.bot_has_perms(kick_members=True)
    @checks.has_perms(kick_members=True)
    async def kick(
        self,
        ctx,
        users: commands.Greedy[converters.DiscordMember],
        *,
        reason: typing.Optional[str] = "No reason",
    ):
        """
        Usage:      -kick <target> [target]... [reason]
        Example:    -kick @Jacob Sarah for advertising
        Permission: Kick Members
        Output:     Kicks passed members from the server.
        """
        if not len(users):
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}kick <target> [target]... [reason]`",
            )

        kicked = []
        failed = []
        for target in users:
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
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['success']} Kicked `{', '.join(kicked)}`",
            )
            self.bot.dispatch("mod_action", ctx, targets=kicked)
        if failed:
            await helpers.error_info(ctx, failed)

    ##################
    ## Ban Commands ##
    ##################

    @decorators.command(
        brief="Ban users from the server.",
        permissions=["ban_members"],
    )
    @commands.guild_only()
    @checks.bot_has_perms(ban_members=True)
    @checks.has_perms(ban_members=True)
    async def ban(
        self,
        ctx,
        targets: commands.Greedy[converters.DiscordMember],
        delete_message_days: typing.Optional[int] = 1,
        *,
        reason: typing.Optional[str] = "No reason.",
    ):
        """
        Usage: -ban <target> [target]... [delete message days = 1] [reason]
        Example: -ban @Jacob Sarah 4 for advertising
        Permission: Ban Members
        Output: Ban passed members from the server.
        """
        if not len(targets):
            return await ctx.usage(
                "<target1> [target2].. [delete message days = 1] [reason]"
            )

        if delete_message_days > 7:
            delete_message_days = 7
        elif delete_message_days < 0:
            delete_message_days = 0

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

    @decorators.command(brief="Temporarily ban users.")
    async def tempban(
        self,
        ctx,
        targets: commands.Greedy[converters.DiscordMember],
        duration: time.FutureTime,
        delete_message_days: typing.Optional[int] = 0,
        reason: typing.Optional[str] = "No reason.",
    ):
        """
        Usage: -tempban <user> [user]... [hours till unban] [days to delete messages] [reason]
        Alias: -timedban
        Permission: Ban Members
        """
        if not len(targets):
            return await ctx.usage(
                "<user> [hours until unban] [days to delete messages] [reason]"
            )

        until = f"until {duration.dt:%Y-%m-%d %H:%M UTC}"

        if delete_message_days > 7:
            delete_message_days = 7
        elif delete_message_days < 0:
            delete_message_days = 0

        query = """
                INSERT INTO tasks
                VALUES ($1, $2, $3, $4)
                """

        banned = []
        failed = []
        for target in targets:
            res = await checks.check_priv(ctx, target)
            if res:
                failed.append((str(target), res))
                continue
            try:
                await self.bot.cxn.execute(
                    query, target.id, ctx.guild.id, "tempban", duration.dt
                )
            except asyncpg.UniqueViolationError:
                failed.append((target.id, "User is already tempbanned."))
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
            await ctx.success(f"Tempbanned `{', '.join(banned)}` `{until}.`")
            self.bot.dispatch("mod_action", ctx, targets=banned)
            await self.do_timer(
                ctx, banned, seconds=(duration.dt - datetime.utcnow()).total_seconds()
            )
        if failed:
            await helpers.error_info(ctx, failed)

    async def do_timer(self, ctx, users, seconds):
        await asyncio.sleep(seconds)
        for user in users:
            try:
                member = await converters.BannedMember().convert(ctx, user)
            except Exception as e:
                print(e)
            if member:
                try:
                    await ctx.guild.unban(member.user, reason="Tempban timer expired.")
                except Exception as e:
                    print(e)

    @decorators.command(brief="Softban users from the server.")
    @commands.guild_only()
    @checks.bot_has_perms(ban_members=True)
    @checks.has_perms(kick_members=True)
    async def softban(
        self,
        ctx,
        targets: commands.Greedy[converters.DiscordMember],
        delete_message_days: typing.Optional[int] = 7,
        *,
        reason: typing.Optional[str] = "No reason.",
    ):
        """
        Usage:      -softban <targets> [delete message = 7] [reason]
        Example:    -softban @Jacob Sarah 6 for advertising
        Permission: Kick Members
        Output:     Softbans members from the server.
        Notes:
            A softban bans the member and immediately
            unbans s/he in order to delete messages.
            The days to delete messages is set to 7 days.
        """
        if not len(targets):
            return await ctx.usage("<user> [days to delete messages] [reason]")

        if delete_message_days > 7:
            delete_message_days = 7
        elif delete_message_days < 0:
            delete_message_days = 0

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
                    target, reason=converters.ActionReason().convert(ctx, reason)
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

    @decorators.command(brief="Hackban multiple users.")
    @checks.bot_has_perms(ban_members=True)
    @checks.has_perms(ban_members=True)
    async def hackban(
        self,
        ctx,
        users: commands.Greedy[converters.UserIDConverter],
        *,
        args=None,
    ):
        """
        Usage: -hackban <user id> <user id>... [--reason] [--delete]
        Example:
            -hackban 805871188462010398 --reason for spamming --delete 2
        Permission: Ban Members
        Output: Hackbans multiple users.
        Notes: Users do not have to be in the server.
        """
        if not len(users):
            return await ctx.usage("<user> [user]... [--reason] [--delete]")

        if args:
            parser = converters.Arguments(add_help=False, allow_abbrev=False)
            parser.add_argument("--reason", nargs="+", default="No reason.")
            parser.add_argument("--delete", type=int, default=1)

            try:
                args = parser.parse_args(shlex.split(args))
            except Exception as e:
                return await ctx.fail(str(e).capitalize())

            if args.reason:
                reason = " ".join(args.reason)
            reason = await converters.ActionReason().convert(ctx, reason)

            if args.delete:
                delete = args.delete
                if delete > 7:
                    delete = 7
                if delete < 0:
                    delete = 0
            else:
                delete = 1
        else:
            delete = 1
            reason = "No reason"
        banned = []
        failed = []
        for user in users:
            if isinstance(user, discord.Member):
                res = await checks.check_priv(ctx, user)
                if res:
                    failed.append((str(user), res))
                    continue
            try:
                await ctx.guild.ban(
                    user,
                    reason=reason,
                    delete_message_days=delete,
                )
                banned.append(str(user))
            except Exception as e:
                failed.append((str(user), e))
                continue
        if banned:
            await ctx.success(f"Hackbanned `{', '.join(banned)}`")
            self.bot.dispatch("mod_action", ctx, targets=banned)
        if failed:
            await helpers.error_info(ctx, failed)

    @decorators.command(brief="Unban a previously banned user.", aliases=["revokeban"])
    @commands.guild_only()
    @checks.has_perms(ban_members=True)
    async def unban(self, ctx, member: converters.BannedMember, *, reason: str = None):
        """
        Usage:      -unban <user> [reason]
        Alias:      -revokeban
        Example:    Unban Hecate#3523 Because...
        Permission: Ban Members
        Output:     Unbans a member from the server.
        Notes:      Pass either the user's ID or their username
        """
        if not member:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}unban <id/name#discriminator> [reason]`",
            )
        if reason is None:
            reason = utils.responsible(
                ctx.author, f"Unbanned member {member} by command execution"
            )

        await ctx.guild.unban(member.user, reason=reason)
        if member.reason:
            await ctx.send_or_reply(
                content=f'{self.bot.emote_dict["success"]} Unbanned `{member.user} (ID: {member.user.id})`, previously banned for `{member.reason}.`',
            )
        else:
            await ctx.send_or_reply(
                content=f'{self.bot.emote_dict["success"]} Unbanned `{member.user} (ID: {member.user.id}).`',
            )
        self.bot.dispatch("mod_action", ctx, targets=[str(member.user)])

    # https://github.com/AlexFlipnote/discord_bot.py with my own additions

    ###################
    ## Prune Command ##
    ###################

    @decorators.group(
        brief="Remove any type of content.",
        aliases=["prune", "delete", "remove"],
        description="Methods:"
        "\nAll - Purge all messages."
        "\nBots - Purge messages sent by bots."
        "\nContains - Custom purge messages."
        "\nEmbeds - Purge messages with embeds."
        "\nEmojis - Purge messages with emojis."
        "\nFiles - Purge messages with attachments."
        "\nHumans - Purge  messages sent by humans."
        "\nImages - Purge messages with images."
        "\nInvites - Purge messages with invites."
        "\nMentions - Purge messages with mentions."
        "\nReactions - Purge reactions from messages."
        "\nUntil - Purge messages until a message."
        "\nUrls - Purge messages with URLs."
        "\nUser - Purge messages sent by a user."
        "\nWebhooks - Purge messages sent by wehooks.",
    )
    @commands.guild_only()
    @commands.max_concurrency(5, per=commands.BucketType.guild)
    @checks.bot_has_perms(manage_messages=True)
    @checks.has_perms(manage_messages=True)
    async def purge(self, ctx):
        """
        Usage: -purge <option> <amount>
        Aliases: -prune, -delete, -remove
        Permission: Manage Messages
        Options:
            all, bots, contains, embeds,
            emojis, files, humans, images,
            invites, mentions, reactions,
            until, urls, user, webhooks.
        Output:
            Deletes messages that match
            a specific search criteria
        Examples:
            -prune user Hecate
            -prune bots
            -prune invites 1000
        Notes:
            Specify the amount kwarg
            to search that number of
            messages. For example,
            -prune user Hecate 1000
            will search for all messages
            in the past 1000 sent in the
            channel, and delete all that
            were sent by Hecate.
            Default amount is 100.
        """
        args = str(ctx.message.content).split(" ")
        if ctx.invoked_subcommand is None:
            try:
                args[1]
            except IndexError:
                return await ctx.usage("<option> [amount]")
            await self._remove_all(ctx, search=int(args[1]))

    async def do_removal(
        self, ctx, limit, predicate, *, before=None, after=None, message=True
    ):
        if limit > 2000:
            return await ctx.send_or_reply(
                content=f"Too many messages to search given ({limit}/2000)",
            )

        if not before:
            before = ctx.message
        else:
            before = discord.Object(id=before)

        if after:
            after = discord.Object(id=after)

        try:
            deleted = await ctx.channel.purge(
                limit=limit, before=before, after=after, check=predicate
            )
        except discord.Forbidden:
            return await ctx.send_or_reply(
                content="I do not have permissions to delete messages.",
            )
        except discord.HTTPException as e:
            return await ctx.send_or_reply(
                content=f"Error: {e} (try a smaller search?)",
            )

        deleted = len(deleted)
        if message is True:
            msg = await ctx.send_or_reply(
                content=f'{self.bot.emote_dict["trash"]} Deleted {deleted} message{"" if deleted == 1 else "s"}',
            )
            await asyncio.sleep(7)
            await ctx.message.delete()
            await msg.delete()

    @purge.command(brief="Purge messages with embeds.")
    async def embeds(self, ctx, search=100):
        """
        Usage: -purge embeds [amount]
        Output:
            Deletes all messages that
            contain embeds in them.
        Examples:
            -purge embeds 2000
            -prune embeds
        """
        await self.do_removal(ctx, search, lambda e: len(e.embeds))

    @purge.command(brief="Purge messages with invites.", aliases=["ads"])
    async def invites(self, ctx, search=100):
        """
        Usage: -purge invites [amount]
        Alias: -purge ads
        Output:
            Deletes all messages with
            invite links in them.
        Examples:
            -purge invites
            -prune invites 125
        """

        def predicate(m):
            print(self.dregex.search(m.content))
            return self.dregex.search(m.content)

        await self.do_removal(ctx, search, predicate)

    @purge.command(aliases=["link", "url", "links"], brief="Purge messages with URLs.")
    async def urls(self, ctx, search=100):
        """
        Usage: -purge urls [amount]
        Aliases:
            -purge link
            -purge links
            -purge url
        Output:
            Deletes all messages that
            contain URLs in them.
        Examples:
            -purge urls
            -prune urls 125
        """

        def predicate(m):
            print(self.uregex.search(m.content))
            return self.uregex.search(m.content)

        await self.do_removal(ctx, search, predicate)

    @purge.command(brief="Purge messages with attachments.", aliases=["attachments"])
    async def files(self, ctx, search=100):
        """
        Usage: -purge files [amount]
        Aliases:
            -purge attachments
        Output:
            Deletes all messages that
            contain attachments in them.
        Examples:
            -purge attachments
            -prune files 125
        """
        await self.do_removal(ctx, search, lambda e: len(e.attachments))

    @purge.command(
        brief="Purge messages with mentions.", aliases=["pings", "ping", "mention"]
    )
    async def mentions(self, ctx, search=100):
        """
        Usage: -purge mentions [amount]
        Aliases:
            -purge pings
            -purge ping
            -purge mention
        Output:
            Deletes all messages that
            contain user mentions in them.
        Examples:
            -purge mentions
            -prune pings 125
        """
        await self.do_removal(
            ctx, search, lambda e: len(e.mentions) or len(e.role_mentions)
        )

    @purge.command(
        brief="Purge messages with images.", aliases=["pictures", "pics", "image"]
    )
    async def images(self, ctx, search=100):
        """
        Usage: -purge mentions [amount]
        Aliases:
            -purge pics
            -purge pictures
            -purge image
        Output:
            Deletes all messages that
            contain images in them.
        Examples:
            -purge pictures
            -prune images 125
        """
        await self.do_removal(
            ctx, search, lambda e: len(e.embeds) or len(e.attachments)
        )

    @purge.command(name="all", brief="Purge all messages.", aliases=["messages"])
    async def _remove_all(self, ctx, search=100):
        """
        Usage: -purge all [amount]
        Aliases:
            -purge
            -purge messages
        Output:
            Deletes all messages.
        Examples:
            -purge
            -prune 2000
            -prune messages 125
        """
        await self.do_removal(ctx, search, lambda e: True)

    @purge.command(brief="Purge messages sent by a user.", aliases=["member"])
    async def user(self, ctx, member: converters.DiscordMember = None, search=100):
        """
        Usage: -purge user <user> [amount]
        Aliases:
            -purge member
        Output:
            Deletes all messages that
            were sent by the passed user.
        Examples:
            -purge user
            -prune member 125
        """
        if member is None:
            return await ctx.usage(f"<user> [amount]")
        await self.do_removal(ctx, search, lambda e: e.author == member)

    @purge.command(brief="Customize purging messages.", aliases=["has"])
    async def contains(self, ctx, *, substr: str):
        """
        Usage: -purge contains <string>
        Alias:
            -purge has
        Output:
            Deletes all messages that
            contain the passed string.
        Examples:
            -purge contains hello
            -prune has no
        Notes:
            The string must a minimum
            of 2 characters in length.
        """
        if len(substr) < 2:
            await ctx.fail(
                content="The substring length must be at least 3 characters.",
            )
        else:
            await self.do_removal(ctx, 100, lambda e: substr in e.content)

    @purge.command(
        name="bots", brief="Purge messages sent by bots.", aliases=["robots"]
    )
    async def _bots(self, ctx, search=100, prefix=None):
        """
        Usage: -purge bots [amount] [prefix]
        Alias:
            -purge robots
        Output:
            Deletes all messages
            that were sent by bots.
        Examples:
            -purge robots 200
            -prune bote 150 >
        Notes:
            Specify an optional prefix to
            remove all messages that start
            with that prefix. This is useful
            for removing command invocations
        """

        if not str(search).isdigit():
            prefix = search
            search = 100
        if prefix:

            def predicate(m):
                return (m.webhook_id is None and m.author.bot) or m.content.startswith(
                    prefix
                )

        else:

            def predicate(m):
                return m.webhook_id is None and m.author.bot

        await self.do_removal(ctx, search, predicate)

    @purge.command(
        name="webhooks", aliases=["webhook"], brief="Purge messages sent by wehooks."
    )
    async def webhooks(self, ctx, search=100):
        """
        Usage: -purge webhooks [amount]
        Alias:
            -purge webhook
        Output:
            Deletes all messages that
            were sent by webhooks.
        Examples:
            -purge webhook
            -prune webhooks 125
        """

        def predicate(m):
            return m.webhook_id

        await self.do_removal(ctx, search, predicate)

    @purge.command(
        name="humans",
        aliases=["users", "members", "people"],
        brief="Purge messages sent by humans.",
    )
    async def _users(self, ctx, search=100):
        """
        Usage: -purge humans [amount]
        Aliases:
            -purge users
            -purge members
            -purge people
        Output:
            Deletes all messages
            sent by user accounts.
            Bot and webhook messages
            will not be deleted.
        Examples:
            -purge humans
            -prune people 125
        """

        def predicate(m):
            return m.author.bot is False

        await self.do_removal(ctx, search, predicate)

    @purge.command(
        name="emojis",
        aliases=["emotes", "emote", "emoji"],
        brief="Purge messages with emojis.",
    )
    async def _emojis(self, ctx, search=100):
        """
        Usage: -purge emojis [amount]
        Aliases:
            -purge emotes
            -purge emote
            -purge emoji
        Output:
            Deletes all messages that
            contain custom discord emojis.
        Examples:
            -purge emojis
            -prune emotes 125
        """
        custom_emoji = re.compile(r"<a?:(.*?):(\d{17,21})>|[\u263a-\U0001f645]")

        def predicate(m):
            return custom_emoji.search(m.content)

        await self.do_removal(ctx, search, predicate)

    @purge.command(name="reactions", brief="Purge reactions from messages.")
    async def _reactions(self, ctx, search=100):
        """
        Usage: -purge emojis [amount]
        Output:
            Demoves all reactions from
            messages that were reacted on.
        Examples:
            -purge reactions
            -prune reactions 125
        Notes:
            The messages are not deleted.
            Only the reactions are removed.
        """
        if search > 2000:
            return await ctx.send_or_reply(
                content=f"Too many messages to search for ({search}/2000)",
            )

        total_reactions = 0
        async for message in ctx.history(limit=search, before=ctx.message):
            if len(message.reactions):
                total_reactions += sum(r.count for r in message.reactions)
                await message.clear_reactions()
        await ctx.send_or_reply(
            f'{self.bot.emote_dict["trash"]} Successfully removed {total_reactions} reactions.',
            delete_after=7,
        )

    @purge.command(
        name="until", aliases=["after"], brief="Purge messages after a message."
    )
    async def _until(self, ctx, message_id: int):
        """
        Usage: -purge until <message id>
        Alias: -purge after
        Output:
            Purges all messages until
            the given message_id.
            Given ID is not deleted
        Examples:
            -purge until 810377376269
            -prune after 810377376269
        """
        channel = ctx.message.channel
        try:
            message = await channel.fetch_message(message_id)
        except commands.errors.NotFound:
            await ctx.send_or_reply(
                content="Message could not be found in this channel",
            )
            return

        await ctx.message.delete()
        await channel.purge(after=message)
        return True

    async def _basic_cleanup_strategy(self, ctx, search):
        count = 0
        async for msg in ctx.history(limit=search, before=ctx.message):
            if msg.author == ctx.me and not (msg.mentions or msg.role_mentions):
                await msg.delete()
                count += 1
        return {"Bot": count}

    async def _complex_cleanup_strategy(self, ctx, search):
        prefixes = tuple(self.bot.get_guild_prefixes(ctx.guild))  # thanks startswith

        def check(m):
            return m.author == ctx.me or m.content.startswith(prefixes)

        deleted = await ctx.channel.purge(limit=search, check=check, before=ctx.message)
        return Counter(m.author.display_name for m in deleted)

    async def _regular_user_cleanup_strategy(self, ctx, search):
        prefixes = tuple(self.bot.get_guild_prefixes(ctx.guild))

        def check(m):
            return (m.author == ctx.me or m.content.startswith(prefixes)) and not (
                m.mentions or m.role_mentions
            )

        deleted = await ctx.channel.purge(limit=search, check=check, before=ctx.message)
        return Counter(m.author.display_name for m in deleted)

    @decorators.command(
        brief="Clean up bot command usage.",
        aliases=["clean"],
        updated="2021-05-05 16:00:23.974656",
    )
    @commands.guild_only()
    async def cleanup(self, ctx, search=100):
        """
        Usage: -cleanup [search]
        Alias: -clean
        Output: Cleans up the bot's messages from the channel.
        Notes:
            If a search number is specified, it searches that many messages to delete.
            If the bot has Manage Messages permissions then it will try to delete
            messages that look like they invoked the bot as well.
            After the cleanup is completed, the bot will send you a message with
            which people got their messages deleted and their count. This is useful
            to see which users are spammers. Regular users can delete up to 25 while
            moderators can delete up to 2000 messages
        """
        strategy = self._basic_cleanup_strategy
        is_mod = ctx.channel.permissions_for(ctx.author).manage_messages
        if ctx.channel.permissions_for(ctx.me).manage_messages:
            if is_mod:
                strategy = self._complex_cleanup_strategy
            else:
                strategy = self._regular_user_cleanup_strategy

        if is_mod:
            search = min(max(2, search), 2000)
        else:
            search = min(max(2, search), 25)

        spammers = await strategy(ctx, search)
        deleted = sum(spammers.values())
        messages = [
            f"**{self.bot.emote_dict['trash']} Deleted {deleted} message{'' if deleted == 1 else 's'}\n**"
        ]
        if deleted:
            spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
            messages.extend(f"`{author}`: {count}" for author, count in spammers)
        desc = "\n".join(messages)
        em = discord.Embed()
        em.color = self.bot.constants.embed
        em.description = desc

        await ctx.send_or_reply(embed=em, delete_after=10)

    #########################
    ## Profanity Listeners ##
    #########################

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if self.bot.ready is False:
            return
        if not before.guild:
            return
        if before.author.bot:
            return
        immune = before.author.guild_permissions.manage_messages
        if immune:
            return
        msg = str(after.content)

        try:
            filtered_words = self.bot.server_settings[after.guild.id]["profanities"]
        except KeyError:
            await database.fix_server(after.guild.id)
            try:
                filtered_words = self.bot.server_settings[after.guild.id]["profanities"]
            except Exception:
                return

        if filtered_words == []:
            return

        profanity.load_censor_words(filtered_words)

        for filtered_word in filtered_words:
            if profanity.contains_profanity(msg) or filtered_word in msg:
                try:
                    await after.delete()
                    return await after.author.send(
                        f"Your message `{after.content}` was removed for containing the filtered word `{filtered_word}`"
                    )
                except Exception:
                    return

    @commands.Cog.listener()
    async def on_message(self, message):
        if self.bot.ready is False:
            return
        if not message.guild:
            return
        if message.author.bot:
            return
        immune = message.author.guild_permissions.manage_messages
        if immune:
            return
        msg = str(message.content)
        try:
            filtered_words = self.bot.server_settings[message.guild.id]["profanities"]
        except KeyError:
            await database.fix_server(message.guild.id)
            try:
                filtered_words = self.bot.server_settings[message.guild.id][
                    "profanities"
                ]
            except Exception:
                return

        if filtered_words == []:
            return

        profanity.load_censor_words(filtered_words)

        for filtered_word in filtered_words:
            if profanity.contains_profanity(msg) or filtered_word in msg:
                try:
                    await message.delete()
                    return await message.author.send(
                        f"Your message `{message.content}` was removed for containing a filtered word."
                    )
                except Exception:
                    return

    @decorators.command(brief="Set the slowmode for a channel")
    @commands.guild_only()
    @checks.bot_has_perms(manage_channels=True)
    @checks.has_perms(manage_channels=True)
    async def slowmode(self, ctx, channel=None, time: float = None):
        """
        Usage: -slowmode [channel] [seconds]
        Permission: Manage Channels
        Output:
            Sets the channel's slowmode to your input value.
        Notes:
            If no slowmode is passed, will reset the slowmode.
        """
        if channel is None:
            channel_obj = ctx.channel
            time = 0.0
        else:
            try:
                channel_obj = await commands.TextChannelConverter().convert(
                    ctx, channel
                )
            except commands.ChannelNotFound:
                channel_obj = ctx.channel
                if channel.isdigit():
                    time = float(channel)
                else:
                    time = 0.0
        try:
            await channel_obj.edit(slowmode_delay=time)
        except discord.HTTPException as e:
            await ctx.send_or_reply(
                content=f'{self.bot.emote_dict["failed"]} Failed to set slowmode because of an error\n{e}',
            )
        else:
            await ctx.send_or_reply(
                content=f'{self.bot.emote_dict["success"]} Slowmode for {channel_obj.mention} set to `{time}s`',
            )

    @decorators.command(aliases=["lockdown", "lockchannel"], brief="Lock a channel")
    @commands.guild_only()
    @checks.bot_has_perms(manage_channels=True, manage_roles=True)
    @checks.has_perms(administrator=True)
    async def lock(self, ctx, channel=None, minutes_: int = None):
        """
        Usage: -lock [channel] [minutes]
        Aliases: -lockdown, -lockchannel
        Permission: Administrator
        Output:
            Locked channel for the specified time. Infinite if not specified
        Notes:
            Max timed lock is 2 hours
        """
        if channel is None:
            channel_obj = ctx.channel
        else:
            try:
                channel_obj = await commands.TextChannelConverter().convert(
                    ctx, channel
                )
            except commands.ChannelNotFound:
                channel_obj = ctx.channel
                if channel.isdigit():
                    minutes_ = int(channel)
                else:
                    minutes_ = None
        try:
            channel = channel_obj
            overwrites_everyone = channel.overwrites_for(ctx.guild.default_role)
            my_overwrites = channel.overwrites_for(ctx.guild.me)
            everyone_overwrite_current = overwrites_everyone.send_messages
            msg = await ctx.send_or_reply(
                content=f"Locking channel {channel.mention}...",
            )
            try:
                await self.bot.cxn.execute(
                    "INSERT INTO lockedchannels VALUES ($1, $2, $3, $4)",
                    channel.id,
                    ctx.guild.id,
                    ctx.author.id,
                    str(everyone_overwrite_current),
                )
            except asyncpg.UniqueViolationError:
                return await msg.edit(
                    content=f"{self.bot.emote_dict['failed']} Channel {channel.mention} is already locked."
                )

            my_overwrites.send_messages = True
            overwrites_everyone.send_messages = False
            await ctx.message.channel.set_permissions(
                ctx.guild.default_role,
                overwrite=overwrites_everyone,
                reason=(
                    utils.responsible(ctx.author, "Channel locked by command execution")
                ),
            )
            if minutes_:
                if minutes_ > 120:
                    raise commands.BadArgument("Max timed lock is 120 minutes.")
                elif minutes_ < 0:
                    raise commands.BadArgument("Minutes must be greater than 0.")
                minutes = minutes_

                await msg.edit(
                    content=f"{self.bot.emote_dict['lock']} Channel {channel.mention} locked for `{minutes}` minute{'' if minutes == 1 else 's'}. ID: `{channel.id}`"
                )
                await asyncio.sleep(minutes * 60)
                await self.unlock(ctx, channel=channel, surpress=True)
            else:
                await msg.edit(
                    content=f"{self.bot.emote_dict['lock']} Channel {channel.mention} locked. ID: `{channel.id}`"
                )
        except discord.Forbidden:
            await msg.edit(
                content=f"{self.bot.emote_dict['failed']} I have insufficient permission to lock channels."
            )

    @decorators.command(brief="Unlock a channel.", aliases=["unlockchannel"])
    @commands.guild_only()
    @checks.bot_has_perms(manage_channels=True)
    @checks.has_perms(administrator=True)
    async def unlock(self, ctx, channel: discord.TextChannel = None, surpress=False):
        """
        Usage: -unlock [channel]
        Alias: -unlockchannel
        Permission: Administrator
        Output: Unlocks a previously locked channel
        """
        if channel is None:
            channel = ctx.channel
        try:
            locked = (
                await self.bot.cxn.fetchrow(
                    "SELECT channel_id FROM lockedchannels WHERE channel_id = $1",
                    channel.id,
                )
                or (None)
            )
            if locked is None:
                if surpress is True:
                    return
                else:
                    return await ctx.send_or_reply(
                        f"{self.bot.emote_dict['lock']} Channel {channel.mention} is already unlocked. ID: `{channel.id}`"
                    )

            msg = await ctx.send_or_reply(
                content=f"Unlocking channel {channel.mention}...",
            )
            old_overwrites = await self.bot.cxn.fetchrow(
                "SELECT everyone_perms FROM lockedchannels WHERE channel_id = $1",
                channel.id,
            )
            everyone_perms = old_overwrites[0]

            if everyone_perms == "None":
                everyone_perms = None
            elif everyone_perms == "False":
                everyone_perms = False
            elif everyone_perms == "True":
                everyone_perms = True

            overwrites_everyone = ctx.channel.overwrites_for(ctx.guild.default_role)
            overwrites_everyone.send_messages = everyone_perms
            await ctx.message.channel.set_permissions(
                ctx.guild.default_role,
                overwrite=overwrites_everyone,
                reason=(
                    utils.responsible(
                        ctx.author, "Channel unlocked by command execution"
                    )
                ),
            )
            await self.bot.cxn.execute(
                "DELETE FROM lockedchannels WHERE channel_id = $1", channel.id
            )
            await msg.edit(
                content=f"{self.bot.emote_dict['unlock']} Channel {channel.mention} unlocked. ID: `{channel.id}`"
            )
        except discord.errors.Forbidden:
            await msg.edit(
                content=f"{self.bot.emote_dict['failed']} I have insufficient permission to unlock channels."
            )
