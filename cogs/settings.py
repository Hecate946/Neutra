import re
import asyncio
import discord

from discord.ext import commands, menus
from collections import OrderedDict

from utilities import permissions, pagination
from secret import constants


def setup(bot):
    bot.add_cog(Settings(bot))

class Settings(commands.Cog):
    """
    Configure your server settings.
    """

    def __init__(self, bot):
        self.bot = bot
        
        self.emote_dict = bot.emote_dict
        self.dregex = re.compile(r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?")
        #self.dregex = re.compile(r"(https?:\/\/)?(www\.)?(discord\.(gg|io|me|li)|discordapp\.com\/invite)\/.+[a-z]")
        #self.dregex = re.compile(r"(?i)(discord(\.gg|app\.com)\/)(?!attachments)([^\s]+)")

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
            await self.bot.cxn.execute("UPDATE moderation SET mute_role = $1 WHERE server_id = $2", role.id, ctx.guild.id)
        except Exception as e: return await ctx.send(e)
        msg = await ctx.send(f"{self.emote_dict['error']} Creating mute system. This process may take several minutes.")
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
        await msg.edit(content=f"{self.emote_dict['success']} Saved `{role.name}` as this server's mute role.")

    """ 
    @commands.command(aliases=["setprefix"], brief="Set your server's custom prefix.")
    @permissions.has_permissions(manage_guild=True)
    async def prefix(self, ctx, new: str = None):
        '''
        Usage: -prefix [new prefix]
        Alias: -setprefix
        Output: A new prefix for the server
        Example: -prefix $
        Notes: 
            The bot will always respond to @NGC0000 in addition 
            to the set prefix. The default prefix is -. 
            The bot will only respond to that prefix in DMs.
            The new prefix set must be under 5 characters.
        '''
        if new is None:
            prefix = await get_prefix(bot=self.bot, message=ctx.message)
            prefix = prefix[-1]
            await ctx.send(f"{ctx.author.mention}, the current prefix is {prefix}")
        else:
            if not ctx.guild: return await ctx.send("<:fail:816521503554273320> This command can only be used inside of servers.")
            if len(new) > 5:
                await ctx.send(f"{ctx.author.mention}, that prefix is too long. The prefix must be a maximum of five characters in length.")
            else:
                query = '''UPDATE servers SET prefix = $1 WHERE server_id = $2'''
                await self.bot.cxn.execute(query, new, ctx.guild.id)
                await ctx.send(f"{ctx.author.mention}, the prefix has been set to {new}") """


    @commands.command(aliases=["setprefix"], brief="Set your server's custom prefix.")
    @commands.guild_only()
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
            prefix = self.bot.server_settings[ctx.guild.id]['prefix']
            await ctx.send(f"{ctx.author.mention}, the current prefix is {prefix}")
        else:
            if len(new) > 5:
                await ctx.send(f"{ctx.author.mention}, that prefix is too long. The prefix must be a maximum of five characters in length.")
            else:
                self.bot.server_settings[ctx.guild.id]['prefix'] = new
                query = '''UPDATE servers SET prefix = $1 WHERE server_id = $2'''
                await self.bot.cxn.execute(query, new, ctx.guild.id)
                await ctx.send(f"{ctx.author.mention}, the prefix has been set to {new}")


    @commands.command(brief="Enable or disable auto-deleting invite links")
    @permissions.has_permissions(administrator=True)
    async def antiinvite(self, ctx, *, yes_no = None):
        """
        Usage:      -antiinvite <yes|enable|true|on||no|disable|false|off>
        Aliases:    -removeinvites, -deleteinvites, -antiinvites
        Permission: Administrator
        Output:     Removes invite links sent by users without the Manage Messages permission.
        """
        query = '''SELECT anti_invite FROM moderation WHERE server_id = $1'''
        current = await self.bot.cxn.fetchrow(query, ctx.guild.id) or None
        current = current[0]
        if current is True:
            removeinvitelinks = True
        else:
            removeinvitelinks = False
        if yes_no is None:
            # Output current setting
            msg =  "{} currently *{}*.".format("Removal of invite links","enabled" if current is True else "disabled")
        elif yes_no.lower() in [ "yes", "on", "true", "enabled", "enable" ]:
            yes_no = True
            removeinvitelinks = True
            msg = "{} {} *enabled*.".format("Removal of invite links","remains" if current is True else "is now")
        elif yes_no.lower() in [ "no", "off", "false", "disabled", "disable" ]:
            yes_no = False
            removeinvitelinks = False
            msg = "{} {} *disabled*.".format("Removal of invite links","is now" if current is True else "remains")
        else:
            msg = "That is not a valid setting."
            yes_no = current
        if yes_no != current:
            await self.bot.cxn.execute("UPDATE moderation SET anti_invite = $1 WHERE server_id = $2", removeinvitelinks, ctx.guild.id)
        await ctx.send(msg)


    @commands.Cog.listener()
    async def on_message(self, message):
        if self.bot.bot_ready is False:
            return
        if not message.guild: return
        if not self.dregex.search(message.content): return
        
        removeinvitelinks = await self.bot.cxn.fetchrow("SELECT anti_invite FROM moderation WHERE server_id = $1", message.guild.id) or None
        if removeinvitelinks is None:
            return
        if removeinvitelinks[0] is not True:
            return
        removeinvitelinks = removeinvitelinks[0]

        member = message.guild.get_member(message.author.id)
        if message.author.id in constants.owners: return # We are immune!
        if member.guild_permissions.manage_messages: return # We are immune!
  
        try:
            await message.delete()
            await message.channel.send("No invite links allowed", delete_after=7)
        except discord.Forbidden:
            return #await message.channel.send("I have insufficient permission to delete invite links")
        except discord.NotFound:
            return
        except Exception as e:
            return # await message.channel.send(e)


    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if self.bot.bot_ready is False:
            return
        if not before.guild: return
        if not self.dregex.search(after.content): return 
        
        removeinvitelinks = await self.bot.cxn.fetchrow("SELECT anti_invite FROM moderation WHERE server_id = $1", after.guild.id) or None
        if removeinvitelinks is None:
            return
        if removeinvitelinks[0] is not True:
            return
        removeinvitelinks = removeinvitelinks[0]

        member = after.guild.get_member(after.author.id)
        if after.author.id in constants.owners: return # We are immune!
        if member.guild_permissions.manage_messages: return # We are immune!
  
        try:
            await after.delete()
            await after.channel.send("No invite links allowed", delete_after=7)
        except discord.Forbidden: return #await message.channel.send("I have insufficient permission to delete invite links")
        except discord.NotFound: return
        except Exception as e: return # await message.channel.send(e)


    @commands.command(brief="Disallows certain users from using the bot within your server.")
    @permissions.has_permissions(administrator=True)
    async def ignore(self, ctx, user: discord.Member = None, react:str = "", *, reason: str = None):
        """
        Usage: -ignore <user> [react] [reason]
        Output: Will not process commands from the passed user.
        Permission: Administrator
        Notes:
            Specify the "react" to choose whether or not to
            react to the user's attempted commands.
        """

        if user is None: return await ctx.send(f"Usage: `{ctx.prefix}ignore <user> [react] [reason]`")

        if user.guild_permissions.administrator: return await ctx.send(f"{self.emote_dict['failed']} You cannot punish other staff members")
        if user.id in constants.owners: return await ctx.send(f"{self.emote_dict['failed']} You cannot punish my creator.")
        if user.top_role.position > ctx.author.top_role.position: return await ctx.send(f"{self.emote_dict['failed']} User `{user}` is higher in the role hierarchy than you.")

        if react.upper() == "REACT":
            react = True
        else:
            reason = react + " " + reason
            react = False

        query = '''SELECT server_id FROM ignored WHERE user_id = $1 AND server_id = $2'''
        already_ignord = await self.bot.cxn.fetchrow(query, user.id, ctx.guild.id)
        
        if "None" not in str(already_ignord):
            return await ctx.send(f"{self.emote_dict['error']} User `{user}` is already being ignored.")

        query = '''INSERT INTO ignored VALUES ($1, $2, $3, $4, $5, $6)'''
        await self.bot.cxn.execute(query, ctx.guild.id, user.id, ctx.author.id, reason, react, ctx.message.created_at.utcnow())
        if reason is not None:
            await ctx.send(f"{self.emote_dict['success']} Ignored `{user}` {reason}")
        else:
            await ctx.send(f"{self.emote_dict['success']} Ignored `{user}`")


    @commands.command(brief="Reallow certain to use using the bot within your server.", aliases=['listen'])
    @permissions.has_permissions(administrator=True)
    async def unignore(self, ctx, user: discord.Member = None):
        """
        Usage: -unignore <user>
        Output: Will delete the passed user from the ignored list
        Permission: Administrator
        """

        if user is None: return await ctx.send(f"Usage: `{ctx.prefix}ignore <user> [react] [reason]`")

        query = '''SELECT user_id FROM ignored WHERE user_id = $1 AND server_id = $2'''
        blacklisted = await self.bot.cxn.fetchrow(query, user.id, ctx.guild.id) or None
        if blacklisted is None: return await ctx.send(f"{self.emote_dict['error']} User was not ignored")

        query = '''SELECT reason FROM ignored WHERE user_id = $1 AND server_id = $2'''
        reason = await self.bot.cxn.fetchrow(query, user.id, ctx.guild.id) or None

        query = '''DELETE FROM ignored WHERE user_id = $1 AND server_id = $2'''
        await self.bot.cxn.execute(query, user.id, ctx.guild.id)

        if "None" in str(reason): 
            await ctx.send(f"{self.emote_dict['success']} Removed `{user}` from the ignore list.")
        else:
            await ctx.send(f"{self.emote_dict['success']} Removed `{user}`from the ignore list. " 
                           f"Previously ignored: `{reason[0]}`")


    async def message(self, message):
        # Check the message and see if we should allow it
        ctx = await self.bot.get_context(message)
        # never against the owners
        if message.author.id in constants.owners: return

        if not ctx.command:
            # No command - no need to check
            return
        # Get the list of ignored users
        
        query = '''SELECT user_id FROM ignored WHERE user_id = $1 and server_id = $2'''
        ignored_users = await self.bot.cxn.fetchrow(query, message.author.id, message.guild.id) or None
        if "None" in str(ignored_users):
            return
        if int(ignored_users[0]) != message.author.id: 
            return

        query = '''SELECT react FROM ignored WHERE user_id = $1 and server_id = $2'''
        to_react = await self.bot.cxn.fetchrow(query, message.author.id, message.guild.id)
        to_react = to_react[0]
        if to_react is True:
            await message.add_reaction(self.emote_dict['failed'])
        # We have an ignored user
        return { 'Ignore' : True, 'Delete' : False }
        
    @commands.command(brief="Toggle whether you want to have a user's old roles be reassigned to them on rejoin.", aliases=['stickyroles'])
    @commands.guild_only()
    @permissions.has_permissions(manage_guild=True)
    async def reassign(self, ctx, *, yes_no = None):
        """
        Usage:      -reassign <yes|enable|true|on||no|disable|false|off>
        Aliases:    -stickyroles
        Permission: Manage Server
        Output:     Reassigns roles when past members rejoin the server.
        """
        query = '''SELECT reassign FROM roleconfig WHERE server_id = $1'''
        current = await self.bot.cxn.fetchrow(query, ctx.guild.id)
        current = current[0]
        if current == False: 
            reassign = False
        else:
            current == True
            reassign = True
        if yes_no is None:
            # Output what we have
            msg =  "{} currently *{}*.".format("Reassigning roles on member rejoin","enabled" if current == True else "disabled")
        elif yes_no.lower() in [ "yes", "on", "true", "enabled", "enable" ]:
            yes_no = True
            reassign = True
            msg = "{} {} *enabled*.".format("Reassigning roles on member rejoin","remains" if current == True else "is now")
        elif yes_no.lower() in [ "no", "off", "false", "disabled", "disable" ]:
            yes_no = False
            reassign = False
            msg = "{} {} *disabled*.".format("Reassigning roles on member rejoin","is now" if current == True else "remains")
        else:
            msg = "That is not a valid setting."
            yes_no = current
        if yes_no != current:
            await self.bot.cxn.execute("UPDATE roleconfig SET reassign = $1 WHERE server_id = $2", reassign, ctx.guild.id)
        await ctx.send(msg)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if self.bot.bot_ready is False:
            return
        required_perms = member.guild.me.guild_permissions.manage_roles
        if not required_perms:
            return

        query = '''SELECT reassign FROM roleconfig WHERE server_id = $1'''
        reassign = await self.bot.cxn.fetchrow(query, member.guild.id)
        if reassign is False or reassign[0] is False: 
            pass
        else:
            query = '''SELECT roles FROM userroles WHERE user_id = $1 and server_id = $2'''
            old_roles = await self.bot.cxn.fetchrow(query, member.id, member.guild.id) or None
            if old_roles is None or old_roles[0] is None:
                return
            roles = str(old_roles[0]).split(",")
            for role_id in roles:
                role = member.guild.get_role(int(role_id))
                try:
                    await member.add_roles(role)
                except Exception as e: print(e)

        query = '''SELECT autoroles FROM roleconfig WHERE server_id = $1'''
        autoroles = await self.bot.cxn.fetchrow(query, member.guild.id) or None
        if autoroles is None or autoroles[0] is None: 
            return
        else:
            roles = str(autoroles[0]).split(",")
            for role_id in roles:
                role = self.bot.get_role(int(role_id))
                try:
                    await member.add_roles(role)
                except Exception as e: print(e)


    @commands.group(invoke_without_command=True, name="filter", aliases=['profanity'], brief="Manage the server's word filter list (Command Group).")
    @commands.guild_only()
    @permissions.has_permissions(manage_guild=True)
    async def _filter(self, ctx):
        """ 
        Usage:      -filter <method>
        Alias:      -profanity
        Example:    -filter add <badword>
        Permission: Manage Server
        Output:     Adds, removes, clears, or shows the filter.
        Methods:
            add
            remove
            display     (Alias: show)
            clear
        Notes:
            Words added the the filter list will delete all
            messages containing that word. Users with the
            Manage Messages permission are immune.
        """
        if ctx.invoked_subcommand is None:
            help_command = self.bot.get_command("help")
            await help_command(ctx, invokercommand="filter")


    @_filter.command(name="add", aliases=['+'])
    @permissions.has_permissions(manage_guild=True)
    async def add_word(self, ctx, *, words_to_filter: str=None):
        if words_to_filter is None:
            return await ctx.channel.send(f"Usage: `{ctx.prefix}filter add <word>`")

        words_to_filter = words_to_filter.split(",")

        insertion = ",".join(x.strip().lower() for x in words_to_filter)

        query = '''SELECT words FROM profanity WHERE server_id = $1'''
        word_list = await self.bot.cxn.fetchrow(query, ctx.guild.id) or None
        if word_list is None:         

            query = '''INSERT INTO profanity VALUES ($1, $2)'''
            await self.bot.cxn.execute(query, ctx.guild.id, insertion)

            await ctx.send(f'Added word{"" if len(insertion) == 1 else "s"} `{insertion}` to the filter')
        else:
            word_list = word_list[0].split(',')
            word_list = list(OrderedDict.fromkeys(word_list))

            for i in words_to_filter:
                if i not in word_list:
                    word_list.append(i.strip().lower())
                else:
                    old_index = word_list.index(i)
                    word_list.pop(old_index)
                    word_list.append(i)
        new_words = ','.join(word_list)
        await self.bot.cxn.execute("""
        UPDATE profanity SET words = $1 WHERE server_id = $2
        """, new_words, ctx.guild.id)
        await ctx.send(f'Added word{"" if len(insertion) == 1 else "s"} `{insertion}` to the filter')

    @_filter.command(name="remove", aliases=['-'], brief="Remove a word from the servers filtere list")
    @permissions.has_permissions(manage_guild=True)
    async def remove_word(self, ctx, *, word: str=None):
        if word is None:
            return await ctx.send(f"Usage: `{ctx.prefix}filter remove <word>`")


        query = '''SELECT words FROM profanity WHERE server_id = $1'''
        word_list = await self.bot.cxn.fetchrow(query, ctx.guild.id) or None
        if word_list is None:
            return await ctx.send(f"{self.emote_dict['error']} This server has no filtered words.")   

        word_list = word_list[0].split(',')
        word_list = list(OrderedDict.fromkeys(word_list))

        if word not in word_list: 
            return await ctx.send(f"{self.emote_dict['error']} Word `{word}` is not in the filtered list.")

        else:

            old_index = word_list.index(word)
            word_list.pop(old_index)
            new_words = ','.join(word_list)

            query = '''UPDATE profanity SET words = $1 WHERE server_id = $2'''
            await self.bot.cxn.execute(query, new_words, ctx.guild.id)

            await ctx.send(f'Removed "{word}" from the filter')


    @_filter.command(brief="Display a list of this server's filtered words.", aliases=['show'])
    @permissions.has_permissions(manage_guild=True)
    async def display(self, ctx):
        words = await self.bot.cxn.fetchrow("""
        SELECT words FROM profanity WHERE server_id = $1
        """, ctx.guild.id) or None


        if words == [] or words is None:
            return await ctx.send(f"No filtered words yet, use `{ctx.prefix}filter add <word>` to filter words")
        word_list = words[0].split(",")

        p = pagination.SimplePages(entries=[f"`{x}`" for x in word_list], per_page=20)
        p.embed.title = 'Filtered words in {} ({:,} total)'.format(ctx.guild.name,len(word_list))

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)


    @_filter.command(name="clear")
    @permissions.has_permissions(manage_guild=True)
    async def _clear(self, ctx):

        query = '''DELETE FROM profanity WHERE server_id = $1'''
        await self.bot.cxn.execute(query, ctx.guild.id)

        await ctx.send("Removed all filtered words")