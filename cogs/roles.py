import discord
import colorsys

from io import BytesIO
from discord.ext import commands

from utilities import permissions, default
from core import OWNERS


EMBED_MAX_LEN = 2048 # constant for paginating embeds
MAX_USERS = 30 # max people to list for -whohas
STATUSMAP1 = {discord.Status.online:'1',discord.Status.dnd:'2',discord.Status.idle:'3'} ##for sorting
STATUSMAP2 = {discord.Status.online:'<:online:810650040838258711>',discord.Status.dnd:'<:dnd:810650845007708200>',discord.Status.idle:'<:idle:810650560146833429>',discord.Status.offline:'<:offline:810650959859810384>'}


def setup(bot):
    bot.add_cog(Roles(bot))


class Roles(commands.Cog):
    """
    Manage all actions regarding roles.
    """
    def __init__(self, bot):
        self.bot = bot
        self.cxn = bot.connection


    @commands.command(brief="Gets info on a specific role", aliases=["ri"])
    @commands.guild_only()
    async def roleinfo(self, ctx, *, role: discord.Role):
        """
        Usage:  -roleinfo <role>
        Alias:  -ri
        Output: Info on the passed role
        """
        
        owner = ctx.guild.owner
        member = ctx.message.author
        guild=ctx.guild

        # perm_list = [Perm[0] for Perm in role.permissions if Perm[1]]

        embed = discord.Embed(color=default.config()["embed_color"], timestamp=ctx.message.created_at)
        
        embed.set_author(name=f"{owner}", icon_url=owner.avatar_url)
        embed.set_thumbnail(url=guild.icon_url)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar_url)

        embed.add_field(name=f"**Role Info for {role.name}:**", value=
                                                                           f"> **Name:** {role.mention}\n"
                                                                           f"> **ID:** {role.id}\n"
                                                                           f"> **Guild:** {role.guild}\n"
                                                                           f"> **Created at:** {role.created_at.__format__('%B %d, %Y at %I:%M %p')}\n"
                                                                           f"> **Position:** {role.position}\n"
                                                                           f"> **Hoisted:** {role.hoist}\n"
                                                                           f"> **Color:** {role.color}\n"
                                                                           f"> **Mentionable:** {role.mentionable}\n"
                                                                           f"> **Managed:** {role.managed}\n"
                                                                           # f"> **Bot Role:** {role.is_bot_managed()}\n"
                                                                           # f"> **Booster Role:** {role.is_premium_subscriber()}\n"
                                                                           , inline=False)
        # embed.add_field(name="Permissions:", value=str(role.permissions), inline=False)
        # embed.add_field(name="Permissions:", value=", ".join(perm_list).replace("_", " ").replace("guild", "server").title().replace("Tts", "TTS"), inline=False)
# .replace("_", " ").replace("guild", "server").title().replace("Tts", "TTS")
        await ctx.send(embed=embed)


    @commands.command(aliases=["ar",'adrl', 'addrl', 'adrole'], brief="Adds multiple roles to multiple users")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @permissions.has_permissions(manage_guild=True, manage_roles=True)
    async def addrole(self, ctx, targets: commands.Greedy[discord.Member], *roles: discord.Role):
        """
        Usage:      -removerole [user] [user...] [role] [role]...
        Aliases:    -ar, -adrole, -adrl, -addrl
        Example:    -ar Hecate#3523 @NGC0000 @Verified Member
        Permission: Manage Server, Manage Roles
        Output:     Adds multiple roles to multiple users
        """
        if ctx.message.guild.me.permissions_in(ctx.message.channel).manage_roles == False: return await ctx.send("Sorry, I do not have the manage_roles permission")

        if len(targets) == 0: return await ctx.send(f"Usage: `{ctx.prefix}ar <user> [user] [user] <role> [role] [role]...`")
        if len(roles) == 0: return await ctx.send(f"Usage: `{ctx.prefix}ar <user> [user] [user] <role> [role] [role]...`")
        target_list = []
        target_names = []
        for target in targets:
            role_list = []
            for role in roles:
                if role.permissions.administrator and ctx.author.id not in OWNERS: return await ctx.send("I cannot manipulate an admin role")
                if role.position >= ctx.author.top_role.position and ctx.author.id not in OWNERS: return await ctx.send("That role is higher than your highest role") 
                try:
                    await target.add_roles(role)
                except discord.Forbidden:
                    return await ctx.send('I do not have permission to do that')
                role_list.append(role)
                target_list.append(target)
            if role_list:
                role_names = []
                for role in role_list: 
                    name = role.name
                    role_names += [name]
            name = f"{target.name}#{target.discriminator}"
            target_names.append(name)
        await ctx.send(f'<:checkmark:816534984676081705> '
                       f'Added user{"" if len(target_names) == 1 else "s"} `{", ".join(target_names)}` '
                       f'the role{"" if len(role_list) == 1 else "s"} `{", ".join(role_names)}`')


    @commands.command(aliases=["rr",'remrole','rmrole','rmrl'], brief="Removes multiple roles from multiple users")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @permissions.has_permissions(manage_guild=True, manage_roles=True)
    async def removerole(self, ctx, targets: commands.Greedy[discord.Member], *roles: discord.Role):
        """
        Usage:      -removerole [user] [user...] [role] [role]...
        Aliases:    -rr, -remrole, -rmrole, -rmrl
        Example:    -rr Hecate#3523 @NGC0000 @Verified Member
        Permission: Manage Server, Manage Roles
        Output:     Removes multiple roles from multiple users
        """
        if ctx.message.guild.me.permissions_in(ctx.message.channel).manage_roles == False: return await ctx.send("Sorry, I do not have the manage_roles permission")

        if len(targets) == 0: return await ctx.send(f"Usage: `{ctx.prefix}rr <user> [user] [user] <role> [role] [role]...`")
        if len(roles) == 0: return await ctx.send(f"Usage: `{ctx.prefix}rr <user> [user] [user] <role> [role] [role]...`")
        target_list = []
        target_names = []
        for target in targets:
            role_list = []
            for role in roles:
                if role.permissions.administrator and ctx.author.id not in OWNERS: return await ctx.send("I cannot manipulate an admin role")
                if role.position > ctx.author.top_role.position and ctx.author.id not in OWNERS and ctx.author.id != ctx.guild.owner.id: 
                    return await ctx.send("That role is higher than your highest role") 
                if role.position == ctx.author.top_role.position and ctx.author.id not in OWNERS and ctx.author.id != ctx.guild.owner.id: 
                    return await ctx.send("That role is your highest role") 
                try:
                    await target.remove_roles(role)
                except discord.Forbidden:
                    return await ctx.send('I do not have permission to do that')
                role_list.append(role)
                target_list.append(target)
            if role_list:
                role_names = []
                for role in role_list: 
                    name = role.name
                    role_names += [name]
            name = f"{target.name}#{target.discriminator}"
            target_names.append(name)
        await ctx.send(f'<:checkmark:816534984676081705> '
                       f'Removed user{"" if len(target_names) == 1 else "s"} `{", ".join(target_names)}` '
                       f'the role{"" if len(role_list) == 1 else "s"} `{", ".join(role_names)}`')


    @commands.command(brief="Sends a txt file to your DMs with a list of roles for the server")
    @commands.guild_only()
    @permissions.has_permissions(manage_messages=True)
    async def dumproles(self, ctx):
        """
        Usage:  -dumproles
        Alias:  -txtroles
        Output:  Sends a list of roles for the server to your DMs
        Permission: Manage Messages
        """
        allroles = ""

        for num, role in enumerate(sorted(ctx.guild.roles, reverse=True), start=1):
            allroles += f"[{str(num).zfill(2)}] {role.id}\t{role.name}\t[ Users: {len(role.members)} ]\r\n"

        data = BytesIO(allroles.encode('utf-8'))
        try:
            await ctx.author.send(content=f"Roles in **{ctx.guild.name}**", file=discord.File(data, filename=f"{default.timetext('Roles')}"))
            await ctx.message.add_reaction("📬")
        except:
            await ctx.send(content=f"Roles in **{ctx.guild.name}**", file=discord.File(data, filename=f"{default.timetext('Roles')}"))


    @commands.command(aliases=['cr','rolecreate'], brief="Create a role with a specified name")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @permissions.has_permissions(manage_roles=True)
    async def createrole(self, ctx, *, role_name:str):
        """
        Usage:      -createrole <name>
        Aliases:    -cr, -rolecreate
        Output:     Creates a role with your specified name
        Permission: Manage Roles
        """
        if role_name is None: return await ctx.send(f"Usage: `{ctx.prefix}createrole <role>`")
        try:
            await ctx.guild.create_role(name=role_name)
            role = discord.utils.get(ctx.guild.roles, name=role_name)
            await ctx.send(f'<:checkmark:816534984676081705> Created role `{role.name}`')
        except discord.Forbidden:
            await ctx.send('<:fail:816521503554273320> I do not have sufficient permissions to create roles.')


    @commands.command(brief="Deletes a role with a specified name.", aliases=["dr","roledelete"])
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @permissions.has_permissions(administrator=True)
    async def deleterole(self, ctx, *, role: discord.Role):
        """
        Usage:      -deleterole <name>
        Aliases:    -dr, -roledelete
        Output:     Deletes a role with your specified name
        Permission: Administrator
        """
        if role is None: return await ctx.send(f"Usage: `{ctx.prefix}deleterole <role>`")
        else:
            await role.delete()
            await ctx.send(f'<:checkmark:816534984676081705> Deleted role `{role.name}`')

        
    @commands.group(brief="Adds or removes a role to all users with a role. (Command Group)", aliases=['multirole'])
    @commands.guild_only()
    @commands.bot_has_permissions(manage_guild=True, manage_roles=True)
    @permissions.has_permissions(manage_guild=True, manage_roles=True)
    async def massrole(self, ctx):
        """ 
        Usage:      -massrole <method> <role1> <role2>
        Alias:      -multirole
        Example:    -massrole add @everyone Verified
        Permission: Manage Server, Manage Roles
        Output:     Adds or removes a role to all users with a given role
        Methods:
            add          
            remove (Aliases: rem, rm)
       
        Notes:
            Command may take a few minutes to complete its execution.
            Please be patient.
        """
        if ctx.invoked_subcommand is None:
            help_command = self.bot.get_command("help")
            await help_command(ctx, invokercommand="massrole")


    @massrole.command(brief="Adds all members with a certain role a new role.")
    @permissions.has_permissions(manage_guild=True)
    async def add(self, ctx, role1: discord.Role = None, role2: discord.Role = None):
        if role1 is None: return await ctx.send('Usage: `{ctx.prefix}massrole add <role1> <role2> ')
        if role2 is None: return await ctx.send('Usage: `{ctx.prefix}massrole add <role1> <role2> ')
        if ctx.author.top_role.position < role2.position and ctx.author.id not in OWNERS: return await ctx.send("You have insufficient permission to execute this command")
        if ctx.author.top_role.position < role1.position and ctx.author.id not in OWNERS: return await ctx.send("You have insufficient permission to execute this command")
        if role2.permissions.administrator and ctx.author.id not in OWNERS: return await ctx.send("I cannot manipulate an admin role")
        number_of_members = []
        for member in ctx.guild.members:
            if role1 in member.roles and not role2 in member.roles:
                number_of_members.append(member)

        members_to_add_roles = len(number_of_members)
        if members_to_add_roles < 1: return await ctx.send(f"<:error:816456396735905844> No members to add roles to")
        msg = await ctx.send(f"<:error:816456396735905844> Adding role `{role2.name}` to `{members_to_add_roles}` member{'' if members_to_add_roles == 1 else 's'}. This process may take several minutes.")
        for member in role1.members: 
            try:
                await member.add_roles(role2)
            except discord.Forbidden:
                return await ctx.send("I do not have permission to do that")
        # we made it
        await msg.edit(content=f"<:checkmark:816534984676081705> Added role `{role2.name}` to `{members_to_add_roles}` member{'' if members_to_add_roles == 1 else 's'}")


    @massrole.command(brief="Removes all members with a certain role a new role", aliases=["rm","rem"])
    async def remove(self, ctx, role1: discord.Role, role2: discord.Role):
        if role1 is None: return await ctx.send('Usage: `{ctx.prefix}massrole add <role1> <role2> ')
        if role2 is None: return await ctx.send('Usage: `{ctx.prefix}massrole add <role1> <role2> ')
        if ctx.author.top_role.position < role2.position and ctx.author.id not in OWNERS: return await ctx.send("You have insufficient permission to execute this command")
        if ctx.author.top_role.position < role1.position and ctx.author.id not in OWNERS: return await ctx.send("You have insufficient permission to execute this command")
        if role2.permissions.administrator and ctx.author.id not in OWNERS: return await ctx.send("I cannot manipulate an admin role")
        number_of_members = []
        for member in ctx.guild.members:
            if role1 in member.roles and role2 in member.roles:
                number_of_members.append(member)

        members_to_add_roles = len(number_of_members)
        if members_to_add_roles < 1: return await ctx.send(f"<:error:816456396735905844> No members to remove roles from")
        msg = await ctx.send(f"<:error:816456396735905844> Removing role `{role2.name}` from `{members_to_add_roles}` member{'' if members_to_add_roles == 1 else 's'}. This process may take several minutes.")
        for member in role1.members: 
            try:
                await member.remove_roles(role2)
            except discord.Forbidden:
                return await ctx.send("I do not have permission to do that")
        # we made it
        await msg.edit(content=f"<:checkmark:816534984676081705> Removed role `{role2.name}` from `{members_to_add_roles}` member{'' if members_to_add_roles == 1 else 's'}")


    def get_user(message, user):
        try:
            member = message.mentions[0]
        except:
            member = message.guild.get_member_named(user)
        if not member:
            try:
                member = message.guild.get_member(int(user))
            except ValueError:
                pass
        if not member:
            return None
        return member

    def role_check(self, user, role_query):
        # returns True or False if a user has named role
        return any((role.name in role_query for role in user.roles))

    def alphanum_filter(self, text):
        # filter for searching a role by name without having to worry about case or punctuation
        return ''.join(i for i in text if i.isalnum()).lower()

    def rolelist_filter(self, roles, id_list):
        # filters the full role hierarchy based on the predefined lists above
        return [role for role in roles if int(role.id) in id_list]

    def get_named_role(self, server, rolename):
        # finds a role in a server by name
        check_name = self.alphanum_filter(rolename)
        return next((role for role in server.roles if self.alphanum_filter(role.name) == check_name),None)

    def role_accumulate(self, check_roles, members):
        ## iterate over the members to accumulate a count of each role
        rolecounts = {}
        for role in check_roles: # populate the accumulator dict
            if not role.is_default():
                rolecounts[role] = 0

        for member in members:
            for role in member.roles:
                if role in check_roles and not role.is_default(): # want to exclude @everyone from this list
                    rolecounts[role] += 1

        return rolecounts

    async def rolelist_paginate(self, ctx, rlist, title='Server Roles'):
        # takes a list of roles and counts and sends it out as multiple embed as nessecary
        pages = []
        buildstr = ''
        for role,count in rlist: # this generates and paginates the info
            line = '{:,} {}\n'.format(count,role.mention)
            if len(buildstr) + len(line) > EMBED_MAX_LEN:
                pages.append(buildstr) # split the page here
                buildstr = line
            else:
                buildstr += line
        if buildstr:
            pages.append(buildstr) #if the string has data not already listed in the pages, add it

        for index,page in enumerate(pages): # enumerate so we can add a page number
            embed = discord.Embed(title=f'{title}', description=page, color=default.config()["embed_color"])
            embed.set_footer(text='Page {:,}/{:,}'.format(index+1, len(pages)))
            await ctx.send(embed=embed)

    # The next couple commands are mostly from CorpBot.py with a few modifications
    # https://github.com/corpnewt/CorpBot.py

    @commands.command(pass_context=True, brief="Shows an embed of all the server roles.", aliases=["roles"])
    @commands.guild_only()
    @permissions.has_permissions(manage_messages=True)
    async def listroles(self, ctx, sort_order:str='default'):
        """
        Usage: -listroles
        Alias: -roles
        Output:
            Shows roles and their member counts. Takes one argument,
            sort_order, which can be default, name, count, or color.
        Permission: Manage Messages    
        """

        sort_order = sort_order.lower()
        if not sort_order in ['default', 'name', 'count', 'color']: # make sure it has valid args
            return await ctx.send("Invalid arguments.\n ```yaml\nVALID OPTIONS:\n=============\n\n default\nname\ncount\ncolor\n```")
        
        check_roles = ctx.guild.roles # we use roles for these because sometimes we want to see the order
        
        ## now we iterate over the members to accumulate a count of each role
        rolecounts = self.role_accumulate(check_roles, ctx.guild.members)
        
        sorted_list = []
        if sort_order == 'default': # default sort = the server role hierarchy
            for role in check_roles:
                if role in rolecounts:
                    sorted_list.append((role, rolecounts.get(role,0)))
        elif sort_order == 'name': # name sort = alphabetical by role name
            sorted_list = sorted(rolecounts.items(), key=lambda tup: tup[0].name.lower())
        elif sort_order == 'count': # count sort = decreasing member count
            sorted_list = sorted(rolecounts.items(), key=lambda tup: tup[1], reverse=True)
        elif sort_order == 'color': # color sort: by increasing hue value in HSV color space
            sorted_list = sorted(rolecounts.items(), key=lambda tup: colorsys.rgb_to_hsv(tup[0].color.r, tup[0].color.g, tup[0].color.b)[0])
        
        if not sorted_list: # another failsafe
            return

        sorted_list = sorted_list[::-1]
        await self.rolelist_paginate(ctx,sorted_list) # send the list to get actually printed to discord


    @commands.command(pass_context=True, brief="Counts the number of members with a specific role.")
    @commands.guild_only()
    async def rolecall(self, ctx, *, rolename):
        """
        Usage: -rolecall <role>
        Output: 
            Shows the number of people with the passed role.
        """
        check_role = self.get_named_role(ctx.guild, rolename)
        if not check_role:
            return await ctx.send("<:fail:816521503554273320> I could not find that role!")

        count = 0
        online = 0
        for member in ctx.guild.members:
            if check_role in member.roles:
                count += 1
                if member.status != discord.Status.offline:
                    online += 1

        embed = discord.Embed(title=check_role.name, description='{}/{} online'.format(online, count), color=default.config()["embed_color"])
        embed.set_footer(text='ID: {}'.format(check_role.id))
        await ctx.send(embed=embed)

    @commands.command(pass_context=True, brief="Lists the people who have the specified role.")
    @commands.guild_only()
    async def whohas(self, ctx, *, rolename):
        """
        Usage: -whohas <role>
        Output:
            Lists the people who have the specified role with their status.
        Notes:
            Can take a -nick or -username argument to enhance output.
        """
        mode = 0 # tells how to display: 0 = just mention, 1 = add nickname, 2 = add username
        rolename = rolename.lower()
        if '-nick' in rolename:
            mode = 1
            rolename = rolename.replace('-nick','')
        elif '-username' in rolename:
            mode = 2
            rolename = rolename.replace('-username','')

        check_role = self.get_named_role(ctx.guild, rolename)
        if not check_role:
            return await ctx.send("I can't find that role!")

        users = [member for member in ctx.guild.members if check_role in member.roles]

        sorted_list = sorted(users, key=lambda usr: (STATUSMAP1.get(usr.status,'4')) + (usr.nick.lower() if usr.nick else usr.name.lower()))
        truncated = False
        if len(sorted_list) > MAX_USERS:
            sorted_list = sorted_list[:MAX_USERS] ## truncate to the limit
            truncated = True
        if mode == 2: # add full username
            page = '\n'.join('{} {} ({}#{})'.format(STATUSMAP2.get(member.status, '<:offline:810650959859810384>'), member.mention, member.name, member.discriminator) for member in sorted_list) # not bothering with multiple pages cause 30 members is way shorter than one embed
        elif mode == 1: # add nickname
            page = '\n'.join('{} {} ({})'.format(STATUSMAP2.get(member.status, '<:offline:810650959859810384>'), member.mention, member.display_name) for member in sorted_list)
        else:
            page = '\n'.join('{} {}'.format(STATUSMAP2.get(member.status, '<:offline:810650959859810384>'), member.mention) for member in sorted_list)

        if truncated:
            page += '\n*and {} more...*'.format(len(users) - MAX_USERS)

        embed = discord.Embed(title='{:,} members with {}'.format(len(users), check_role.name), description=page, color=check_role.color)
        embed.set_footer(text='ID: {}'.format(check_role.id))
        await ctx.send(embed=embed)


    @commands.command(aliases=['rp'], brief="Get the permissions for a passed role.")
    @commands.guild_only()
    async def roleperms(self, ctx, *, role):
        """
        Usage:  -roleperms <role>
        Alias:  -rp
        Output: Embed with all the permissions granted to that role
        """

        permissions = ""
        permissionsne = ""
        role = discord.utils.get(ctx.message.guild.roles, name=role)
        try:
            for perm in role.permissions:
                perm = (perm[0].replace("_", " ").title(), perm[1])
                permissions += "**{}**: {}\n".format(*perm)
                permissionsne += "{}: {}\n".format(*perm)
            embed = discord.Embed(title="Permissions for role {}".format(role), color=role.color)
            embed.description = permissions
            try:
                await ctx.send(embed=embed)
            except:
                await ctx.send("```Permissions for role {}\n\n{}```".format(role, permissionsne))
        except:
            await ctx.send("```Couldn't find role, are you sure you typed it correctly?\n\nYou typed: '{}'```".format(role))


    @commands.command(pass_context=True, brief="Counts the number of roles on the server. (excluding @everyone)")
    @commands.guild_only()
    async def rolecount(self, ctx):
        """
        Usage: -rolecount
        """
        await ctx.send('This server has {:,} total roles.'.format(len(ctx.guild.roles) - 1))

    @commands.command(pass_context=True, brief="Shows a list of roles that have zero members.")
    @commands.guild_only()
    async def emptyroles(self, ctx):
        """
        Usage: -emptyroles
        """

        check_roles = ctx.guild.roles # grab in hierarchy order so they're easier to find in the server settings
        rolecounts = self.role_accumulate(check_roles, ctx.guild.members) # same accumulate as the `roles` command

        sorted_list = []
        for role in check_roles:
            if role in rolecounts and rolecounts[role] == 0: # only add if count = 0
                sorted_list.append((role, rolecounts.get(role,0)))

        if not sorted_list: # another failsafe
            return await ctx.send('Seems there are no empty roles...')

        await self.rolelist_paginate(ctx, sorted_list, title='Empty Roles')


    @commands.group(brief="Edit the specifications of a passed role. (Command Group)", aliases=["changerole"])
    @commands.guild_only()
    @permissions.has_permissions(manage_roles=True, manage_guild=True)
    async def editrole(self, ctx: commands.Context):
        """ 
        Usage:      -editrole <method> <role>
        Alias:      -changerole
        Example:    -editrole color @Verified #ff0000
        Permission: Manage Server, Manage Roles
        Output:     Edits the color or name of a role.
        Methods:
            color  (Alias: colour)        
            name
        Notes:
            Use double quotes around the role, name, 
            and color if they contain spaces.
        """
        if ctx.invoked_subcommand is None:
            help_command = self.bot.get_command("help")
            await help_command(ctx, invokercommand="editrole")


    @editrole.command(name="colour", aliases=["color"])
    async def editrole_colour(self, ctx: commands.Context, role: discord.Role, value: discord.Colour = None):
        """
        Edit a role's colour.
        Use double quotes if the role contains spaces.
        """
        usage = "`{}editrole colour Test #ff9900`".format(ctx.prefix)
        if not value:
            await ctx.send(usage)
        author = ctx.author
        reason = "{}({}) changed the colour of role '{}'".format(author.name, author.id, role.name)

        try:
            await role.edit(reason=reason, color=value)
            await ctx.send("<:checkmark:816534984676081705> Successfully edited role.")
        except Exception as e:
            await ctx.send(e)


    @editrole.command(name="name")
    async def edit_role_name(self, ctx: commands.Context, role: discord.Role, name: str = None):
        """
        Edit a role's name.
        Use double quotes if the role or the name contain spaces.
        """
        usage = "`{}editrole name \"Hecatex Bot\" Test`".format(ctx.prefix)
        if not name:
            await ctx.send(usage)
        author = ctx.message.author
        old_name = role.name
        reason = "{}({}) changed the name of role '{}' to '{}'".format(
            author.name, author.id, old_name, name
        )

        try:
            await role.edit(reason=reason, name=name)
            await ctx.send("<:checkmark:816534984676081705> Successfully edited role.")
        except Exception as e:
            await ctx.send(e)


    async def say_permissions(self, ctx, member, channel):
        permissions = channel.permissions_for(member)
        e = discord.Embed(colour=member.colour)
        avatar = member.avatar_url_as(static_format='png')
        e.set_author(name=str(member), url=avatar)
        allowed, denied = [], []
        for name, value in permissions:
            name = name.replace('_', ' ').replace('guild', 'server').title()
            if value:
                allowed.append(name)
            else:
                denied.append(name)

        e.add_field(name='Allowed', value='\n'.join(allowed))
        e.add_field(name='Denied', value='\n'.join(denied))
        await ctx.send(embed=e)


    @commands.command(name="permissions",brief="Shows a member's permissions in a specific channel.")
    @commands.guild_only()
    async def _permissions(self, ctx, member: discord.Member = None, channel: discord.TextChannel = None):
        """
        Usage:  -permissions [member] [channel]
        Output: Shows a member's permissions in a specific channel.
        Notes:
            Will default to yourself and the current channel
            if they are not specified.
        """
        channel = channel or ctx.channel
        if member is None:
            member = ctx.author

        await self.say_permissions(ctx, member, channel)


    @commands.command(brief="Shows the bot's permissions in a specific channel.")
    @commands.guild_only()
    async def botpermissions(self, ctx, *, channel: discord.TextChannel = None):
        """
        Usage:  -botpermissions [channel]
        Output: Shows the bot's permissions in a specific channel.
        Notes:
            Will default to the current channel
            if a channel is not specified.
        """
        channel = channel or ctx.channel
        member = ctx.guild.me
        await self.say_permissions(ctx, member, channel)