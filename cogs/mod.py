import re
import typing
import asyncio
import asyncpg
import discord

from better_profanity import profanity
from collections import Counter
from datetime import datetime, timedelta
from discord.ext import commands

from settings import database
from utilities import converters, permissions, utils, helpers


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

    @commands.command(brief="Move a user from a voice channel.")
    @commands.guild_only()
    @permissions.bot_has_permissions(move_members=True)
    @permissions.has_permissions(move_members=True)
    async def vcmove(
        self, ctx, targets: commands.Greedy[discord.Member] = None, channel: discord.VoiceChannel = None
    ):
        """
        Usage: -vcmove <target> <target>... <channel>
        Output: Moves members into a new voice channel
        Permission: Move Members
        """
        if not targets:
            return await ctx.send_or_reply(content=f"Usage: `{ctx.prefix}vc move <to channel> <target> [target]...`",
            )
        if not channel:
            return await ctx.send_or_reply(content=f"Usage: `{ctx.prefix}vc move <to channel> <target> [target]...`",
            )
        vcmoved = []
        for target in targets:
            try:
                await target.edit(voice_channel=channel)
            except discord.HTTPException:
                await ctx.send_or_reply(
                    content=f"{self.bot.emote_dict['error']} Target is not connected to a voice channel"
                )
                continue
            vcmoved.append(str(target))
        if vcmoved:
            await ctx.send_or_reply(content=f"{self.bot.emote_dict['success']} VC Moved `{', '.join(vcmoved)}`"
            )

    @commands.command(brief="Kick all users from a voice channel.")
    @commands.guild_only()
    @permissions.has_permissions(move_members=True)
    @permissions.bot_has_permissions(move_members=True)
    async def vcpurge(self, ctx, channel: discord.VoiceChannel = None):
        """
        Usage: -vcpurge <voice channel>
        Output: Kicks all members from the channel
        Permission: Move Members
        """
        if channel is None:
            return await ctx.send_or_reply(content=f"Usage: `{ctx.prefix}vcpurge <voice channel name/id>`",
            )
        if len(channel.members) == 0:
            return await ctx.send_or_reply(content=f"{self.bot.emote_dict['error']} No members in voice channel {channel.mention}.",
            )
        failed = []
        for member in channel.members:
            try:
                await member.edit(voice_channel=None)
            except Exception:
                failed.append(str(member))
                continue
        await ctx.send_or_reply(
            content=f"{self.bot.emote_dict['success']} Purged {channel.mention}.",
        )
        if failed:
            await ctx.send_or_reply(content=f"{self.bot.emote_dict['success']} Failed to vckick {len(failed)} user{'' if len(failed) == 1 else 's'}.",
            )

    @commands.command(brief="Kick users from a voice channel.")
    @commands.guild_only()
    @permissions.has_permissions(move_members=True)
    @permissions.bot_has_permissions(move_members=True)
    async def vckick(self, ctx, targets: commands.Greedy[discord.Member]):
        """
        Usage: -vckick <target> <target>..
        Output: Kicks passed members from their channel
        Permission: Move Members
        """
        if not len(targets):
            return await ctx.send_or_reply(content=f"Usage: `{ctx.prefix}vckick <target> [target]...`",
            )
        vckicked = []
        for target in targets:
            try:
                await target.edit(voice_channel=None)
            except discord.HTTPException:
                await ctx.send_or_reply(
                    f"{self.bot.emote_dict['error']} Target is not connected to a voice channel."
                )
            vckicked.append(str(target))
        if vckicked:
            await ctx.send_or_reply(content=f"{self.bot.emote_dict['success']} VC Kicked `{', '.join(vckicked)}`"
            )

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
            messages in any channel. Roles will be given back to
            the user upon -unmute, or when their timed mute ends.
        """
        global target
        if not len(targets):
            return await ctx.send_or_reply(content=f"Usage: `{ctx.prefix}mute <target> [target]... [minutes] [reason]`",
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
                        f"{self.bot.emote_dict['error']} Member `{target.display_name}` is already muted."
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
                    content=f"{self.bot.emote_dict['error']} Member is not muted",
                )

        if unmuted:
            await ctx.send_or_reply(content=f'{self.bot.emote_dict["success"]} Unmuted `{", ".join(unmuted)}`',
            )
            self.bot.dispatch("mod_action", ctx, targets=unmuted)

    @commands.command(name="unmute",
                      brief="Unmute previously muted members.",
                      aliases=["endmute"])
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
            await ctx.send_or_reply(content=f"Usage: `{ctx.prefix}unmute <target> [target]...`",
            )

        else:
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
            res = await permissions.check_priv(ctx, target)
            if res:
                failed.append((str(target), res))
                continue
            try:
                await ctx.channel.set_permissions(
                    target, overwrite=overwrite
                )
                restrict.append(str(target))
            except Exception as e:
                failed.append((str(target), e))
                continue
        if restrict:
            await ctx.send_or_reply(content=f"{self.bot.emote_dict['success']} {ctx.command.name.capitalize()}ed `{', '.join(restrict)}`"
            )
            self.bot.dispatch("mod_action", ctx, targets=restrict)
        if failed:
            await helpers.error_info(ctx, failed)

    @commands.command(brief="Restrict users from sending messages.")
    @commands.guild_only()
    @permissions.has_permissions(kick_members=True)
    async def block(self, ctx, targets: commands.Greedy[discord.Member]):
        """
        Usage: -block <target> [target]...
        Example: -block Hecate 708584008065351681 @Elizabeth
        Permission: Kick Members
        Output: Stops users from messaging in the channel.
        """
        if not len(targets):
            return await ctx.send_or_reply(content=f"Usage: `{ctx.prefix}block <target> [target] [target]...`",
            )
        await self.restrictor(ctx, targets, "on", "block")

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
            return await ctx.send_or_reply(content=f"Usage: `{ctx.prefix}unblock <target> [target] [target]...`",
            )
        await self.restrictor(ctx, targets, "off", "unblock")

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
            return await ctx.send_or_reply(content=f"Usage: `{ctx.prefix}blind <target> [target] [target]...`",
            )
        await self.restrictor(ctx, targets, "on", "blind")

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
            return await ctx.send_or_reply(content=f"Usage: `{ctx.prefix}unblind <target> [target] [target]...`",
            )
        await self.restrictor(ctx, targets, "off", "unblind")

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
            return await ctx.send_or_reply(content=f"Usage: `{ctx.prefix}kick <target> [target]... [reason]`",
            )

        kicked = []
        failed = []
        for target in users:
            res = await permissions.check_priv(ctx, target)
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
            await ctx.send_or_reply(content=f"{self.bot.emote_dict['success']} Kicked `{', '.join(kicked)}`",
            )
            self.bot.dispatch("mod_action", ctx, targets=kicked)
        if failed:
            await helpers.error_info(ctx, failed)
            

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
            return await ctx.send_or_reply(content=f"Usage: `{ctx.prefix}ban <target1> [target2] [delete message days] [reason]`",
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
        failed = []
        for target in targets:
            res = permissions.check_priv(ctx, target)
            if res:
                failed.append((str(target), res))
                continue
            try:
                await ctx.guild.ban(
                    target, reason=reason, delete_message_days=delete_message_days
                )
                banned.append(str(target))
            except Exception as e:
                failed.append(str(target), e)
                continue
        if banned:
            await ctx.send_or_reply(content=f"{self.bot.emote_dict['success']} Banned `{', '.join(banned)}`",
            )
            self.bot.dispatch("mod_action", ctx, targets=banned)
        if failed:
            await helpers.error_info(ctx, failed)

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
            return await ctx.send_or_reply(content=f"Usage: `{ctx.prefix}softban <member> [days to delete messages] [reason]`",
            )

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
        failed = []
        for target in targets:
            res = await permissions.check_priv(ctx, target)
            if res:
                failed.append((str(target), res))
                continue
            try:
                await ctx.guild.ban(
                    target, reason=reason, delete_message_days=delete_message_days
                )
                await ctx.guild.unban(target, reason=reason)
                banned.append(str(target))
            except Exception as e:
                failed.append((str(target), e))
                continue
        if banned:
            await ctx.send_or_reply(content=f"{self.bot.emote_dict['success']} Softbanned `{', '.join(banned)}`",
            )
            self.bot.dispatch("mod_action", ctx, targets=banned)
        if failed:
            await helpers.error_info(ctx, failed)

    @commands.command(brief="Hackban multiple users by ID.")
    @permissions.bot_has_permissions(ban_members=True)
    @permissions.has_permissions(ban_members=True)
    async def hackban(self, ctx, *, users: commands.Greedy[discord.User]):
        """
        Usage: -hackban <id> [id] [id]...
        Example: -hackban 805871188462010398 243507089479579784
        Permission: Ban Members
        Output: Hackbans multiple users by ID.
        Notes: Users do not have to be in the server."""
        if not len(users):
            return await ctx.send_or_reply(content=f"Usage: `{ctx.prefix}hackban <id> [id] [id]...`",
            )
        banned = []
        failed = []
        for user in users:
            res = permissions.check_priv(ctx, user)
            if res:
                failed.append((str(user), res))
                continue
            try:
                await ctx.guild.ban(
                    user,
                    reason=f"Hackban executed by {ctx.author}",
                    delete_message_days=7,
                )
                banned.append(user)
            except Exception as e:
                failed.append((str(user), e))
                continue
        if banned:
            await ctx.send_or_reply(content=f"{self.bot.emote_dict['success']} Hackbanned `{', '.join(banned)}`"
            )
            self.bot.dispatch("mod_action", ctx, targets=banned)
        if failed:
            await helpers.error_info(ctx, failed)

    @commands.command(brief="Unban a previously banned user.",
                      aliases=["revokeban"])
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
            return await ctx.send_or_reply(content=f"Usage: `{ctx.prefix}unban <id/name#discriminator> [reason]`",
            )
        if reason is None:
            reason = utils.responsible(
                ctx.author, f"Unbanned member {member} by command execution"
            )

        await ctx.guild.unban(member.user, reason=reason)
        if member.reason:
            await ctx.send_or_reply(content=f'{self.bot.emote_dict["success"]} Unbanned `{member.user} (ID: {member.user.id})`, previously banned for `{member.reason}.`',
            )
        else:
            await ctx.send_or_reply(content=f'{self.bot.emote_dict["success"]} Unbanned `{member.user} (ID: {member.user.id}).`',
            )
        self.bot.dispatch("mod_action", ctx, targets=[str(member.user)])

    # https://github.com/AlexFlipnote/discord_bot.py with my own additions

    ###################
    ## Prune Command ##
    ###################

    @commands.group(brief="Remove any type of content.",
                    aliases=["purge", "delete", "remove"])
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
            return await ctx.send_or_reply(content=f"Too many messages to search given ({limit}/2000)",
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
            return await ctx.send_or_reply(content="I do not have permissions to delete messages.",
            )
        except discord.HTTPException as e:
            return await ctx.send_or_reply(content=f"Error: {e} (try a smaller search?)",
            )

        deleted = len(deleted)
        if message is True:
            msg = await ctx.send_or_reply(content=f'{self.bot.emote_dict["trash"]} Deleted {deleted} message{"" if deleted == 1 else "s"}',
            )
            await asyncio.sleep(7)
            await ctx.message.delete()
            await msg.delete()

    @prune.command()
    async def embeds(self, ctx, search=100):
        """Removes messages that have embeds in them."""
        await self.do_removal(ctx, search, lambda e: len(e.embeds))

    @prune.command()
    async def invites(self, ctx, search=100):
        """Removes messages that have discord invite links in them."""
        def predicate(m):
            print(self.dregex.search(m.content))
            return self.dregex.search(m.content)
        await self.do_removal(ctx, search, predicate)

    @prune.command(aliases=['link', 'url', 'links'])
    async def urls(self, ctx, search=100):
        """Removes messages that have URLs in them."""
        def predicate(m):
            print(self.uregex.search(m.content))
            return self.uregex.search(m.content)
        await self.do_removal(ctx, search, predicate)

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
            await ctx.send_or_reply(content="The substring length must be at least 3 characters.",
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

        if not search.isdigit():
            prefix = search
            search = 100
        if prefix:

            def predicate(m):
                return (
                    m.webhook_id is None and m.author.bot) or m.content.startswith(prefix)

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
        custom_emoji = re.compile(
            r"<a?:(.*?):(\d{17,21})>|[\u263a-\U0001f645]")

        def predicate(m):
            return custom_emoji.search(m.content)

        await self.do_removal(ctx, search, predicate)

    @prune.command(name="reactions")
    async def _reactions(self, ctx, search=100):
        """Removes all reactions from messages that have them."""

        if search > 2000:
            return await ctx.send_or_reply(content=f"Too many messages to search for ({search}/2000)",
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

    @prune.command(name="until", aliases=["after"])
    async def _until(self, ctx, message_id: int):
        """Prune messages in a channel until the given message_id. Given ID is not deleted"""
        channel = ctx.message.channel
        try:
            message = await channel.fetch_message(message_id)
        except commands.errors.NotFound:
            await ctx.send_or_reply(content="Message could not be found in this channel",
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

    @commands.command(brief="Clean up command usage.",
                      search=200, aliases=["clean"])
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
            spammers = sorted(
                spammers.items(),
                key=lambda t: t[1],
                reverse=True)
            messages.extend(
                f"`{author}`: {count}" for author,
                count in spammers)
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

    @commands.command(brief="Set the slowmode for a channel")
    @commands.guild_only()
    @permissions.bot_has_permissions(manage_channels=True)
    @permissions.has_permissions(manage_channels=True)
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
            await ctx.send_or_reply(content=f'{self.bot.emote_dict["failed"]} Failed to set slowmode because of an error\n{e}',
            )
        else:
            await ctx.send_or_reply(content=f'{self.bot.emote_dict["success"]} Slowmode for {channel_obj.mention} set to `{time}s`',
            )

    @commands.command(aliases=["lockdown", "lockchannel"], brief="Lock a channel")
    @commands.guild_only()
    @permissions.bot_has_permissions(manage_channels=True, manage_roles=True)
    @permissions.has_permissions(administrator=True)
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
            msg = await ctx.send_or_reply(content=f"Locking channel {channel.mention}...",
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

    @commands.command(brief="Unlock a channel.", aliases=["unlockchannel"])
    @commands.guild_only()
    @permissions.bot_has_permissions(manage_channels=True)
    @permissions.has_permissions(administrator=True)
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

            msg = await ctx.send_or_reply(content=f"Unlocking channel {channel.mention}...",
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