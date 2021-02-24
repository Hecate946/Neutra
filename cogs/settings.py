import discord
import random
import re

from discord.ext import commands

from utilities import permissions
from lib.bot import owners, get_prefix
from lib.db import db

   
def setup(bot):
    bot.add_cog(Settings(bot))


class Settings(commands.Cog):

    """
    Configure your server settings.
    """

    def __init__(self, bot):
        self.bot = bot
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
                db.execute("UPDATE guilds SET Prefix = ? WHERE GuildID = ?", new, ctx.guild.id)
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
        current = db.record("SELECT RemoveInviteLinks FROM guilds WHERE GuildID = ?", ctx.guild.id) or (None)
        current = str(current).strip("',()")
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
            db.execute("UPDATE guilds SET RemoveInviteLinks = ? WHERE GuildID = ?", removeinvitelinks, ctx.guild.id)
        await ctx.send(msg)


    @commands.Cog.listener()
    @commands.guild_only()
    async def on_message(self, message):

        if isinstance(message.channel, discord.DMChannel): return None
        if not self.dregex.search(message.content): return None 
        
        removeinvitelinks = db.record("SELECT RemoveInviteLinks FROM guilds WHERE GuildID = ?", message.guild.id) or (None)
        removeinvitelinks = str(removeinvitelinks).strip("',()")
        if removeinvitelinks == "None": return None

        member = message.guild.get_member(int(message.author.id))
        if message.author.id in owners: return None # We are immune!
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
        if user.id in owners: return await ctx.send(f"<:fail:812062765028081674> You cannot punish my creator.")
        if user.top_role.position > ctx.author.position: return await ctx.send(f"<:fail:812062765028081674> User `{user}` is higher in the role hierarchy than you.")

        if react.upper() == "REACT":
            react = True
        else:
            react = False

        already_ignord = db.record("""
        SELECT server FROM ignored WHERE user = ? AND server = ?
        """, user.id, ctx.guild.id)
        
        if "None" not in str(already_ignord): return await ctx.send(f":warning: User `{user}` is already being ignored.")

        db.execute("""
        INSERT INTO ignored VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ctx.guild.id, ctx.guild.name, user.id, str(user), reason, ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S'), str(ctx.author), react)
        if reason is not None:
            await ctx.send(F"<:ballot_box_with_check:805871188462010398> Ignored `{user}` {reason}")
        else:
            await ctx.send(F"<:ballot_box_with_check:805871188462010398> Ignored `{user}`")


    @commands.command(brief="Reallow certain to use using the bot within your server.", aliases=['listen'])
    @permissions.has_permissions(administrator=True)
    async def unignore(self, ctx, user: discord.User = None):

        if user is None: return await ctx.send(f"Usage: `{ctx.prefix}ignore <user> [react] [reason]`")

        blacklisted = db.record("""
        SELECT user FROM ignored WHERE user = ? AND server = ?
        """, user.id, ctx.guild.id) or None
        if blacklisted is None: return await ctx.send(f":warning: User was not ignored")

        reason = db.record("""
        SELECT reason FROM ignored WHERE user = ? AND server = ?
        """, user.id, ctx.guild.id) or None

        db.execute("""
        DELETE FROM ignored WHERE user = ? AND server = ?
        """, user.id, ctx.guild.id)

        if "None" in str(reason): 
            await ctx.send(f"<:ballot_box_with_check:805871188462010398> Removed `{user}` from the ignore list.")
        else:
            await ctx.send(f"<:ballot_box_with_check:805871188462010398> Removed `{user}`from the ignore list. " 
                           f"Previously ignored: `{str(reason).strip('(),')}`")


    async def message(self, message):
        # Check the message and see if we should allow it
        ctx = await self.bot.get_context(message)
        # never against the owners
        if message.author.id in owners: return

        if not ctx.command:
            # No command - no need to check
            return
        # Get the list of ignored users
        
        ignored_users = db.record("""
        SELECT user FROM ignored WHERE user = ? and server = ?
        """, message.author.id, message.guild.id) or None
        if "None" in str(ignored_users):
            return
        if int(str(ignored_users).strip("(),'")) != message.author.id: 
            return

        to_react = db.record("""
        SELECT react FROM ignored WHERE user = ? and server = ?
        """, message.author.id, message.guild.id)
        to_react = int(to_react[0])
        if to_react == 1:
            await message.add_reaction("<:fail:812062765028081674>")
        # We have an ignored user
        return { 'Ignore' : True, 'Delete' : False }


    @commands.Cog.listener()
    async def on_member_join(self, member):
        required_perms = member.guild.me.guild_permissions.manage_roles
        if not required_perms: 
            print("no")
            return
        print("hi")


        reassign = db.record("""
        SELECT reassign FROM roleconfig WHERE server = ?
        """, member.guild.id) or None
        print(reassign)
        if reassign is None or reassign[0] == 0 or reassign[0] is None: 
            pass
        else:
            old_roles = db.record("""
            SELECT roles FROM users WHERE server = ? and id = ?
            """, member.guild.id, member.id) or None
            print(old_roles)
            if old_roles is None: return
            roles = str(old_roles[0]).split(",")
            for role_id in roles:
                role = member.guild.get_role(int(role_id))
                try:
                    await member.add_roles(role)
                except Exception as e: raise e

        autoroles = db.record("""
        SELECT autoroles FROM roleconfig WHERE server = ?
        """, member.guild.id) or None
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
        current = db.record("SELECT reassign FROM roleconfig WHERE server = ?", ctx.guild.id)
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
            db.execute("UPDATE roleconfig SET reassign = ? WHERE server = ?", reassign, ctx.guild.id)
        await ctx.send(msg)