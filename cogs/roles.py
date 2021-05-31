import discord
import colorsys

from discord.ext import commands, menus

from utilities import checks
from utilities import helpers
from utilities import humantime
from utilities import pagination
from utilities import converters
from utilities import decorators


def setup(bot):
    bot.add_cog(Roles(bot))


class Roles(commands.Cog):
    """
    Manage all actions regarding roles.
    """

    def __init__(self, bot):
        self.bot = bot
        self.statusmap1 = {
            discord.Status.online: "1",
            discord.Status.dnd: "2",
            discord.Status.idle: "3",
        }  # for sorting
        self.statusmap2 = {
            discord.Status.online: bot.emote_dict["online"],
            discord.Status.dnd: bot.emote_dict["dnd"],
            discord.Status.idle: bot.emote_dict["idle"],
            discord.Status.offline: bot.emote_dict["offline"],
        }

    @decorators.command(
        aliases=["ri"],
        brief="Get information on a role.",
        implemented="2021-03-12 04:03:05.031691",
        updated="2021-05-10 07:11:40.514042",
        examples="""
                {0}ri 828763460346839050
                {0}roleinfo @Helper
                """,
    )
    async def roleinfo(self, ctx, role: converters.DiscordRole):
        """
        Usage: {0}roleinfo <role>
        Alias: {0}ri
        Output:
            Shows details on the role's color,
            creation date, users, and creator.
        """
        roleinfo = {}
        roleinfo["users"] = sum(
            1 for member in role.guild.members if role in member.roles
        )
        roleinfo["created"] = f"Created on {role.created_at.__format__('%m/%d/%Y')}"
        roleinfo["color"] = str(role.color).upper()

        embed = discord.Embed(color=self.bot.constants.embed)
        embed.set_author(name=role.name, icon_url=ctx.guild.icon_url)
        embed.set_footer(text=f"Role ID: {role.id} | {roleinfo['created']}")
        embed.set_thumbnail(url=ctx.guild.icon_url)
        embed.add_field(name="Mention", value=role.mention)
        embed.add_field(name="Users", value=roleinfo["users"])
        embed.add_field(name="Hoisted", value=role.hoist)
        embed.add_field(name="Color", value=roleinfo["color"])
        embed.add_field(name="Position", value=role.position)
        embed.add_field(name="Mentionable", value=role.mentionable)
        await ctx.send_or_reply(embed=embed)

    @decorators.command(
        aliases=["ar", "adrl", "addrl", "adrole"], brief="Adds roles to users."
    )
    @commands.guild_only()
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(manage_roles=True)
    async def addrole(
        self,
        ctx,
        users: commands.Greedy[converters.DiscordMember],
        *roles: converters.DiscordRole,
    ):
        """
        Usage:      {0}addrole [users]... [roles]...
        Aliases:    {0}ar, {0}adrole, {0}adrl, {0}addrl
        Example:    {0}ar Hecate#3523 @Snowbot @Verified Member
        Permission: Manage Roles
        Output:     Adds multiple roles to multiple users
        """
        if not len(users) or not len(roles):
            return await ctx.usage(ctx.command.signature)

        target_list = []
        target_names = []
        for target in users:
            role_list = []
            for role in roles:
                if (
                    role.permissions.administrator
                    and ctx.author.id not in self.bot.owner_ids
                ):
                    return await ctx.send_or_reply(
                        content="I cannot manipulate an admin role",
                    )
                if (
                    role.position >= ctx.author.top_role.position
                    and ctx.author.id not in self.bot.constants.owners
                ):
                    return await ctx.send_or_reply(
                        content="That role is higher than your highest role",
                    )
                try:
                    await target.add_roles(role)
                except discord.Forbidden:
                    return await ctx.send_or_reply(
                        content="I do not have permission to do that",
                    )
                role_list.append(role)
                target_list.append(target)
            if role_list:
                role_names = []
                for role in role_list:
                    name = role.name
                    role_names += [name]
            name = f"{target.name}#{target.discriminator}"
            target_names.append(name)
        await ctx.send_or_reply(
            f'{self.bot.emote_dict["success"]} '
            f'Added user{"" if len(target_names) == 1 else "s"} `{", ".join(target_names)}` '
            f'the role{"" if len(role_list) == 1 else "s"} `{", ".join(role_names)}`'
        )

    @decorators.command(
        aliases=["rr", "remrole", "rmrole", "rmrl"], brief="Removes roles from users."
    )
    @commands.guild_only()
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(manage_roles=True)
    async def removerole(
        self,
        ctx,
        targets: commands.Greedy[converters.DiscordMember],
        *roles: converters.DiscordRole,
    ):
        """
        Usage:      {0}removerole [user] [user] [role] [role]...
        Aliases:    {0}rr, {0}remrole, {0}rmrole, {0}rmrl
        Example:    {0}rr Hecate#3523 @Snowbot @Verified Member
        Permission: Manage Roles
        Output:     Removes multiple roles from multiple users
        """
        if (
            ctx.message.guild.me.permissions_in(ctx.message.channel).manage_roles
            is False
        ):
            return await ctx.send_or_reply(
                content="Sorry, I do not have the manage_roles permission",
            )

        if len(targets) == 0:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}rr <user> [user] [user] <role> [role] [role]...`",
            )
        if len(roles) == 0:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}rr <user> [user] [user] <role> [role] [role]...`",
            )
        target_list = []
        target_names = []
        for target in targets:
            role_list = []
            for role in roles:
                if (
                    role.permissions.administrator
                    and ctx.author.id not in self.bot.constants.owners
                ):
                    return await ctx.send_or_reply(
                        content="I cannot manipulate an admin role",
                    )
                if (
                    role.position > ctx.author.top_role.position
                    and ctx.author.id not in self.bot.constants.owners
                    and ctx.author.id != ctx.guild.owner.id
                ):
                    return await ctx.send_or_reply(
                        content="That role is higher than your highest role",
                    )
                if (
                    role.position == ctx.author.top_role.position
                    and ctx.author.id not in self.bot.constants.owners
                    and ctx.author.id != ctx.guild.owner.id
                ):
                    return await ctx.send_or_reply(
                        content="That role is your highest role",
                    )
                try:
                    await target.remove_roles(role)
                except discord.Forbidden:
                    return await ctx.send_or_reply(
                        content="I do not have permission to do that",
                    )
                role_list.append(role)
                target_list.append(target)
            if role_list:
                role_names = []
                for role in role_list:
                    name = role.name
                    role_names += [name]
            name = f"{target.name}#{target.discriminator}"
            target_names.append(name)
        await ctx.send_or_reply(
            f'{self.bot.emote_dict["success"]} '
            f'Removed user{"" if len(target_names) == 1 else "s"} `{", ".join(target_names)}` '
            f'the role{"" if len(role_list) == 1 else "s"} `{", ".join(role_names)}`'
        )

    # @decorators.group(
    #     brief="Mass adds or removes a role to users.", aliases=["multirole"]
    # )
    # @commands.guild_only()
    # @checks.bot_has_perms(manage_roles=True)
    # @checks.has_perms(manage_roles=True)
    # async def massrole(self, ctx):
    #     """
    #     Usage:      {0}massrole <method> <role1> <role2>
    #     Alias:      {0}multirole
    #     Example:    {0}massrole add @everyone Verified
    #     Permission: Manage Roles
    #     Output:     Adds or removes a role to all users with a given role
    #     Methods:
    #         add
    #         remove (Aliases: rem, rm)

    #     Notes:
    #         Command may take a few minutes to complete its execution.
    #         Please be patient.
    #     """
    #     if ctx.invoked_subcommand is None:
    #         help_command = self.bot.get_command("help")
    #         await help_command(ctx, invokercommand="massrole")

    # @massrole.command(brief="Adds all members with a certain role a new role.")
    # async def add(
    #     self,
    #     ctx,
    #     role1: converters.DiscordRole = None,
    #     role2: converters.DiscordRole = None,
    # ):
    #     if role1 is None:
    #         return await ctx.send_or_reply(
    #             content="Usage: `{ctx.prefix}massrole add <role1> <role2> ",
    #         )
    #     if role2 is None:
    #         return await ctx.send_or_reply(
    #             content="Usage: `{ctx.prefix}massrole add <role1> <role2> ",
    #         )
    #     if (
    #         ctx.author.top_role.position < role1.position
    #         and ctx.author.id not in self.bot.constants.owners
    #     ):
    #         return await ctx.send_or_reply(
    #             "You have insufficient permission to execute this command"
    #         )
    #     if (
    #         role2.permissions.administrator
    #         and ctx.author.id not in self.bot.constants.owners
    #     ):
    #         return await ctx.send_or_reply(
    #             content="I cannot manipulate an admin role",
    #         )
    #     if (
    #         role2.position > ctx.author.top_role.position
    #         and ctx.author.id not in self.bot.constants.owners
    #         and ctx.author.id != ctx.guild.owner.id
    #     ):
    #         return await ctx.send_or_reply(
    #             content="That role is higher than your highest role",
    #         )
    #     if (
    #         role2.position == ctx.author.top_role.position
    #         and ctx.author.id not in self.bot.constants.owners
    #         and ctx.author.id != ctx.guild.owner.id
    #     ):
    #         return await ctx.send_or_reply(
    #             content="That role is your highest role",
    #         )
    #     if (
    #         role1.position > ctx.author.top_role.position
    #         and ctx.author.id not in self.bot.constants.owners
    #         and ctx.author.id != ctx.guild.owner.id
    #     ):
    #         return await ctx.send_or_reply(
    #             content="That role is higher than your highest role",
    #         )
    #     if (
    #         role1.position == ctx.author.top_role.position
    #         and ctx.author.id not in self.bot.constants.owners
    #         and ctx.author.id != ctx.guild.owner.id
    #     ):
    #         return await ctx.send_or_reply(
    #             content="That role is your highest role",
    #         )
    #     number_of_members = []
    #     for member in ctx.guild.members:
    #         if role1 in member.roles and not role2 in member.roles:
    #             number_of_members.append(member)

    #     members_to_add_roles = len(number_of_members)
    #     if members_to_add_roles < 1:
    #         return await ctx.send_or_reply(
    #             content=f"{self.bot.emote_dict['warn']} No members to add roles to",
    #         )
    #     msg = await ctx.send_or_reply(
    #         f"{self.bot.emote_dict['warn']} Adding role `{role2.name}` to `{members_to_add_roles}` member{'' if members_to_add_roles == 1 else 's'}. This process may take several minutes."
    #     )
    #     for member in role1.members:
    #         try:
    #             await member.add_roles(role2)
    #         except discord.Forbidden:
    #             return await ctx.send_or_reply(
    #                 content="I do not have permission to do that",
    #             )
    #     # we made it
    #     await msg.edit(
    #         content=f"{self.bot.emote_dict['success']} Added role `{role2.name}` to `{members_to_add_roles}` member{'' if members_to_add_roles == 1 else 's'}"
    #     )

    # @massrole.command(
    #     brief="Removes all members with a certain role a new role",
    #     aliases=["rm", "rem"],
    # )
    # async def remove(
    #     self, ctx, role1: converters.DiscordRole, role2: converters.DiscordRole
    # ):
    #     if role1 is None:
    #         return await ctx.send_or_reply(
    #             content="Usage: `{ctx.prefix}massrole add <role1> <role2> ",
    #         )
    #     if role2 is None:
    #         return await ctx.send_or_reply(
    #             content="Usage: `{ctx.prefix}massrole add <role1> <role2> ",
    #         )
    #     if (
    #         ctx.author.top_role.position < role1.position
    #         and ctx.author.id not in self.bot.constants.owners
    #     ):
    #         return await ctx.send_or_reply(
    #             "You have insufficient permission to execute this command"
    #         )
    #     if (
    #         role2.permissions.administrator
    #         and ctx.author.id not in self.bot.constants.owners
    #     ):
    #         return await ctx.send_or_reply(
    #             content="I cannot manipulate an admin role",
    #         )
    #     if (
    #         role2.position > ctx.author.top_role.position
    #         and ctx.author.id not in self.bot.constants.owners
    #         and ctx.author.id != ctx.guild.owner.id
    #     ):
    #         return await ctx.send_or_reply(
    #             content="That role is higher than your highest role",
    #         )
    #     if (
    #         role2.position == ctx.author.top_role.position
    #         and ctx.author.id not in self.bot.constants.owners
    #         and ctx.author.id != ctx.guild.owner.id
    #     ):
    #         return await ctx.send_or_reply(
    #             content="That role is your highest role",
    #         )
    #     if (
    #         role1.position > ctx.author.top_role.position
    #         and ctx.author.id not in self.bot.constants.owners
    #         and ctx.author.id != ctx.guild.owner.id
    #     ):
    #         return await ctx.send_or_reply(
    #             content="That role is higher than your highest role",
    #         )
    #     if (
    #         role1.position == ctx.author.top_role.position
    #         and ctx.author.id not in self.bot.constants.owners
    #         and ctx.author.id != ctx.guild.owner.id
    #     ):
    #         return await ctx.send_or_reply(
    #             content="That role is your highest role",
    #         )
    #     number_of_members = []
    #     for member in ctx.guild.members:
    #         if role1 in member.roles and role2 in member.roles:
    #             number_of_members.append(member)

    #     members_to_add_roles = len(number_of_members)
    #     if members_to_add_roles < 1:
    #         return await ctx.send_or_reply(
    #             content=f"{self.bot.emote_dict['warn']} No members to remove roles from",
    #         )
    #     msg = await ctx.send_or_reply(
    #         f"{self.bot.emote_dict['warn']} Removing role `{role2.name}` from `{members_to_add_roles}` member{'' if members_to_add_roles == 1 else 's'}. This process may take several minutes."
    #     )
    #     for member in role1.members:
    #         try:
    #             await member.remove_roles(role2)
    #         except discord.Forbidden:
    #             return await ctx.send_or_reply(
    #                 content="I do not have permission to do that",
    #             )
    #     # we made it
    #     await msg.edit(
    #         content=f"{self.bot.emote_dict['success']} Removed role `{role2.name}` from `{members_to_add_roles}` member{'' if members_to_add_roles == 1 else 's'}"
    #     )

    def role_accumulate(self, check_roles, members):
        ## iterate over the members to accumulate a count of each role
        rolecounts = {}
        for role in check_roles:  # populate the accumulator dict
            if not role.is_default():
                rolecounts[role] = 0

        for member in members:
            for role in member.roles:
                if (
                    role in check_roles and not role.is_default()
                ):  # want to exclude @everyone from this list
                    rolecounts[role] += 1

        return rolecounts

    async def rolelist_paginate(self, ctx, rlist, title="Server Roles"):
        # takes a list of roles and counts and sends it out as multiple embed as nessecary
        pages = []
        buildstr = ""
        for role, count in rlist:  # this generates and paginates the info
            line = "{:,} {}\n".format(count, role.mention)
            if len(buildstr) + len(line) > pagination.DESC_LIMIT:
                pages.append(buildstr)  # split the page here
                buildstr = line
            else:
                buildstr += line
        if buildstr:
            pages.append(
                buildstr
            )  # if the string has data not already listed in the pages, add it

        for index, page in enumerate(pages):  # enumerate so we can add a page number
            embed = discord.Embed(
                title=f"{title}", description=page, color=self.bot.constants.embed
            )
            embed.set_footer(text="Page {:,}/{:,}".format(index + 1, len(pages)))
            await ctx.send_or_reply(embed=embed)

    # The next couple commands are mostly from CorpBot.py with a few modifications
    # https://github.com/corpnewt/CorpBot.py

    @decorators.command(brief="Show an embed of all server roles.", aliases=["roles"])
    @commands.guild_only()
    async def listroles(self, ctx, sort_order: str = "default"):
        """
        Usage: -listroles
        Alias: -roles
        Permission: Manage Messages
        Output:
            Shows roles and their member counts. Takes one argument,
            sort_order, which can be default, name, count, or color.
        """

        sort_order = sort_order.lower()
        if not sort_order in [
            "default",
            "name",
            "count",
            "color",
        ]:  # make sure it has valid args
            return await ctx.send_or_reply(
                "Invalid arguments.\n ```yaml\nVALID OPTIONS:\n=============\n\n default\nname\ncount\ncolor\n```"
            )

        check_roles = (
            ctx.guild.roles
        )  # we use roles for these because sometimes we want to see the order

        ## now we iterate over the members to accumulate a count of each role
        rolecounts = self.role_accumulate(check_roles, ctx.guild.members)

        sorted_list = []
        if sort_order == "default":  # default sort = the server role hierarchy
            for role in check_roles:
                if role in rolecounts:
                    sorted_list.append((role, rolecounts.get(role, 0)))
        elif sort_order == "name":  # name sort = alphabetical by role name
            sorted_list = sorted(
                rolecounts.items(), key=lambda tup: tup[0].name.lower()
            )
        elif sort_order == "count":  # count sort = decreasing member count
            sorted_list = sorted(
                rolecounts.items(), key=lambda tup: tup[1], reverse=True
            )
        elif (
            sort_order == "color"
        ):  # color sort: by increasing hue value in HSV color space
            sorted_list = sorted(
                rolecounts.items(),
                key=lambda tup: colorsys.rgb_to_hsv(
                    tup[0].color.r, tup[0].color.g, tup[0].color.b
                )[0],
            )

        if not sorted_list:  # another failsafe
            return

        sorted_list = sorted_list[::-1]
        await self.rolelist_paginate(
            ctx, sorted_list
        )  # send the list to get actually printed to discord

    @decorators.command(brief="Counts the users with a role.")
    @commands.guild_only()
    async def rolecall(self, ctx, *, role: converters.DiscordRole = None):
        """
        Usage: -rolecall <role>
        Output:
            Shows the number of people with the passed role.
        """
        if role is None:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}rolecall <role>`",
            )

        count = 0
        online = 0
        for member in ctx.guild.members:
            if role in member.roles:
                count += 1
                if member.status != discord.Status.offline:
                    online += 1

        embed = discord.Embed(
            title=role.name,
            description="{}/{} online".format(online, count),
            color=self.bot.constants.embed,
        )
        embed.set_footer(text="ID: {}".format(role.id))
        await ctx.send_or_reply(embed=embed)

    @decorators.command(brief="Show the people who have a role.")
    @commands.guild_only()
    async def whohas(self, ctx, *, role: converters.DiscordRole = None):
        """
        Usage: -whohas <role>
        Permission: Manage Messages
        Output:
            Lists the people who have the specified role with their status.
        Notes:
        """
        if role is None:
            return await ctx.send_or_reply(
                content=f"Usage `{ctx.prefix}whohas <role>`",
            )

        users = [member for member in ctx.guild.members if role in member.roles]

        sorted_list = sorted(
            users,
            key=lambda usr: (self.statusmap1.get(usr.status, "4"))
            + (usr.nick.lower() if usr.nick else usr.name.lower()),
        )

        page = [
            "{} {}".format(
                self.statusmap2.get(member.status, self.bot.emote_dict["offline"]),
                member.mention,
            )
            for member in sorted_list
        ]

        p = pagination.SimplePages(entries=page, per_page=20, index=False)
        p.embed.title = "{:,} members with {}".format(len(users), role.name)

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @decorators.command(aliases=["rp"], brief="Show the permissions for a role.")
    @commands.guild_only()
    async def roleperms(self, ctx, *, role: converters.DiscordRole = None):
        """
        Usage:  -roleperms <role>
        Alias:  -rp
        Output:
            Embed with all the permissions
            granted to the passed role
        """
        if role is None:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}roleperms <role>`",
            )

        permissions = ""
        permissionsne = ""
        try:
            for perm in role.permissions:
                perm = (perm[0].replace("_", " ").title(), perm[1])
                permissions += "**{}**: {}\n".format(*perm)
                permissionsne += "{}: {}\n".format(*perm)
            embed = discord.Embed(
                title="Permissions for role {}".format(role), color=role.color
            )
            embed.description = permissions
            try:
                await ctx.send_or_reply(embed=embed)
            except Exception:
                await ctx.send_or_reply(
                    "```Permissions for role {}\n\n{}```".format(role, permissionsne)
                )
        except Exception:
            await ctx.send_or_reply(
                "```Couldn't find role, are you sure you typed it correctly?\n\nYou typed: '{}'```".format(
                    role
                )
            )

    @decorators.command(brief="Counts the roles on the server.")
    @commands.guild_only()
    async def rolecount(self, ctx):
        """
        Usage: -rolecount
        Output: Counts all server roles
        """
        await ctx.send_or_reply(
            "This server has {:,} total roles.".format(len(ctx.guild.roles) - 1)
        )

    @decorators.command(brief="Show roles that have no users.")
    @commands.guild_only()
    async def emptyroles(self, ctx):
        """
        Usage: {0}emptyroles
        Output: Shows all roles with zero users
        """

        check_roles = (
            ctx.guild.roles
        )  # grab in hierarchy order so they're easier to find in the server settings
        rolecounts = self.role_accumulate(
            check_roles, ctx.guild.members
        )  # same accumulate as the `roles` command

        sorted_list = []
        for role in check_roles:
            if role in rolecounts and rolecounts[role] == 0:  # only add if count = 0
                sorted_list.append((role, rolecounts.get(role, 0)))

        if not sorted_list:  # another failsafe
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['warn']} No empty roles found.",
            )

        await self.rolelist_paginate(ctx, sorted_list, title="Empty Roles")


    async def do_massrole(self, ctx, add_or_remove, targets, role, obj_type):
        if add_or_remove.lower() == "add":
            add = True
        else:
            add = False
        res = await checks.role_priv(ctx, role)
        if res:
            return await ctx.fail(res)

        success = []
        failed = []
        
        warning = "This process may take several minutes. Please be patient."
        msg = await ctx.load(f"{'Add' if add else 'Remov'}ing role `{role.name}` {'to' if add else 'from'} {len(targets)} {obj_type}{'' if len(targets) ==1 else 's'}. {warning}")

        for target in targets:
            try:
                reason=f"Role {'add' if add else 'remov'}ed by command."
                if add:
                    await target.add_roles(role, reason=reason)
                else:
                    await target.remove_roles(role, reason=reason)
                success.append(str(target))
            except Exception as e:
                failed.append((str(target), e))

        if success:
            await msg.edit(content=f"{self.bot.emote_dict['success']} {'Add' if add else 'Remov'}ed role `{role.name}` {'to' if add else 'from'} {len(success)} {obj_type}{'' if len(success) == 1 else 's'}.")
            self.bot.dispatch("mod_action", ctx, targets=success)
        if failed:
            if not success:
                await msg.delete()
            await helpers.error_info(ctx, failed)

    @decorators.group(
        aliases=["massrole", "multirole"],
        brief="Manage mass adding/removing roles.",
        implemented="2021-05-16 15:06:06.479013",
        updated="2021-05-31 05:13:52.253369",
        invoke_without_command=True,
        case_insensitive=True,
        examples="""
                {0}role add all @Helper
                {0}massrole remove @Helper Mod
                {0}multirole add bots @Bots
                """
    )
    async def role(self, ctx):
        """
        Usage: {0}role <add/remove> <option> <arguments>
        Aliases: {0}massrole, {0}multirole
        Permission: Manage Roles
        Output:
            Mass adds or removes a role to and from
            all users matching your specifications
        Add options:
            all/everyone:  Add everyone a role
            humans/people:  Add humans a role
            bots/robots:  Add bots a role
            in:  Add people with a role a new role
        Remove options:
            all/everyone:  Remove everyone a role
            humans/people:  Remove humans a role
            bots/robots:  Remove bots a role
            in:  Remove people with a role a new role
        Examples:
            {0}role add all @Helper
            {0}massrole remove @Helper Mod
            {0}multirole add bots @Bots
        """
        if ctx.invoked_subcommand is None:
            await ctx.usage()
    
    @role.group(
        aliases=['apply'],
        brief="Add roles users with a role.",
        implemented="2021-05-16 15:06:06.479013",
        updated="2021-05-31 05:13:52.253369",
    )
    async def add(self, ctx):
        """
        Usage: {0}role <add/remove> <option> <arguments>
        Aliases: {0}massrole, {0}multirole
        Permission: Manage Roles
        Output:
            Mass adds a role to all users
            matching your specifications.
        Options:
            all/everyone:  Add everyone a role
            humans/people:  Add humans a role
            bots/robots:  Add bots a role
            in:  Add people with a role a new role
        Examples:
            {0}role add all @Helper
            {0}massrole add in @Helper Mod
            {0}multirole add bots @Bots
        """
        if ctx.invoked_subcommand is None:
            await ctx.usage()

    @add.command(
        name="in",
        brief="Add roles to users with a role",
        implemented="2021-05-16 15:06:06.479013",
        updated="2021-05-31 05:13:52.253369",
    )
    async def _in(self, ctx, role1: converters.DiscordRole, *, role2: converters.DiscordRole):
        """
        Usage: {0}role add in <role1> <role2>
        Permission: Manage Roles
        Output:
            Adds role2 to all users who
            currently have role1.
        Notes:
            If the role is multiple words,
            it must be surrounded in quotes.
            e.g. "Bot Role" or 'Bot Role'
        """
        res = await checks.role_priv(ctx, role1)
        if res:
            return await ctx.fail(res)

        res = await checks.role_priv(ctx, role2)
        if res:
            return await ctx.fail(res)
        
        role1_members = [member for member in ctx.guild.members if role1 in member.roles]
        targets = [member for member in role1_members if role2 not in member.roles]

        await self.do_massrole(ctx, "add", targets, role2, "user")

    @add.command(
        aliases=['people'],
        brief="Add roles to all human users.",
        implemented="2021-05-16 15:06:06.479013",
        updated="2021-05-31 05:13:52.253369",
    )
    async def humans(self, ctx, *, role: converters.DiscordRole):
        """
        Usage: {0}role add humans <role>
        Alias: {0}role add people <role>
        Permission: Manage Roles
        Output:
            Adds a role to all humans
            in the server. Excludes bots.
        """
        humans = [member for member in ctx.guild.members if not member.bot]
        targets = [human for human in humans if role not in human.roles]

        await self.do_massrole(ctx, "add", targets, role, "human")

    @add.command(
        aliases=['robots'],
        brief="Add roles to all bot users.",
        implemented="2021-05-16 15:06:06.479013",
        updated="2021-05-31 05:13:52.253369",
    )
    async def bots(self, ctx, *, role: converters.DiscordRole):
        """
        Usage: {0}role add humans <role>
        Alias: {0}role add people <role>
        Permission: Manage Roles
        Output:
            Adds a role to all humans
            in the server. Excludes bots.
        """
        bots = [member for member in ctx.guild.members if member.bot]
        targets = [bot for bot in bots if role not in bot.roles]

        await self.do_massrole(ctx, "add", targets, role, "bot")

    @add.command(
        name="all",
        aliases=['everyone', 'users', 'members'],
        brief="Add roles to all bot users.",
        implemented="2021-05-16 15:06:06.479013",
        updated="2021-05-31 05:13:52.253369",
    )
    async def _all(self, ctx, *, role: converters.DiscordRole):
        """
        Usage: {0}role add all <role>
        Alias: {0}role add everyone <role>
        Permission: Manage Roles
        Output:
            Adds a role to all users
            in the server. Includes bots.
        """
        targets = [member for member in ctx.guild.members if role not in member.roles]
        await self.do_massrole(ctx, "add", targets, role, "user")

    @role.group(
        aliases=['rm', 'rem'],
        brief="Add roles users with a role.",
        implemented="2021-05-16 15:06:06.479013",
        updated="2021-05-31 05:13:52.253369",
        invoke_without_command=True,
        case_insensitive=True
    )
    async def remove(self, ctx):
        """
        Usage: {0}role <add/remove> <option> <arguments>
        Aliases: {0}massrole, {0}multirole
        Permission: Manage Roles
        Output:
            Mass adds a role to all users
            matching your specifications.
        Options:
            all/everyone:  Add everyone a role
            humans/people:  Add humans a role
            bots/robots:  Add bots a role
            in:  Add people with a role a new role
        Examples:
            {0}role add all @Helper
            {0}massrole add in @Helper Mod
            {0}multirole add bots @Bots
        """
        if ctx.invoked_subcommand is None:
            await ctx.usage()

    async def _in(self, ctx, role1: converters.DiscordRole, *, role2: converters.DiscordRole):
        """
        Usage: {0}role remove in <role1> <role2>
        Permission: Manage Roles
        Output:
            Removes role2 from all users who
            currently have role1.
        Notes:
            If role1 is multiple words,
            it must be surrounded in quotes.
            e.g. "Bot Role" or 'Bot Role'
        """
        res = await checks.role_priv(ctx, role1)
        if res:
            return await ctx.fail(res)

        res = await checks.role_priv(ctx, role2)
        if res:
            return await ctx.fail(res)
        
        role1_members = [member for member in ctx.guild.members if role1 in member.roles]
        targets = [member for member in role1_members if role2 in member.roles]

        await self.do_massrole(ctx, "remove", targets, role2, "user")

    @remove.command(
        name="all",
        aliases=['everyone'],
        brief="Remove a role from everyone",
        implemented="2021-05-16 15:06:06.479013",
        updated="2021-05-31 05:13:52.253369",
    )
    async def _all(self, ctx, *, role: converters.DiscordRole):
        """
        Usage: {0}role remove all <role>
        Alias: {0}role remove everyone <role>
        Permission: Manage Roles
        Output:
            Removes a role from users
            in the server. Includes bots.
        """
        targets = [member for member in ctx.guild.members if role in member.roles]
        await self.do_massrole(ctx, "remove", targets, role, "user")

    @remove.command(
        aliases=['robots'],
        brief="Remove roles from all bot users.",
        implemented="2021-05-16 15:06:06.479013",
        updated="2021-05-31 05:13:52.253369",
    )
    async def bots(self, ctx, *, role: converters.DiscordRole):
        """
        Usage: {0}role remove bots <role>
        Alias: {0}role remove robots <role>
        Permission: Manage Roles
        Output:
            Removes a role from all bots
            in the server. Excludes humans.
        """
        bots = [member for member in ctx.guild.members if member.bot]
        targets = [bot for bot in bots if role in bot.roles]
        await self.do_massrole(ctx, "remove", targets, role, "bot")

    @remove.command(
        aliases=['people'],
        brief="Remove roles from all bot users.",
        implemented="2021-05-16 15:06:06.479013",
        updated="2021-05-31 05:13:52.253369",
    )
    async def humans(self, ctx, *, role: converters.DiscordRole):
        """
        Usage: {0}role remove humans <role>
        Alias: {0}role remove people <role>
        Permission: Manage Roles
        Output:
            Removes a role from all humans
            in the server. Excludes bots.
        """    
        humans = [member for member in ctx.guild.members if not member.bot]
        targets = [human for human in humans if role in human.roles]
        await self.do_massrole(ctx, "remove", targets, role, "human")

    @decorators.command(
        aliases=["trole"],
        brief="Temporarily add roles to users.",
        implemented="2021-05-31 04:09:38.799221",
        updated="2021-05-31 04:09:38.799221",
        examples="""
                {0}temprole @Hecate 2 days for advertising
                {0}trole 708584008065351681 Hecate 2 hours for spamming
                """,
    )
    @commands.guild_only()
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(manage_roles=True)
    async def temprole(
        self,
        ctx,
        user: converters.DiscordMember,
        role: converters.DiscordRole,
        *,
        duration: humantime.UserFriendlyTime(
            commands.clean_content, default="\u2026"
        ) = None,
    ):
        """
        Usage: {0}temprole <user> <duration>
        Alias: {0}trole
        Output:
            Adds a role to a user for the specified duration.
            The duration can be a a short time form, e.g. 30d or a more human
            duration like "until thursday at 3PM".
        """
        task = self.bot.get_cog("Tasks")
        if not task:
            raise commands.BadArgument("This feature is unavailable.")

        if not duration:
            raise commands.BadArgument("You must specify a duration.")

        endtime = duration.dt

        res = await checks.role_priv(ctx, role)
        if res:  # We failed the role hierarchy test
            return await ctx.fail(res)

        if role in user.roles:
            return await ctx.fail(f"User `{user}` already has role `{role.name}`")

        try:
            await user.add_roles(role)
        except Exception as e:
            await helpers.error_info(ctx, [(str(user), e)])
            return
        timer = await task.create_timer(
            endtime,
            "temprole",
            ctx.guild.id,
            user.id,
            role.id,
            connection=self.bot.cxn,
            created=ctx.message.created_at,
        )

        self.bot.dispatch("mod_action", ctx, targets=[str(user)])
        try:
            time_fmt = humantime.human_timedelta(duration.dt, source=timer.created_at)
        except Exception:
            time_fmt = "unknown duration"
        await ctx.success(f"Temproled `{user}` the role `{role.name}` for {time_fmt}.")

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_temprole_timer_complete(self, timer):
        guild_id, member_id, role_id = timer.args

        guild = self.bot.get_guild(guild_id)
        if not guild:  # We were kicked or it was deleted.
            return
        member = guild.get_member(member_id)
        if not member:  # They left the server
            return
        role = guild.get_role(role_id)
        if not role:  # Role deleted.
            return

        reason = f"Temprole removal from timer made on {timer.created_at}."
        try:
            await member.remove_roles(role, reason)
        except Exception:  # We tried
            pass
