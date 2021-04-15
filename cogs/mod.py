import io
import re
import typing
import asyncio
import asyncpg
import discord

from collections import Counter
from discord.ext import commands
from datetime import datetime, timedelta
from better_profanity import profanity

from utilities import permissions, utils, converters, pagination
from settings import database


def setup(bot):
    bot.add_cog(Moderation(bot))


class Moderation(commands.Cog):
    """
    Keep your server under control.
    """

    def __init__(self, bot):
        self.bot = bot

        self.emote_dict = bot.emote_dict
        self.mention_re = re.compile(r"[0-9]{17,21}")

    ###################
    ## Mute Commands ##
    ###################

    @commands.command(
        brief="Mute users for misbehaving.", aliases=["hackmute", "hardmute"]
    )
    @commands.guild_only()
    @permissions.has_permissions(kick_members=True)
    async def mute(
        self,
        ctx,
        targets: commands.Greedy[discord.Member],
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
            messages in any channel except for messages in #muted
            (if still exists). Roles will be given back to the user
            upon -unmute, or when their timed mute ends.
        """
        global target
        if not len(targets):
            return await ctx.send(
                f"Usage: `{ctx.prefix}mute <target> [target]... [minutes] [reason]`"
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
                    return await ctx.send(
                        f"use `{ctx.prefix}muterole <role>` to initialize the muted role."
                    )
                self.mute_role = ctx.guild.get_role(int(self.mute_role))
            except Exception as e:
                print("really?")
                return await ctx.send(e)
            muted = []
            for target in targets:
                if target.bot:
                    await ctx.send(
                        f"{self.bot.emote_dict['failed']} I cannot mute bots."
                    )
                    continue
                if not self.mute_role in target.roles:
                    role_ids = ",".join([str(r.id) for r in target.roles])
                    end_time = (
                        datetime.utcnow() + timedelta(seconds=minutes * 60)
                        if minutes
                        else None
                    )
                    if target.id in self.bot.constants.owners:
                        return await ctx.send(
                            reference=self.bot.rep_ref(ctx),
                            content="You cannot mute my developer.",
                        )
                    if target.id == ctx.author.id:
                        return await ctx.send(
                            "I don't think you really want to mute yourself..."
                        )
                    if target.id == self.bot.user.id:
                        return await ctx.send(
                            reference=self.bot.rep_ref(ctx),
                            content="I don't think I want to mute myself...",
                        )
                    if (
                        target.guild_permissions.kick_members
                        and ctx.author.id != ctx.guild.owner.id
                    ):
                        return await ctx.send(
                            reference=self.bot.rep_ref(ctx),
                            content="You cannot punish other staff members.",
                        )
                    if ctx.guild.me.top_role.position < target.top_role.position:
                        return await ctx.send(
                            f"My highest role is below `{target}'s` highest role. Aborting mute."
                        )

                    if ctx.guild.me.top_role.position == target.top_role.position:
                        return await ctx.send(
                            f"I have the same permissions as `{target}`. Aborting mute."
                        )
                    if ctx.guild.me.top_role.position < self.mute_role.position:
                        return await ctx.send(
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
                        return await ctx.send(e)
                    try:
                        await target.edit(roles=[self.mute_role])
                        muted.append(target)
                    except Exception as e:
                        return await ctx.send(e)
                    if reason:
                        try:
                            await target.send(
                                f"<:announce:807097933916405760> You have been muted in **{ctx.guild.name}** {reason}. Mute duration: `{minutes if minutes is not None else 'Infinite'} minute{'' if minutes == 1 else 's'}`"
                            )
                        except Exception:
                            return
                    global unmutereason
                    unmutereason = reason

                    if minutes:
                        unmutes.append(target)
                else:
                    await ctx.send(
                        f"{self.emote_dict['error']} Member `{target.display_name}` is already muted."
                    )
            if muted:
                allmuted = []
                for member in muted:
                    users = []
                    people = await self.bot.fetch_user(int(member.id))
                    users.append(people)
                    for user in users:
                        username = f"{user.name}#{user.discriminator}"
                        allmuted += [username]
                if minutes is None:
                    msg = f'{self.bot.emote_dict["success"]} Muted `{", ".join(allmuted)}` indefinetely'
                else:
                    msg = f'{self.bot.emote_dict["success"]} Muted `{", ".join(allmuted)}` for {minutes:,} minute{"" if minutes == 1 else "s"}'
                await ctx.send(msg)
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
            return await ctx.send(e)
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
                    unmuted.append(target)
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
                unmuted.append(target)
                if unmutereason:
                    try:
                        await target.send(
                            f"<:announce:807097933916405760> You have been unmuted in **{ctx.guild.name}**"
                        )
                    except Exception:
                        return

            else:
                return await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content=f"{self.emote_dict['error']} Member is not muted",
                )

        if unmuted:
            allmuted = []
            for member in unmuted:
                users = []
                people = await self.bot.fetch_user(int(member.id))
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    allmuted += [username]
            await ctx.send(
                f'{self.bot.emote_dict["success"]} Unmuted `{", ".join(allmuted)}`'
            )
            self.bot.dispatch("mod_action", ctx, targets=allmuted)

    @commands.command(
        name="unmute", brief="Unmute previously muted members.", aliases=["endmute"]
    )
    @commands.guild_only()
    @permissions.bot_has_permissions(manage_roles=True)
    @permissions.has_permissions(kick_members=True)
    async def unmute_members(self, ctx, targets: commands.Greedy[discord.Member]):
        """
        Usage: -unmute <target> [target]...
        Alias: -endmute
        Example: -unmute Hecate @Elizabeth 708584008065351681
        Permissiom: Kick Members
        Output: Unmutes members muted by the -hardmute command.
        """
        if not len(targets):
            await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"Usage: `{ctx.prefix}unmute <target> [target]...`",
            )

        else:
            await self.unmute(ctx, targets)

    ##########################
    ## Restriction Commands ##
    ##########################

    @commands.command(brief="Restrict users from sending messages.")
    @commands.guild_only()
    @permissions.has_permissions(kick_members=True)
    async def block(self, ctx, targets: commands.Greedy[discord.Member]):
        """
        Usage:      -block <target> [target]...
        Example:    -block Hecate 708584008065351681 @Elizabeth
        Permission: Kick Members
        Output:     Stops users from messaging in the channel.
        """
        if not len(targets):  # checks if there is user
            return await ctx.send(
                f"Usage: `{ctx.prefix}block <target> [target] [target]...`"
            )
        blocked = []
        for target in targets:
            if (
                ctx.author.id not in self.bot.constants.owners
                and ctx.author.id != ctx.guild.owner.id
                and not ctx.author.guild_permissions.kick_members
            ):
                return await ctx.send(
                    "You have insufficient permission to execute that command."
                )
            if target.id in self.bot.constants.owners:
                return await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content="You cannot block my master.",
                )
            if target.id == ctx.author.id:
                return await ctx.send(
                    "I don't think you really want to block yourself..."
                )
            if target.id == self.bot.user.id:
                return await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content="I don't think I want to block myself...",
                )
            if (
                target.guild_permissions.kick_members
                and ctx.author.id not in self.bot.constants.owners
                and ctx.author.id != ctx.guild.owner.id
            ):
                return await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content="You cannot punish other staff members.",
                )
            try:
                await ctx.channel.set_permissions(
                    target, send_messages=False
                )  # gives back send messages permissions
                blocked.append(target)
            except Exception:
                await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content="`{0}` could not me block".format(target),
                )
        if blocked:
            blocked_users = []
            for unblind in blocked:
                users = []
                people = await self.bot.fetch_user(int(unblind.id))
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    blocked_users += [username]
            await ctx.send(
                "<:checkmark:816534984676081705> Blocked `{0}`".format(
                    ", ".join(blocked_users)
                )
            )
            self.bot.dispatch("mod_action", ctx, targets=blocked_users)

    @commands.command(brief="Reallow users to send messages.")
    @commands.guild_only()
    @permissions.has_permissions(kick_members=True)
    async def unblock(self, ctx, targets: commands.Greedy[discord.Member] = None):
        """
        Usage:      -unblock <target> [target]...
        Example:    -unblock Hecate 708584008065351681 @Elizabeth
        Permission: Kick Members
        Output:     Reallows blocked users to send messages.
        """
        if not targets:  # checks if there is user
            return await ctx.send(
                f"Usage: `{ctx.prefix}unblock <target> [target] [target]...`"
            )
        unblocked = []
        for target in targets:
            if (
                ctx.author.id not in self.bot.constants.owners
                and ctx.author.id != ctx.guild.owner.id
                and not ctx.author.guild_permissions.kick_members
            ):
                return await ctx.send(
                    "You have insufficient permission to execute that command."
                )
            if target.id in self.bot.constants.owners:
                return await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content="You cannot unblock my master.",
                )
            if target.id == ctx.author.id:
                return await ctx.send(
                    "I don't think you really want to unblock yourself..."
                )
            if target.id == self.bot.user.id:
                return await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content="I don't think I want to unblock myself...",
                )
            if (
                target.guild_permissions.kick_members
                and ctx.author.id not in self.bot.constants.owners
                and ctx.author.id != ctx.guild.owner.id
            ):
                return await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content="You cannot punish other staff members.",
                )
            try:
                await ctx.channel.set_permissions(
                    target, send_messages=None
                )  # gives back send messages permissions
                unblocked.append(target)
            except Exception:
                await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content="`{0}` could not me unblock".format(target),
                )
        if unblocked:
            unblocked_users = []
            for unblind in unblocked:
                users = []
                people = await self.bot.fetch_user(int(unblind.id))
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    unblocked_users += [username]
            await ctx.send(
                "<:checkmark:816534984676081705> Unblocked `{0}`".format(
                    ", ".join(unblocked_users)
                )
            )
            self.bot.dispatch("mod_action", ctx, targets=unblocked_users)

    @commands.command(brief="Hide a channel from a user.")
    @commands.guild_only()
    @permissions.has_permissions(kick_members=True)
    async def blind(self, ctx, targets: commands.Greedy[discord.Member] = None):
        """
        Usage:      -blind <target> [target]...
        Example:    -blind Hecate 708584008065351681 @Elizabeth
        Permission: Kick Members
        Output:     Prevents users from seeing the channel.
        """
        if not targets:  # checks if there is user
            return await ctx.send(
                f"Usage: `{ctx.prefix}blind <target> [target] [target]...`"
            )
        blinded = []
        for target in targets:
            if (
                ctx.author.id not in self.bot.constants.owners
                and ctx.author.id != ctx.guild.owner.id
                and not ctx.author.guild_permissions.kick_members
            ):
                return await ctx.send(
                    "You have insufficient permission to execute that command."
                )
            if target.id in self.bot.constants.owners:
                return await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content="You cannot blind my master.",
                )
            if target.id == ctx.author.id:
                return await ctx.send(
                    "I don't think you really want to blind yourself..."
                )
            if target.id == self.bot.user.id:
                return await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content="I don't think I want to blind myself...",
                )
            if (
                target.guild_permissions.kick_members
                and ctx.author.id not in self.bot.constants.owners
                and ctx.author.id != ctx.guild.owner.id
            ):
                return await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content="You cannot punish other staff members.",
                )
            try:
                await ctx.channel.set_permissions(
                    target, send_messages=False, read_messages=False
                )  # gives back send messages permissions
                blinded.append(target)
            except Exception:
                await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content="`{0}` could not me blinded".format(target),
                )
        if blinded:
            blinded_users = []
            for unblind in blinded:
                users = []
                people = await self.bot.fetch_user(int(unblind.id))
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    blinded_users += [username]
            await ctx.send(
                "<:checkmark:816534984676081705> Blinded `{0}`".format(
                    ", ".join(blinded_users)
                )
            )
            self.bot.dispatch("mod_action", ctx, targets=blinded_users)

    @commands.command(brief="Reallow users see a channel.")
    @commands.guild_only()
    @permissions.has_permissions(kick_members=True)
    async def unblind(self, ctx, targets: commands.Greedy[discord.Member] = None):
        """
        Usage:      -unblind <target> [target]...
        Example:    -unblind Hecate 708584008065351681 @Elizabeth
        Permission: Kick Members
        Output:     Reallows blinded users to see the channel.
        """
        if not targets:  # checks if there is user
            return await ctx.send(
                f"Usage: `{ctx.prefix}unblind <target> [target] [target]...`"
            )
        unblinded = []
        for target in targets:
            if (
                ctx.author.id not in self.bot.constants.owners
                and ctx.author.id != ctx.guild.owner.id
                and not ctx.author.guild_permissions.kick_members
            ):
                return await ctx.send(
                    "You have insufficient permission to execute that command."
                )
            if target.id in self.bot.constants.owners:
                return await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content="You cannot unblind my master.",
                )
            if target.id == ctx.author.id:
                return await ctx.send(
                    "I don't think you really want to unblind yourself..."
                )
            if target.id == self.bot.user.id:
                return await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content="I don't think I want to unblind myself...",
                )
            if (
                target.guild_permissions.kick_members
                and ctx.author.id not in self.bot.constants.owners
                and ctx.author.id != ctx.guild.owner.id
            ):
                return await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content="You cannot punish other staff members.",
                )
            try:
                await ctx.channel.set_permissions(
                    target, send_messages=None, read_messages=None
                )  # gives back send messages permissions
                unblinded.append(target)
            except Exception:
                await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content="`{0}` could not me unblinded".format(target),
                )
        if unblinded:
            unblinded_users = []
            for unblind in unblinded:
                users = []
                people = await self.bot.fetch_user(int(unblind.id))
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    unblinded_users += [username]
            await ctx.send(
                "<:checkmark:816534984676081705> Unblinded `{0}`".format(
                    ", ".join(unblinded_users)
                )
            )
            self.bot.dispatch("mod_action", ctx, targets=unblinded_users)

    ##################
    ## Kick Command ##
    ##################

    @commands.command(brief="Kick users from the server.")
    @commands.guild_only()
    @permissions.bot_has_permissions(kick_members=True)
    @permissions.has_permissions(kick_members=True)
    async def kick(
        self,
        ctx,
        users: commands.Greedy[discord.Member],
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
            return await ctx.send(
                f"Usage: `{ctx.prefix}kick <target> [target]... [reason]`"
            )

        if await permissions.checker(ctx, value=users):
            return
        kicked = []
        immune = []
        for target in users:
            try:
                await ctx.guild.kick(target, reason=reason)
                kicked.append(f"{target.name}#{target.discriminator}")
            except Exception:
                immune.append(f"{target.name}#{target.discriminator}")
                continue
        if kicked:
            await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"{self.emote_dict['success']} Kicked `{', '.join(kicked)}`",
            )
            self.bot.dispatch("mod_action", ctx, targets=kicked)
        if immune:
            await ctx.send(
                f"{self.emote_dict['failed']} Failed to kick `{', '.join(immune)}`"
            )

    ##################
    ## Ban Commands ##
    ##################

    @commands.command(brief="Ban users from the server.")
    @commands.guild_only()
    @permissions.bot_has_permissions(ban_members=True)
    @permissions.has_permissions(ban_members=True)
    async def ban(
        self,
        ctx,
        targets: commands.Greedy[discord.Member],
        delete_message_days=None,
        *,
        reason: typing.Optional[str] = "No reason",
    ):
        """
        Usage:      -ban <target> [target]... [delete message days = 1] [reason]
        Example:    -ban @Jacob Sarah 4 for advertising
        Permission: Ban Members
        Output:     Ban passed members from the server.
        """
        if not len(targets):
            return await ctx.send(
                f"Usage: `{ctx.prefix}ban <target1> [target2] [delete message days] [reason]`"
            )

        if await permissions.checker(ctx, value=targets):
            return

        if delete_message_days:
            if not delete_message_days.isdigit():
                if reason == "No reason":
                    reason = str(delete_message_days)
                else:
                    reason = str(delete_message_days) + " " + reason
                delete_message_days = 1
            else:
                delete_message_days = int(delete_message_days)
                if delete_message_days > 7:
                    delete_message_days = 7
                elif delete_message_days < 0:
                    delete_message_days = 0
                else:
                    delete_message_days = 1
        else:
            delete_message_days = 1

        banned = []
        immune = []
        for target in targets:
            try:
                await ctx.guild.ban(
                    target, reason=reason, delete_message_days=delete_message_days
                )
                banned.append(f"{target.name}#{target.discriminator}")
            except Exception:
                immune.append(f"{target.name}#{target.discriminator}")
                continue
        if banned:
            await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"{self.emote_dict['success']} Banned `{', '.join(banned)}`",
            )
            self.bot.dispatch("mod_action", ctx, targets=banned)
        if immune:
            await ctx.send(
                f"{self.emote_dict['failed']} Failed to ban `{', '.join(immune)}`"
            )

    @commands.command(brief="Softban users from the server.")
    @commands.guild_only()
    @permissions.bot_has_permissions(ban_members=True)
    @permissions.has_permissions(kick_members=True)
    async def softban(
        self,
        ctx,
        targets: commands.Greedy[discord.Member],
        delete_message_days=None,
        *,
        reason: str = "No reason",
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
            return await ctx.send(
                f"Usage: `{ctx.prefix}softban <member> [days to delete messages] [reason]`"
            )

        if await permissions.checker(ctx, value=targets):
            return

        if delete_message_days:
            if not delete_message_days.isdigit():
                if reason == "No reason":
                    reason = str(delete_message_days)
                else:
                    reason = str(delete_message_days) + " " + reason
                delete_message_days = 7
            else:
                delete_message_days = int(delete_message_days)
                if delete_message_days > 7:
                    delete_message_days = 7
                elif delete_message_days < 0:
                    delete_message_days = 0
                else:
                    delete_message_days = 7
        else:
            delete_message_days = 7

        banned = []
        immune = []
        for target in targets:
            try:
                await ctx.guild.ban(
                    target, reason=reason, delete_message_days=delete_message_days
                )
                await ctx.guild.unban(target, reason=reason)
                banned.append(f"{target.name}#{target.discriminator}")
            except Exception:
                immune.append(f"{target.name}#{target.discriminator}")
                continue
        if banned:
            await ctx.send(
                f"{self.emote_dict['success']} Softbanned `{', '.join(banned)}`"
            )
            self.bot.dispatch("mod_action", ctx, targets=banned)
        if immune:
            await ctx.send(
                f"{self.emote_dict['failed']} Failed to softban `{', '.join(immune)}`"
            )

    @commands.command(brief="Hackban multiple users by ID.")
    @permissions.bot_has_permissions(ban_members=True)
    @permissions.has_permissions(manage_guild=True)
    async def hackban(self, ctx, *users: str):
        """
        Usage:      -hackban <id> [id] [id]...
        Example:    -hackban 805871188462010398 243507089479579784
        Permission: Manage Server
        Output:     Hackbans multiple users by ID.
        Notes:      Users do not have to be in the server."""
        if not users:
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"Usage: `{ctx.prefix}hackban <id> [id] [id]...`",
            )
        banned = []
        for user in users:
            try:
                u = ctx.guild.get_member(int(user))
                if (
                    u.guild_permissions.kick_members
                    and ctx.author.id not in self.bot.constants.owners
                    and ctx.author.id != ctx.guild.owner.id
                ):
                    return await ctx.send(
                        reference=self.bot.rep_ref(ctx),
                        content="You cannot punish other staff members.",
                    )
            except Exception:
                try:
                    u = discord.Object(id=user)
                except TypeError:
                    return await ctx.send(
                        f"{self.bot.emote_dict['failed']} User snowflake must be integer. Ex: 708584008065351681."
                    )
            if (
                ctx.author.id not in self.bot.constants.owners
                and not ctx.author.guild_permissions.manage_guild
            ):
                return await ctx.send(
                    "You have insufficient permission to execute that command."
                )
            if u.id in self.bot.constants.owners:
                return await ctx.send(
                    f"{self.bot.emote_dict['failed']} You cannot hackban my creator."
                )
            if u.id == ctx.author.id:
                return await ctx.send(
                    f"I don't think you really want to hackban yourself..."
                )
            if u.id == self.bot.user.id:
                return await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content="I don't think I want to hackban myself...",
                )
            try:
                await ctx.guild.ban(
                    u,
                    reason=f"Hackban executed by {ctx.author}",
                    delete_message_days=7,
                )
                banned.append(user)
            except Exception:
                uu = ctx.message.guild.get_member(user)
                if uu is None:
                    await ctx.send(
                        f"{self.bot.emote_dict['failed']} `{user}` could not be hackbanned."
                    )
                else:
                    await ctx.send(
                        f"{self.bot.emote_dict['failed']} `{uu}` is already on the server and could not be hackbanned."
                    )
                continue
        if banned:
            hackbanned = []
            for ban in banned:
                users = []
                people = await self.bot.fetch_user(ban)
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    hackbanned += [username]
            await ctx.send(
                "{1} Hackbanned `{0}`".format(
                    ", ".join(hackbanned), self.bot.emote_dict["success"]
                )
            )
            self.bot.dispatch("mod_action", ctx, targets=hackbanned)

    @commands.command(brief="Unban a previously banned user.", aliases=["revokeban"])
    @commands.guild_only()
    @permissions.has_permissions(ban_members=True)
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
            return await ctx.send(
                f"Usage: `{ctx.prefix}unban <id/name#discriminator> [reason]`"
            )
        if reason is None:
            reason = utils.responsible(
                ctx.author, f"Unbanned member {member} by command execution"
            )

        await ctx.guild.unban(member.user, reason=reason)
        if member.reason:
            await ctx.send(
                f'{self.bot.emote_dict["success"]} Unbanned `{member.user} (ID: {member.user.id})`, previously banned for `{member.reason}.`'
            )
        else:
            await ctx.send(
                f'{self.bot.emote_dict["success"]} Unbanned `{member.user} (ID: {member.user.id}).`'
            )
        self.bot.dispatch("mod_action", ctx, targets=[str(member.user)])

    # https://github.com/AlexFlipnote/discord_bot.py

    ###################
    ## Prune Command ##
    ###################

    @commands.group(
        brief="Remove any type of content.", aliases=["purge", "delete", "remove"]
    )
    @commands.guild_only()
    @commands.max_concurrency(5, per=commands.BucketType.guild)
    @permissions.bot_has_permissions(manage_messages=True)
    @permissions.has_permissions(manage_messages=True)
    async def prune(self, ctx):
        """
        Usage:      -prune <method> <amount>
        Alias:      -purge, -delete, -remove
        Examples:   -prune user Hecate, -prune bots
        Output:     Deletes messages that match your method criteria
        Permission: Manage Messages
        Output:     Message removal within your search specification.
        Methods:
            all       Prune all messages
            bots      Prunes bots and their invoked commands
            contains  Prune messages that contain a substring
            embeds    Prunes all embeds
            files     Prunes all attachments
            humans    Prunes human messages
            images    Prunes all images
            mentions  Prunes all mentions
            reactions Prune all reactions from messages
            until     Prune until a given message ID
            user      Prune a user
        """
        args = str(ctx.message.content).split(" ")
        if ctx.invoked_subcommand is None:
            try:
                args[1]
            except IndexError:
                help_command = self.bot.get_command("help")
                return await help_command(ctx, invokercommand="prune")
            await self._remove_all(ctx, search=int(args[1]))

    async def do_removal(
        self, ctx, limit, predicate, *, before=None, after=None, message=True
    ):
        if limit > 2000:
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
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
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content="I do not have permissions to delete messages.",
            )
        except discord.HTTPException as e:
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"Error: {e} (try a smaller search?)",
            )

        deleted = len(deleted)
        if message is True:
            msg = await ctx.send(
                f'{self.bot.emote_dict["trash"]} Deleted {deleted} message{"" if deleted == 1 else "s"}'
            )
            await asyncio.sleep(7)
            await ctx.message.delete()
            await msg.delete()

    @prune.command()
    async def embeds(self, ctx, search=100):
        """Removes messages that have embeds in them."""
        await self.do_removal(ctx, search, lambda e: len(e.embeds))

    @prune.command()
    async def files(self, ctx, search=100):
        """Removes messages that have attachments in them."""
        await self.do_removal(ctx, search, lambda e: len(e.attachments))

    @prune.command()
    async def mentions(self, ctx, search=100):
        """Removes messages that have mentions in them."""
        await self.do_removal(
            ctx, search, lambda e: len(e.mentions) or len(e.role_mentions)
        )

    @prune.command()
    async def images(self, ctx, search=100):
        """Removes messages that have embeds or attachments."""
        await self.do_removal(
            ctx, search, lambda e: len(e.embeds) or len(e.attachments)
        )

    @prune.command(name="all")
    async def _remove_all(self, ctx, search=100):
        """Removes all messages."""
        await self.do_removal(ctx, search, lambda e: True)

    @prune.command()
    async def user(self, ctx, member: discord.Member, search=100):
        """Removes all messages by the member."""
        await self.do_removal(ctx, search, lambda e: e.author == member)

    @prune.command()
    async def contains(self, ctx, *, substr: str):
        """Removes all messages containing a substring.
        The substring must be at least 2 characters long.
        """
        if len(substr) < 2:
            await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content="The substring length must be at least 3 characters.",
            )
        else:
            await self.do_removal(ctx, 100, lambda e: substr in e.content)

    async def get_server_prefixes(self, guild):
        prefixes = self.bot.server_settings[guild.id]["prefixes"]
        if prefixes == []:
            prefixes.append(self.bot.constants.prefix)
        prefixes.append(f"<@{self.bot.constants.client}")
        prefixes.append(f"<@!{self.bot.constants.client}")
        return prefixes

    @prune.command(name="bots")
    async def _bots(self, ctx, search=100, prefix=None):
        """Removes a bot user's messages and messages with their optional prefix."""

        if prefix:

            def predicate(m):
                return (m.webhook_id is None and m.author.bot) or m.content.startswith(
                    prefix
                )

        else:

            def predicate(m):
                return m.webhook_id is None and m.author.bot

        await self.do_removal(ctx, search, predicate)

    @prune.command(name="webhooks", aliases=["webhook"])
    async def webhooks(self, ctx, search=100):
        """Removes a webhook's messages."""

        def predicate(m):
            return m.webhook_id

        await self.do_removal(ctx, search, predicate)

    @prune.command(name="humans", aliases=["users"])
    async def _users(self, ctx, search=100, prefix=None):
        """Removes only user messages. """

        def predicate(m):
            return m.author.bot is False

        await self.do_removal(ctx, search, predicate)

    @prune.command(name="emojis", aliases=["emotes"])
    async def _emojis(self, ctx, search=100):
        """Removes all messages containing custom emoji."""
        custom_emoji = re.compile(r"<a?:(.*?):(\d{17,21})>|[\u263a-\U0001f645]")

        def predicate(m):
            return custom_emoji.search(m.content)

        await self.do_removal(ctx, search, predicate)

    @prune.command(name="reactions")
    async def _reactions(self, ctx, search=100):
        """Removes all reactions from messages that have them."""

        if search > 2000:
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"Too many messages to search for ({search}/2000)",
            )

        total_reactions = 0
        async for message in ctx.history(limit=search, before=ctx.message):
            if len(message.reactions):
                total_reactions += sum(r.count for r in message.reactions)
                await message.clear_reactions()
        await ctx.send(
            f'{self.bot.emote_dict["trash"]} Successfully removed {total_reactions} reactions.',
            delete_after=7,
        )

    @prune.command(name="until", aliases=["after"])
    async def _until(self, ctx, message_id: int):
        """Prune messages in a channel until the given message_id. Given ID is not deleted"""
        channel = ctx.message.channel
        try:
            message = await channel.fetch_message(message_id)
        except commands.errors.NotFound:
            await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content="Message could not be found in this channel",
            )
            return

        await ctx.message.delete()
        await channel.purge(after=message)
        return True

    async def get_server_prefixes(self, guild):
        prefixes = self.bot.server_settings[guild.id]["prefixes"].copy()
        if prefixes == []:
            prefixes.append(self.bot.constants.prefix)
        prefixes.append(f"<@!{self.bot.constants.client}>")
        prefixes.append(f"<@{self.bot.constants.client}>")
        return prefixes

    async def cleanup_strategy(self, ctx, search):
        prefixes = tuple(await self.get_server_prefixes(ctx.guild))

        def check(m):
            return m.author == ctx.me or m.content.startswith(prefixes)

        deleted = await ctx.channel.purge(limit=search, check=check, before=ctx.message)
        return Counter(str(m.author) for m in deleted)

    @commands.command(brief="Clean up command usage.", search=200, aliases=["clean"])
    @commands.guild_only()
    @permissions.bot_has_permissions(manage_messages=True)
    @permissions.has_permissions(manage_messages=True)
    async def cleanup(self, ctx, search=100):
        """
        Usage: -cleanup [search]
        Alias: -clean
        Output: Cleans up the bot's messages from the channel.
        Permission: Manage Messages
        Notes:
            If a search number is specified, it searches that many messages to delete.
            If the bot has Manage Messages permissions then it will try to delete
            messages that look like they invoked the bot as well.
            After the cleanup is completed, the bot will send you a message with
            which people got their messages deleted and their count. This is useful
            to see which users are spammers.
        """
        strategy = self.cleanup_strategy

        spammers = await strategy(ctx, search)
        deleted = sum(spammers.values())
        messages = [
            f'**{self.bot.emote_dict["trash"]} {deleted} message{" was" if deleted == 1 else "s were"} deleted.**'
        ]
        if deleted:
            messages.append("")
            spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
            messages.extend(f"`{author}`: {count}" for author, count in spammers)
        desc = "\n".join(messages)
        em = discord.Embed()
        em.color = self.bot.constants.embed
        em.description = desc

        await ctx.send(reference=self.bot.rep_ref(ctx), embed=em, delete_after=10)

    #########################
    ## Profanity Listeners ##
    #########################

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if self.bot.bot_ready is False:
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
        if self.bot.bot_ready is False:
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
