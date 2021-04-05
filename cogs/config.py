import subprocess
import asyncio
import asyncpg
import discord
import random
import os
import csv
import io
import sys
import copy
import time
import importlib
import aiohttp
import datetime
import traceback
import json

from discord.ext import commands, menus

from utilities import utils, permissions, pagination, converters


def setup(bot):
    bot.add_cog(Config(bot))


class Config(commands.Cog):
    """
    Owner only configuration cog.
    """
    # TODO rework this cog. this is out of date and still uses postgres instead of local cache.
    def __init__(self, bot):
        self.bot = bot
        
        self.emote_dict = bot.emote_dict

    # This cog is owner only
    async def cog_check(self, ctx):
        if not await self.bot.is_owner(ctx.author):
            return
        return True

      ##############################
     ## Aiohttp Helper Functions ##
    ##############################

    async def query(self, url, method="get", res_method="text", *args, **kwargs):
        async with getattr(self.bot.session, method.lower())(url, *args, **kwargs) as res:
            return await getattr(res, res_method)()


    async def get(self, url, *args, **kwargs):
        return await self.query(url, "get", *args, **kwargs)


    async def post(self, url, *args, **kwargs):
        return await self.query(url, "post", *args, **kwargs)


    @commands.group(hidden=True, brief="Change the bot's specifications.")
    async def change(self, ctx):
        """ 
        Usage:      -search <method> <new>
        Examples:   -change name Milky Way, -change avatar <url>
        Permission: Bot Owner
        Output:     Edited Bot Specification.
        Methods:
            avatar        (Alias: pfp)
            nickname      (Alias: nick)
            username      (Alias: name)
        """
        if ctx.invoked_subcommand is None:
            help_command = self.bot.get_command("help")
            await help_command(ctx, invokercommand="change")


    @change.command(name="username", hidden=True, aliases=['name','user'], brief="Change username.")
    async def change_username(self, ctx, *, name: str):
        try:
            await self.bot.user.edit(username=name)
            await ctx.send(f"Successfully changed username to **{name}**")
        except discord.HTTPException as err:
            await ctx.send(err)


    @change.command(name="nickname", hidden=True, brief="Change nickname.")
    async def change_nickname(self, ctx, *, name: str = None):
        try:
            await ctx.guild.me.edit(nick=name)
            if name:
                await ctx.send(f"Successfully changed nickname to **{name}**")
            else:
                await ctx.send("Successfully removed nickname")
        except Exception as err:
            await ctx.send(err)


    @change.command(name="avatar", hidden=True, brief="Change avatar.")
    async def change_avatar(self, ctx, url: str = None):
        if url is None and len(ctx.message.attachments) == 0:
            return await ctx.send(f"Usage: `{ctx.prefix}change avatar <avatar>`")
        if url is None and len(ctx.message.attachments) == 1:
            url = ctx.message.attachments[0].url
        else:
            url = url.strip('<>') if url else None

        try:
            bio = await self.get(url, res_method="read")
            await self.bot.user.edit(avatar=bio)
            em = discord.Embed(description="**Successfully changed the avatar. Currently using:**", color=self.bot.constants.embed)
            em.set_image(url=url)
            await ctx.send(embed=em)
        except aiohttp.InvalidURL:
            await ctx.send("Invalid URL.")
        except discord.InvalidArgument:
            await ctx.send("This URL does not contain a useable image.")
        except discord.HTTPException as err:
            await ctx.send(err)
        except TypeError:
            await ctx.send("Provide an attachment or a valid URL.")


    @change.command(brief="Change the bot default presence", aliases=["pres"])
    async def presence(self, ctx, *, presence: str = ""):
        if ctx.author.id not in self.bot.constants.owners: return None
        if presence == "":
            msg = "<:checkmark:816534984676081705> presence has been reset."
        else:
            msg = f"{self.emote_dict['success']} presence now set to `{presence}`"
        utils.edit_config(value="presence", changeto=presence)
        await self.bot.set_status()
        self.bot.constants.presence = presence
        await ctx.send(msg)


    @change.command(brief="Set the bot's default status type.")
    async def status(self, ctx, status: str = None):
        if ctx.author.id not in self.bot.constants.owners:
            return

        if status.lower() in ['online','green']:
            status = "online"
        elif status.lower() in ['idle','moon','sleep','yellow']:
            status = "idle"
        elif status.lower() in ['dnd','do-not-disturb', 'do_not_disturb', 'red']:
            status = "dnd"
        elif status.lower() in ['offline','gray','invisible','invis']:
            status = "offline"
        else:
            return await ctx.send(f"{self.bot.emote_dict['failed']} `{status}` is not a valid status.")
        
        utils.edit_config(value="status", changeto=status)
        self.bot.constants.status = status
        await self.bot.set_status()
        await ctx.send(f"{self.emote_dict['success']} status now set as `{status}`")


    @change.command(brief="Set the bot's default activity type.", aliases=["action"])
    async def activity(self, ctx, activity: str = None):

        if activity.lower() in ['play','playing','game','games']:
            activity = "playing"
        elif activity.lower() in ['listen','listening', 'hearing', 'hear']:
            activity = "listening"
        elif activity.lower() in ['watch','watching','looking','look']:
            activity = "watching"
        elif activity.lower() in ['comp','competing','compete']:
            activity = "competing"
        else:
            return await ctx.send(f"<:fail:812062765028081674> `{activity}` is not a valid status.")

        utils.edit_config(value="activity", changeto=activity)
        self.bot.constants.activity = activity
        await self.bot.set_status()
        await ctx.send(f"{self.emote_dict['success']} status now set as `{activity}`")


    @commands.command(brief="Blacklist users or servers from executing any commands on the bot.", invoke_without_command=True)
    async def blacklist(self, ctx, user: converters.DiscordUser = None, react:str = "", *, reason: str = None):
        """
        Usage: -blacklist <user> [react] [reason]
        """
        if ctx.author.id not in self.bot.constants.owners: return None
        if user is None: return await ctx.send(f"Usage: `{ctx.prefix}blacklist <user> [react] [reason]`")
        if react.upper() == "REACT":
            react = True
        else:
            react = False
        try:
            query = '''INSERT INTO blacklist VALUES ($1, $2, $3, $4, $5, $6)'''
            await self.bot.cxn.execute(query, user.id, str(user), reason, ctx.message.created_at.utcnow(), str(ctx.author), react)
        except asyncpg.exceptions.UniqueViolationError: return await ctx.send(f":warning: User `{user}` already blacklisted.")
        if reason is not None:
            await ctx.send(f"{self.emote_dict['success']} Blacklisted `{user}` {reason}")
        else:
            await ctx.send(f"{self.emote_dict['success']} Blacklisted `{user}`")


    @commands.command(brief="Removes users from the command blacklist.")
    async def unblacklist(self, ctx, user: converters.DiscordUser = None):
        """
        Usage: -unblacklist [user]
        """
        if ctx.author.id not in self.bot.constants.owners: return None

        if user is None: return await ctx.send(f"Usage: `{ctx.prefix}blacklist <user> [react = (true/enable/yes/on)] [reason]`")

        query = '''SELECT user_id FROM blacklist WHERE user_id = $1'''
        blacklisted = await self.bot.cxn.fetchrow(query, user.id) or None
        if blacklisted is None: return await ctx.send(f":warning: User was not blacklisted")


        query = '''SELECT reason FROM blacklist WHERE user_id = $1'''
        reason = await self.bot.cxn.fetchrow(query, user.id) or None

        query = '''DELETE FROM blacklist WHERE user_id = $1'''
        await self.bot.cxn.execute(query, user.id)

        if "None" in str(reason): 
            await ctx.send(f"{self.emote_dict['success']} Removed `{user}` from the blacklist.")
        else:
            await ctx.send(f"{self.emote_dict['success']} Removed `{user}`from the blacklist. " 
                            f"Previously blacklisted: `{str(reason).strip('(),')}`")


    @commands.command(brief="Clear the user blacklist")
    async def clearblacklist(self, ctx):
        """
        Usage: -clearblacklist
        """
        if ctx.author.id not in self.bot.constants.owners: return None
        try:
            query = '''DELETE FROM blacklist'''
            await self.bot.cxn.execute(query)
        except Exception as e:
            return await ctx.send(e)
        await ctx.send(f"{self.emote_dict['success']} Cleared the blacklist.")


    @commands.command(brief="Blacklist a server")
    async def serverblacklist(self, ctx, server = None, react:str = "", *, reason:str = None):
        """
        Usage: -serverblacklist [server] [react] [reason]
        """
        if ctx.author.id not in self.bot.constants.owners: return None
        if server is None: return await ctx.send(f"Usage: `{ctx.prefix}serverblacklist <server> [react] [reason]`")


        if react.upper() == "REACT":
            react = True
        else:
            react = False
        # Check id first, then name
        guild = next((x for x in self.bot.guilds if str(x.id) == str(server)),None)
        if not guild:
            guild = next((x for x in self.bot.guilds if x.name.lower() == server.lower()),None)
        if guild:
            try:
                query = '''INSERT INTO serverblacklist VALUES ($1, $2, $3, $4, $5, $6)'''
                await self.bot.cxn.execute(query, guild.id, str(guild.name), reason, ctx.message.created_at.utcnow(), str(ctx.author), react)
            except asyncpg.exceptions.UniqueViolationError:
                return await ctx.send(f":warning: Server `{server}` is already blacklisted")
            if reason is None:
                await ctx.send(f"{self.emote_dict['success']} Blacklisted `{guild.name}`")
            else:
                await ctx.send(f"{self.emote_dict['success']} Blacklisted `{guild.name}`. {reason}")
            return

        await ctx.send(f"<:failed:812062765028081674> Server `{server}` not found")


    @commands.command(brief="Unblacklist users from executing any commands on the bot.")
    async def serverunblacklist(self, ctx, server = None):
        """
        Usage: -serverunblacklist <server name/server id>
        """
        if ctx.author.id not in self.bot.constants.owners: return None

        if server is None: return await ctx.send(f"Usage: `{ctx.prefix}serverunblacklist <server name/server id>`")

        guild = next((x for x in self.bot.guilds if str(x.id) == str(server)),None)
        if not guild:
            guild = next((x for x in self.bot.guilds if x.name.lower() == server.lower()),None)
        if guild:

            query = '''SELECT server_id FROM serverblacklist WHERE server_id = $1'''
            blacklisted = await self.bot.cxn.fetchrow(query, guild.id) or None
            if blacklisted is None: return await ctx.send(f":warning: Server was not blacklisted")

            query = '''SELECT reason FROM serverblacklist WHERE server_id = $1'''
            reason = await self.bot.cxn.fetchrow(query, guild.id) or None

            query = '''DELETE FROM serverblacklist WHERE server_id = $1'''
            await self.bot.cxn.execute(query, guild.id)

            if "None" in str(reason): 
                await ctx.send(f"{self.emote_dict['success']} Removed `{guild.name}` from the blacklist.")
            else:
                await ctx.send(f"{self.emote_dict['success']} Removed `{guild.name}`from the blacklist. " 
                                f"Previously blacklisted: `{str(reason).strip('(),')}`")
            return
        await ctx.send(f"<:fail:812062765028081674> Server `{server}` not found")


    @commands.command(brief="Clear the server blacklist")
    async def clearserverblacklist(self, ctx):
        """
        Usage: -clearserverblacklist
        """
        if ctx.author.id not in self.bot.constants.owners: return None
        try:
            await self.bot.cxn.execute("""DELETE FROM serverblacklist""")
        except Exception as e:
            return await ctx.send(e)
        await ctx.send(f"{self.emote_dict['success']} Cleared the server blacklist.")


    async def message(self, message):
        # Check the message and see if we should allow it
        if message.author.id in self.bot.constants.owners: return
        ctx = await self.bot.get_context(message)

        if not ctx.command:
            return
        # Get the list of blacklisted users

        query = '''SELECT server_id FROM serverblacklist WHERE server_id = $1'''
        ignored_servers = await self.bot.cxn.fetchrow(query, message.guild.id) or None
        
        if "None" not in str(ignored_servers):
            if int(str(ignored_servers).strip("(),'")) == message.guild.id: 

                query = '''SELECT react FROM serverblacklist WHERE server_id = $1'''
                to_react = await self.bot.cxn.fetchrow(query, message.guild.id)
                to_react = int(to_react[0])

                if to_react == 1:
                    await message.add_reaction("<:fail:812062765028081674>")
                return { 'Ignore' : True, 'Delete' : False }

        query = '''SELECT user_id FROM blacklist WHERE user_id = $1'''
        ignored_users = await self.bot.cxn.fetchrow(query, message.author.id) or None

        if "None" in str(ignored_users):
            return
        if int(ignored_users[0]) != message.author.id: 
            return
        else:
            query = '''SELECT react FROM blacklist WHERE user_id = $1'''
            to_react = await self.bot.cxn.fetchrow(query, message.author.id)
            to_react = int(to_react[0])
            if to_react == 1:
                await message.add_reaction(self.bot.emote_dict['failed'])
            # We have a disabled command - ignore it
            return { 'Ignore' : True, 'Delete' : False }


    @commands.command()
    async def toggle(self, ctx, *,command):
        EXCEPTIONS = ['toggle']
        command = self.bot.get_command(command)
        if command is None:
            return await ctx.send(f"Usage: `{ctx.prefix}toggle <command>`")
        if command.name in EXCEPTIONS:
            return await ctx.send(f"{self.emote_dict['error']} command {command.qualified_name} cannot be disabled.")

        command.enabled = not command.enabled
        ternary = "Enabled" if command.enabled else "Disabled"
        await ctx.send(f"{self.emote_dict['success']} {ternary} {command.qualified_name}.")


    @commands.command(hidden=True)
    async def leaveserver(self, ctx, *, target_server: converters.DiscordGuild = None):
        """Leaves a server - can take a name or id (owner only)."""
        if target_server is None:
            if ctx.guild:
                target_server = ctx.guild
            else:
                return await ctx.send(f"Usage: `{ctx.prefix}leaveserver <server>`")
        c = await pagination.Confirmation(
            f"{self.bot.emote_dict['exclamation']} **This action will result in me leaving `{target_server.name}.` Do you wish to continue?**"
        ).prompt(ctx)

        if c:
            await target_server.leave()
            try:
                await ctx.send(f"{self.emote_dict['success']} Successfully left server **{target_server.name}**")
            except:
                return
            return
        await ctx.send(f"{self.bot.emote_dict['exclamation']} **Cancelled.**")
