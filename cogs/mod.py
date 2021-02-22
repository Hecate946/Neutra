import discord
import re
import asyncio
import typing
import sqlite3


from datetime import datetime, timedelta
from discord.ext import commands

from utilities import permissions, default, converters
from lib.db import db
from lib.bot import owners


def setup(bot):
    bot.add_cog(Moderation(bot))


class Moderation(commands.Cog):
    """
    Keep your server under control.
    """

    def __init__(self, bot):
        self.bot = bot
        self.mention_re = re.compile(r"[0-9]{17,21}")


    @commands.command(aliases=["nick", "setnick"], brief="Edit or reset a member's nickname.")
    @commands.guild_only()
    @permissions.has_permissions(manage_nicknames=True)
    async def nickname(self, ctx, user: discord.Member, *, nickname: str = None):
        """
        Usage:      -nickname <member> [nickname]
        Aliases:    -nick, -setnick
        Examples:   -nickname NGC0000 NGC, -nickname NGC0000
        Permission: Manage Nicknames
        Output:     Edits a member's nickname on the server.
        Notes:      Nickname will reset if no member is passed.
        """
        if user is None: return await ctx.send(f"Usage: `{ctx.prefix}nickname <user> <nickname>`")
        if user.id == ctx.guild.owner.id: return await ctx.send(f"<:fail:812062765028081674> User `{user}` is the server owner. I cannot edit the nickname of the server owner.")
        try:
            await user.edit(nick=nickname, reason=default.responsible(ctx.author, "Nickname edited by command execution"))
            message = f"<:ballot_box_with_check:805871188462010398> Nicknamed `{user}: {nickname}`"
            if nickname is None:
                message = f"<:ballot_box_with_check:805871188462010398> Reset nickname for `{user}`"
            await ctx.send(message)
        except discord.Forbidden:
            await ctx.send(f"<:fail:812062765028081674> I do not have permission to edit `{user}'s` nickname.")


    @commands.command(brief="Unbans a member from the server.", aliases=['revokeban'])
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
        if not member: return await ctx.send(f"Usage: `{ctx.prefix}unban <id/member> [reason]`")
        if reason is None:
            reason = default.responsible(ctx.author, f"Unbanned member {member} by command execution")

        await ctx.guild.unban(member.user, reason=reason)
        if member.reason:
            await ctx.send(f'<:ballot_box_with_check:805871188462010398> Unbanned `{member.user} (ID: {member.user.id})`, previously banned for `{member.reason}.`')
        else:
            await ctx.send(f'<:ballot_box_with_check:805871188462010398> Unbanned `{member.user} (ID: {member.user.id}).`')


    @commands.command(brief="Setup server muting system.", aliases=["setmuterole"])
    @commands.guild_only()
    @permissions.has_permissions(administrator=True)
    async def muterole(self, ctx, role:discord.Role = None):
        """
        Usage:      -muterole <role>
        Alias:      -setmuterole
        Example:    -muterole @Muted
        Permission: Administrator
        Output:
            This command will set a role of your choice as the 
            "Muted" role. The bot will also create a channel 
            named "muted" specifically for muted members.
        Notes:
            Channel "muted" may be deleted after command execution 
            if so desired.
        """
        if role is None: return await ctx.send(f"Usage: `{ctx.prefix}setmuterole [role]`")
        if not ctx.guild.me.guild_permissions.administrator: return await ctx.send("I cannot create a muted role without administrator permissions")
        if ctx.guild.me.top_role.position < role.position: return await ctx.send("The muted role is above my highest role. Aborting...")
        if ctx.author.top_role.position < role.position and ctx.author.id != ctx.guild.owner.id: return await ctx.send("The muted role is above your highest role. Aborting...")
        try:
            db.execute("UPDATE guilds SET MuteRole = ? WHERE GuildID = ?", role.id, ctx.guild.id)
        except Exception as e: return await ctx.send(e)
        msg = await ctx.send(f":warning: Creating mute system. This process may take several minutes.")
        for channel in ctx.guild.channels:
            await channel.set_permissions(role, view_channel=False)
        muted_channel = []
        for channel in ctx.guild.channels:
            if channel.name == "muted":
                muted_channel.append(channel)
        if not muted_channel:
            overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            await ctx.guild.create_text_channel(name="muted", overwrites=overwrites, topic="Punishment Channel", slowmode_delay = 30)
        await msg.edit(content=f"<:ballot_box_with_check:805871188462010398> Saved `{role.name}` as this server's mute role.")


    @commands.command(brief="Softmute members. (Users can read messages)", aliases=["sm"])
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @permissions.has_permissions(kick_members=True)
    async def softmute(self, ctx, targets: commands.Greedy[discord.Member], minutes: typing.Optional[int], *, reason: typing.Optional[str] = None):
        """
        Usage:     -mute <target> [target]... [minutes] [reason]
        Alias:     -softmute
        Example:   -mute person1 person2 10 for spamming
        Pemission: Kick Members
        Output:    Adds the mute role to passed users.
        Notes: 
            Command -muterole must be executed prior to usage of 
            this command. Upon usage, will not be able to send 
            messages in any channel except for messages in #muted 
            (if still exists). Muted role will be removed from the 
            user upon -unmute, or when their timed mute ends.
        """
        global target
        if not len(targets): return await ctx.send(f"Usage: `{ctx.prefix}mute <target> [target]... [minutes] [reason]`")

        else:
            unmutes = []
            try:
                self.mute_role = db.record("SELECT MuteRole FROM guilds WHERE GuildID = ?", ctx.guild.id) or (None)
                self.mute_role = str(self.mute_role).strip("()',")
                if str(self.mute_role) == "None": return await ctx.send(f"use `{ctx.prefix}muterole <role>` to initialize the muted role.")
                self.mute_role = ctx.guild.get_role(int(self.mute_role))
            except Exception as e: return await ctx.send(e)
            muted = []
            for target in targets:
                if not self.mute_role in target.roles:
                    if target.id in owners: return await ctx.send('You cannot mute my master.')
                    if target.id == ctx.author.id: return await ctx.send('I don\'t think you really want to mute yourself...')
                    if target.id == self.bot.user.id: return await ctx.send('I don\'t think I want to mute myself...')
                    if target.guild_permissions.kick_members and ctx.author.id not in owners and ctx.author.id != ctx.guild.owner.id: return await ctx.send('You cannot punish other staff members.')
                    if ctx.guild.me.top_role.position < target.top_role.position and ctx.author.id not in owners: return await ctx.send(f"My highest role is below {target}'s highest role. Aborting mute.")
                    if ctx.guild.me.top_role.position < self.mute_role.position: return await ctx.send("My highest role is below the mute role. Aborting mute.")
                    try:
                        await target.add_roles(self.mute_role)
                        muted.append(target)
                    except Exception as e: 
                        return await ctx.send(e)
                    if reason:
                        try:
                            await target.send(f"<:announce:807097933916405760> You have been muted in **{ctx.guild.name}** {reason}. Mute duration: `{minutes} minute{'' if minutes == 1 else 's'}`")
                        except: return
                    global unmutereason
                    unmutereason = reason

                    if minutes:
                        unmutes.append(target)
                else:
                    await ctx.send(f":warning: Member `{target.display_name}` is already muted.")
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
                    msg = f'<:ballot_box_with_check:805871188462010398> Softmuted `{", ".join(allmuted)}` indefinetely'
                else:
                    msg = f'<:ballot_box_with_check:805871188462010398> Softmuted `{", ".join(allmuted)}` for {minutes:,} minute{"" if minutes == 1 else "s"}'
                await ctx.send(msg)
            if len(unmutes):
                await asyncio.sleep(minutes*60)
                await self.unmute(ctx, targets)


    @commands.command(brief='Hardmute members. (Users cannot read messages)', aliases=["hackmute","mute"])
    @commands.guild_only()
    @permissions.has_permissions(kick_members=True)
    async def hardmute(self, ctx, targets: commands.Greedy[discord.Member], minutes: typing.Optional[int], *, reason: typing.Optional[str] = None):
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
        if not len(targets): return await ctx.send(f"Usage: `{ctx.prefix}mute <target> [target]... [minutes] [reason]`")

        else:
            unmutes = []
            try:
                self.mute_role = db.record("SELECT MuteRole FROM guilds WHERE GuildID = ?", ctx.guild.id) or (None)
                self.mute_role = str(self.mute_role).strip("()',")
                if str(self.mute_role) == "None": return await ctx.send(f"use `{ctx.prefix}muterole <role>` to initialize the muted role.")
                self.mute_role = ctx.guild.get_role(int(self.mute_role))
            except Exception as e: return await ctx.send(e)
            muted = []
            for target in targets:
                if not self.mute_role in target.roles:
                    role_ids = ",".join([str(r.id) for r in target.roles])
                    end_time = datetime.utcnow() + timedelta(seconds=minutes*60) if minutes else None
                    if target.id in owners: return await ctx.send('You cannot mute my master.')
                    if target.id == ctx.author.id: return await ctx.send('I don\'t think you really want to mute yourself...')
                    if target.id == self.bot.user.id: return await ctx.send('I don\'t think I want to mute myself...')
                    if target.guild_permissions.kick_members and ctx.author.id not in owners and ctx.author.id != ctx.guild.owner.id: return await ctx.send('You cannot punish other staff members.')
                    if ctx.guild.me.top_role.position < target.top_role.position and ctx.author.id not in owners: return await ctx.send(f"My highest role is below {target}'s highest role. Aborting mute.")
                    if ctx.guild.me.top_role.position < self.mute_role.position: return await ctx.send("My highest role is below the mute role. Aborting mute.")
                    try:
                        db.execute("INSERT INTO mutes VALUES (?, ?, ?)", target.id, role_ids, getattr(end_time, "isoformat", lambda: None)())
                    except sqlite3.IntegrityError: return await ctx.send(f"Database error occured. Contact the bot developer by using {ctx.prefix}bugreport <report>")
                    try:
                        await target.edit(roles=[self.mute_role])
                        muted.append(target)
                    except Exception as e: 
                        return await ctx.send(e)
                    if reason:
                        try:
                            await target.send(f"<:announce:807097933916405760> You have been muted in **{ctx.guild.name}** {reason}. Mute duration: `{minutes} minute{'' if minutes == 1 else 's'}`")
                        except: return
                    global unmutereason
                    unmutereason = reason

                    if minutes:
                        unmutes.append(target)
                else:
                    await ctx.send(f":warning: Member `{target.display_name}` is already muted.")
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
                    msg = f'<:ballot_box_with_check:805871188462010398> Hardmuted `{", ".join(allmuted)}` indefinetely'
                else:
                    msg = f'<:ballot_box_with_check:805871188462010398> Hardmuted `{", ".join(allmuted)}` for {minutes:,} minute{"" if minutes == 1 else "s"}'
                await ctx.send(msg)
            if len(unmutes):
                await asyncio.sleep(minutes*60)
                await self.unmute(ctx, targets)


    async def unmute(self, ctx, targets):
        try:
            self.mute_role = db.record("SELECT MuteRole FROM guilds WHERE GuildID = ?", ctx.guild.id) or (None)
            self.mute_role = str(self.mute_role).strip("()',")
            self.mute_role = ctx.guild.get_role(int(self.mute_role))
        except Exception as e: return await ctx.send(e)
        unmuted = []
        for target in targets:
            if self.mute_role in target.roles:
                role_ids = db.field("SELECT RoleIDs FROM mutes WHERE UserID = ?", target.id) or (None)
                if str(role_ids) == "None": 
                    await target.remove_roles(self.mute_role)
                    unmuted.append(target)
                    continue
                roles = [ctx.guild.get_role(int(id_)) for id_ in role_ids.split(",") if len(id_)]

                db.execute("DELETE FROM mutes WHERE UserID = ?", target.id)

                await target.edit(roles=roles)
                unmuted.append(target)
                if unmutereason:
                    try:
                        await target.send(f"<:announce:807097933916405760> You have been unmuted in **{ctx.guild.name}**")
                    except: return 

            else: return await ctx.send(":warning: Member is not muted")

        if unmuted:   
            allmuted = []
            for member in unmuted: 
                users = []
                people = await self.bot.fetch_user(int(member.id))
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    allmuted += [username]
            await ctx.send(f'<:ballot_box_with_check:805871188462010398> Unmuted `{", ".join(allmuted)}`')


    @commands.command(name="unmute", brief="Unmute previously muted members.", aliases=['endmute'])
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
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
            await ctx.send(f"Usage: `{ctx.prefix}unmute <target> [target]...`")

        else:
            await self.unmute(ctx, targets)


    @commands.command(brief="Restrict users from sending messages in a channel.")
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
            return await ctx.send(f"Usage: `{ctx.prefix}block <target> [target] [target]...`")
        blocked = []
        for target in targets:
            if ctx.author.id not in owners and ctx.author.id != ctx.guild.owner.id and not ctx.author.guild_permissions.kick_members: return await ctx.send('You have insufficient permission to execute that command.')
            if target.id in owners: return await ctx.send('You cannot block my master.')
            if target.id == ctx.author.id: return await ctx.send('I don\'t think you really want to block yourself...')
            if target.id == self.bot.user.id: return await ctx.send('I don\'t think I want to block myself...') 
            if target.guild_permissions.kick_members and ctx.author.id not in owners and ctx.author.id != ctx.guild.owner.id: return await ctx.send('You cannot punish other staff members.')
            try:
                await ctx.channel.set_permissions(target, send_messages=False)  # gives back send messages permissions
                blocked.append(target)
            except:
                await ctx.send("`{0}` could not me block".format(target))
        if blocked:
            blocked_users = []
            for unblind in blocked: 
                users = []
                people = await self.bot.fetch_user(int(unblind.id))
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    blocked_users += [username]
            await ctx.send('<:ballot_box_with_check:805871188462010398> Blocked `{0}`'.format(", ".join(blocked_users)))


    @commands.command(brief="Reallow users to send messages in a channel.")
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
            return await ctx.send(f"Usage: `{ctx.prefix}unblock <target> [target] [target]...`")
        unblocked = []
        for target in targets:
            if ctx.author.id not in owners and ctx.author.id != ctx.guild.owner.id and not ctx.author.guild_permissions.kick_members: return await ctx.send('You have insufficient permission to execute that command.')
            if target.id in owners: return await ctx.send('You cannot unblock my master.')
            if target.id == ctx.author.id: return await ctx.send('I don\'t think you really want to unblock yourself...')
            if target.id == self.bot.user.id: return await ctx.send('I don\'t think I want to unblock myself...') 
            if target.guild_permissions.kick_members and ctx.author.id not in owners and ctx.author.id != ctx.guild.owner.id: return await ctx.send('You cannot punish other staff members.')
            try:
                await ctx.channel.set_permissions(target, send_messages=None)  # gives back send messages permissions
                unblocked.append(target)
            except:
                await ctx.send("`{0}` could not me unblock".format(target))
        if unblocked:
            unblocked_users = []
            for unblind in unblocked: 
                users = []
                people = await self.bot.fetch_user(int(unblind.id))
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    unblocked_users += [username]
            await ctx.send('<:ballot_box_with_check:805871188462010398> Unblocked `{0}`'.format(", ".join(unblocked_users)))


    @commands.command(brief="Restrict users from reading messages in a channel.")
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
            return await ctx.send(f"Usage: `{ctx.prefix}blind <target> [target] [target]...`")
        blinded = []
        for target in targets:
            if ctx.author.id not in owners and ctx.author.id != ctx.guild.owner.id and not ctx.author.guild_permissions.kick_members: return await ctx.send('You have insufficient permission to execute that command.')
            if target.id in owners: return await ctx.send('You cannot blind my master.')
            if target.id == ctx.author.id: return await ctx.send('I don\'t think you really want to blind yourself...')
            if target.id == self.bot.user.id: return await ctx.send('I don\'t think I want to blind myself...') 
            if target.guild_permissions.kick_members and ctx.author.id not in owners and ctx.author.id != ctx.guild.owner.id: return await ctx.send('You cannot punish other staff members.')
            try:
                await ctx.channel.set_permissions(target, send_messages=False, read_messages=False)  # gives back send messages permissions
                blinded.append(target)
            except:
                await ctx.send("`{0}` could not me blinded".format(target))
        if blinded:
            blinded_users = []
            for unblind in blinded: 
                users = []
                people = await self.bot.fetch_user(int(unblind.id))
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    blinded_users += [username]
            await ctx.send('<:ballot_box_with_check:805871188462010398> Blinded `{0}`'.format(", ".join(blinded_users)))


    @commands.command(brief="Reallow users see the channel.")
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
            return await ctx.send(f"Usage: `{ctx.prefix}unblind <target> [target] [target]...`")
        unblinded = []
        for target in targets:
            if ctx.author.id not in owners and ctx.author.id != ctx.guild.owner.id and not ctx.author.guild_permissions.kick_members: return await ctx.send('You have insufficient permission to execute that command.')
            if target.id in owners: return await ctx.send('You cannot unblind my master.')
            if target.id == ctx.author.id: return await ctx.send('I don\'t think you really want to unblind yourself...')
            if target.id == self.bot.user.id: return await ctx.send('I don\'t think I want to unblind myself...') 
            if target.guild_permissions.kick_members and ctx.author.id not in owners and ctx.author.id != ctx.guild.owner.id: return await ctx.send('You cannot punish other staff members.')
            try:
                await ctx.channel.set_permissions(target, send_messages=None, read_messages=None)  # gives back send messages permissions
                unblinded.append(target)
            except:
                await ctx.send("`{0}` could not me unblinded".format(target))
        if unblinded:
            unblinded_users = []
            for unblind in unblinded: 
                users = []
                people = await self.bot.fetch_user(int(unblind.id))
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    unblinded_users += [username]
            await ctx.send('<:ballot_box_with_check:805871188462010398> Unblinded `{0}`'.format(", ".join(unblinded_users)))


    @commands.command(brief="Kick members from the server")
    @commands.guild_only()
    @commands.bot_has_permissions(kick_members=True)
    @permissions.has_permissions(kick_members=True)
    async def kick(self, ctx, users: commands.Greedy[discord.Member], *, reason: typing.Optional[str] = "No reason"):
        """
        Usage:      -kick <target> [target]... [reason]
        Example:    -kick @Jacob Sarah for advertising
        Permission: Kick Members
        Output:     Kicks passed members from the server.
        """
        if not len(users): return await ctx.send(f"Usage: `{ctx.prefix}kick <target> [target]... [reason]")

        kicked = []
        for target in users:
            if target.id in owners: return await ctx.send('You cannot kick my master.')
            if target.id == ctx.author.id: return await ctx.send('I don\'t think you really want to kick yourself...')
            if target.id == self.bot.user.id: return await ctx.send('I don\'t think I want to kick myself...')
            if target.guild_permissions.kick_members and ctx.author.id not in owners and ctx.author.id != ctx.guild.owner.id: return await ctx.send('You cannot punish other staff members.')
            if ctx.guild.me.top_role.position > target.top_role.position and not target.guild_permissions.administrator:
                try:
                    await ctx.guild.kick(target, reason=reason)
                    kicked.append(f"{target.name}#{target.discriminator}")
                except:
                    await ctx.send('<:fail:812062765028081674> `{0}` could not be kicked.'.format(target))
                    continue
            if kicked:
                await ctx.send('<:ballot_box_with_check:805871188462010398> Kicked `{0}`'.format(", ".join(kicked)))

    @commands.command(brief="Ban members from the server.")
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    @permissions.has_permissions(ban_members=True)
    async def ban(self, ctx, targets: commands.Greedy[discord.Member], delete_message_days:int=1, *, reason: typing.Optional[str] = "No reason"):
        """
        Usage:      -ban <target> [target]... [delete message days = 1] [reason]
        Example:    -ban @Jacob Sarah 4 for advertising
        Permission: Ban Members
        Output:     Ban passed members from the server.
        """
        if not len(targets): return await ctx.send(f"Usage: `{ctx.prefix}ban <target1> [target2] [delete message days] [reason]`")

        if delete_message_days > 7:
            delete_message_days = 7
        elif delete_message_days < 0:
            delete_message_days = 0
        else:
            delete_message_days = delete_message_days
        banned = []
        for target in targets:
            if target.id in owners: return await ctx.send('You cannot ban my master.')
            if target.id == ctx.author.id: return await ctx.send('I don\'t think you really want to ban yourself...')
            if target.id == self.bot.user.id: return await ctx.send('I don\'t think I want to ban myself...')
            if target.guild_permissions.kick_members and ctx.author.id not in owners and ctx.author.id != ctx.guild.owner.id: return await ctx.send('You cannot punish other staff members.')
            if (ctx.guild.me.top_role.position > target.top_role.position and not target.guild_permissions.administrator):
                try:
                    await ctx.guild.ban(target, reason=reason, delete_message_days=delete_message_days)
                    banned.append(f"{target.name}#{target.discriminator}")
                except:
                    await ctx.send('<:fail:812062765028081674> `{0}` could not be banned.'.format(target))
                    continue
        if banned:
            await ctx.send('<:ballot_box_with_check:805871188462010398> Banned `{0}`'.format(", ".join(banned)))


    @commands.command(brief="Softbans members from the server.")
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    @permissions.has_permissions(kick_members=True)
    async def softban(self, ctx, targets: commands.Greedy[discord.Member], delete_message_days:int = 7, *, reason:str = "No reason"):
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
        if not len(targets): return await ctx.send(f"Usage: `{ctx.prefix}softban <member> [days to delete messages] [reason]`")

        banned = []
        for target in targets:
            if ctx.author.id not in owners and ctx.author.id != ctx.guild.owner.id and not ctx.author.guild_permissions.kick_members: return await ctx.send('You have insufficient permission to execute that command.')
            if target.id in owners: return await ctx.send('You cannot hackban my master.')
            if target.id == ctx.author.id: return await ctx.send('I don\'t think you really want to hackban yourself...')
            if target.id == self.bot.user.id: return await ctx.send('I don\'t think I want to hackban myself...')
            if target.guild_permissions.kick_members and ctx.author.id not in owners and ctx.author.id != ctx.guild.owner.id: return await ctx.send('You cannot punish other staff members.')
            try:
                await ctx.guild.ban(target, reason=reason, delete_message_days=delete_message_days)
                await ctx.guild.unban(target, reason=reason)
                banned.append(f"{target.name}#{target.discriminator}")
            except:
                await ctx.send('<:fail:812062765028081674> `{0}` could not be softbanned.'.format(target))
                continue
        if banned:
            await ctx.send('<:ballot_box_with_check:805871188462010398> Softbanned `{0}`'.format(", ".join(banned)))


    @commands.command(pass_context=True, brief="Hackban multiple users by ID.")
    @commands.bot_has_permissions(ban_members=True)
    @permissions.has_permissions(manage_guild=True)
    async def hackban(self, ctx, *users:str):
        """
        Usage:      -hackban <id> [id] [id]...
        Example:    -hackban 805871188462010398 243507089479579784
        Permission: Manage Server
        Output:     Hackbans multiple users by ID.
        Notes:      Users do not have to be in the server."""
        if not users:
            return await ctx.send(f"Usage: `{ctx.prefix}hackban <id> [id] [id]...`")
        banned = []
        for user in users:
            try:
                u = ctx.guild.get_member(int(user))
                if u.guild_permissions.kick_members and ctx.author.id not in owners and ctx.author.id != ctx.guild.owner.id: return await ctx.send('You cannot punish other staff members.')
            except:
                try:
                    u = discord.Object(id=user)
                except TypeError:
                    return await ctx.send('User snowflake must be integer. Ex: 708584008065351681.')
            if ctx.author.id not in owners and not ctx.author.guild_permissions.manage_guild: return await ctx.send('You have insufficient permission to execute that command.')
            if u.id in owners: return await ctx.send('You cannot hackban my master.')
            if u.id == ctx.author.id: return await ctx.send('I don\'t think you really want to hackban yourself...')
            if u.id == self.bot.user.id: return await ctx.send('I don\'t think I want to hackban myself...')
            try:
                await ctx.guild.ban(u, reason=f"Hackban executed by `{ctx.author}`", delete_message_days=7)
                banned.append(user)
            except:
                uu = ctx.message.guild.get_member(user)
                if uu is None:
                    await ctx.send('<:fail:812062765028081674> `{0}` could not be hackbanned.'.format(user))
                else:
                    await ctx.send('<:fail:812062765028081674> `{0}` is already on the server and could not be banned.'.format(uu))
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
            await ctx.send('<:ballot_box_with_check:805871188462010398> Hackbanned `{0}`'.format(", ".join(hackbanned)))

    # command mostly from Alex Flipnote's discord_bot.py bot
    # https://github.com/AlexFlipnote/discord_bot.py

    @commands.group(brief='Remove any type of content in the last 2000 messages.', aliases=["cleanup","purge","clean"])
    @commands.guild_only()
    @commands.max_concurrency(1, per=commands.BucketType.guild)
    @commands.bot_has_permissions(manage_messages=True)
    @permissions.has_permissions(manage_messages=True)
    async def prune(self, ctx):
        """
        Usage:      -prune <method> <amount>
        Alias:      -purge, -cleanup, -clean
        Examples:   -prune user Hecate, -prune bots
        Output:     Deletes messages that match your method criteria
        Permission: Manage Messages
        Output:     Message cleanup within your search specification.
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


    async def do_removal(self, ctx, limit, predicate, *, before=None, after=None, message=True):
        if limit > 2000:
            return await ctx.send(f'Too many messages to search given ({limit}/2000)')

        if not before:
            before = ctx.message
        else:
            before = discord.Object(id=before)

        if after:
            after = discord.Object(id=after)

        try:
            deleted = await ctx.channel.purge(limit=limit, before=before, after=after, check=predicate)
        except discord.Forbidden:
            return await ctx.send('I do not have permissions to delete messages.')
        except discord.HTTPException as e:
            return await ctx.send(f'Error: {e} (try a smaller search?)')

        deleted = len(deleted)
        if message is True:
            msg = await ctx.send(f'<:trashcan:805643072896892949> Deleted {deleted} message{"" if deleted == 1 else "s"}')
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
        await self.do_removal(ctx, search, lambda e: len(e.mentions) or len(e.role_mentions))


    @prune.command()
    async def images(self, ctx, search=100):
        """Removes messages that have embeds or attachments."""
        await self.do_removal(ctx, search, lambda e: len(e.embeds) or len(e.attachments))


    @prune.command(name='all')
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
            await ctx.send('The substring length must be at least 3 characters.')
        else:
            await self.do_removal(ctx, 100, lambda e: substr in e.content)


    @prune.command(name='bots')
    async def _bots(self, ctx, search=100, prefix=None):
        """Removes a bot user's messages and messages with their optional prefix."""

        getprefix = db.field("SELECT Prefix FROM guilds WHERE GuildID = ?", ctx.guild.id)

        def predicate(m):
            return (m.webhook_id is None and m.author.bot) or m.content.startswith(tuple(getprefix))

        await self.do_removal(ctx, search, predicate)


    @prune.command(name='humans')
    async def _users(self, ctx, search=100, prefix=None):
        """Removes only user messages. """

        def predicate(m):
            return m.author.bot is False

        await self.do_removal(ctx, search, predicate)


    @prune.command(name='emojis')
    async def _emojis(self, ctx, search=100):
        """Removes all messages containing custom emoji."""
        custom_emoji = re.compile(r'<a?:(.*?):(\d{17,21})>|[\u263a-\U0001f645]')

        def predicate(m):
            return custom_emoji.search(m.content)

        await self.do_removal(ctx, search, predicate)


    @prune.command(name='reactions')
    async def _reactions(self, ctx, search=100):
        """Removes all reactions from messages that have them."""

        if search > 2000:
            return await ctx.send(f'Too many messages to search for ({search}/2000)')

        total_reactions = 0
        async for message in ctx.history(limit=search, before=ctx.message):
            if len(message.reactions):
                total_reactions += sum(r.count for r in message.reactions)
                await message.clear_reactions()
        await ctx.send(f'<:trashcan:805643072896892949> Successfully removed {total_reactions} reactions.', delete_after=7)


    @prune.command(name='until')
    async def _until(self, ctx, message_id: int):
        """Prune messages in a channel until the given message_id. Given ID is not deleted""" 
        channel = ctx.message.channel
        try:
            message = await channel.fetch_message(message_id)
        except commands.errors.NotFound:
            await ctx.send("Message could not be found in this channel")
            return

        await ctx.message.delete()
        await channel.purge(after=message)
        return True
