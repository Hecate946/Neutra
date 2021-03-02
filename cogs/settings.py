from utilities.http import query
import discord
import random
import re

from discord.ext import commands

from utilities import permissions
from core import OWNERS, get_prefix, bot


def setup(bot):
    bot.add_cog(Settings(bot))


class Settings(commands.Cog):

    """
    Configure your server settings.
    """

    def __init__(self, bot):
        self.bot = bot
        self.cxn = bot.connection
        self.dregex = re.compile(r"(?i)(discord(\.gg|app\.com)\/)(?!attachments)([^\s]+)")


    @commands.command(aliases=["setprefix"], brief="Set your server's custom prefix.")
    @permissions.has_permissions(manage_guild=True)
    async def prefix(self, ctx, new: str = None):
        """
        Usage: -prefix [new prefix]
        Alias: -setprefix
        Output: A new prefix for the server
        Example: -prefix $
        Notes: 
            The bot will always respond to @NGC0000 in addition 
            to the set prefix. The default prefix is -. 
            The bot will only respond to that prefix in DMs.
            The new prefix set must be under 5 characters.
        """
        if new is None:
            prefix = await get_prefix(bot=self.bot, message=ctx.message)
            prefix = prefix[-1]
            await ctx.send(f"{ctx.author.mention}, the current prefix is {prefix}")
        else:
            if not ctx.guild: return await ctx.send("<:fail:812062765028081674> This command can only be used inside of servers.")
            if len(new) > 5:
                await ctx.send(f"{ctx.author.mention}, that prefix is too long. The prefix must be a maximum of five characters in length.")
            else:
                query = '''UPDATE servers SET prefix = $1 WHERE server_id = $2'''
                await self.cxn.execute(query, new, ctx.guild.id)
                await ctx.send(f"{ctx.author.mention}, the prefix has been set to {new}")


    @commands.command(pass_context=True, brief="Enable or disable auto-deleting invite links")
    @permissions.has_permissions(administrator=True)
    async def antiinvite(self, ctx, *, yes_no = None):
        """
        Usage:      -antiinvite <yes|enable|true|on||no|disable|false|off>
        Aliases:    -removeinvites, -deleteinvites, -antiinvites
        Permission: Administrator
        Output:     Removes invite links sent by users without the Manage Messages permission.
        """
        query = '''SELECT anti_invite FROM moderation WHERE server_id = $1'''
        current = await self.cxn.fetchrow(query, ctx.guild.id) or (None)
        current = str(current[0])
        if current == "true": 
            removeinvitelinks = "true"
        else:
            removeinvitelinks = None
        if yes_no == None: 
            # Output what we have
            msg =  "{} currently *{}*.".format("removal of invite links","enabled" if current == "true" else "disabled")
        elif yes_no.lower() in [ "yes", "on", "true", "enabled", "enable" ]:
            yes_no = 'true'
            removeinvitelinks = 'true'
            msg = "{} {} *enabled*.".format("removal of invite links","remains" if current is None else "is now")
        elif yes_no.lower() in [ "no", "off", "false", "disabled", "disable" ]:
            yes_no = False
            removeinvitelinks = None
            msg = "{} {} *disabled*.".format("removal of invite links","is now" if current else "remains")
        else:
            msg = "That is not a valid setting."
            yes_no = current
        if yes_no != current:
            await self.cxn.execute("UPDATE moderation SET anti_invite = $1 WHERE server_id = $2", removeinvitelinks, ctx.guild.id)
        await ctx.send(msg)


    @commands.Cog.listener()
    @commands.guild_only()
    async def on_message(self, message):

        if isinstance(message.channel, discord.DMChannel): return None
        if not self.dregex.search(message.content): return None 
        
        removeinvitelinks = await self.cxn.fetchrow("SELECT anti_invite FROM moderation WHERE server_id = $1", message.guild.id) or (None)
        removeinvitelinks = str(removeinvitelinks[0])
        if removeinvitelinks == "None": return None

        member = message.guild.get_member(int(message.author.id))
        if message.author.id in OWNERS: return None # We are immune!
        if member.guild_permissions.manage_messages: return None # We are immune!
  
        try:
            await message.delete()
            await message.channel.send("No invite links allowed", delete_after=7)
        except discord.Forbidden: return await message.channel.send("I have insufficient permission to delete invite links")
        except discord.NotFound: return None
        except Exception as e: return await message.channel.send(e)


    @commands.command(brief="Disallows certain users from using the bot within your server.")
    @permissions.has_permissions(administrator=True)
    async def ignore(self, ctx, user: discord.User = None, react:str = "", *, reason: str = None):

        if user is None: return await ctx.send(f"Usage: `{ctx.prefix}ignore <user> [react] [reason]`")

        if user.guild_permissions.administrator: return await ctx.send(f"<:fail:812062765028081674> You cannot punish other staff members")
        if user.id in OWNERS: return await ctx.send(f"<:fail:812062765028081674> You cannot punish my creator.")
        if user.top_role.position > ctx.author.position: return await ctx.send(f"<:fail:812062765028081674> User `{user}` is higher in the role hierarchy than you.")

        if react.upper() == "REACT":
            react = True
        else:
            react = False

        query = '''SELECT server_id FROM ignored WHERE id = $1 AND server_id = $2'''
        already_ignord = await self.cxn.fetchrow(query, user.id, ctx.guild.id)
        
        if "None" not in str(already_ignord): return await ctx.send(f":warning: User `{user}` is already being ignored.")

        query = '''INSERT INTO ignored VALUES ($1, $2, $3, $4, $5, $6, $7, $8)'''
        await self.cxn.execute(query, ctx.guild.id, ctx.guild.name, user.id, str(user), reason, ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S'), str(ctx.author), react)
        if reason is not None:
            await ctx.send(F"<:ballot_box_with_check:805871188462010398> Ignored `{user}` {reason}")
        else:
            await ctx.send(F"<:ballot_box_with_check:805871188462010398> Ignored `{user}`")


    @commands.command(brief="Reallow certain to use using the bot within your server.", aliases=['listen'])
    @permissions.has_permissions(administrator=True)
    async def unignore(self, ctx, user: discord.User = None):

        if user is None: return await ctx.send(f"Usage: `{ctx.prefix}ignore <user> [react] [reason]`")

        query = '''SELECT id FROM ignored WHERE id = $1 AND server = $2'''
        blacklisted = await self.cxn.fetchrow(query, user.id, ctx.guild.id) or None
        if blacklisted is None: return await ctx.send(f":warning: User was not ignored")

        query = '''SELECT reason FROM ignored WHERE id = $1 AND server = $2'''
        reason = await self.cxn.fetchrow(query, user.id, ctx.guild.id) or None

        query = '''DELETE FROM ignored WHERE id = $1 AND server = $2'''
        await self.cxn.execute(query, user.id, ctx.guild.id)

        if "None" in str(reason): 
            await ctx.send(f"<:ballot_box_with_check:805871188462010398> Removed `{user}` from the ignore list.")
        else:
            await ctx.send(f"<:ballot_box_with_check:805871188462010398> Removed `{user}`from the ignore list. " 
                           f"Previously ignored: `{str(reason).strip('(),')}`")


    async def message(self, message):
        # Check the message and see if we should allow it
        ctx = await self.bot.get_context(message)
        # never against the OWNERS
        if message.author.id in OWNERS: return

        if not ctx.command:
            # No command - no need to check
            return
        # Get the list of ignored users
        
        query = '''SELECT id FROM ignored WHERE id = $1 and server = $2'''
        ignored_users = await self.cxn.fetchrow(query, message.author.id, message.guild.id) or None
        if "None" in str(ignored_users):
            return
        if int(str(ignored_users).strip("(),'")) != message.author.id: 
            return

        query = '''SELECT react FROM ignored WHERE id = $2 and server = $2'''
        to_react = await self.cxn.fetchrow(query, message.author.id, message.guild.id)
        to_react = int(to_react[0])
        if to_react == 1:
            await message.add_reaction("<:fail:812062765028081674>")
        # We have an ignored user
        return { 'Ignore' : True, 'Delete' : False }


    @commands.Cog.listener()
    async def on_member_join(self, member):
        required_perms = member.guild.me.guild_permissions.manage_roles
        if not required_perms:
            return


        query = '''SELECT reassign FROM roleconfig WHERE server = $1'''
        reassign = await self.cxn.fetchrow(query, member.guild.id) or None
        if reassign is None or reassign[0] == 0 or reassign[0] is None: 
            pass
        else:
            query = '''SELECT roles FROM users WHERE id = $1 and server_id = $2'''
            old_roles = await self.cxn.fetchrow(query, member.guild.id, member.id) or None
            if old_roles is None: return
            roles = str(old_roles[0]).split(",")
            for role_id in roles:
                role = member.guild.get_role(int(role_id))
                try:
                    await member.add_roles(role)
                except Exception as e: raise e

        query = '''SELECT autoroles FROM roleconfig WHERE server_id = $1'''
        autoroles = await self.cxn.fetchrow(query, member.guild.id) or None
        if autoroles is None or autoroles[0] is None: 
            pass
        else:
            roles = str(autoroles[0]).split(",")
            for role_id in roles:
                role = self.bot.get_role(int(role_id))
                try:
                    await member.add_roles(role)
                except Exception as e: raise e
        
    @commands.command(brief="Toggle whether you want to have a user's old roles be reassigned to them on rejoin.")
    @commands.guild_only()
    @permissions.has_permissions(manage_guild=True)
    async def reassign(self, ctx, *, yes_no = None):
        """
        Usage:      -reassign <yes|enable|true|on||no|disable|false|off>
        Aliases:    -stickyroles
        Permission: Manage Server
        Output:     Reassigns roles when past members rejoin the server.
        """
        query = '''SELECT reassign FROM roleconfig WHERE server = $1'''
        current = await self.cxn.fetchrow(query, ctx.guild.id)
        current = current[0]
        if current == 1: 
            reassign = True
        else:
            current == 0
            reassign = False
        if yes_no is None:
            # Output what we have
            msg =  "{} currently *{}*.".format("Reassigning roles on member rejoin","enabled" if current == 1 else "disabled")
        elif yes_no.lower() in [ "yes", "on", "true", "enabled", "enable" ]:
            yes_no = True
            reassign = True
            msg = "{} {} *enabled*.".format("Reassigning roles on member rejoin","remains" if current == 1 else "is now")
        elif yes_no.lower() in [ "no", "off", "false", "disabled", "disable" ]:
            yes_no = False
            reassign = False
            msg = "{} {} *disabled*.".format("Reassigning roles on member rejoin","is now" if current == 1 else "remains")
        else:
            msg = "That is not a valid setting."
            yes_no = current
        if yes_no != current:
            await self.cxn.execute("UPDATE roleconfig SET reassign = $1 WHERE server = $2", reassign, ctx.guild.id)
        await ctx.send(msg)