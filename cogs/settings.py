import re
import discord

from discord.ext import commands, menus

from utilities import permissions, pagination


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
    @commands.bot_has_guild_permissions(manage_roles=True)
    @permissions.has_permissions(manage_guild=True)
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
        msg = await ctx.send(f"{self.emote_dict['error']} Creating mute system. This process may take several minutes.")
        if role is None:
            role = await ctx.guild.create_role(name="Muted", reason="For the server muting system")
        try:
            if ctx.guild.me.top_role.position < role.position:
                return await msg.edit(content=f"{self.bot.emote_dict['failed']} The muted role is above my highest role.")
            if ctx.author.top_role.position < role.position and ctx.author.id != ctx.guild.owner.id:
                return await msg.edit(content=f"{self.bot.emote_dict['failed']} The muted role is above your highest role.")
            await self.bot.cxn.execute("UPDATE servers SET muterole = $1 WHERE server_id = $2", role.id, ctx.guild.id)
        except Exception as e:
            return await msg.edit(content=e)
        channels = []
        for channel in ctx.guild.text_channels:
            try:
                await channel.set_permissions(role, send_messages=False)
            except discord.Forbidden:
                channels.append(channel.name)
                continue
        if channels:
            return await msg.edit(content=f"{self.bot.emote_dict['failed']} I do not have permission to edit channel{'' if len(channels) == 1 else 's'}: `{', '.join(channels)}`")
        # muted_channel = []
        # for channel in ctx.guild.channels:
        #     if channel.name == "muted":
        #         muted_channel.append(channel)
        # if not muted_channel:
        #     overwrites = {
        #     ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        #     role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        #     }
        #     await ctx.guild.create_text_channel(name="muted", overwrites=overwrites, topic="Punishment Channel", slowmode_delay = 30)
        await msg.edit(content=f"{self.emote_dict['success']} Saved `{role.name}` as this server's mute role.")

        


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
            await ctx.reply(f"The current prefix is `{prefix}`")
        else:
            if len(new) > 5:
                await ctx.send(f"{ctx.author.mention}, that prefix is too long. The prefix must be a maximum of five characters in length.")
            else:
                self.bot.server_settings[ctx.guild.id]['prefix'] = new
                query = '''UPDATE servers SET prefix = $1 WHERE server_id = $2'''
                await self.bot.cxn.execute(query, new, ctx.guild.id)
                await ctx.reply(f"{self.bot.emote_dict['success']} The prefix has been set to `{new}`")


    @commands.command(brief="Enable or disable auto-deleting invite links", aliases=['removeinvitelinks','deleteinvites','antiinvites'])
    @permissions.has_permissions(manage_guild=True)
    async def antiinvite(self, ctx, *, yes_no = None):
        """
        Usage:      -antiinvite <yes|enable|true|on||no|disable|false|off>
        Aliases:    -removeinvites, -deleteinvites, -antiinvites
        Permission: Administrator
        Output:     Removes invite links sent by users without the Manage Messages permission.
        """
        query = '''SELECT antiinvite FROM servers WHERE server_id = $1'''
        current = await self.bot.cxn.fetchval(query, ctx.guild.id)
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
        if yes_no != current and yes_no is not None:
            self.bot.server_settings[ctx.guild.id]['antiinvite'] = removeinvitelinks
            await self.bot.cxn.execute("UPDATE servers SET antiinvite = $1 WHERE server_id = $2", removeinvitelinks, ctx.guild.id)
        await ctx.send(msg)


    @commands.Cog.listener()
    async def on_message(self, message):
        if self.bot.bot_ready is False:
            return
        if not message.guild: return
        if not self.dregex.search(message.content): return
        
        removeinvitelinks = self.bot.server_settings[message.guild.id]['antiinvite']

        if removeinvitelinks is not True:
            return

        member = message.guild.get_member(message.author.id)
        if message.author.id in self.bot.constants.owners: return # We are immune!
        if member.guild_permissions.manage_messages: return # We are immune!
  
        try:
            await message.delete()
            await message.channel.send("No invite links allowed", delete_after=7)
        except Exception:
            return # await message.channel.send(e)


    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if self.bot.bot_ready is False:
            return
        if not before.guild: return
        if not self.dregex.search(after.content): return 
        
        removeinvitelinks = self.bot.server_settings[after.guild.id]['antiinvite']

        if removeinvitelinks is not True:
            return

        member = after.author
        if member.id in self.bot.constants.owners: return # We are immune!
        if member.guild_permissions.manage_messages: return # We are immune!
        try:
            await after.delete()
            await after.channel.send("No invite links allowed", delete_after=7)
        except Exception:
            return


    @commands.command(brief="Disallows certain users from using the bot within your server.")
    @permissions.has_permissions(administrator=True)
    async def ignore(self, ctx, user: discord.Member = None, react:str = ""):
        """
        Usage: -ignore <user> [react] [reason]
        Output: Will not process commands from the passed user.
        Permission: Administrator
        Notes:
            Specify the "react" to choose whether or not to
            react to the user's attempted commands.
        """

        if user is None:
            return await ctx.send(f"Usage: `{ctx.prefix}ignore <user> [react]`")

        if user.guild_permissions.administrator: return await ctx.send(f"{self.emote_dict['failed']} You cannot punish other staff members")
        if user.id in self.bot.constants.owners: return await ctx.send(f"{self.emote_dict['failed']} You cannot punish my creator.")
        if user.top_role.position > ctx.author.top_role.position: return await ctx.send(f"{self.emote_dict['failed']} User `{user}` is higher in the role hierarchy than you.")

        if react is None:
            react = False

        if react.upper() == "REACT":
            react = True
        else:
            react = False

        query = '''SELECT server_id FROM ignored WHERE user_id = $1 AND server_id = $2'''
        already_ignored = await self.bot.cxn.fetchval(query, user.id, ctx.guild.id) or None
        
        if already_ignored is not None:
            return await ctx.send(f"{self.emote_dict['error']} User `{user}` is already being ignored.")

        query = '''INSERT INTO ignored VALUES ($1, $2, $3, $4, $5)'''
        await self.bot.cxn.execute(query, ctx.guild.id, user.id, ctx.author.id, react, ctx.message.created_at.utcnow())

        self.bot.server_settings[ctx.guild.id]['ignored_users'][user.id] = react

        await ctx.send(f"{self.emote_dict['success']} Ignored `{user}`")


    @commands.command(brief="Reallow certain to use using the bot within your server.", aliases=['listen'])
    @commands.guild_only()
    @permissions.has_permissions(administrator=True)
    async def unignore(self, ctx, user: discord.Member = None):
        """
        Usage: -unignore <user>
        Alias: -listen
        Output: Will delete the passed user from the ignored list
        Permission: Administrator
        """

        if user is None:
            return await ctx.send(f"Usage: `{ctx.prefix}unignore <user>`")

        query = '''SELECT user_id FROM ignored WHERE user_id = $1 AND server_id = $2'''
        blacklisted = await self.bot.cxn.fetchval(query, user.id, ctx.guild.id) or None
        if blacklisted is None:
            return await ctx.send(f"{self.emote_dict['error']} User was not ignored.")


        query = '''DELETE FROM ignored WHERE user_id = $1 AND server_id = $2'''
        await self.bot.cxn.execute(query, user.id, ctx.guild.id)

        self.bot.server_settings[ctx.guild.id]['ignored_users'].pop(user.id, None)

        await ctx.send(f"{self.emote_dict['success']} Removed `{user}` from the ignore list.")


    async def message(self, message):
        # Check the message and see if we should allow it
        ctx = await self.bot.get_context(message)
        # never against the owners
        if message.author.id in self.bot.constants.owners: return

        if not ctx.command:
            # No command - no need to check
            return

        try:
            react = self.bot.server_settings[message.guild.id]['ignored_users'][message.author.id]
        except KeyError:
            # This means they aren't in the dict of ignored users.
            return

        if react is True:
            await message.add_reaction(self.emote_dict['failed'])
        # We have an ignored user
        return { 'Ignore' : True, 'Delete' : False }
        

    @commands.command(brief="Toggle whether you want to have a user's old roles be reassigned to them on rejoin.", aliases=['stickyroles'])
    @commands.guild_only()
    @commands.bot_has_guild_permissions(manage_roles=True)
    @permissions.has_permissions(manage_guild=True, manage_roles=True)
    async def reassign(self, ctx, *, yes_no = None):
        """
        Usage:      -reassign <yes|enable|true|on||no|disable|false|off>
        Aliases:    -stickyroles
        Permission: Manage Server
        Output:     Reassigns roles when past members rejoin the server.
        """
        current = self.bot.server_settings[ctx.guild.id]['reassign']
        if current == False: 
            reassign = False
        else:
            current == True
            reassign = True
        if yes_no is None:
            # Output what we have
            msg =  "{} currently **{}**.".format("Reassigning roles on member rejoin","enabled" if current == True else "disabled")
        elif yes_no.lower() in [ "yes", "on", "true", "enabled", "enable" ]:
            yes_no = True
            reassign = True
            msg = "{} {} **enabled**.".format("Reassigning roles on member rejoin","remains" if current == True else "is now")
        elif yes_no.lower() in [ "no", "off", "false", "disabled", "disable" ]:
            yes_no = False
            reassign = False
            msg = "{} {} **disabled**.".format("Reassigning roles on member rejoin","is now" if current == True else "remains")
        else:
            msg = f"{self.bot.emote_dict['error']} That is not a valid setting."
            yes_no = current
        if yes_no != current and yes_no is not None:
            await self.bot.cxn.execute("UPDATE servers SET reassign = $1 WHERE server_id = $2", reassign, ctx.guild.id)
            self.bot.server_settings[ctx.guild.id]['reassign'] = reassign
        await ctx.send(msg)


    @commands.Cog.listener()
    async def on_member_join(self, member):
        if self.bot.bot_ready is False:
            return
        required_perms = member.guild.me.guild_permissions.manage_roles
        if not required_perms:
            return

        reassign = self.bot.server_settings[member.guild.id]['reassign']
        if reassign is not True:
            pass
        else:
            query = '''SELECT roles FROM userroles WHERE user_id = $1 and server_id = $2'''
            old_roles = await self.bot.cxn.fetchval(query, member.id, member.guild.id) or None
            if old_roles is None:
                return
            roles = str(old_roles).split(",")
            for role_id in roles:
                role = member.guild.get_role(int(role_id))
                try:
                    await member.add_roles(role)
                except Exception as e:
                    print(e)

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
                except Exception as e:
                    print(e)


    @commands.group(invoke_without_command=True, name="filter", aliases=['profanity'], brief="Manage the server's word filter list (Command Group).")
    @commands.guild_only()
    @permissions.has_permissions(manage_guild=True)
    async def _filter(self, ctx):
        """ 
        Usage:      -filter <method>
        Alias:      -profanity
        Example:    -filter add <badwords>
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
            Manage Messages permission are immune. To add or 
            remove multiple words with one command, separate 
            the words with a comma.
            Example: -filter add badword1, badword2, badword3
        """
        if ctx.invoked_subcommand is None:
            help_command = self.bot.get_command("help")
            await help_command(ctx, invokercommand="filter")


    @_filter.command(name="add", aliases=['+'])
    @permissions.has_permissions(manage_guild=True)
    async def add_words(self, ctx, *, words_to_filter: str=None):
        if words_to_filter is None:
            return await ctx.channel.send(f"Usage: `{ctx.prefix}filter add <word>`")

        words_to_filter = words_to_filter.split(",")


        current_filter = self.bot.server_settings[ctx.guild.id]['profanities']

        added = []
        existing = []
        for word in words_to_filter:
            if word.strip().lower() not in current_filter:
                current_filter.append(word.strip().lower())
                added.append(word.strip().lower())
            else:
                existing.append(word.strip().lower())

        insertion = ",".join(current_filter)

        query = '''UPDATE servers SET profanities = $1 WHERE server_id = $2;'''
        await self.bot.cxn.execute(query, insertion, ctx.guild.id)

        if existing:
            await ctx.send(
                f"{self.bot.emote_dict['error']} The word{'' if len(existing) == 1 else 's'} `{', '.join(existing)}` "
                f"{'was' if len(existing) == 1 else 'were'} already in the word filter."
            )
        
        if added:
            await ctx.send(
                f"{self.bot.emote_dict['success']} The word{'' if len(added) == 1 else 's'} `{', '.join(added)}` "
                f"{'was' if len(added) == 1 else 'were'} successfully added to the word filter."
            )

    @_filter.command(name="remove", aliases=['-'], brief="Remove a word from the servers filtere list")
    @permissions.has_permissions(manage_guild=True)
    async def remove_words(self, ctx, *, words: str=None):
        if words is None:
            return await ctx.send(f"Usage: `{ctx.prefix}filter remove <word>`")

        words_to_remove = words.lower().split(',')

        word_list = self.bot.server_settings[ctx.guild.id]['profanities']
        if word_list == []:
            return await ctx.send(f"{self.emote_dict['error']} This server has no filtered words.")  

        removed = []
        not_found = []
        for word in words_to_remove:
            if word.strip().lower() not in word_list:
                not_found.append(word)
                continue
            else:
                word_index = word_list.index(word.strip().lower())
                word_list.pop(word_index)
                removed.append(word.strip().lower())
        
        insertion = ','.join(word_list)

        query = '''UPDATE servers SET profanities = $1 WHERE server_id = $2;'''
        await self.bot.cxn.execute(query, insertion, ctx.guild.id)

        if not_found:
            await ctx.send(
                f"{self.bot.emote_dict['error']} The word{'' if len(not_found) == 1 else 's'} `{', '.join(not_found)}` "
                f"{'was' if len(not_found) == 1 else 'were'} not in the word filter."
            )
        
        if removed:
            await ctx.send(
                f"{self.bot.emote_dict['success']} The word{'' if len(removed) == 1 else 's'} `{', '.join(removed)}` "
                f"{'was' if len(removed) == 1 else 'were'} successfully removed from the word filter."
            )


    @_filter.command(brief="Display a list of this server's filtered words.", aliases=['show'])
    @permissions.has_permissions(manage_guild=True)
    async def display(self, ctx):
        words = self.bot.server_settings[ctx.guild.id]['profanities']

        if words == []:
            return await ctx.send(f"No filtered words yet, use `{ctx.prefix}filter add <word>` to filter words")

        p = pagination.SimplePages(entries=[f"`{x}`" for x in words], per_page=20)
        p.embed.title = 'Filtered words in {} ({:,} total)'.format(ctx.guild.name, len(words))

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)


    @_filter.command(name="clear")
    @permissions.has_permissions(manage_guild=True)
    async def _clear(self, ctx):

        query = '''UPDATE servers SET profanities = NULL where server_id = $1;'''
        await self.bot.cxn.execute(query, ctx.guild.id)
        self.bot.server_settings[ctx.guild.id]['profanities'] = []

        await ctx.send(f"{self.bot.emote_dict['success']} Removed all filtered words.")